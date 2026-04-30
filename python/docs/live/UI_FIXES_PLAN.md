# SpeakNatural — UI Fixes Plan

_Full plan for GO_LIVE_PLAN.md Item 5 — UI Fixes + Dashboard._

---

## Overview

| # | Feature | Status |
|---|---------|--------|
| A | LLM-generated call names (inline-editable) | ⬜ Not started |
| B | Profile page (move calendar/Zoom integrations out of header) | ⬜ Not started |
| E | Rep column fix | ⬜ Not started |
| G | AI-generated call summary (dashboard column) | ⬜ Not started |

---

## Feature A — LLM-Generated Call Names

### Problem

Calls are identified only by `audio_filename` (e.g.
`gmeet_bot_recording_20240415.wav`). For bot-joined calls there is no
meaningful filename at all. Users have no way to tell calls apart in
the dashboard.

### Goal

- Auto-generate a short, human-readable name for each call during
  analysis (e.g. "Acme Corp Discovery — Apr 15").
- Let users rename calls inline with a single click.

### Alternatives Considered

**A1 — Parse filename only, no LLM (rejected)**
Works for manually uploaded files if the user named them well.
Completely useless for bot-joined calls where the filename is a
timestamp or UUID. Not worth the complexity of partial coverage.

**A2 — Use calendar event title as call name (chosen for bot-joined calls)**
For bot-joined calls the Attendee webhook payload includes the
calendar event title — that is the most accurate name since it
reflects what the user actually put in their calendar. Store this
title in `sales_calls.call_name` at bot scheduling time (in
`attendee_service.py`) so it is available before analysis completes.
LLM name generation (below) is the fallback for manual uploads and
any bot call where the event title is missing or generic.

**A3 — User sets name at upload time (rejected)**
Puts burden on the user before they know what the call was about.
Most uploads are drag-and-drop; adding a required name field
degrades the upload UX.

### What to build

#### A1 — DB Migration

```sql
-- migrations/006_call_name.sql
ALTER TABLE sales_calls ADD COLUMN call_name TEXT;
```

Nullable — existing rows have no name; the display layer falls back
to the formatted filename.

#### A2 — Name Population Strategy

For **bot-joined calls**: store the calendar event title into
`call_name` when the bot is scheduled in `attendee_service.py`.
This runs before analysis — the name is visible in the dashboard
immediately, not after a multi-minute pipeline.

For **manual uploads** (and bot calls with no useful event title):
run the LLM fallback below inside `_analyze_call` after analysis
completes.

#### A3 — LLM Name Generation (fallback)

Add `call_name` as an additional field in the existing main analysis
LLM prompt rather than a separate call. The transcript is already
being sent — this adds ~10 output tokens at zero extra cost.

Extend the existing analysis response schema to include:

```python
call_name: str  # 4–8 words, title case, e.g. "Acme Corp Discovery — Apr 15"
```

Instruction to add to the existing prompt:

```
Also return a "call_name": a 4–8 word title-case label for this call.
Format: "<Company or topic> — <Month Day>" if a company is identifiable,
otherwise "<Topic> — <Month Day>".
Examples: "Acme Corp Discovery — Apr 15", "Pricing Objections — Mar 3"
```

Store via `update_call_name(call_id, name)` in `database.py`.

#### A3 — PATCH Endpoint

Add to `sales_service.py`:

```
PATCH /sales/calls/{call_id}
Body: {"call_name": "New Name"}
Auth: required (must own the call)
Response: 200 {"call_id": "...", "call_name": "New Name"}
```

Validation: `call_name` max 100 chars, strip whitespace.

Add `update_call_name(call_id, name, rep_id)` to `database.py` —
update only if `rep_id` matches (ownership check).

Add `CallUpdateRequest` and `CallUpdateResponse` models to
`models.py`.

#### A4 — Frontend Inline Edit

**CallDashboard.tsx:**

- Replace `formatCallTitle(call)` with `call.call_name ??
  formatCallTitle(call)` for display.
- On click of the call name cell: render an `<input>` pre-filled
  with current name.
- On blur or Enter: `PATCH /sales/calls/{id}` → optimistic update.
- On Escape: revert.
- Show a small pencil icon on row hover to signal editability.

**AnalysisView.tsx:**

