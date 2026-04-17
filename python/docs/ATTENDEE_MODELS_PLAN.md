# Attendee Models Refactor Plan

## Context

Attendee API responses and webhook payloads are currently handled
as free-form dicts throughout `attendee_utils.py` and
`attendee_service.py`. This leads to fragile nested `.get()` chains,
no IDE autocomplete, and silent failures when the API shape changes.

The fix: Pydantic models for the three key data shapes. Pydantic is
already a dependency (used in `models.py`). No new packages needed.

All models use `extra="ignore"` — unknown fields from the Attendee
API never cause validation errors.

---

## Progress

| Task | Status |
|------|--------|
| 1 — Create `python/models/attendee.py` | ✅ Done |
| 2 — Update `attendee_utils.py` | ✅ Done |
| 3 — Update `attendee_service.py` | ✅ Done |

---

## Task 1 — Create `python/models/attendee.py`

New `python/models/` directory with an `__init__.py`.
Future models (e.g. Zoom, Teams) live here as separate files.



Three models:

### `AttendeeCalendarEvent`
Returned by `get_calendar_events()` and `get_calendar_event()`.

```python
class AttendeeCalendarEvent(_Base):
    id: str
    name: str | None = None
    meeting_url: str | None = None
    description: str | None = None
    location: str | None = None
    bots: list[Any] = []   # non-empty = bot already scheduled
```

### `AttendeeBotData`
Returned by `get_bot()`. Adds `resolve_calendar_id()` to replace
the 3-level fallback chain currently in `_ingest_and_analyze_recording`:

```python
# Before (attendee_service.py:464)
calendar_id = (
    bot_data.get("calendar_event", {}).get("calendar_id")
    or bot_data.get("calendar_id")
    or (bot_data.get("metadata") or {}).get("calendar_id")
)

# After
calendar_id = bot_data.resolve_calendar_id()
```

```python
class AttendeeBotData(_Base):
    id: str
    recording_url: str | None = None
    calendar_id: str | None = None
    calendar_event: _BotCalendarEvent | None = None
    metadata: _BotMetadata | None = None

    def resolve_calendar_id(self) -> str | None:
        return (
            (self.calendar_event.calendar_id
             if self.calendar_event else None)
            or self.calendar_id
            or (self.metadata.calendar_id if self.metadata else None)
        )
```

### `AttendeeWebhookPayload`
Parsed from the raw webhook body. Also includes
`zoom_oauth_connection_id` for the Zoom OAuth work coming next.

```python
class AttendeeWebhookPayload(_Base):
    trigger: str = ""
    idempotency_key: str = ""
    calendar_id: str | None = None      # calendar.events_update
    bot_id: str | None = None           # bot.state_change
    zoom_oauth_connection_id: str | None = None
    data: _WebhookData | None = None    # event_type, state
```

---

## Task 2 — Update `python/utils/attendee_utils.py`

Return type changes only — no logic changes.

| Function | Return before | Return after |
|----------|--------------|--------------|
| `get_bot()` | `dict` | `AttendeeBotData` |
| `get_calendar_events()` | `list[dict]` | `list[AttendeeCalendarEvent]` |
| `get_calendar_event()` | `dict` | `AttendeeCalendarEvent` |
| `schedule_existing_upcoming_meets()` | `list[dict]` | `list[AttendeeBotData]` |

`get_meeting_platform()` signature changes from `event: dict`
to `event: AttendeeCalendarEvent`. Also adds `location` field
to the platform check — Zoom URLs often live there rather than
in `meeting_url`.

```python
# Before
def get_meeting_platform(event: dict) -> str | None:
    url = event.get("meeting_url", "") or ""
    ...
    desc = event.get("description", "") or ""

# After
def get_meeting_platform(event: AttendeeCalendarEvent) -> str | None:
    for text in (event.meeting_url, event.location, event.description):
        platform = _platform_from_url(text or "")
        if platform:
            return platform
    return None
```

---

## Task 3 — Update `python/api/attendee_service.py`

Access style changes only — no logic changes.

### Webhook handler

```python
# Before
payload = json.loads(body)
trigger = payload.get("trigger", "")
idempotency_key = payload.get("idempotency_key", "")
...
event_type = payload.get("data", {}).get("event_type", "")
bot_id = payload.get("bot_id")

# After
payload = AttendeeWebhookPayload.model_validate(json.loads(body))
trigger = payload.trigger
idempotency_key = payload.idempotency_key
...
event_type = payload.data.event_type if payload.data else ""
bot_id = payload.bot_id
```

### `_schedule_bot_if_needed`

```python
# Before
calendar_id = payload.get("calendar_id")
...
if not get_meeting_platform(event) or event.get("bots"):
...
event.get("name", event["id"])

# After
calendar_id = payload.calendar_id
...
if not get_meeting_platform(event) or event.bots:
...
event.name or event.id
```

### `_ingest_and_analyze_recording`

```python
# Before
bot_data = get_bot(bot_id)
recording_url = bot_data.get("recording_url")
calendar_id = (
    bot_data.get("calendar_event", {}).get("calendar_id")
    or bot_data.get("calendar_id")
    or (bot_data.get("metadata") or {}).get("calendar_id")
)

# After
bot_data = get_bot(bot_id)
recording_url = bot_data.recording_url
calendar_id = bot_data.resolve_calendar_id()
```

---

## Files Summary

| Task | New Files | Modified Files |
|------|-----------|----------------|
| 1 | `models/__init__.py`, `models/attendee.py` | — |
| 2 | — | `utils/attendee_utils.py` |
| 3 | — | `api/attendee_service.py` |
