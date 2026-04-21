"""
Attendee.dev API utilities.

Covers calendar linking, bot scheduling, and webhook registration.
All functions are synchronous (short-lived HTTP calls).
"""

import os
import requests
from models.attendee import (
    AttendeeCalendarEvent,
    AttendeeBotData,
)

_API_KEY = os.getenv("ATTENDEE_API_KEY")
_ATTENDEE_BASE_URL = "https://app.attendee.dev/api/v1"
_HEADERS = {
    "Authorization": f"Token {_API_KEY}",
    "Content-Type": "application/json",
}


def link_google_calendar(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    user_email: str,
) -> dict:
    """
    Link a Google Calendar to Attendee.dev.

    Returns the created calendar object including its `id`, which
    must be stored in user_profiles.attendee_calendar_id.

    Args:
        refresh_token: Google OAuth refresh token
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        user_email: Used as deduplication key to prevent duplicate
                    calendar syncs for the same user

    Returns:
        Attendee calendar object (dict with at least `id`)

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    payload = {
        "platform": "google",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "deduplication_key": user_email,
    }
    resp = requests.post(
        f"{_ATTENDEE_BASE_URL}/calendars",
        headers=_HEADERS,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def register_calendar_webhook(webhook_url: str) -> dict:
    """
    Register a project-level webhook for calendar.events_update.

    Called once after linking a calendar. Attendee will POST to
    webhook_url whenever a new or updated calendar event is synced,
    allowing bots to be auto-scheduled without any manual action.

    Note: this only covers events created/updated *after* registration.
    Call schedule_existing_upcoming_meets() separately to handle events
    that already exist at link time.

    Args:
        webhook_url: Publicly reachable URL for POST /attendee/webhook

    Returns:
        Created webhook object from Attendee

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.post(
        f"{_ATTENDEE_BASE_URL}/webhooks",
        headers=_HEADERS,
        json={
            "url": webhook_url,
            "triggers": ["calendar.events_update"],
        },
    )
    resp.raise_for_status()
    return resp.json()


def schedule_existing_upcoming_meets(
    calendar_id: str,
    webhook_url: str,
) -> list[AttendeeBotData]:
    """
    One-time initial pass: schedule bots for all upcoming Google Meet
    events that already exist at calendar-link time.

    Only needed once on first link — future events are handled
    automatically via the calendar.events_update webhook.

    Args:
        calendar_id: Attendee calendar ID from link_google_calendar()
        webhook_url: Publicly reachable URL for POST /attendee/webhook

    Returns:
        List of created bot objects (empty if none were scheduled)
    """
    events_resp = requests.get(
        f"{_ATTENDEE_BASE_URL}/calendar_events",
        headers=_HEADERS,
        params={"calendar_id": calendar_id},
    )
    events_resp.raise_for_status()
    events = [
        AttendeeCalendarEvent.model_validate(e)
        for e in events_resp.json().get("results", [])
    ]

    scheduled = []
    for event in events:
        if not get_meeting_platform(event) or event.bots:
            continue

        try:
            bot = schedule_bot_for_event(
                event.id, webhook_url, calendar_id=calendar_id
            )
            scheduled.append(bot)
        except requests.HTTPError as e:
            print(
                f"Failed to schedule bot for event {event.id}: "
                f"{e.response.status_code} {e.response.text}"
            )

    return scheduled