- Same inline-edit pattern in the blue banner title.

**types/index.ts:** Add `call_name?: string` to
`SalesCallListItem` and `SalesCallAnalysis`.

**services/api.ts:** Add `updateCall(callId, patch)` →
`PATCH /sales/calls/{callId}`.

### Files to create/modify

| File | Change |
|------|--------|
| `python/migrations/006_call_name.sql` | New migration |
| `python/api/models.py` | `CallUpdateRequest`, `CallUpdateResponse` |
| `python/api/database.py` | `update_call_name()`, `_generate_call_name()` helper |
| `python/api/sales_service.py` | `PATCH` endpoint, call name generation in pipeline |
| `ui/wireframe/src/types/index.ts` | `call_name` field |
| `ui/wireframe/src/services/api.ts` | `updateCall()` |
| `ui/wireframe/src/components/CallDashboard.tsx` | Inline edit |
| `ui/wireframe/src/components/AnalysisView.tsx` | Inline edit in banner |

### Test

1. Upload a call → after analysis, call name appears in dashboard
   (not the raw filename).
2. Click name → input appears, type new name → blur → name persists
   on refresh.
3. Escape reverts.
4. Bot-joined call: name is generated from transcript, not filename.

---

## Feature B — Profile Page

### Problem

"Connect Calendar" and "Connect Zoom" buttons live in the main
app header. This is visually noisy on the dashboard, and there is
no dedicated place to see account information or manage integrations.

### Goal

- Move calendar and Zoom integration status/controls to a
  `/profile` page.
- Header gets a compact profile icon (avatar initials or icon)
  linking to `/profile`.
- Profile page shows: user email, Google Calendar status, Zoom
  status, sign-out.

### Alternatives Considered

**B1 — Settings modal instead of a page (rejected)**
A modal is fine for two settings but will feel cramped as we add
billing status, notification preferences, etc. A full page is the
correct long-term pattern; cost is the same now.

**B2 — Keep integrations in header but make them smaller (rejected)**
The header is prime real estate. Integrations are a one-time setup
action, not something users interact with on every session. They
belong in a settings context, not persistent chrome.

### What to build

#### B1 — ProfilePage.tsx (new)

Route: `/profile` — auth-guarded (same guard as dashboard).

**Layout:**

```
┌─────────────────────────────────────────────┐
│  ← Back to Dashboard                        │
│                                             │
│  Profile                                    │
│  ─────────────────────────────────────────  │
│  Email       avanrathod@gmail.com           │
│                                             │
│  Integrations                               │
│  ─────────────────────────────────────────  │
│  Google Calendar                            │
│  [● Connected]  [Disconnect]                │
│  or                                         │
│  [Connect Google Calendar]                  │
│                                             │
│  Zoom                                       │
│  [● Connected]  [Disconnect]                │
│  or                                         │
│  [Connect Zoom]                             │
│                                             │
│  ─────────────────────────────────────────  │
│  [Sign out]                                 │
└─────────────────────────────────────────────┘
```

State: reads `calendarLinked` and `zoomLinked` from the same
existing API calls (`/attendee/status`, `/attendee/auth/zoom/status`).
Move the `handleLinkCalendar` and `handleConnectZoom` logic from
`App.tsx` into `ProfilePage.tsx`.

#### B2 — Header Cleanup (App.tsx)

Remove: "Connect Calendar" button, "Calendar connected" badge,
"Connect Zoom" button from the header.

Add: profile icon button (user initials or a person icon) that
navigates to `/profile`. Place it to the left of the existing
"Sign out" area, or replace the sign-out button entirely (sign-out
moves to the profile page).

#### B3 — Routing (App.tsx)

Add `/profile` to the authenticated routes alongside `/dashboard`.
Pass `user` and `supabase` as props to `ProfilePage`.

### Files to create/modify

| File | Change |
|------|--------|
| `ui/wireframe/src/pages/ProfilePage.tsx` | New page |
| `ui/wireframe/src/App.tsx` | Add route, remove header buttons, add profile icon |

### Test

1. Open dashboard → header shows profile icon, no integration
   buttons.
2. Click profile icon → `/profile` page loads with correct email.
3. Calendar not connected → "Connect Google Calendar" button works
   (OAuth flow unchanged).
