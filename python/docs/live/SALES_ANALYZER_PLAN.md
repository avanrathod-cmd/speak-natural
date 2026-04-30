# Sales Call Analyzer MVP — Implementation Plan

## Context

Build a sales call AI analyzer on top of the existing `speak-right`
codebase (FastAPI + AWS Transcribe + Supabase + S3 + `google-genai`
already integrated). Managers upload sales call audio → AI scores rep
performance and lead quality → manager chat surfaces team insights.

**LLM:** Gemini via `google-genai` (already used in
`metrics_generator.py` and `generate_ssml.py`). Model configurable
via `.env` — switching providers requires only env var changes, no
code changes.

---

## Coding Conventions

- **Line length:** ~80 characters max
- **Function ordering:** public functions first, private at the bottom
  of the class/module
- **REST:** APIs must adhere to REST principles — GET must be
  read-only with no side effects, POST/PUT/PATCH for writes,
  resource names in URLs (nouns not verbs)
- **Endpoint files:** files that expose HTTP endpoints use the suffix
  `_service.py` (e.g. `sales_service.py`, not `sales_router.py`)
- **Method naming:** method names must reflect their DB table
  (e.g. `get_sales_script`, `get_coaching_session`)
  - Existing `DatabaseService` methods have `# TODO: rename to
    get/update/delete_coaching_session_*` markers pending a refactor

---

## Execution Strategy

Each task is independently completable and testable in a single
session. Work in order. Each task ends with a concrete verification
step.

---

## Progress

| Task | Status |
|---|---|
| 1 — DB Migration | ✅ Done |
| 2 — Shared LLM Client | ✅ Done |
| 3 — Script Generator + API | ✅ Done |
| 4 — Sales Call Analyzer | ⬜ Not started |
| 5 — Sales Call Processor + Upload API | ⬜ Not started |
| 6 — Frontend: Routing + Call Upload Page | ⬜ Not started |
| 7 — Frontend: Manager Dashboard | ⬜ Not started |
| 8 — Frontend: Script Generator Page | ⬜ Not started |
| 9 — Manager AI Chat (deferred) | ⬜ Deferred |

---

## Task 1 — Database Migration ✅

**Files created:**
- `python/migrations/002_sales_analyzer.sql`

**Tables created:**
```sql
organizations, user_profiles, products, sales_scripts,
sales_calls, call_analyses,
manager_chat_sessions, manager_chat_messages
```

Key columns in `call_analyses`:
- Scores (0–100): `overall_rep_score`, `script_adherence_score`,
  `communication_score`, `objection_handling_score`,
  `closing_score`, `lead_score`
- `engagement_level` TEXT, `customer_sentiment` TEXT
- `rep_analysis` JSONB, `customer_analysis` JSONB,
  `vocal_metrics` JSONB, `full_transcript` JSONB

**Test:** Run migration on Supabase dev.
`SELECT table_name FROM information_schema.tables
WHERE table_schema='public';` → all 8 tables visible.

---

## Task 2 — Shared LLM Client ✅

**Files created:**
- `python/utils/llm_client.py`

**What it does:** Single `call_llm(prompt, system="", json_mode=True)`
function.
- Default provider: Gemini (`google-genai`, same SDK already in use)
- JSON mode enabled by default (`response_mime_type: "application/json"`)
- Provider + model read from `.env`:

