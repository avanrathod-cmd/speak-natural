# Auto Call Recording via Attendee.dev — Implementation Plan

## Context

Sales reps currently must manually record, download, and upload audio files to
get a call analyzed. This creates friction and means many calls are never
analyzed. The feature request is to automatically record sales calls — like
Fireflies.ai — by having a bot join scheduled Google Meet calls and pipe the
recording through the existing analysis pipeline.

---

## Problem Summary

```
Current flow:  Rep records call → downloads audio → manually uploads → analyzed
Target flow:   User links calendar once → every new Google Meet gets a bot
               auto-joined → recording saved to our S3 → fully analyzed
               → appears in dashboard. Zero manual steps after linking.
```

**Key decisions:**
1. Use **webhooks** (not polling) for both bot scheduling and recording ingestion
2. `POST /attendee/sync` is eliminated — bots are auto-scheduled via
   `calendar.events_update` webhook when a new meeting is created
3. The full analysis pipeline runs automatically end-to-end — no "Analyze"
   button needed

---

## Full Flow

```
User links Google Calendar once (POST /attendee/link)
      ↓ registers calendar.events_update webhook on Attendee
New Google Meet added to calendar
      ↓ Attendee fires calendar.events_update webhook
POST /attendee/webhook
      ↓ trigger == "calendar.events_update"?
      ↓ schedule bot for the new event automatically
        (bot created with bot.state_change webhook)
Meeting happens → Attendee bot auto-joins and records
      ↓ meeting ends → post_processing_completed
POST /attendee/webhook
      ↓ trigger == "bot.state_change", event_type == "post_processing_completed"
      ↓ background: fetch recording_url from Attendee API
          ↓ download MP4 → convert to WAV → upload to our S3
          ↓ DB: create call record (status="pending")
          ↓ SalesCallProcessorService.process_call()
          ↓ AWS Transcribe → LLM analysis → DB (status="completed")
          ← Attendee can expire its copy; we own the file + analysis
[Dashboard: call appears fully analyzed — no user action needed]
```

---

## Webhook Details

### Two webhook triggers on the same endpoint

`POST /attendee/webhook` handles two triggers:

| `trigger` | When | Action |
|---|---|---|
| `calendar.events_update` | New/updated calendar event | Schedule bot if it's a Google Meet without one |
| `bot.state_change` (event_type: `post_processing_completed`) | Recording ready | Download → S3 → analyze |

### Registering the `calendar.events_update` webhook

When the user calls `POST /attendee/link`, we register a project-level webhook
on Attendee for `calendar.events_update` in addition to saving the calendar ID:

```python
requests.post(
    "https://app.attendee.dev/api/v1/webhooks",
    headers=ATTENDEE_HEADERS,
    json={
        "url": f"{BASE_URL}/attendee/webhook",
        "triggers": ["calendar.events_update"],
    }
)
```

This is a one-time registration per project (not per bot). New meetings trigger
it automatically from that point on.

### Bot Creation — configure bot.state_change webhook at scheduling time

```python
bot_payload = {
    "calendar_event_id": event["id"],
    "bot_name": "SpeakNatural Bot",
    "recording_settings": {"format": "mp4"},
    "webhooks": [{"url": f"{BASE_URL}/attendee/webhook",
                  "triggers": ["bot.state_change"]}]
}
```

### Webhook Payloads

**calendar.events_update:**
```json
{
  "idempotency_key": "uuid-per-delivery",
  "calendar_id": "cal_xxx",
  "trigger": "calendar.events_update",
  "data": {
    "state": "connected",
    "last_successful_sync_at": "2026-04-08T10:00:00Z",
    "last_attempted_sync_at": "2026-04-08T10:00:00Z",
    "connection_failure_data": null
  }
}
```

**Important:** The payload contains NO event data — it is only a sync
notification. To get the actual events, call:
```
GET /api/v1/calendar_events?calendar_id=cal_xxx
```
Filter results for `meeting_platform == "google_meet"` and
`bot_id == null` to find events that need a bot scheduled.

**bot.state_change (recording ready):**
```json
{
  "idempotency_key": "uuid-per-delivery",
  "bot_id": "bot_xxx",
  "trigger": "bot.state_change",
  "data": {
    "new_state": "ended",
    "old_state": "post_processing",
    "event_type": "post_processing_completed",
    "created_at": "2026-04-07T10:00:00Z"
  }
}
```

The recording is ready **only** when `event_type == "post_processing_completed"`.
All other `bot.state_change` events are ignored with a 200 response.

### Signature Verification

Attendee sends `X-Webhook-Signature` header signed with HMAC-SHA256:
1. Sort JSON payload keys alphabetically
2. Compute HMAC-SHA256 using base64-decoded `ATTENDEE_WEBHOOK_SECRET`
3. Compare result to header value — reject with 403 if mismatch

### Idempotency (3 layers)

