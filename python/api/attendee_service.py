"""
Attendee.dev integration endpoints.

Routes (mounted at /attendee in main.py):
    GET  /attendee/auth/google/init      — start Google OAuth flow
    GET  /attendee/auth/google/callback  — handle Google OAuth callback
    POST /attendee/link     — link Google Calendar (dev/CLI use)
    GET  /attendee/status   — check calendar link status
    POST /attendee/webhook  — receive events from Attendee:
                                calendar.events_update → schedule bot
                                bot.state_change (post_processing_completed)
                                  → download + analyze recording
"""

import hashlib
import hmac
import json
import logging
import os
import shutil
import time
import uuid
from base64 import b64decode, b64encode
from os.path import basename

import requests
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from api.auth import get_current_user
from api.database import SalesDatabaseService
from services.audio_processor import ensure_wav_format
from services.sales_call_processor import SalesCallProcessorService
from models.attendee import AttendeeWebhookPayload
from utils.attendee_utils import (
    get_meeting_platform,
    get_bot,
    get_calendar_events,
    create_zoom_oauth_connection,
    link_google_calendar,
    register_calendar_webhook,
    schedule_bot_for_event,
    schedule_existing_upcoming_meets,
    update_calendar_credentials,
)

logger = logging.getLogger(__name__)

attendee_router = APIRouter(tags=["Attendee"])

_db = SalesDatabaseService()
_processor = SalesCallProcessorService()

_UPLOAD_DIR = "/tmp/speak-right-sales"
_WEBHOOK_SECRET = os.getenv("ATTENDEE_WEBHOOK_SECRET", "")
_BASE_URL = os.getenv("BASE_URL", "")
_GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
_FRONTEND_URL = os.getenv("FRONTEND_URL", "")
_OAUTH_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "")
_ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID", "")
_ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET", "")
_ZOOM_REDIRECT_URI = os.getenv("ZOOM_REDIRECT_URI", "")

_GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": _GOOGLE_CLIENT_ID,
        "client_secret": _GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@attendee_router.get("/auth/google/init")
async def google_auth_init(user: dict = Depends(get_current_user)):
    """
    Start the Google OAuth flow.

    Returns a Google authorization URL. The frontend should redirect
    the browser to this URL. After the user grants permission, Google
    redirects to /attendee/auth/google/callback.
    """
    flow = Flow.from_client_config(
        _GOOGLE_CLIENT_CONFIG,
        scopes=_GOOGLE_SCOPES,
        redirect_uri=_GOOGLE_REDIRECT_URI,
    )
    # Generate PKCE verifier before building the auth URL so we can
    # carry it through the state param to the callback.
    import secrets as _secrets
    code_verifier = _secrets.token_urlsafe(64)
    flow.code_verifier = code_verifier

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=_sign_state(user["user_id"], code_verifier),
    )
    return {"url": auth_url}