```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

Switching to Anthropic: change two env vars, zero code changes.

**Files modified:** `python/.env.example` (added `LLM_PROVIDER`,
`LLM_MODEL`, `GEMINI_API_KEY`)

**Verified:**
```bash
cd python && uv run python -c "
from utils.llm_client import call_llm
print(call_llm('Return JSON: {\"status\": \"ok\"}'))
"
# Output: {'status': 'ok'}
```

---

## Task 3 — Script Generator Service + API ✅

**Goal:** Manager fills in product info → Gemini generates a
structured sales script.

**Files created:**
- `python/services/script_generator.py` — `ScriptGeneratorService`
- `python/api/sales_service.py` — products + scripts endpoints

**Files modified:**
- `python/api/database.py` — added `SalesDatabaseService` subclass
  with `create_product()`, `create_sales_script()`,
  `update_sales_script()`, `get_sales_script()`,
  `get_latest_sales_script_for_product()`, `list_products()`
- `python/api/models.py` — added `ProductCreateRequest`,
  `ProductResponse`, `ScriptResponse`, `RegenerateScriptRequest`
- `python/api/main.py` — `app.include_router(sales_router,
  prefix="/sales")`

**Script output format (Gemini JSON mode):**
```json
{
  "opening": "...",
  "discovery_questions": ["q1", "q2", "q3", "q4", "q5"],
  "value_propositions": ["vp1", "vp2", "vp3"],
  "objection_handlers": {"price too high": "response..."},
  "closing": "...",
  "key_phrases": ["must say this", "mention this"]
}
```

**Endpoints:**
```
POST /sales/products              → create product + auto-generate script
GET  /sales/products              → list org products
                                    ?search=  filter across name,
                                              description,
                                              customer_profile,
                                              talking_points
                                    ?order_by= column (default: created_at)
                                    ?order_desc= bool (default: true)
GET  /sales/scripts/{id}          → get script detail
POST /sales/scripts/regenerate    → overwrite script for existing product
```

**Notable design decisions:**
- Products are org-scoped (all users in an org see the same products)
- `_ensure_org` auto-creates an org on first write; pure reads use
  `_get_org_id` (no side effects)
- `POST /scripts/regenerate` overwrites the existing script in place;
  falls back to creating one if none exists
- `list_products` search uses `_build_or_filter` helper (PostgREST OR)
- TODO: hardcoded searchable columns — consider Postgres full-text
  search when schema evolves
- TODO (post-MVP): introduce `teams` table so different sales teams
  within an org can have different product sets

**Verified:**
```bash
cd python && uv run python -c "
from services.script_generator import ScriptGeneratorService
import json
svc = ScriptGeneratorService()
r = svc.generate_script('CRM Pro', 'A CRM tool', 'Sales managers', 'Easy setup')
print(json.dumps(r, indent=2))
"
# All 6 script fields populated
```

---

## Task 4 — Sales Call Analyzer (Core Intelligence)

**Goal:** Given an AWS Transcribe transcript JSON, identify speakers
and produce two Gemini analysis outputs.

**Files to create:**
- `python/services/sales_call_analyzer.py` — `SalesCallAnalyzerService`

**Methods:**
1. `identify_speakers(transcript_data, rep_hint=None)`
   - Returns `{salesperson_label: str, customer_labels: list[str]}`
   - One sales rep per call; multiple customer reps supported
   - Heuristic: rep = speaker with most words; fallback = first speaker
   - `rep_hint` overrides heuristic (e.g. "spk_0")
2. `extract_speaker_turns(transcript_data, speaker_map)`
   - Returns `{rep_turns, customer_turns, full_transcript}`
   - All turns from any label in `customer_labels` merged into one
3. `analyze_rep_performance(rep_turns, script, vocal_metrics) → dict`
4. `analyze_customer_behavior(customer_turns, product_description)
   → dict`

**Rep analysis output schema:**
```json
{
  "overall_rep_score": 72,
  "script_adherence_score": 65,
  "objection_handling_score": 80,
  "closing_score": 70,
  "communication_score": 75,
  "key_moments": [{"time": "2:34", "type": "objection_handled",
                   "note": "..."}],
  "script_gaps": ["forgot to mention pricing"],
  "strengths": ["good discovery questions"],
  "improvements": ["close stronger"],
  "coaching_summary": "..."
}
```

**Customer analysis output schema:**
```json
{
  "lead_score": 78,
  "engagement_level": "high",
  "customer_sentiment": "positive",
  "interests": ["feature X", "integration Y"],
  "objections": ["pricing", "implementation time"],
  "buying_signals": ["asked about contract terms"],
  "recommended_product_fit": "Enterprise plan",
  "suggested_next_steps": ["send pricing deck", "schedule demo"],
  "analysis_summary": "..."
}
```

**Test (no audio needed — use a sample transcript JSON):**
```bash
cd python && uv run python -c "
import json
from services.sales_call_analyzer import SalesCallAnalyzerService
svc = SalesCallAnalyzerService()
transcript = json.load(open('tests/sample_transcript.json'))
speaker_map = svc.identify_speakers(transcript)
print('Speaker map:', speaker_map)
turns = svc.extract_speaker_turns(transcript, speaker_map)
rep_result = svc.analyze_rep_performance(
    turns['rep_turns'], script=None, vocal_metrics={})