4. Calendar connected → shows "Connected" badge + Disconnect option.
5. Same for Zoom.
6. Sign out from profile page works.

---

## Feature E — Rep Column Fix

The "Rep" column currently shows "—" for every call. Extract a
display name from `audio_filename` (e.g. `john_smith_2024.wav` →
"John Smith"). Fall back to "Unknown Rep".

### Files to modify

- `ui/wireframe/src/components/CallDashboard.tsx`

---

## Feature G — AI-Generated Call Summary Column

### Problem

The dashboard rows show scores and metadata but give no hint of
what the call was actually about. Users who want to find a specific
call have to open each one individually.

### Goal

Add a short (1–2 sentence) summary to each dashboard row so users
can instantly recall the call without opening it. Example:
_"Discovery call with a logistics firm interested in team pricing.
Main objection was integration complexity with their CRM."_

### What to build

#### G1 — DB Column

Add to the same migration as call names (or a separate one):

```sql
ALTER TABLE sales_calls ADD COLUMN call_summary TEXT;
```

Nullable — generated during analysis, empty for pre-existing calls.

#### G2 — LLM Summary Generation

Add `call_summary` to the same existing analysis LLM call as the
name (Feature A). Both fields ride on the transcript that is already
being sent — no extra cost, no extra latency.

Extend the analysis response schema:

```python
call_summary: str  # 1–2 sentences, plain English
```

Instruction to add to the existing prompt:

```
Also return a "call_summary": 1–2 sentences for a CRM dashboard.
Cover who the prospect is (company/role if mentioned), the main
topic, and the key outcome or next step. Factual, no filler.
```

Store via `update_call_summary(call_id, summary)` in `database.py`.

#### G3 — API + Models

Include `call_summary` in `CallListItemResponse` (models.py) and
the `GET /sales/calls` DB query so it is returned in the dashboard
list without an extra API call.

#### G4 — Frontend Dashboard Column

Add a "Summary" column to `CallDashboard.tsx`:

```
┌─────────────────────────────────┬──────┬──────┬──────────────────────────────────────┐
│ Call Name                       │ Date │ Rep  │ Summary                              │
├─────────────────────────────────┼──────┼──────┼──────────────────────────────────────┤
│ Acme Corp Discovery — Apr 15    │ ...  │ ...  │ Discovery with Acme logistics; main  │
│                                 │      │      │ concern was CRM integration.          │
└─────────────────────────────────┴──────┴──────┴──────────────────────────────────────┘
```

- Column is truncated with ellipsis if too long; full text on hover
  via `title` attribute (no tooltip library needed).
- Falls back to empty/`—` for calls that predate this feature.
- On smaller viewports, Summary column is hidden (same breakpoint
  as the existing score columns).

### Files to create/modify

| File | Change |
|------|--------|
| `python/migrations/006_call_name.sql` | Add `call_summary TEXT` column (alongside `call_name`) |
| `python/api/models.py` | `call_summary` in `CallListItemResponse` |
| `python/api/database.py` | `update_call_summary()`, include in list query |
| `python/api/sales_service.py` | Summary generation in analysis pipeline |
| `ui/wireframe/src/types/index.ts` | `call_summary?: string` in `SalesCallListItem` |
| `ui/wireframe/src/components/CallDashboard.tsx` | Summary column |

### Test

1. Analyze a call → summary appears in dashboard row.
2. Long summary truncates with ellipsis; hover shows full text.
3. Pre-existing calls show `—` without errors.

---

## Dependencies

Features B and E are frontend-only. Features A and G share a
migration and both run during analysis — implement together.

```
A + G (call names + summary)  ← share migration 006_call_name.sql;
                                 implement pipeline changes together
B (profile)                   ← frontend-only
E (rep column)                ← frontend-only
```

Suggested order: **B + E in parallel → A+G together**.

---

## New Files Summary

| Feature | New Files | Key Modified Files |
|---------|-----------|--------------------|
| A + G | `006_call_name.sql` | `sales_service.py`, `database.py`, `models.py`, `CallDashboard.tsx`, `AnalysisView.tsx`, `types/index.ts`, `api.ts` |
| B | `pages/ProfilePage.tsx` | `App.tsx` |
| C–F | — | `CallDashboard.tsx`, `AnalysisView.tsx` |