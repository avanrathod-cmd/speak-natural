# SpeakNatural — Go-Live Plan

## Context

The core product is working end-to-end: Google Meet recordings are
auto-ingested via Attendee.dev, analyzed by Gemini, and surfaced in
a React dashboard. Before sharing publicly, six areas need to be
completed.

**Stack reminders:**
- Backend: FastAPI + Supabase + S3 + AWS Transcribe
- LLM: Gemini via `google-genai` (LLM_PROVIDER/LLM_MODEL env vars)
- Frontend: React + TypeScript + Tailwind (`ui/wireframe/src/`)
- Bot recording: Attendee.dev (already integrated for Google Meet)
- Conventions: `_service.py` suffix for HTTP endpoints,
  public functions first, ~80 char lines, REST nouns not verbs

---

## Work Items (Execution Order)

| # | Area | Status |
|---|------|--------|
| 1 | Meeting Integrations (Zoom + Teams) | ✅ Done |
| 2 | Share Meeting Reviews | ⬜ Not started |
| 3 | Download Transcripts + Summary | ✅ Done |
| 4 | Payment Gateway (Dodo Payments) | ⬜ Not started |
| 5 | UI Fixes + Dashboard | ⬜ Not started |
| 6 | Video Recording (optional) | ⬜ Not started |

**Why this order:**
- Item 1 first: Zoom + Teams are the bottleneck for demo reach.
  Google Meet alone limits who you can show this to.
- Items 2–3 next: Share + Download are zero-marginal-cost
  retention features that make the product feel complete. Do these
  before charging anyone.
- Item 4 (Stripe): Wire up payment only after the core UX works
  end-to-end on real meetings. Charging before you can reliably
  deliver Zoom + Teams would be a mistake.
- Item 5 (UI) last: Polish is valuable but carries low launch risk.
  Push it until after payment is proven working — bugs here don't
  block revenue.

---

## Infrastructure Costs + Suggested Pricing

Understanding your cost structure before setting prices.

### Per-Call Variable Costs (assuming 30-min call)

| Service | Cost/call | Notes |
|---------|-----------|-------|
| AWS Transcribe | ~$0.72 | $0.024/min × 30 min |
| Attendee.dev bot | ~$0.50–$1.00 | ~$1–2/bot-hour; check your plan |
| Gemini analysis | ~$0.002 | Negligible; ~7K tokens per call |
| S3 audio storage | ~$0.0002/mo | 10 MB × $0.023/GB |
| **Total per call** | **~$1.22–$1.72** | Transcribe + bot dominate |

The two costs to control: **Transcribe** and **Attendee.dev bots**.
If you can negotiate a volume deal with Attendee or switch to a
model with cheaper transcription (Deepgram at $0.0043/min is 5×
cheaper than AWS), your per-call cost drops to ~$0.20–$0.40.

### Monthly Fixed Costs

| Service | Cost/month | Notes |
|---------|------------|-------|
| Supabase Pro | $25 | Free tier OK up to ~50 active users |
| Hosting (backend) | $20–50 | Railway/Render Pro or AWS ECS |
| Domain + SSL | ~$1.25 | |
| Stripe fees | 2.9% + $0.30 | Per transaction, not monthly |
| **Total fixed** | **~$46–76** | |

### Suggested Pricing Tiers

| Plan | Price | Call Limit | Reasoning |
|------|-------|------------|-----------|
| Free | $0 | 3 calls/month | ~$3.50–5 in variable cost; loss leader to acquire users |
| Pro | $49/month | 20 calls | ~$24–34 variable + ~$8 fixed share = comfortable margin |
| Pro+ | $99/month | Unlimited* | *Soft limit at 60 calls — flag above that for review |
| Team | $199/month | Unlimited* | Up to 10 org members; ~$200 headroom on 60 calls |

**Why $49 not $29 for Pro:**
At $29 with unlimited calls, a single power user doing 25 calls/month
costs you ~$43 in variable costs — you lose money. $49 with a 20-call
limit gives healthy margin and positions the product as
professional-grade, not a consumer tool.

**Key levers to improve margin:**
1. Switch AWS Transcribe → Deepgram ($0.0043/min) for ~5× cost
   reduction on transcription.