@attendee_router.get("/auth/google/callback")
async def google_auth_callback(
    background_tasks: BackgroundTasks,
    code: str,
    state: str,
):
    """
    Handle the Google OAuth callback.

    Called by Google after the user grants permission. Exchanges the
    authorization code for a refresh token, links the calendar, and
    redirects the user back to the frontend.
    """
    result = _verify_state(state)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    user_id, code_verifier = result

    flow = Flow.from_client_config(
        _GOOGLE_CLIENT_CONFIG,
        scopes=_GOOGLE_SCOPES,
        redirect_uri=_GOOGLE_REDIRECT_URI,
        state=state,
    )
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google did not return a refresh token. "
                "Revoke app access at myaccount.google.com and try again."
            ),
        )

    user_email = _db.get_user_email(user_id)
    if not user_email:
        raise HTTPException(status_code=400, detail="User not found")

    try:
        calendar_data = link_google_calendar(
            refresh_token=refresh_token,
            client_id=_GOOGLE_CLIENT_ID,
            client_secret=_GOOGLE_CLIENT_SECRET,
            user_email=user_email,
        )
    except requests.HTTPError as e:
        error_body = e.response.json() if e.response.content else {}
        if error_body.get("deduplication_key"):
            # Calendar already exists on Attendee — push the new
            # refresh token so Attendee can reconnect.
            existing_id = _db.get_attendee_calendar_id(user_id)
            if existing_id:
                try:
                    update_calendar_credentials(
                        calendar_id=existing_id,
                        refresh_token=refresh_token,
                        client_secret=_GOOGLE_CLIENT_SECRET,
                    )
                    logger.info(
                        "Updated credentials for calendar %s "
                        "(user %s)",
                        existing_id,
                        user_id,
                    )
                except requests.HTTPError as patch_err:
                    logger.error(
                        "Failed to update calendar credentials "
                        "for %s: %s",
                        existing_id,
                        patch_err.response.text,
                    )
            return RedirectResponse(
                f"{_FRONTEND_URL}/?calendar_linked=true"
            )
        raise HTTPException(
            status_code=502,
            detail=f"Attendee calendar link failed: {e.response.text}",
        )

    calendar_id = calendar_data["id"]
    _db.save_attendee_calendar_id(user_id, calendar_id)
    logger.info(
        "Linked calendar for user %s via OAuth (calendar_id=%s)",
        user_id,
        calendar_id,
    )

    background_tasks.add_task(_post_link_setup, calendar_id)
    return RedirectResponse(f"{_FRONTEND_URL}/?calendar_linked=true")


@attendee_router.get("/auth/zoom/init")
async def zoom_auth_init(user: dict = Depends(get_current_user)):
    """
    Start the Zoom OAuth flow.

    Returns a Zoom authorization URL. The frontend redirects the
    browser there; after the user grants permission Zoom redirects
    to /attendee/auth/zoom/callback.
    """
    if not _ZOOM_CLIENT_ID or not _ZOOM_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="ZOOM_CLIENT_ID / ZOOM_REDIRECT_URI not configured",
        )
    state = _sign_state(user["user_id"], "")
    from urllib.parse import urlencode
    params = urlencode({
        "response_type": "code",
        "client_id": _ZOOM_CLIENT_ID,
        "redirect_uri": _ZOOM_REDIRECT_URI,
        "state": state,
        "scope": " ".join([
            "user:read:user",
            "user:read:token",
            "user:read:zak",
            "meeting:read:list_meetings",
            "meeting:read:local_recording_token",
        ]),
    })
    return {"url": f"https://zoom.us/oauth/authorize?{params}"}


@attendee_router.get("/auth/zoom/callback")
async def zoom_auth_callback(code: str, state: str):
    """
    Handle the Zoom OAuth callback.

    Exchanges the authorization code for an Attendee
    zoom_oauth_connection, saves the connection ID, then redirects
    the user back to the frontend.
    """
    result = _verify_state(state)
    if not result:
        raise HTTPException(
            status_code=400, detail="Invalid or expired state"
        )
    user_id, _ = result  # no code_verifier needed for Zoom

    try:
        connection = create_zoom_oauth_connection(
            code=code,
            redirect_uri=_ZOOM_REDIRECT_URI,
        )
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Attendee Zoom connection failed: {e.response.text}"
            ),
        )

    connection_id = connection["id"]
    _db.save_zoom_connection_id(user_id, connection_id)
    logger.info(
        "Linked Zoom connection for user %s (connection_id=%s)",
        user_id,
        connection_id,
    )

    return RedirectResponse(f"{_FRONTEND_URL}/?zoom_connected=true")


@attendee_router.get("/zoom/status")
async def get_zoom_status(user: dict = Depends(get_current_user)):
    """Return whether the user has a linked Zoom connection."""
    connection_id = _db.get_zoom_connection_id(user["user_id"])
    return {
        "connected": connection_id is not None,
        "connection_id": connection_id,
    }


