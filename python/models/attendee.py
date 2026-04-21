"""
Pydantic models for Attendee.dev API responses and webhook payloads.

All models use extra="ignore" so unknown fields returned by the
Attendee API never cause validation errors.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Calendar events  (GET /calendar_events)
# ---------------------------------------------------------------------------

class AttendeeCalendarEvent(_Base):
    id: str
    name: str | None = None
    meeting_url: str | None = None
    description: str | None = None
    location: str | None = None
    # Non-empty list means a bot is already scheduled
    bots: list[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bots  (GET /bots/{id})
# ---------------------------------------------------------------------------

class _BotCalendarEvent(_Base):
    """Nested calendar_event object inside a bot response."""
    calendar_id: str | None = None
    meeting_url: str | None = None


class _BotMetadata(_Base):
    """
    Free-form metadata dict we attach when scheduling a bot
    (POST /bots payload) and read back from GET /bots/{id}.

    calendar_id  — Attendee calendar ID of the owning user; used in
                   _ingest_and_analyze_recording to look up which
                   user_profile owns the bot so we can create the
                   sales_calls record under the right rep_id.
    event_name   — Calendar event title at schedule time (e.g.
                   "Acme Corp Demo"). Written to sales_calls.call_name
                   when the recording arrives, before LLM analysis runs,
                   so the dashboard shows a readable name immediately.
    """
    calendar_id: str | None = None
    event_name: str | None = None


class AttendeeBotData(_Base):
    id: str
    recording_url: str | None = None
    # Attendee may surface calendar_id at different nesting levels
    # depending on how the bot was created — use resolve_calendar_id()
    calendar_id: str | None = None
    calendar_event: _BotCalendarEvent | None = None
    metadata: _BotMetadata | None = None

    def resolve_calendar_id(self) -> str | None:
        """
        Return calendar_id from whichever level Attendee populated.

        Precedence: calendar_event.calendar_id → bot.calendar_id
        → metadata.calendar_id
        """
        return (
            (self.calendar_event.calendar_id
             if self.calendar_event else None)
            or self.calendar_id
            or (self.metadata.calendar_id if self.metadata else None)
        )


# ---------------------------------------------------------------------------
# Webhook payloads  (POST /attendee/webhook)
# ---------------------------------------------------------------------------

class _WebhookData(_Base):
    event_type: str | None = None
    state: str | None = None


class AttendeeWebhookPayload(_Base):
    trigger: str = ""
    idempotency_key: str = ""
    # calendar.events_update
    calendar_id: str | None = None
    # bot.state_change
    bot_id: str | None = None
    # zoom_oauth_connection.state_change
    zoom_oauth_connection_id: str | None = None
    data: _WebhookData | None = None