2. Negotiate Attendee.dev volume pricing once you hit 50+ users.
3. Add a per-call add-on ($2/call) above plan limits instead of
   hard blocking, to avoid churning power users.

---

## Item 1 — Meeting Integrations (Zoom + Microsoft Teams)

**Goal:** Auto-record Zoom and Teams meetings the same way Google
Meet is already handled. Attendee.dev already supports all three
platforms — this is mostly extending our URL-detection logic.

### Alternatives Considered

**A — Build native Zoom/Teams OAuth apps (rejected)**
Both platforms have official bot/recording APIs, but they require:
- App review processes (weeks to months per platform)
- Enterprise agreements for Teams recording APIs
- Ongoing compliance with each platform's usage policies

Attendee.dev already handles all of this. We use it for Google Meet
and the bot mechanics are identical for Zoom and Teams. Switching
would be months of work with no product benefit.

**B — Use Recall.ai instead of Attendee.dev (rejected)**
Recall.ai is a strong alternative with cleaner API design. However,
Attendee.dev is already fully integrated (OAuth, webhooks, bot
scheduling, recording download). Migrating mid-product to Recall
would rewrite `attendee_service.py` and `attendee_utils.py` with
no user-facing benefit at this stage.

**C — User-initiated upload of Zoom cloud recordings (rejected)**
Zoom can save cloud recordings automatically; users could manually
upload them. This is much simpler to implement but degrades the core
value prop: the differentiator is zero-touch recording. Requiring
users to log into Zoom, find the file, and upload it is the UX we
are replacing.

### What to build

#### Current state

`_is_google_meet(event)` in `attendee_utils.py` checks for
`meet.google.com`. Only Google Meet events get bots scheduled.

#### 1a — Extend URL Detection

Replace `_is_google_meet` with `_get_meeting_platform`:

```python
_PLATFORM_PATTERNS: dict[str, list[str]] = {
    "google_meet": ["meet.google.com"],
    "zoom":        [
        "zoom.us/j/",
        "zoom.us/my/",
        "us02web.zoom.us",
        "us06web.zoom.us",
    ],
    "teams": [
        "teams.microsoft.com/l/meetup-join",
        "teams.live.com/meet/",
    ],
}

def _get_meeting_platform(event: dict) -> str | None:
    """
    Return 'google_meet' | 'zoom' | 'teams' | None.
    Checks event['meeting_url'] and event.get('description', '').
    """
```

Update `_schedule_bot_if_needed` in `attendee_service.py`:
```python
# Before:
if not _is_google_meet(event) or event.get("bots"):

# After:
platform = _get_meeting_platform(event)
if not platform or event.get("bots"):
```

### Status: Partially done

URL detection is complete (`get_meeting_platform` replaces
`_is_google_meet` — Zoom and Teams meetings are now detected).

Zoom bots additionally require a **per-user Zoom OAuth connection**
because Zoom mandated onbehalf tokens for external meetings on
March 2, 2026. Without it bots fail with `AUTHRET_JWTTOKENWRONG`.

Full implementation plan: `python/docs/ZOOM_OAUTH_PLAN.md`

Teams bot support is expected to have the same requirement —
verify with Attendee docs before implementing.

### Files modified so far

- `python/utils/attendee_utils.py` — `get_meeting_platform`,
  `_platform_from_url`, `update_calendar_credentials`
- `python/api/attendee_service.py` — updated imports + call sites

**Test:** Schedule a Zoom test meeting in a calendar that is already
linked → confirm Attendee dashboard shows a bot joining → confirm
call appears with `meeting_platform: "zoom"`.

Note: Zoom and Teams require the meeting host to allow recording
(bot admission). Attendee handles the mechanics, but your users
must ensure their Attendee plan covers Zoom/Teams bots.

---

## Item 2 — Share Meeting Reviews

**Goal:** Any user can generate a shareable link. Anyone with the
link can view a read-only analysis page — no login required.

### Alternatives Considered

**A — Require recipients to sign up to view (rejected)**
Forces the recipient into an account funnel. Kills the "forward to
your manager" use case. The whole value of sharing is instant,
frictionless access for someone who doesn't use SpeakRight.