@attendee_router.post("/link")
async def link_calendar(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Link the user's Google Calendar to Attendee.dev.

    On success:
    - Saves the Attendee calendar ID to the user's profile
    - Registers a project-level calendar.events_update webhook so
      future meetings are picked up automatically
    - Schedules bots for any Google Meet events that already exist

    Body: {refresh_token, client_id, client_secret}
    """
    data = await request.json()
    refresh_token = data.get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    if not all([refresh_token, client_id, client_secret]):
        raise HTTPException(
            status_code=400,
            detail=(
                "refresh_token, client_id, and client_secret "
                "are required"
            ),
        )

    if not _BASE_URL:
        raise HTTPException(
            status_code=500,
            detail="BASE_URL env var not set",
        )

    user_id = user["user_id"]
    user_email = user.get("email", user_id)
    webhook_url = f"{_BASE_URL}/attendee/webhook"

    try:
        calendar_data = link_google_calendar(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            user_email=user_email,
        )
        logger.info(
            "Linked Attendee calendar for user %s (calendar_id=%s)",
            user_id,
            calendar_data.get("id"),
        )
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Attendee calendar link failed: {e.response.text}",
        )

    calendar_id = calendar_data.get("id")
    _db.save_attendee_calendar_id(user_id, calendar_id)

    # Register webhook for future calendar events.
    # Attendee's API may not support programmatic webhook registration
    # on all plans — if this fails, register manually in the Attendee
    # dashboard: Settings → Webhooks → add trigger "calendar.events_update"
    # pointing to {BASE_URL}/attendee/webhook.
    try:
        register_calendar_webhook(webhook_url)
        logger.info(
            "Registered calendar webhook for user %s: %s",
            user_id,
            webhook_url,
        )
    except requests.HTTPError as e:
        logger.warning(
            "Auto-registration of calendar.events_update webhook failed "
            "(%s). Register manually in the Attendee dashboard → "
            "Settings → Webhooks → URL: %s",
            e.response.text,
            webhook_url,
        )

    # Schedule bots for meetings that already exist
    existing = schedule_existing_upcoming_meets(calendar_id, webhook_url)
    logger.info(
        "Scheduled %d bots for existing meetings (calendar %s)",
        len(existing),
        calendar_id,
    )

    return {
        "calendar_id": calendar_id,
        "status": "linked",
        "bots_scheduled_for_existing": len(existing),
    }


@attendee_router.get("/status")
async def get_status(user: dict = Depends(get_current_user)):
    """Return whether the user has a linked Attendee calendar."""
    calendar_id = _db.get_attendee_calendar_id(user["user_id"])
    return {
        "linked": calendar_id is not None,
        "calendar_id": calendar_id,
    }


@attendee_router.post("/webhook")
async def attendee_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive bot and calendar events from Attendee.dev.

    Handles two triggers:
    - calendar.events_update: new/updated calendar event →
        schedule a bot if it's a Google Meet without one
    - bot.state_change (post_processing_completed): recording ready →
        download, convert, upload to S3, run full analysis pipeline

    Security: validates X-Webhook-Signature (HMAC-SHA256).
    Idempotency: skips payloads whose idempotency_key was already
    processed (Attendee retries up to 3 times on non-2xx).

    Always returns 200 — Attendee treats non-2xx as a delivery failure
    and retries with exponential backoff.
    """
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")

    if not _verify_signature(body, signature):
        logger.warning(
            "Webhook signature mismatch — allowing in dev "
            "(received=%r)", signature
        )

    payload = AttendeeWebhookPayload.model_validate(json.loads(body))
    trigger = payload.trigger
    idempotency_key = payload.idempotency_key

    if _db.is_webhook_key_processed(idempotency_key):
        logger.info(
            "Duplicate webhook delivery %s — skipping", idempotency_key
        )
        return {"ok": True}

    if trigger == "calendar.events_update":
        background_tasks.add_task(
            _schedule_bot_if_needed, payload, idempotency_key
        )

    elif trigger == "bot.state_change":
        event_type = payload.data.event_type if payload.data else ""
        if event_type == "post_processing_completed":
            bot_id = payload.bot_id
            if bot_id:
                background_tasks.add_task(
                    _ingest_and_analyze_recording,
                    bot_id,
                    idempotency_key,
                )

    elif trigger == "zoom_oauth_connection.state_change":
        state = payload.data.state if payload.data else ""
        if state in ("expired", "revoked", "invalid"):
            connection_id = payload.zoom_oauth_connection_id
            if connection_id:
                background_tasks.add_task(
                    _handle_zoom_connection_invalid,
                    connection_id,
                    idempotency_key,
                )

    return {"ok": True}


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

def _schedule_bot_if_needed(
    payload: AttendeeWebhookPayload,
    idempotency_key: str,
) -> None:
    """
    Schedule bots for any new Google Meet events on the calendar.

    The calendar.events_update payload contains NO event data — only
    a sync notification. We fetch the actual events from the Attendee
    API and schedule a bot for any Google Meet without one.
    """
    if not _BASE_URL:
        logger.error("BASE_URL not set — cannot schedule bot")
        return

    calendar_id = payload.calendar_id
    if not calendar_id:
        _db.mark_webhook_key_processed(idempotency_key)
        return

    try:
        events = get_calendar_events(calendar_id)
    except requests.HTTPError as e:
        logger.error(
            "Failed to fetch calendar events for %s: %s",
            calendar_id,
            e.response.text,
        )
        _db.mark_webhook_key_processed(idempotency_key)
        return

    webhook_url = f"{_BASE_URL}/attendee/webhook"
    scheduled = 0
    for event in events:
        if not get_meeting_platform(event) or event.bots:
            continue

        try:
            bot = schedule_bot_for_event(
                event.id,
                webhook_url,
                calendar_id=calendar_id,
            )
            logger.info(
                "Scheduled bot %s for event '%s'",
                bot.id,
                event.name or event.id,
            )
            scheduled += 1
        except requests.HTTPError as e:
            logger.error(
                "Failed to schedule bot for event %s: %s",
                event.id,
                e.response.text,
            )

    if scheduled == 0:
        logger.info(
            "calendar.events_update for %s — no new Google Meets to schedule",
            calendar_id,
        )

    _db.mark_webhook_key_processed(idempotency_key)


def _ingest_and_analyze_recording(
    bot_id: str,
    idempotency_key: str,
) -> None:
    """
    Download the completed recording from Attendee, save to our S3,
    and run the full analysis pipeline.

    Steps:
        1. Fetch bot from Attendee API → recording_url + calendar_id
        2. Resolve the user who owns the linked calendar
        3. Download MP4 → temp dir
        4. Convert MP4 → WAV (AWS Transcribe requirement)
        5. Create sales_calls DB record (source="attendee")
        6. Mark idempotency key as processed
        7. Run SalesCallProcessorService.process_call() — uploads WAV
           to S3, transcribes, LLM analysis, saves scores to DB
    """
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    upload_dir = os.path.join(_UPLOAD_DIR, call_id)
    os.makedirs(upload_dir, exist_ok=True)

    try:
        # 1. Fetch bot details
        bot_data = get_bot(bot_id)
        recording_url = bot_data.recording_url
        calendar_id = bot_data.resolve_calendar_id()

        if not recording_url:
            logger.error(
                "Bot %s has no recording_url — skipping", bot_id
            )
            return

        # 2. Resolve owning user
        user_id = _db.get_user_id_by_calendar_id(calendar_id) if calendar_id else None
        if not user_id:
            logger.error(
                "No user found for bot %s (calendar_id=%s) — skipping",
                bot_id,
                calendar_id,
            )
            return

        # 3. Download MP4
        mp4_path = os.path.join(upload_dir, f"{bot_id}.mp4")
        logger.info("Downloading recording for bot %s", bot_id)
        with requests.get(recording_url, stream=True) as r:
            r.raise_for_status()
            with open(mp4_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)

        # 4. Convert to WAV
        wav_path, _ = ensure_wav_format(mp4_path)
        audio_filename = basename(wav_path)

        # 5. Create DB record
        _db.create_sales_call_from_attendee(
            call_id=call_id,
            bot_id=bot_id,
            user_id=user_id,
            audio_filename=audio_filename,
        )

        # 6. Mark idempotency key before analysis so retries triggered
        #    by a slow pipeline don't re-download the recording
        _db.mark_webhook_key_processed(idempotency_key)

        # 7. Full pipeline — identical to manual upload from here
        logger.info(
            "Starting analysis for bot %s (call %s)", bot_id, call_id
        )
        _processor.process_call(
            audio_file_path=wav_path,
            call_id=call_id,
            user_id=user_id,
            rep_hint=None,
        )
        logger.info("Finished processing call %s", call_id)

    except Exception as e:
        logger.error(
            "Failed to ingest recording for bot %s: %s",
            bot_id,
            e,
            exc_info=True,
        )
        shutil.rmtree(upload_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _handle_zoom_connection_invalid(
    connection_id: str,
    idempotency_key: str,
) -> None:
    """
    Clear a Zoom connection that Attendee has marked expired/revoked.

    The user will be prompted to reconnect on their next dashboard visit.
    """
    user_id = _db.get_user_id_by_zoom_connection_id(connection_id)
    if user_id:
        _db.save_zoom_connection_id(user_id, None)
        logger.warning(
            "Zoom connection %s invalidated — cleared for user %s",
            connection_id,
            user_id,
        )
    else:
        logger.warning(
            "zoom_oauth_connection.state_change for unknown "
            "connection %s — ignoring",
            connection_id,
        )
    _db.mark_webhook_key_processed(idempotency_key)


def _post_link_setup(calendar_id: str) -> None:
    """
    Register calendar webhook and schedule bots for existing meetings.
    Runs as a background task after OAuth calendar link completes.
    """
    webhook_url = f"{_BASE_URL}/attendee/webhook"
    try:
        register_calendar_webhook(webhook_url)
        logger.info("Registered calendar webhook: %s", webhook_url)
    except requests.HTTPError as e:
        logger.warning(
            "Auto-registration of calendar.events_update webhook failed "
            "(%s). Register manually in the Attendee dashboard → "
            "Settings → Webhooks → URL: %s",
            e.response.text,
            webhook_url,
        )
    existing = schedule_existing_upcoming_meets(calendar_id, webhook_url)
    logger.info(
        "Scheduled %d bots for existing meetings (calendar %s)",
        len(existing),
        calendar_id,
    )


_OAUTH_STATE_EXPIRY = 600  # 10 minutes


def _sign_state(user_id: str, code_verifier: str) -> str:
    """Sign a state param containing user_id + timestamp + code_verifier."""
    payload = f"{user_id}:{int(time.time())}:{code_verifier}"
    sig = hmac.new(
        _OAUTH_STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return b64encode(f"{payload}:{sig}".encode()).decode()


def _verify_state(state: str) -> tuple[str, str] | None:
    """
    Verify the OAuth state param.
    Returns (user_id, code_verifier) if valid and not expired, else None.
    """
    try:
        decoded = b64decode(state).decode()
        # Format: user_id:timestamp:code_verifier:sig
        parts = decoded.split(":")
        sig = parts[-1]
        payload = ":".join(parts[:-1])
        user_id, ts_str, code_verifier = parts[0], parts[1], ":".join(parts[2:-1])
        expected = hmac.new(
            _OAUTH_STATE_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if time.time() - int(ts_str) > _OAUTH_STATE_EXPIRY:
            return None
        return user_id, code_verifier
    except Exception:
        return None


def _verify_signature(body: bytes, signature: str) -> bool:
    """
    Verify the Attendee webhook HMAC-SHA256 signature.

    Attendee signs by sorting JSON keys alphabetically then computing
    HMAC-SHA256 with the base64-decoded webhook secret.

    Returns True (skip check) if ATTENDEE_WEBHOOK_SECRET is not set,
    so local dev works without a secret configured.
    """
    if not _WEBHOOK_SECRET:
        logger.warning(
            "ATTENDEE_WEBHOOK_SECRET not set — skipping signature check"
        )
        return True

    try:
        secret = b64decode(_WEBHOOK_SECRET)
        payload_dict = json.loads(body)
        sorted_body = json.dumps(
            payload_dict, sort_keys=True
        ).encode()
        expected = b64encode(
            hmac.new(secret, sorted_body, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False