def schedule_bot_for_event(
    calendar_event_id: str,
    webhook_url: str,
    calendar_id: str | None = None,
    event_name: str | None = None,
) -> AttendeeBotData:
    """
    Create an Attendee bot for a specific calendar event.

    The bot joins automatically at the event start time (Attendee
    derives join_at from the calendar_event_id). A bot.state_change
    webhook is registered so we are notified when the recording is ready.

    For Zoom meetings, Attendee automatically applies the
    zoom_oauth_connection for the matching user — no extra field needed.

    Args:
        calendar_event_id: Attendee calendar event ID
        webhook_url: Publicly reachable URL for POST /attendee/webhook
        calendar_id: Stored in bot metadata for calendar_id lookup

    Returns:
        Created bot object from Attendee

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    payload: dict = {
        "calendar_event_id": calendar_event_id,
        "deduplication_key": calendar_event_id,
        "bot_name": "SpeakNatural Bot",
        "recording_settings": {"format": "mp4"},
        "webhooks": [
            {
                "url": webhook_url,
                "triggers": ["bot.state_change"],
            }
        ],
    }
    if calendar_id:
        payload["metadata"] = {"calendar_id": calendar_id}
        if event_name:
            payload["metadata"]["event_name"] = event_name

    resp = requests.post(f"{_ATTENDEE_BASE_URL}/bots", headers=_HEADERS, json=payload)
    resp.raise_for_status()
    return AttendeeBotData.model_validate(resp.json())


_PLATFORM_PATTERNS: dict[str, list[str]] = {
    "google_meet": ["meet.google.com"],
    "zoom": [
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


def get_meeting_platform(event: AttendeeCalendarEvent) -> str | None:
    """
    Return 'google_meet' | 'zoom' | 'teams' | None.

    Checks meeting_url, location, then description — Zoom URLs
    are often in the location field rather than meeting_url.
    """
    for text in (event.meeting_url, event.location, event.description):
        platform = _platform_from_url(text or "")
        if platform:
            return platform
    return None


def _platform_from_url(url: str) -> str | None:
    """Return the platform name if url matches a known pattern."""
    for platform, patterns in _PLATFORM_PATTERNS.items():
        if any(p in url for p in patterns):
            return platform
    return None


def create_zoom_oauth_connection(
    code: str,
    redirect_uri: str,
) -> dict:
    """
    Exchange a Zoom OAuth authorization code for an Attendee
    zoom_oauth_connection.

    Called from the Zoom OAuth callback after the user grants
    permission. Attendee stores the Zoom credentials and returns
    a connection object whose `id` must be saved to user_profiles.

    Args:
        code: Authorization code from Zoom OAuth redirect
        redirect_uri: Must match the redirect URI registered in
                      the Zoom app and sent in the auth request

    Returns:
        Attendee zoom_oauth_connection object (dict with at least `id`)

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.post(
        f"{_ATTENDEE_BASE_URL}/zoom_oauth_connections",
        headers=_HEADERS,
        json={"authorization_code": code, "redirect_uri": redirect_uri},
    )
    resp.raise_for_status()
    return resp.json()


def get_zoom_oauth_connection(connection_id: str) -> dict:
    """
    Fetch a zoom_oauth_connection by ID.

    Used to check connection status after a
    zoom_oauth_connection.state_change webhook.

    Args:
        connection_id: Attendee zoom_oauth_connection ID

    Returns:
        Connection object from Attendee

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.get(
        f"{_ATTENDEE_BASE_URL}/zoom_oauth_connections/{connection_id}",
        headers=_HEADERS,
    )
    resp.raise_for_status()
    return resp.json()


def update_calendar_credentials(
    calendar_id: str,
    refresh_token: str,
    client_secret: str,
) -> dict:
    """
    Update the refresh token on an existing Attendee calendar.

    Called when a user re-links their calendar after the previous
    token has expired or been revoked. Attendee rejects a second
    POST /calendars with the same deduplication_key, so we PATCH
    the existing calendar instead.

    Attendee PATCH /calendars/{id} accepts only:
    refresh_token, client_secret, metadata.

    Args:
        calendar_id: Attendee calendar ID stored in user_profiles
        refresh_token: New Google OAuth refresh token
        client_secret: Google OAuth client secret

    Returns:
        Updated calendar object from Attendee

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.patch(
        f"{_ATTENDEE_BASE_URL}/calendars/{calendar_id}",
        headers=_HEADERS,
        json={
            "refresh_token": refresh_token,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_calendar_event(event_id: str) -> AttendeeCalendarEvent:
    """Fetch a single calendar event by ID."""
    resp = requests.get(
        f"{_ATTENDEE_BASE_URL}/calendar_events/{event_id}",
        headers=_HEADERS,
    )
    resp.raise_for_status()
    return AttendeeCalendarEvent.model_validate(resp.json())


def get_calendar_events(calendar_id: str) -> list[AttendeeCalendarEvent]:
    """
    Fetch all upcoming calendar events synced by Attendee.

    Called after a calendar.events_update webhook fires — the webhook
    payload only signals that events changed, not what changed.

    Args:
        calendar_id: Attendee calendar ID

    Returns:
        List of calendar event objects

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.get(
        f"{_ATTENDEE_BASE_URL}/calendar_events",
        headers=_HEADERS,
        params={"calendar_id": calendar_id},
    )
    resp.raise_for_status()
    return [
        AttendeeCalendarEvent.model_validate(e)
        for e in resp.json().get("results", [])
    ]


def get_bot(bot_id: str) -> AttendeeBotData:
    """
    Fetch a single bot by ID from the Attendee API, including its
    recording URL from the /recording sub-resource.

    Args:
        bot_id: Attendee bot ID from the webhook payload

    Returns:
        Bot object with `recording_url` injected from the recording
        endpoint, plus `calendar_event` if present.

    Raises:
        requests.HTTPError: if the Attendee API returns non-2xx
    """
    resp = requests.get(f"{_ATTENDEE_BASE_URL}/bots/{bot_id}", headers=_HEADERS)
    resp.raise_for_status()
    bot = resp.json()

    rec_resp = requests.get(
        f"{_ATTENDEE_BASE_URL}/bots/{bot_id}/recording", headers=_HEADERS
    )
    if rec_resp.ok:
        bot["recording_url"] = rec_resp.json().get("url")

    return AttendeeBotData.model_validate(bot)
