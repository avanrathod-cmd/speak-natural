# Guest / Ephemeral Sales Call Analysis — Design Plan

## Overview

A guest (unauthenticated) user should be able to upload one call and receive
a full analysis without any data persisted in the database. S3 is used
transiently during transcription (same as the authenticated flow) and the
audio object is deleted from S3 immediately after AWS Transcribe finishes.
No DB rows are written at any point.

The pipeline and response shape are identical to the authenticated flow.

---

## Decision: Transcription approach

**Use AWS Transcribe + S3 (ephemeral S3 only)**

The user requirement is consistency with the existing authenticated pipeline.
AWS Transcribe requires an S3 URI — there is no way to pass audio bytes
directly. The resolution is to use S3 as a temporary scratch space:

1. Upload audio to S3 under a `guest/` prefix
2. Run AWS Transcribe (same job config as authenticated flow)
3. Retrieve the transcript JSON
4. **Delete the S3 object immediately**
5. Run speaker identification + turn extraction + LLM analysis
6. Return the result — nothing written to DB

This reuses `AudioProcessorService`, `SalesCallAnalyzerService`, and all
existing parsing logic unchanged. Diarization quality is identical to the
authenticated flow.

Previously considered alternatives and why they were ruled out:

| Option | Ruled out because |
|--------|-------------------|
| Gemini multimodal | Weaker diarization, diverges from authenticated pipeline |
| Local Whisper | Heavy deps, no diarization, slow on CPU |
| OpenAI Whisper API | No diarization, 25 MB limit, new vendor |
| Google STT | Different JSON schema, new dependency, 60 s sync limit |

---

## 1. Endpoint Design Alternatives

AWS Transcribe is asynchronous and takes 30–90 seconds. This rules out a
simple synchronous POST — total wall time (upload + transcribe + analyze)
would be 90–180 seconds, well beyond any reasonable HTTP timeout.

### Option 1 — Synchronous POST (blocks until complete)

**Pros**
- Simplest client code: one `fetch()`, no polling
- Zero server-side state

**Cons**
- AWS Transcribe alone takes 30–90 s; total time 90–180 s
- Exceeds Railway's 60 s default request timeout — **not viable**

**Fit:** Ruled out given AWS Transcribe latency.

---

### Option 2 — Async with In-Memory Job Store ✓ Recommended

`POST /sales/guest/analyze` accepts the file, generates a UUID `job_id`,
enqueues processing as a FastAPI `BackgroundTask`, and returns
`{job_id, status: "pending"}` immediately.

A module-level `dict[str, dict]` in `guest_service.py` stores job state.
The client polls `GET /sales/guest/{job_id}/status` every 3 seconds —
exactly the same pattern the frontend already uses for authenticated calls.
When status is `"completed"`, the client fetches
`GET /sales/guest/{job_id}/result`, then calls
`DELETE /sales/guest/{job_id}` to explicitly clean up. The DELETE endpoint
is the single point of responsibility for all cleanup — S3 object deletion
and job store removal — making it reusable for authenticated sessions in
future.

**Pros**
- No timeout risk — upload response is instant
- Mirrors the existing authenticated polling pattern; frontend reuses the
  same polling logic
- Progress stages can be reported (pending → transcribing → analyzing →
  completed)
- Minimal new code: the dict replaces the DB as the state store
- Client-controlled cleanup via DELETE — REST-idiomatic, no ambiguity

**Cons**
- Dict is not shared across multiple uvicorn workers (safe for single-worker
  Railway deployments)
- Job state lost on server restart (acceptable for a guest/demo flow)
- Orphaned entries (e.g. user closes tab before DELETE fires) live in memory
  until server restart — acceptable at current scale; a TTL sweep can be
  added when the product matures

**Fit:** Best overall — mirrors existing pattern, no timeout risk.

---

### Option 3 — Server-Sent Events / Streaming

Returns an SSE stream with progress events and a final
`{stage: "complete", data: {...}}` event.

**Pros**
- Best UX: real-time progress, single connection

**Cons**
- Browser `EventSource` API only supports GET; POST-based SSE requires
  `fetch()` + `ReadableStream` in React, which is significantly more complex
- Higher implementation complexity on both sides

**Fit:** Best long-term UX; too complex for current MVP.

---

## 2. Recommendation

**Transcription:** AWS Transcribe + ephemeral S3 (upload → transcribe →
delete)

**Endpoint:** Option 2 — async with in-memory job store, polling every 3 s

This produces an experience identical to the authenticated flow from the
frontend's perspective, reuses all existing service code, and avoids any
DB writes.

---

## 3. Implementation Scope

| File | Change |
|------|--------|
| `python/api/guest_service.py` | **New.** Four routes: `POST /sales/guest/analyze` (upload, enqueue background task, return `job_id`), `GET /sales/guest/{job_id}/status`, `GET /sales/guest/{job_id}/result`, `DELETE /sales/guest/{job_id}` (deletes S3 object + removes job store entry — single cleanup point, reusable for authenticated sessions). Job store entry holds `s3_key` so DELETE knows what to remove. Module-level job store dict, no TTL. No auth dependency on any route. |
| `python/api/main.py` | Import `guest_router` from `api.guest_service` and register with `app.include_router(guest_router, prefix="/sales")`. |
| `python/.env.example` | Add `GUEST_MAX_UPLOAD_MB=50` (same ceiling as authenticated flow). |

### No changes needed to:
- `services/sales_call_processor.py` — reused as-is; the guest background
  task calls `process_call()` with a generated `call_id` and skips the
  DB-write steps by calling the underlying services directly
- `services/sales_call_analyzer.py` — `analyze_call()` unchanged
- `services/audio_processor.py` — `upload_audio_to_s3()` and
  `transcribe_audio()` reused; guest task additionally calls
  `s3_client.delete_object()` after transcription completes
- `utils/llm_client.py` — no changes
- `api/database.py` — no changes; guest flow never calls it
- `api/auth.py` — no changes; guest endpoints simply omit the dependency

---

## 4. S3 Cleanup Detail

The guest background task follows this sequence:

1. Save uploaded audio to `/tmp/speak-right-guest/{job_id}/`
2. Convert to WAV via `ensure_wav_format()`
3. Upload to S3 under key `guest/{job_id}/audio/{filename}`
4. Start AWS Transcribe job
5. Poll until complete
6. **Delete S3 object** — `s3_client.delete_object(Bucket=BUCKET, Key=s3_key)`
7. Run `identify_speakers()` → `extract_speaker_turns()` → `analyze_call()`
8. Store result in the in-memory job store dict
9. Clean up local `/tmp` files

If the task fails at any point after step 3, the S3 delete is attempted in
a `finally` block to ensure no objects are left behind.

---

## 5. Risks

**Single-worker constraint.** The in-memory job store only works correctly
when all requests hit the same process. Verify Railway deployment uses
`uvicorn api.main:app` without `--workers N > 1`. If multi-worker is ever
needed, replace the dict with Redis (one-line change with `redis-py`).

**Job state lost on restart.** A guest whose call is processing when the
server restarts will get a stale `job_id` that returns 404. The frontend
should handle this gracefully (show an error, offer to retry).

**Orphaned entries.** If a user closes the tab before `DELETE` fires, the
entry stays in memory until server restart. Acceptable at current scale.
A TTL sweep can be added when the product matures.

**Local tmp cleanup.** `/tmp/speak-right-guest/` files must be removed after
processing regardless of success or failure.