**B — Signed S3 URL direct to analysis JSON (rejected)**
S3 pre-signed URLs expire and are hard to revoke. They also expose
raw JSON to anyone who opens the link — no UI, no branding, no
context. Share should load a full page, not a JSON blob.

**C — Time-expiry only, no manual revoke (rejected)**
Simpler implementation. Rejected because a user who accidentally
shares a link needs a way to kill it immediately — especially if the
call contains sensitive customer information. Revoke is a trust
feature, not a nice-to-have.

### What to build

#### 2a — DB Migration

```sql
-- migrations/003_share_tokens.sql
CREATE TABLE share_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     TEXT NOT NULL
                  REFERENCES sales_calls(id) ON DELETE CASCADE,
    created_by  UUID NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ,          -- NULL = no expiry
    revoked     BOOLEAN DEFAULT false
);
CREATE INDEX ON share_tokens(call_id);
```

#### 2b — Backend Endpoints

Add to `sales_service.py`:

```
POST /sales/calls/{call_id}/share
  → {token: "...", url: "https://<FRONTEND_URL>/share/<token>"}

DELETE /sales/calls/{call_id}/share/{token}   (revoke)

GET  /sales/share/{token}                     (public — no auth)
  → CallAnalysisResponse shape
    + {audio_filename, created_at, duration_seconds}
```

`GET /sales/share/{token}` must:
1. Validate: `id = token AND NOT revoked
   AND (expires_at IS NULL OR expires_at > now())`
2. Return analysis — no auth required
3. Never expose `user_id`, `org_id`, or internal DB IDs

Add DB methods to `database.py`:
`create_share_token()`, `get_analysis_by_share_token()`,
`revoke_share_token()`

#### 2c — Frontend

**ShareModal.tsx (new):**
```
┌──────────────────────────────────────────────┐
│  Share this review                       [X] │
│                                              │
│  ┌──────────────────────────────┐ [Copy Link]│
│  │ https://.../share/abc123...  │            │
│  └──────────────────────────────┘            │
│                                              │
│  [Revoke link]                               │
└──────────────────────────────────────────────┘
```

On first open: `POST /sales/calls/{call_id}/share`, cache URL.
"Copy Link" → `navigator.clipboard.writeText`.
"Revoke" → `DELETE`, clear cache.

**SharedAnalysisPage.tsx (new):**
- Route: `/share/:token` — added before the auth guard in `App.tsx`
- Fetches `GET /sales/share/{token}`
- Renders same analysis UI as `AnalysisView` but:
  - No action bar (no download/share/back buttons)
  - SpeakRight branding + "Powered by SpeakRight" footer (free
    marketing on every share)
  - If token invalid/expired/revoked: show a clean error state

### Files to modify/create

- `python/api/sales_service.py` — share endpoints
- `python/api/database.py` — share token DB methods
- `python/migrations/003_share_tokens.sql` — new file
- `ui/wireframe/src/components/ShareModal.tsx` — new file
- `ui/wireframe/src/pages/SharedAnalysisPage.tsx` — new file
- `ui/wireframe/src/App.tsx` — add `/share/:token` public route
- `ui/wireframe/src/services/api.ts` — add share API calls
- `ui/wireframe/src/components/AnalysisView.tsx` — wire Share button

**Test:**
```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8000/sales/calls/<id>/share \
  -H "Authorization: Bearer <jwt>" | jq -r '.token')

# Unauthenticated fetch
curl http://localhost:8000/sales/share/$TOKEN
# → full analysis JSON, HTTP 200, no Authorization header needed

# Open /share/$TOKEN in incognito — full analysis page, no login
# Revoke → link returns 404
```

---

## Item 3 — Download Transcripts + Summary

**Goal:** One-click download of the meeting transcript and a
factual meeting summary (what was discussed, what was raised,
what are the next steps). No coaching scores or rep analysis.

### Decisions

**PDF — skipped for now.**
Adds heavy server deps or poor client-side rendering. Plain text
forwards cleanly as email, pastes into Notion/Docs, and prints
well via browser.

**JSON — dropped.**
No current use case; can add later if a CRM integration request
comes in.

**Coaching analysis — excluded.**
The export contains only factual meeting data (transcript +
customer-side observations). Scores, strengths, and coaching
tips are visible in the app but not included in the download.