print('Rep score:', rep_result['overall_rep_score'])
"
```

**Depends on:** Task 2

---

## Task 5 — Sales Call Processor + Upload API

**Goal:** Upload audio → background processing → poll status →
get analysis.

**Files to create:**
- `python/services/sales_call_processor.py` —
  `SalesCallProcessorService` (thin orchestrator)

**Pipeline:**
```
1. ensure_wav_format()           ← REUSE audio_processor.py
2. upload_audio_to_s3()          ← REUSE audio_processor.py
3. transcribe_audio()            ← REUSE audio_processor.py
                                    (diarization already ON)
4. identify_speakers()           ← Task 4
5. extract_speaker_turns()       ← Task 4
6. generate_structured_metrics() ← REUSE metrics_generator.py
7. analyze_rep_performance()     ← Task 4
8. analyze_customer_behavior()   ← Task 4
9. save_call_analysis()          ← Supabase (new DB method)
10. upload analysis JSON to S3   ← s3_paths: sales/{call_id}/analysis/
```

**Files to modify:**
- `python/api/sales_service.py` — add:
  ```
  POST /sales/calls/upload          → {call_id, status:"pending"}
  GET  /sales/calls/{call_id}/status
  GET  /sales/calls/{call_id}/analysis
  GET  /sales/calls                 → list (manager: all; rep: own)
  ```
- `python/api/database.py` — add `create_sales_call()`,
  `update_sales_call_status()`, `save_call_analysis()`,
  `get_call_analysis()`
- `python/api/models.py` — add `SalesCallUploadResponse`,
  `CallAnalysisResponse`

Follow existing `BackgroundTasks` pattern in `main.py` exactly.

**Test:**
```bash
curl -X POST http://localhost:8000/sales/calls/upload \
  -H "Authorization: Bearer <token>" \
  -F "audio_file=@tests/sample_call.wav"
# → {"call_id": "call_abc123", "status": "pending"}

