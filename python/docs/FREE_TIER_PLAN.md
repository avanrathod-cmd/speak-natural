# Free Tier Plan

## Overview

Redesign the free tier so new users get a meaningful taste of the product:
**4 hours of cumulative call analysis**, with Zoom, Google Meet, and Teams
all enabled. No seat-count restriction changes — free stays at 1 seat.

---

## What Changes vs. Current Free Tier

| | Current Free | New Free |
|---|---|---|
| Seats | 1 | 1 (unchanged) |
| Call analysis quota | None (unlimited) | 4 hours cumulative |
| Google Meet bot | ✅ | ✅ (unchanged) |
| Zoom bot | ✅ | ✅ (unchanged) |
| Teams bot | ✅ | ✅ (unchanged) |

The only new enforcement is the **4-hour analysis quota**. All integrations
already work for all plans — no gating needed there.

---

## Critical Prerequisite: Populate `duration_seconds`

The `sales_calls.duration_seconds` column exists in the DB but is **never
populated today**. The quota system cannot work without it.

### For manual uploads (`source='manual'`)
- At upload time, validate the file using `mutagen` before queuing:
  1. File must be a parseable audio/video format.
  2. Duration must be readable (not `None`).
  3. Duration must be ≥ 60 seconds — reject with HTTP 400 if shorter.
- Store `duration_seconds` immediately in `sales_calls`.
- This gives us the duration upfront so we can enforce quota before
  processing begins.

### For Attendee bot recordings (`source='attendee'`)
- The Attendee.dev `bot.state_change` webhook and `AttendeeBotData`
  model do not include recording duration.
- The MP4 is already downloaded before the DB record is created
  (existing flow). Read duration from the local file using `mutagen`
  immediately after the download, before creating the `sales_calls` row.
- Apply the same checks as manual uploads:
  1. File must be parseable by `mutagen` (not malformed/corrupt).
  2. Duration must be readable (not `None`).
  3. Duration must be ≥ 60 seconds.
  - On any failure: create the row with `status='failed'` and an
    appropriate error message.

**Implementation location:**
- Manual upload: `python/api/sales_service.py` — upload endpoint
- Attendee bot: `python/api/attendee_service.py` — `bot.state_change`
  handler (around line 609)

---

## Quota Definition

Define analysis quotas per plan in `python/utils/billing_client.py`
alongside the existing `_PLAN_SEAT_LIMITS`:

```python
_PLAN_ANALYSIS_MINUTES: dict[str, int | None] = {
    "free":      240,   # 4 hours
    "solo":      None,  # unlimited
    "team":      None,  # unlimited
    "unlimited": None,  # unlimited
}
```

`None` = no quota enforced. Only the free plan has a hard cap.

---

## Database Changes

### Migration: add denormalized stats to `organizations`

Add three columns to `organizations` so quota checks and billing status
reads are a single-row lookup with no joins or aggregates:

```sql
ALTER TABLE organizations
  ADD COLUMN minutes_analysed  INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN seats_used        INTEGER NOT NULL DEFAULT 0;
```

| Column | Meaning | Updated when |
|---|---|---|
| `minutes_analysed` | Cumulative minutes of completed + in-flight analysis for this org | Call moves to `processing` (increment); call moves to `failed` (decrement) |
| `seats_used` | Count of `manager` + `rep` rows in `user_profiles` for this org | User joins org (increment); user removed (decrement) |

`plan` is fetched live from `subscriptions` when needed — no duplication.

**Why denormalize onto `organizations` instead of querying live?**
- Quota check runs on every upload and every Attendee webhook — a
  lightweight column read is preferable to a `SUM` over `sales_calls`.
- `seats_used` today requires a `COUNT` join; caching it here simplifies
  the seat-limit check in `team_service.py`.
- `plan` is already on `subscriptions` but joining it into every quota
  check adds unnecessary complexity.

**Keeping columns in sync:**

1. `minutes_analysed`
   - **Increment** in `sales_service.py` / `attendee_service.py` when
     a call row is created with `status='processing'` (convert
     `duration_seconds` to minutes via `floor(duration_seconds / 60)`).
   - **Never decremented** — append-only. If a call fails mid-pipeline,
     Deepgram was already called and real cost was incurred. Quota-blocked
     Attendee calls never increment in the first place.

2. `seats_used`
   - **Increment** in `team_service.py` when an invite is accepted and
     a `manager`/`rep` row is created.
   - **Decrement** when a user is removed from the org.
   - Replace the current `_count_seats()` DB query with a direct read of
     this column.

**Backfill on migration:** Set initial values from existing data:

```sql
UPDATE organizations o
SET
  minutes_analysed = (
    SELECT COALESCE(FLOOR(SUM(duration_seconds) / 60.0), 0)
    FROM   sales_calls
    WHERE  org_id = o.id
      AND  status IN ('processing', 'completed')
  ),
  seats_used = (
    SELECT COUNT(*)
    FROM   user_profiles
    WHERE  org_id = o.id
      AND  role IN ('manager', 'rep')
  );
```

---

## Backend Changes

### Quota helpers in `billing_client.py`

```python
class QuotaExceededError(Exception):
    """Raised when an org's analysis quota would be exceeded."""

def get_analysis_minutes_limit(plan: str) -> int | None:
    """Returns quota in minutes, or None if unlimited."""

def check_analysis_quota(
    plan: str, used_minutes: int, incoming_minutes: int
) -> None:
    """
    Raises QuotaExceededError if used + incoming exceeds the plan
    limit. No-ops if the plan has no limit.
    """
```

`QuotaExceededError` is defined in `billing_client.py`. Service layer
callers (`sales_service.py`, `attendee_service.py`) catch it and
convert to HTTP 402. `used_minutes` comes from `org['minutes_analysed']`;
`plan` from `subscriptions` — both already in context, no extra DB
round-trip.

### Manual upload enforcement (`sales_service.py`)

1. Extract `duration_seconds` from uploaded file using `mutagen`.
2. Convert to minutes: `incoming_minutes = floor(duration_seconds / 60)`.
3. Fetch the `organizations` row (contains `minutes_analysed` and join
   `subscriptions` for `plan`).
4. Call `check_analysis_quota(plan, org['minutes_analysed'], incoming_minutes)`
   — raises `QuotaExceededError` if over limit; catch and convert to
   HTTP 402.
5. Create `sales_calls` row with `duration_seconds` set, `status='processing'`.
6. Increment `organizations.minutes_analysed` by `incoming_minutes`.
7. Queue for processing as normal.

**Error response (HTTP 402):**
```json
{
  "detail": "Free plan limit reached. You have used X h Y min of your
             4-hour analysis quota. Upgrade to continue."
}
```

### Attendee bot enforcement (`attendee_service.py`)

After downloading the MP4 and reading `duration_seconds` via `mutagen`:
1. Convert to minutes: `incoming_minutes = floor(duration_seconds / 60)`.
2. Fetch the `organizations` row (contains `minutes_analysed`) and
   `subscriptions` for `plan`.