### What to build

#### 3a — Backend Export Endpoint

Add to `sales_service.py`:

```
GET /sales/calls/{call_id}/export
```

Response headers: `Content-Disposition: attachment;
filename="speakright-<call_id>.txt"`
`Content-Type: text/plain`

**File format:**
```
MEETING TRANSCRIPT — <audio_filename>
Date: <created_at>   Duration: <X min Y sec>
────────────────────────────────────────────

MEETING SUMMARY
  Customer Interests:
    • interest 1
    • interest 2
  Objections Raised:
    • objection 1
  Buying Signals:
    • signal 1
  Suggested Next Steps:
    1. step 1
    2. step 2

FULL TRANSCRIPT
[00:00] Rep: Hello, thanks for joining...
[00:12] Customer: Hi, yeah no problem...
```

Sections with no data are omitted. If `customer_analysis` is
null the MEETING SUMMARY block is omitted entirely.

Add `get_call_for_export()` to `database.py` — fetches
`audio_filename`, `created_at`, `duration_seconds` from
`sales_calls` plus `full_transcript` and `customer_analysis`
from `call_analyses`.

#### 3b — Frontend Download Button

Add a "Download Transcript" button in `AnalysisView` banner:

- Single button (no dropdown needed — txt only)
- `GET /sales/calls/{call_id}/export` with auth token
- `URL.createObjectURL(blob)` → programmatic `<a>` click

### Files to modify

- `python/api/database.py` — add `get_call_for_export()`
- `python/api/sales_service.py` — export endpoint
- `ui/wireframe/src/services/api.ts` — add `exportCall()`
- `ui/wireframe/src/components/AnalysisView.tsx` — download button

**Test:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/sales/calls/<id>/export" \
  -o transcript.txt
# → verify header, meeting summary, and transcript timestamps
```

---

## Item 4 — Payment Framework (Dodo Payments)

**Goal:** Wire up end-to-end payment flow (user pays → webhook →
plan stored in DB). Pricing model (user-based vs consumption-based)
is TBD — enforcement logic is intentionally left out of this item
and added once the model is decided.

### Provider: Dodo Payments

Dodo Payments is a Merchant of Record (MoR) platform built
specifically for Indian founders billing international customers.

**Why Dodo over alternatives:**
- **vs Stripe:** Invite-only in India since May 2024. 6%+ effective
  cost after cross-border fees + FX markup. No e-FIRA docs (required
  for Indian GST compliance).
- **vs LemonSqueezy:** Acquired by Stripe in July 2024. Support has
  slowed, roadmap gone quiet.
- **vs Paddle:** Solid but charges a $150 risk assessment fee for new
  accounts. Slower onboarding.
- **vs Razorpay:** Best for Indian customers (UPI, net banking) but
  settles in INR — cannot hold or receive USD directly.

**Dodo advantages:**
- MoR model: handles RBI/FEMA compliance, VAT in 225+ countries.
  You receive clean INR as a service export.
- 4% + $0.40/transaction — cheaper than Paddle/LemonSqueezy.
- India-native, fast onboarding, Python SDK with Pydantic models.

### Pricing Model (TBD)

The enforcement model is undecided between:
- **User-based:** charge per seat (e.g. Solo $39/mo, Team $99/mo
  unlimited users)
- **Consumption-based:** charge per call or call volume tier

Decision deferred until after the payment flow is live and we see
real usage. The `subscriptions` table schema below is intentionally
flexible — add a `seat_limit` or `calls_limit` column when decided.

**Placeholder plans for Dodo test dashboard (subject to change):**

| Plan | Price | Notes |
|------|-------|-------|
| Free | $0 | Default for all new orgs |
| Pro | $39/month | Placeholder — exact limits TBD |

### What to build

#### 4a — DB Migration

```sql
-- migrations/005_billing.sql
CREATE TABLE subscriptions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID NOT NULL
                           REFERENCES organizations(id),
    dodo_customer_id     TEXT,
    dodo_sub_id          TEXT,
    plan                 TEXT NOT NULL DEFAULT 'free',
    status               TEXT NOT NULL DEFAULT 'active',
    current_period_end   TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ON subscriptions(org_id);
