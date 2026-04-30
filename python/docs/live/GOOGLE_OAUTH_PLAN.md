# Google Calendar OAuth Flow — Implementation Plan

## Context

The current calendar linking flow asks users for their Google OAuth `refresh_token`,
`client_id`, and `client_secret` directly in a form — these are developer credentials
that regular users don't have. The fix is a standard OAuth2 authorization code flow:
user clicks "Connect Google Calendar", gets redirected to Google's consent screen,
grants permission, and is redirected back. The backend handles the code exchange and
stores the refresh token automatically. Zero credentials entered by the user.

---

## Flow

```
User clicks "Connect Google Calendar"
  → GET /attendee/auth/google/init  (authenticated, returns google_oauth_url)
  → Frontend redirects browser to google_oauth_url
  → User clicks "Allow" on Google consent screen
  → Google redirects to GET /attendee/auth/google/callback?code=xxx&state=yyy
  → Backend verifies state, exchanges code for refresh_token
  → Backend calls link_google_calendar() with the refresh_token
  → Backend redirects to {FRONTEND_URL}/?calendar_linked=true
  → Frontend detects query param, refreshes status badge
```

---

## Implementation

### Task 1 — Add dependency

Add `google-auth-oauthlib` to `python/pyproject.toml`:
```toml
"google-auth-oauthlib>=1.2.0",
```

Run `uv add google-auth-oauthlib`.

---

### Task 2 — New env vars

Add to `python/.env`:
```
GOOGLE_REDIRECT_URI={BASE_URL}/attendee/auth/google/callback
FRONTEND_URL=http://localhost:5173          # or production frontend URL
OAUTH_STATE_SECRET=<random-32-char-string>  # for signing state param
```

`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are already set.

---

### Task 3 — Backend: two new endpoints in `python/api/attendee_service.py`

**`GET /attendee/auth/google/init`** (requires `get_current_user`):
```python
from google_auth_oauthlib.flow import Flow

@attendee_router.get("/auth/google/init")
async def google_auth_init(user: dict = Depends(get_current_user)):
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=_sign_state(user["user_id"]),
    )
    return {"url": auth_url}
```

**`GET /attendee/auth/google/callback`** (public — called by Google):
```python
@attendee_router.get("/auth/google/callback")
async def google_auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str,
    state: str,
):
    user_id = _verify_state(state)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens
    flow = Flow.from_client_config(...)
    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token
    user_email = _db.get_user_email(user_id)

    # Link calendar (existing function, unchanged)
    calendar_data = link_google_calendar(
        refresh_token=refresh_token,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        user_email=user_email,
    )
    _db.save_attendee_calendar_id(user_id, calendar_data["id"])

    # Register webhook + schedule existing bots (background)
    background_tasks.add_task(_post_link_setup, user_id, calendar_data["id"])

    # Redirect back to frontend
    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"{FRONTEND_URL}/?calendar_linked=true")
```

**State signing helpers** (HMAC-SHA256, 10-min expiry):
```python
def _sign_state(user_id: str) -> str:
    payload = f"{user_id}:{int(time.time())}"
    sig = hmac.new(OAUTH_STATE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return b64encode(f"{payload}:{sig}".encode()).decode()

def _verify_state(state: str) -> str | None:
    # Decode, check sig, check expiry (< 10 min), return user_id or None
```

**`_post_link_setup` background task** (extracts existing setup logic from `/link`):
```python
def _post_link_setup(user_id: str, calendar_id: str) -> None:
    webhook_url = f"{_BASE_URL}/attendee/webhook"
    try:
        register_calendar_webhook(webhook_url)
    except requests.HTTPError as e:
        logger.warning(...)
    existing = schedule_existing_upcoming_meets(calendar_id, webhook_url)
    logger.info("Scheduled %d bots for existing meetings", len(existing))
```

---

### Task 4 — DB: add `get_user_email` to `python/api/database.py`

The email is in the JWT during normal requests, but the OAuth callback has no JWT.
Fetch from Supabase admin API using the service role key:

```python
def get_user_email(self, user_id: str) -> str | None:
    resp = self._supabase.auth.admin.get_user_by_id(user_id)
    return resp.user.email if resp.user else None
```

---

### Task 5 — Keep `/attendee/link` for backwards compatibility

The existing `POST /attendee/link` endpoint stays unchanged — useful for dev/CLI
use. No removal needed.

---

### Task 6 — Frontend: `ui/wireframe/src/App.tsx`

Replace the manual-credentials modal with a redirect-based flow:

1. Remove the modal with `refresh_token`, `client_id`, `client_secret` fields
   and related state (`showCalendarModal`, `calendarForm`)
2. Replace `handleLinkCalendar` with:
```typescript
const handleLinkCalendar = async () => {
  const token = await getAccessToken();
  const resp = await fetch('/attendee/auth/google/init', {
    headers: { Authorization: `Bearer ${token}` },
  });
  const { url } = await resp.json();
  window.location.href = url;  // full browser redirect to Google
};
```
3. On app mount, check for `?calendar_linked=true` → call `fetchCalendarStatus()`,
   then remove param from URL with `window.history.replaceState`.

---

## Files Changed

| Task | File | Change |
|---|---|---|
| 1 | `python/pyproject.toml` | Add `google-auth-oauthlib` |
| 2 | `python/.env` | Add `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`, `OAUTH_STATE_SECRET` |
| 3 | `python/api/attendee_service.py` | Add `/auth/google/init`, `/auth/google/callback`, state helpers, `_post_link_setup` |
| 4 | `python/api/database.py` | Add `get_user_email` |
| 6 | `ui/wireframe/src/App.tsx` | Replace modal with redirect button + callback param handling |

---

## Google Cloud Console Setup (one-time, manual)

Add to Authorized Redirect URIs on the OAuth client:
```
{BASE_URL}/attendee/auth/google/callback
```

In production, add the stable domain URL too.

---

## Verification

```bash
# 1. uv add google-auth-oauthlib
# 2. Set GOOGLE_REDIRECT_URI, FRONTEND_URL, OAUTH_STATE_SECRET in .env
# 3. Add redirect URI to Google Cloud Console
# 4. Start server + tunnel

# 5. Click "Connect Google Calendar" in UI
#    → redirected to Google consent screen
#    → after Allow, redirected to frontend /?calendar_linked=true
#    → "Calendar connected" badge appears

# 6. Check server logs:
#    "Linked Attendee calendar for user ... (calendar_id=...)"
#    "Scheduled N bots for existing meetings"
```