| Layer | Mechanism |
|---|---|
| `idempotency_key` | UUID per delivery — stored in `webhook_idempotency_keys` table |
| `attendee_bot_id UNIQUE` | DB constraint — duplicate INSERT fails gracefully |
| Early-exit on irrelevant events | Non-actionable triggers return 200 immediately |

### Fetching the Recording URL

The `recording_url` is **not** in the webhook payload. After receiving
`post_processing_completed`, fetch it from the Attendee API:

```python
resp = requests.get(
    f"https://app.attendee.dev/api/v1/bots/{bot_id}",
    headers={"Authorization": f"Token {ATTENDEE_API_KEY}"}
)
recording_url = resp.json()["recording_url"]
```

---

## Tasks

### Task 1 — DB Migration (`migrations/003_attendee_integration.sql`)

```sql
ALTER TABLE user_profiles
  ADD COLUMN attendee_calendar_id TEXT;

ALTER TABLE sales_calls
  ADD COLUMN source          TEXT NOT NULL DEFAULT 'manual',
  ADD COLUMN attendee_bot_id TEXT UNIQUE;

CREATE TABLE webhook_idempotency_keys (
  key        TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

No new status values needed — calls go straight to
`"pending"` → `"processing"` → `"completed"` (existing statuses).

---

### Task 2 — Fix `python/utils/attendee_utils.py`

- `link_google_calendar(refresh_token, client_id, client_secret, user_email)`
  - Fix: replace hardcoded `deduplication_key` with `user_email`
- `schedule_bot_for_event(event_id, webhook_url) → dict`
  - Extracted helper used by both the sync endpoint and the
    `calendar.events_update` webhook handler
- `get_bot(bot_id) → dict`
  - Fetch bot details including `recording_url`
- `register_calendar_webhook(webhook_url) → dict`
  - Registers project-level `calendar.events_update` webhook on Attendee
- Remove old `schedule_all_upcoming_meets` / `get_completed_recordings`

---

### Task 3 — New `python/api/attendee_service.py`

All endpoints require `Depends(get_current_user)` except `/attendee/webhook`.

**`POST /attendee/link`**
```python
Body: {refresh_token, client_id, client_secret}
→ link_google_calendar(user_email=user.email)
→ _db.save_attendee_calendar_id(user.id, calendar_data["id"])
→ register_calendar_webhook(BASE_URL + "/attendee/webhook")
→ Returns: {calendar_id, status: "linked"}
```

**`GET /attendee/status`**
```python
→ Returns: {linked: bool, calendar_id: str | None}
```

**`POST /attendee/webhook`** (public — no user auth)
```python
body = await request.body()
sig = request.headers.get("X-Webhook-Signature")
if not _verify_signature(body, sig):
    raise HTTPException(403)

payload = json.loads(body)
trigger = payload.get("trigger")
idempotency_key = payload.get("idempotency_key", "")

if _db.is_webhook_key_processed(idempotency_key):
    return {"ok": True}   # deduplicate retries

if trigger == "calendar.events_update":
    # New/updated calendar event — schedule bot if it's a Meet
    background_tasks.add_task(_schedule_bot_if_needed, payload, idempotency_key)

elif trigger == "bot.state_change":
    event_type = payload.get("data", {}).get("event_type")
    if event_type == "post_processing_completed":
        bot_id = payload["bot_id"]
        background_tasks.add_task(
            _ingest_and_analyze_recording, bot_id, idempotency_key
        )

return {"ok": True}   # always return 200 within 10s
```

**`_schedule_bot_if_needed(payload, idempotency_key)`** (background task)
```python
# calendar_id is at the top level of the payload
# (payload["data"] only contains sync metadata, NOT event details)
calendar_id = payload.get("calendar_id")
if not calendar_id:
    return

# Fetch actual events from Attendee API
events = get_calendar_events(calendar_id)  # GET /calendar_events?calendar_id=xxx

webhook_url = f"{BASE_URL}/attendee/webhook"
for event in events:
    if (event.get("meeting_platform") != "google_meet"
            or event.get("bot_id") is not None):
        continue  # not a Meet or already has a bot

    try:
        # deduplication_key = event id prevents duplicate bots
        schedule_bot_for_event(event["id"], webhook_url)
    except requests.HTTPError:
        pass  # log and continue

_db.mark_webhook_key_processed(idempotency_key)
```

Also update `schedule_bot_for_event()` to include `deduplication_key`:
```python
bot_payload = {
    "calendar_event_id": event_id,
    "deduplication_key": event_id,  # prevents duplicate bots per event
    "bot_name": "SpeakNatural Bot",
    ...
}
```

**`_ingest_and_analyze_recording(bot_id, idempotency_key)`** (background task)
```python
# 1. Fetch recording_url + calendar_id from Attendee API
bot_data = get_bot(bot_id)
recording_url = bot_data["recording_url"]
calendar_id = bot_data.get("calendar_event", {}).get("calendar_id")

# 2. Resolve owning user
user_id = _db.get_user_id_by_calendar_id(calendar_id)