CREATE UNIQUE INDEX ON subscriptions(dodo_sub_id)
  WHERE dodo_sub_id IS NOT NULL;
```

No usage counters yet — add those when the enforcement model is
decided.

#### 4b — Billing Client

**`python/utils/billing_client.py`** — direct Dodo calls, no
abstraction layer (add that if/when we switch providers):

```python
def create_checkout_session(
    *, product_id: str, user_id: str,
    customer_email: str, customer_name: str,
    success_url: str, cancel_url: str,
) -> str:  # returns checkout_url

def create_portal_session(
    *, customer_id: str, return_url: str,
) -> str:  # returns portal_url

def parse_webhook_event(
    *, payload: bytes, headers: dict,
) -> dict:  # normalised event dict
```

Webhook signature verified via Dodo Python SDK `unwrap()` —
raises 401 on invalid signature.

#### 4c — Billing Service Endpoints

**`python/api/billing_service.py`:**

```
POST /billing/checkout    → {checkout_url}
POST /billing/webhook     → handle Dodo events (no auth)
GET  /billing/status      → {plan, status, period_end}
```

**Webhook events handled:**
- `subscription.active` → upsert subscription row with plan +
  customer IDs
- `subscription.renewed` → update `current_period_end`
- `subscription.plan_changed` → update plan column
- `subscription.cancelled` / `subscription.failed` → set
  plan = 'free'

#### 4d — Frontend

**`PricingPage.tsx` (new):** Placeholder plan cards (Free / Pro).
"Upgrade" → `POST /billing/checkout` → redirect to Dodo Checkout.

**`BillingPage.tsx` (new):** Current plan badge, period end date,
"Manage Billing" button → `GET /billing/portal` → new tab.

**New env vars:**
```
DODO_API_KEY=...
DODO_WEBHOOK_KEY=...
DODO_PRO_PRODUCT_ID=...
FRONTEND_URL=https://your-app.com
```

### Files to create/modify

- `python/utils/billing_client.py` — new file
- `python/api/billing_service.py` — new file
- `python/migrations/005_billing.sql` — new file
- `python/api/main.py` — include billing router at `/billing`
- `ui/wireframe/src/pages/PricingPage.tsx` — new file
- `ui/wireframe/src/pages/BillingPage.tsx` — new file
- `ui/wireframe/src/App.tsx` — add `/pricing`, `/billing` routes
- `ui/wireframe/src/services/api.ts` — add billing API calls

### Test

1. Create Pro product in Dodo test dashboard.
2. Click Upgrade → Dodo Checkout → complete with test card.
3. Dodo fires `subscription.active` webhook → subscription row
   created with `plan = 'pro'`.
4. `GET /billing/status` returns `{plan: "pro", status: "active"}`.

### Deferred (add after pricing model decision)

- Usage enforcement (`_assert_call_limit` or `_assert_seat_limit`
  in `sales_service.py`)
- Usage counters in `subscriptions` table
- HTTP 402 handling in frontend upload flow

---

## Item 5 — UI Fixes + Dashboard

**Full plan: `python/docs/UI_FIXES_PLAN.md`**

**Goal:** Polish the existing UI so the product looks production-ready
when shared with paying customers. Covers LLM-generated call names
(inline-editable), a dedicated profile page, stats cards, filter
tabs, rep column fix, and the AnalysisView action bar.

---

## Item 6 — Video Recording (optional)

**Goal:** Show the original meeting video in the analysis view.

### Alternatives Considered

**A — Stream directly from Attendee CDN (rejected)**
Attendee recording URLs expire. We'd need to refresh them on demand,
adding latency and a dependency on Attendee's availability to play
back old recordings. Storing to our own S3 gives us control and
permanent URLs.

**B — Re-encode to HLS for adaptive streaming (deferred)**
For long meetings (60+ min), progressive MP4 download is slow.
HLS with quality levels is the right long-term answer. Deferred:
at launch, most calls will be under 30 min and MP4 plays fine.

### What to build

- In `_ingest_and_analyze_recording`: upload the original MP4 to S3
  at `sales/{call_id}/recording.mp4` before converting to WAV.
- Add `has_video: bool` to `sales_calls` (migration 006).
- Add `GET /sales/calls/{call_id}/video` → pre-signed S3 URL
  (same pattern as existing audio endpoint).
- In `AnalysisView`: if `has_video`, render `<video>` instead of
  `<audio>`.

**Files to modify:**
- `python/api/attendee_service.py` — upload MP4 before conversion
- `python/api/sales_service.py` — video presigned URL endpoint
- `python/api/database.py` — `has_video` field
- `python/migrations/006_video.sql`
- `ui/wireframe/src/components/AnalysisView.tsx` — video player
- `ui/wireframe/src/services/api.ts` — add `getCallVideo()`

**Storage note:** MP4s are 5–50× larger than WAVs. Set an S3
lifecycle policy to expire `sales/*/recording.mp4` objects after
90 days, or pass the storage cost directly to paid plans
("90-day recording archive on Pro").

---

## Technical Notes to Revisit

### Transcription Provider

Currently using AWS Transcribe with `LanguageCode='en-US'`
(`python/speach_to_text/transcribe.py:137`). Two problems:

1. `en-US` actively hurts Indian English accuracy. Quick fix:
   change to `en-IN` — free, immediate improvement.

2. No provider handles both Indian/Hinglish AND Western accents
   equally well. The decision depends on the customer mix:

| Provider | Indian/Hinglish | Western Accents | Diarization | Cost/30min |
|----------|----------------|-----------------|-------------|------------|
| Whisper large-v3 | Very good | Excellent | No (separate) | $0.18 API / ~$0.05 self-hosted |
| AssemblyAI Universal-2 | Good | Excellent | Native | ~$0.36 |
| Google Chirp | Good | Excellent | Native | $0.48 |
| Sarvam Saarika v2 | Best | Unknown/risky | Native | ~$0.15 |
| AWS Transcribe en-IN | Decent | Poor | Native | $0.72 |

**For mixed-accent calls (Indian rep + US/UK customer):**
Whisper large-v3 + pyannote-audio for diarization, or
AssemblyAI Universal-2 for a lower-ops option.
Sarvam is the best choice only if 90%+ of calls are
Indian/Hinglish with no non-Indian speakers.

**How to implement:** Extract a `TranscriptionClient` abstraction
in `python/utils/transcription_client.py` using the same env-var
pattern as `llm_client.py`:
```
TRANSCRIPTION_PROVIDER=aws      # current
TRANSCRIPTION_PROVIDER=sarvam
TRANSCRIPTION_PROVIDER=openai   # whisper
TRANSCRIPTION_PROVIDER=assemblyai
```
The rest of the pipeline (speaker identification, LLM analysis)
is unchanged — only the normalized transcript format matters.

---

## Dependencies

```
Item 1 (Zoom/Teams)   ← Independent; start immediately
Item 2 (Share)        ← Needs migration 003 only
Item 3 (Download)     ← Independent
Item 4 (Stripe)       ← Independent; benefits from Items 1–3 being stable
Item 5 (UI)           ← Depends on Items 1–4 (uses meeting_platform,
                         Share button, Download button, billing status)
Item 6 (Video)        ← Independent; do last
```

Items 1, 2, 3 can be worked in parallel across sessions.
Item 5 is the only one with explicit dependencies on earlier items.

---

## New Files Summary

| Item | New Files | Key Modified Files |
|------|-----------|--------------------|
| 1 | — | `attendee_utils.py`, `attendee_service.py` |
| 2 | `ShareModal.tsx`, `SharedAnalysisPage.tsx`, `003_share_tokens.sql` | `App.tsx`, `sales_service.py`, `database.py`, `api.ts` |
| 3 | — | `sales_service.py`, `database.py`, `AnalysisView.tsx`, `api.ts` |
| 4 | `stripe_client.py`, `billing_service.py`, `PricingPage.tsx`, `BillingPage.tsx`, `005_billing.sql` | `main.py`, `sales_service.py`, `database.py`, `App.tsx`, `api.ts` |
| 5 | See `UI_FIXES_PLAN.md` | See `UI_FIXES_PLAN.md` |
| 6 | `006_video.sql` | `attendee_service.py`, `sales_service.py`, `database.py`, `AnalysisView.tsx` |