3. Call `check_analysis_quota(plan, org['minutes_analysed'], incoming_minutes)`.
4. If over limit: create the `sales_calls` row with `status='failed'` and
   `error='Analysis quota exceeded. Upgrade your plan.'` — so the call
   appears in the UI with a clear reason rather than silently vanishing.
   Do NOT increment `minutes_analysed` (the call won't be analyzed).
5. If within limit: create the row with `status='processing'`, increment
   `minutes_analysed` by `incoming_minutes`, proceed with analysis.

### Seat limit check (`team_service.py`)

Replace the `_count_seats()` query with a direct read of
`organizations.seats_used`. The check becomes:

```python
org = db.get_org(org_id)
if org["seats_used"] >= org_seat_limit:
    raise HTTPException(402, "Seat limit reached...")
```

### Billing status endpoint (`billing_service.py`)

Extend `GET /billing/status` to include:

```json
{
  "plan": "free",
  "analysis_quota_minutes": 240,
  "analysis_used_minutes": 90,
  "analysis_remaining_minutes": 150,
  "seats_used": 1,
  "seat_limit": 1,
  "...existing fields..."
}
```

`plan` from `subscriptions`, `analysis_used_minutes` from
`organizations.minutes_analysed`, `seats_used` from
`organizations.seats_used`, quota limit from `_PLAN_ANALYSIS_MINUTES`.
Paid plans return `analysis_quota_minutes: null`.

Paid plans return `analysis_quota_minutes: null`.

---

## Frontend Changes

### BillingPage.tsx — quota usage bar

Add an analysis usage section below the seat usage bar (free plan only):

```
Call Analysis
[████████░░░░░░░░░░░░] 1h 30m used of 4h 0m
```

- Show hours + minutes (not raw seconds)
- Color: green → yellow at 75% → red at 100%
- Hidden for paid plans (`analysis_quota_minutes === null`)

### Upload gate

If `analysis_remaining_minutes === 0`:
- Disable the upload button
- Show inline message: "You've used your 4-hour free analysis quota.
  Upgrade to continue uploading calls."
- Link to `/pricing`

### Attendee-sourced calls

When a call appears in the dashboard with `status='failed'` and
`error` contains "quota exceeded":
- Show a distinct badge ("Quota reached") instead of the generic
  "Failed" badge
- Tooltip: "This call wasn't analyzed because your free plan quota is
  full. Upgrade to analyze it."

### PricingPage.tsx — free plan card

```
Free
- 4 hours of call analysis
- Zoom, Google Meet & Teams integrations
- 1 seat
```

---

## Implementation Phases

### Phase 1 — Duration population (prerequisite)
1. Add `mutagen` to `pyproject.toml`
2. Populate `duration_seconds` on manual upload in `sales_service.py`
3. Populate `duration_seconds` from Attendee webhook in `attendee_service.py`

### Phase 2 — DB migration
4. Write migration to add `minutes_analysed` and `seats_used`
   to `organizations`, including the backfill `UPDATE`

### Phase 3 — Backend enforcement
5. Add `_PLAN_ANALYSIS_MINUTES` and quota helpers to `billing_client.py`
6. Enforce at manual upload (HTTP 402 before queuing) + increment counter
7. Enforce at Attendee webhook (fail gracefully) + increment counter
8. Sync `seats_used` on invite acceptance and user removal
9. Extend `GET /billing/status` response with new quota fields

### Phase 4 — UI
11. Add analysis quota bar to `BillingPage.tsx`
12. Disable upload + show upgrade prompt when quota is exhausted
13. Add "Quota reached" badge for Attendee calls blocked by quota
14. Update `PricingPage.tsx` free plan card copy

---

## Testing

### Setup

Add to `pyproject.toml` as dev dependencies:
- `pytest` — test runner
- `httpx` — required by FastAPI `TestClient`

**DB strategy:** mock `DatabaseService` methods with `unittest.mock`.
Fast, no infra needed, appropriate for early stage. Migrate to an
in-memory fake when the system grows, then a full dev environment.

**File validation strategy:** mock `mutagen.File` to return controlled
`info.length` values. No fixture files — we're testing our logic, not
mutagen's parsing.

**Network strategy:** mock `requests.get` (Attendee MP4 download) to
write dummy bytes to disk. Tests must be fully hermetic — no network,
no real DB, no real files.

**Test location:** `python/tests/` directory, one file per service:
- `tests/test_billing_client.py`
- `tests/test_sales_service.py`
- `tests/test_attendee_service.py`

### Behaviors to test (in order)

#### 1. Quota helpers (`billing_client.py`) — pure logic, no mocks needed

| Behavior | Expected |
|---|---|
| `get_analysis_minutes_limit('free')` | `240` |
| `get_analysis_minutes_limit('solo')` | `None` |
| `check_analysis_quota('free', 200, 30)` | passes (230 < 240) |
| `check_analysis_quota('free', 230, 20)` | raises HTTP 402 (250 > 240) |
| `check_analysis_quota('free', 240, 0)` | raises HTTP 402 (at limit) |
| `check_analysis_quota('solo', 99999, 100)` | passes (unlimited) |

#### 2. File validation (`sales_service.py`) — via FastAPI `TestClient`

| Behavior | Expected |
|---|---|
| Upload malformed file | HTTP 400 |
| Upload valid file < 60s | HTTP 400 |
| Upload valid file ≥ 60s, under quota | HTTP 200, call created |

#### 3. Upload quota enforcement (`sales_service.py`)

| Behavior | Expected |
|---|---|
| Upload when `minutes_analysed` at limit | HTTP 402 |
| Upload when under quota | `minutes_analysed` incremented |

#### 4. Attendee bot enforcement (`attendee_service.py`)

| Behavior | Expected |
|---|---|
| Bot recording < 60s | `sales_calls` row with `status='failed'` |
| Bot recording malformed | `sales_calls` row with `status='failed'` |
| Bot recording over quota | `sales_calls` row with `status='failed'`, quota error |
| Bot recording valid + under quota | `sales_calls` row with `status='processing'` |

---

## Decisions

1. **Quota reset:** Lifetime cap (not monthly). Free tier is for product
   evaluation only; monthly reset can be revisited once the product has
   traction and funding.

2. **Attendee duration source:** Read from the downloaded MP4 using
   `mutagen` — the webhook and `AttendeeBotData` model provide no duration
   field. No extra download needed; the MP4 is already fetched before the
   DB record is created.

3. **Over-quota Attendee calls:** Reject the whole call. Create the
   `sales_calls` row with `status='failed'` and a quota error message.
   Partial analysis would produce misleading scores.

4. **Backfill existing calls:** Accept 0 for historical usage. Existing
   calls have `duration_seconds = NULL`, so the backfill SQL naturally
   produces 0 via `COALESCE`. No S3 re-reading required. Existing users
   get a grace period on past calls; the cap applies going forward only.