curl http://localhost:8000/sales/calls/call_abc123/status
curl http://localhost:8000/sales/calls/call_abc123/analysis
# → verify rep_analysis and customer_analysis are both populated
```

**Depends on:** Task 1, Task 2, Task 4

---

## Task 6 — Frontend: Routing + Call Upload Page

All separate pages should have separate URLs for easy navigation
and debugging.

**Files to create:**
- `ui/wireframe/src/pages/sales/CallUploadPage.tsx`
- `ui/wireframe/src/types/sales.ts`

**Files to modify:**
- `ui/wireframe/src/App.tsx` — add `react-router-dom`; existing
  page → `/coach`, new pages → `/sales/*`
- `ui/wireframe/src/services/api.ts` — add `uploadSalesCall()`,
  `getSalesCallStatus()`, `getSalesCallAnalysis()`
- `ui/wireframe/package.json` — add `react-router-dom`, `recharts`

**`CallUploadPage.tsx` layout:**
```
[Script selector dropdown (optional)]
[Drag-and-drop audio upload]   ← reuse existing upload pattern
[Progress: Upload → Transcribe → Analyze → Done]
[Results — two tabs:]
  Tab 1: Rep Performance
    - Score gauges: Overall / Script Adherence / Communication
                    / Objection Handling / Close
    - Key moments (timestamped)
    - Coaching tips
  Tab 2: Customer / Lead
    - Lead score 0–100 with color indicator
    - Engagement level badge
    - Buying signals, Objections, Next steps
```

**Test:** `npm start` → `/sales/upload` → upload sample audio →
watch steps → verify both tabs.

**Depends on:** Task 5

---

## Task 7 — Frontend: Manager Dashboard

**Files to create:**
- `ui/wireframe/src/pages/sales/ManagerDashboardPage.tsx`

**Files to modify:**
- `python/api/sales_service.py` — add
  `GET /sales/dashboard/team`, `GET /sales/dashboard/rep/{rep_id}`
- `ui/wireframe/src/services/api.ts` — add `getTeamDashboard()`,
  `getRepDetail()`

**Layout:**

*Section A — Team Grid:*
```
┌─────────────────────────────────────────────────┐
│  Sarah M.   Calls: 12   Rep: 74   Lead: 68      │
│  [trend sparkline]              [View Detail]    │
├─────────────────────────────────────────────────┤
│  James T.   Calls: 8    Rep: 55   Lead: 72      │
│  [trend sparkline]              [View Detail]    │
└─────────────────────────────────────────────────┘
```

*Section B — Rep Detail (click card):*
- Call history table: Date | Duration | Rep Score | Lead Score |
  Engagement
- Row expand → coaching summary + customer analysis
- Score trend chart (recharts LineChart, last 10 calls)

**Test:** `npm start` → `/sales/dashboard` → rep grid loads →
click rep → call history shows.

**Depends on:** Task 5, Task 6

---

## Task 8 — Frontend: Script Generator Page

**Files to create:**
- `ui/wireframe/src/pages/sales/ScriptGeneratorPage.tsx`

**Files to modify:**
- `ui/wireframe/src/services/api.ts` — add `createProduct()`,
  `getScript()`, `regenerateScript()`

**Layout:**
```
Left (form):                    Right (generated script):
  Product name                    Opening Hook
  Description                     Discovery Questions (5)
  Customer profile                Value Propositions (3)
  Talking points                  Objection Handlers (table)
  [Generate Script]               Closing / Key Phrases
                                  [Save & Assign to Team]
```

**Test:** Fill form → Generate → all 6 sections render → Save →
confirm DB row created.

**Depends on:** Task 3, Task 6

---

## Task 9 — Manager AI Chat (Phase 2)

**Defer until Tasks 1–8 complete and real call data exists.**

**Files to create:**
- `python/services/manager_chat_service.py`
- `ui/wireframe/src/components/sales/ManagerChat.tsx`

**Context strategy:** aggregate SQL queries (not raw transcripts)
→ inject into Gemini system prompt → stream response via SSE.

**Endpoints:**
```
POST /sales/chat                      → {session_id, response}
GET  /sales/chat/{session_id}/history
```

**Test:** Ask "Which reps need coaching this week?" → response
cites real rep names + scores.

**Depends on:** Tasks 1–7

---

## Files Summary

| Task | New Files | Modified Files |
|---|---|---|
| 1 | `migrations/002_sales_analyzer.sql` | — |
| 2 | `utils/llm_client.py` | `.env.example` |
| 3 | `services/script_generator.py`, `api/sales_service.py` | `api/database.py`, `api/models.py`, `api/main.py` |
| 4 | `services/sales_call_analyzer.py` | — |
| 5 | `services/sales_call_processor.py` | `api/sales_service.py`, `api/database.py`, `api/models.py` |
| 6 | `pages/sales/CallUploadPage.tsx`, `types/sales.ts` | `App.tsx`, `services/api.ts`, `package.json` |
| 7 | `pages/sales/ManagerDashboardPage.tsx` | `api/sales_service.py`, `services/api.ts` |
| 8 | `pages/sales/ScriptGeneratorPage.tsx` | `services/api.ts` |
| 9 | `services/manager_chat_service.py`, `components/sales/ManagerChat.tsx` | `api/sales_service.py`, `services/api.ts` |

---

## Critical Existing Files to Reference

- `python/services/audio_processor.py` — reuse `ensure_wav_format`,
  `upload_audio_to_s3`, `transcribe_audio`
- `python/services/metrics_generator.py` — reuse
  `generate_structured_metrics`
- `python/speach_to_text/transcribe.py` — already has
  `ShowSpeakerLabels: True`
- `python/api/main.py` — follow `BackgroundTasks` upload pattern
- `python/api/database.py` — follow Supabase client pattern for
  new DB methods
- `python/migrations/001_create_coaching_sessions.sql` — follow
  for migration 002
