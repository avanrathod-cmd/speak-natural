# Zoom OAuth Integration Plan

## Context

Zoom's onbehalf token became mandatory on March 2, 2026 for external
meetings. Without it, bots fail with `AUTHRET_JWTTOKENWRONG`. Each
user must connect their Zoom account once; bots then join their
meetings on their behalf via Attendee's `zoom_oauth_connection`.

This follows the same pattern as the existing Google Calendar OAuth
flow (`/attendee/auth/google/init` → callback → stored connection).

---

## Prerequisites (one-time setup, no code)

1. In your Zoom General App (Zoom Developer Portal):
   - Add scopes: `user:read:user`, `user:read:token`
   - Add redirect URI:
     `{BASE_URL}/attendee/auth/zoom/callback`

2. In Attendee dashboard →
   Settings → Credentials → Zoom:
   - Paste Client ID, Client Secret, Webhook Secret

3. In Attendee dashboard → Settings → Webhooks:
   - Add trigger `zoom_oauth_connection.state_change`
     pointing to `{BASE_URL}/attendee/webhook`

---

## Progress

| Task | Status |
|------|--------|
| 1 — DB Migration | ✅ Done |
| 2 — Attendee Utils | ✅ Done |
| 3 — Backend Endpoints | ✅ Done |
| 4 — Bot Scheduling Update | ✅ Done |
| 5 — Frontend | ✅ Done |

> **Note:** The Attendee models refactor (typed `AttendeeWebhookPayload`,
> `AttendeeCalendarEvent`, `AttendeeBotData`) is already applied in
> `attendee_utils.py` and `attendee_service.py`. All code snippets in
> this plan use typed attribute access accordingly.

---

## Task 1 — DB Migration

**File:** `python/migrations/004_zoom_oauth.sql`

```sql
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS zoom_connection_id TEXT;

COMMENT ON COLUMN user_profiles.zoom_connection_id
    IS 'Attendee zoom_oauth_connection ID — required for bots to '
       'join Zoom meetings on behalf of this user';
```

---

## Task 2 — Attendee Utils

**File:** `python/utils/attendee_utils.py`

Add two public functions:

**`create_zoom_oauth_connection(code, redirect_uri) → dict`**

Exchanges a Zoom OAuth authorization code for a connection via
the Attendee API. Returns the created connection object including
its `id` (stored as `zoom_connection_id` on the user profile).

```python
POST {ATTENDEE_BASE_URL}/zoom_oauth_connections
Body: {
    "code": code,
    "redirect_uri": redirect_uri,
}
```

**`get_zoom_oauth_connection(connection_id) → dict`**

Fetches a zoom_oauth_connection by ID. Used to check status
after a `zoom_oauth_connection.state_change` webhook.

```python
GET {ATTENDEE_BASE_URL}/zoom_oauth_connections/{connection_id}
```

---

## Task 3 — Backend Endpoints

**File:** `python/api/attendee_service.py`

### New endpoints

```
GET /attendee/auth/zoom/init
  → {url: "<Zoom OAuth authorization URL>"}
  Builds the Zoom OAuth URL:
    https://zoom.us/oauth/authorize
      ?response_type=code
      &client_id={ZOOM_CLIENT_ID}
      &redirect_uri={ZOOM_REDIRECT_URI}
      &state={signed_state}

GET /attendee/auth/zoom/callback?code=...&state=...
  1. Verify state param (reuse _sign_state/_verify_state pattern)
  2. Call create_zoom_oauth_connection(code, redirect_uri)
  3. Save connection_id to user_profiles via database.py
  4. Redirect to {FRONTEND_URL}/?zoom_connected=true

GET /attendee/zoom/status
  → {connected: bool, connection_id: str | null}
  Reads zoom_connection_id from user_profiles.
```

### Webhook handler update

In the existing `attendee_webhook`, add a handler for
`zoom_oauth_connection.state_change`:

```python
elif trigger == "zoom_oauth_connection.state_change":
    # payload is already AttendeeWebhookPayload (typed)
    state = payload.data.state if payload.data else ""
    if state in ("expired", "revoked", "invalid"):
        connection_id = payload.zoom_oauth_connection_id
        background_tasks.add_task(
            _handle_zoom_connection_invalid,
            connection_id,
            idempotency_key,
        )
```

`_handle_zoom_connection_invalid`: looks up the user by
`zoom_connection_id`, clears it from `user_profiles`, logs a
warning. The user will be prompted to reconnect on next visit.

### New env vars

```
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
ZOOM_REDIRECT_URI={BASE_URL}/attendee/auth/zoom/callback
```

---

## Task 4 — Bot Scheduling Update

**File:** `python/utils/attendee_utils.py` — `schedule_bot_for_event`

When scheduling a bot for a Zoom meeting, pass the user's
`zoom_connection_id` in the payload:

```python
def schedule_bot_for_event(
    calendar_event_id: str,
    webhook_url: str,
    calendar_id: str | None = None,
    zoom_connection_id: str | None = None,   # new
) -> AttendeeBotData:
    payload = { ... }
    if zoom_connection_id:
        payload["zoom_oauth_connection_user_id"] = zoom_connection_id
```

**File:** `python/api/attendee_service.py` — `_schedule_bot_if_needed`

Look up the user by `calendar_id`, fetch their
`zoom_connection_id`, pass it when the platform is `zoom`.
Events are now `AttendeeCalendarEvent` (typed), so use attribute
access throughout:

```python
platform = get_meeting_platform(event)
zoom_connection_id = None
if platform == "zoom":
    user_id = _db.get_user_id_by_calendar_id(calendar_id)
    zoom_connection_id = (
        _db.get_zoom_connection_id(user_id) if user_id else None
    )

bot = schedule_bot_for_event(
    event.id,            # was event["id"]
    webhook_url,
    calendar_id=calendar_id,
    zoom_connection_id=zoom_connection_id,
)
```

If `zoom_connection_id` is None for a Zoom meeting, log a warning
and skip — the user hasn't connected their Zoom account yet.

**File:** `python/api/database.py`

Add:
- `save_zoom_connection_id(user_id, connection_id)`
- `get_zoom_connection_id(user_id) → str | None`
- `get_user_id_by_zoom_connection_id(connection_id) → str | None`
  (needed for the state_change webhook handler)

---

## Task 5 — Frontend

**Files:**
- `ui/wireframe/src/App.tsx`
- `ui/wireframe/src/services/api.ts`

### "Connect Zoom" button

Mirror the existing "Connect Calendar" / "Calendar connected" button
in the dashboard header. Show next to it:

```
[Calendar connected ✓]  [Connect Zoom]   ← not yet connected
[Calendar connected ✓]  [Zoom connected ✓]  ← after connect
```

On click:
1. Call `GET /attendee/auth/zoom/init` → get authorization URL
2. `window.location.href = url` → redirect to Zoom OAuth

On return (`?zoom_connected=true` in URL):
- Set `zoomConnected = true` in state
- Clear the query param from URL

### API methods to add in `api.ts`

```typescript
getZoomStatus(token): Promise<{connected: bool}>
initZoomOAuth(token): Promise<{url: string}>
```

---

## Files Summary

| Task | New Files | Modified Files |
|------|-----------|----------------|
| 1 | `004_zoom_oauth.sql` | — |
| 2 | — | `attendee_utils.py` |
| 3 | — | `attendee_service.py` |
| 4 | — | `attendee_utils.py`, `attendee_service.py`, `database.py` |
| 5 | — | `App.tsx`, `api.ts` |