# 3. Download MP4 → temp dir
call_id = f"call_{uuid.uuid4().hex[:12]}"
mp4_path = f"/tmp/speak-right-sales/{call_id}/{bot_id}.mp4"
with requests.get(recording_url, stream=True) as r:
    with open(mp4_path, "wb") as f:
        shutil.copyfileobj(r.raw, f)

# 4. Convert MP4 → WAV (reuses existing AudioProcessorService)
wav_path, _ = ensure_wav_format(mp4_path)

# 5. Create DB record + mark idempotency key
_db.create_sales_call_from_attendee(call_id, bot_id, user_id, basename(wav_path))
_db.mark_webhook_key_processed(idempotency_key)

# 6. Run full pipeline — identical to manual upload from here
SalesCallProcessorService().process_call(wav_path, call_id, user_id)
# → uploads WAV to S3, transcribes, LLM analysis, saves scores
# → status="completed"
```

**`_verify_signature(body: bytes, signature: str) -> bool`**
```python
secret = base64.b64decode(os.getenv("ATTENDEE_WEBHOOK_SECRET"))
payload_dict = json.loads(body)
sorted_body = json.dumps(payload_dict, sort_keys=True).encode()
expected = hmac.new(secret, sorted_body, hashlib.sha256).hexdigest()
return hmac.compare_digest(expected, signature)
```

---

### Task 4 — DB Service Methods (`python/api/database.py`)

```python
def save_attendee_calendar_id(self, user_id: str, calendar_id: str) -> None

def get_attendee_calendar_id(self, user_id: str) -> Optional[str]

def get_user_id_by_calendar_id(self, calendar_id: str) -> Optional[str]
# Looks up user_profiles where attendee_calendar_id == calendar_id

def create_sales_call_from_attendee(
    self, call_id: str, bot_id: str, user_id: str, audio_filename: str
) -> dict
# Inserts: source="attendee", attendee_bot_id=bot_id, status="pending"

def is_webhook_key_processed(self, key: str) -> bool
def mark_webhook_key_processed(self, key: str) -> None
# Backed by webhook_idempotency_keys table
```

---

### Task 5 — Clean up `python/api/main.py`

- Remove all Attendee code added in current diff:
  `poll_and_save_recordings`, `schedule_meetings` endpoint,
  Attendee imports/globals, dead code with hardcoded credentials
- Register `attendee_router` from `attendee_service.py`

---

### Task 6 — Frontend (`ui/wireframe/src/App.tsx`)

- Replace `prompt()` button with a "Connect Calendar" modal:
  - Fields: Refresh Token, Client ID, Client Secret
  - On submit: `POST /attendee/link` → show "Calendar connected" badge
  - `GET /attendee/status` on load to show current link state
- Remove "Sync Meetings" button — no longer needed
- Auto-recorded calls show a "Bot" badge in the calls list

---

## Files Changed

| Task | New Files | Modified Files |
|---|---|---|
| 1 | `migrations/003_attendee_integration.sql` | — |
| 2 | — | `utils/attendee_utils.py` |
| 3 | `api/attendee_service.py` | — |
| 4 | — | `api/database.py` |
| 5 | — | `api/main.py` |
| 6 | — | `ui/wireframe/src/App.tsx` |

`api/link_calendar.py` — keep as dev/CLI setup script, no changes needed.

---

## .env Additions

```
ATTENDEE_WEBHOOK_SECRET=...    # from Attendee Settings → Webhooks
BASE_URL=https://xxx.ngrok.io  # publicly reachable URL (ngrok in dev)
```

Existing: `ATTENDEE_API_KEY`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`.

---

## Verification

```bash
# 1. Run migration on Supabase dev
# 2. Set .env vars, expose server: ngrok http 8000 → set BASE_URL

# 3. Start server
cd python && uv run uvicorn api.main:app --reload

# 4. Link calendar — also registers calendar.events_update webhook
curl -X POST http://localhost:8000/attendee/link \
  -H "Authorization: Bearer <token>" \
  -d '{"refresh_token":"...","client_id":"...","client_secret":"..."}'
# → {calendar_id, status: "linked"}

# 5. Add a Google Meet to the linked calendar
#    → Attendee fires calendar.events_update → bot auto-scheduled
#    → check logs: "Scheduled bot for event evt_xxx"

# 6. Meeting happens → bot joins, records, ends
#    → Attendee fires post_processing_completed webhook
#    → check logs: "Starting analysis for bot bot_xxx"

# 7. Verify call appears fully analyzed
curl http://localhost:8000/sales/calls -H "Authorization: Bearer <token>"
# → call with source="attendee", status="completed"

curl http://localhost:8000/sales/calls/{call_id}/analysis \
  -H "Authorization: Bearer <token>"
# → full scores populated

# 8. Simulate webhook locally for testing
curl -X POST http://localhost:8000/attendee/webhook \
  -H "X-Webhook-Signature: <valid-sig>" \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key":"test-uuid","bot_id":"bot_xxx",
       "trigger":"bot.state_change",
       "data":{"event_type":"post_processing_completed","new_state":"ended"}}'
# → {"ok": true}
```