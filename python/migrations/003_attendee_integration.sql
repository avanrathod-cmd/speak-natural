-- Migration: Attendee.dev calendar integration
-- Description: Adds columns for linking Google Calendar via Attendee
--              and tracking auto-recorded calls
-- Created: 2026-04-07

-- ============================================================
-- user_profiles — store linked Attendee calendar ID
-- ============================================================
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS attendee_calendar_id TEXT;

COMMENT ON COLUMN user_profiles.attendee_calendar_id
    IS 'Attendee.dev calendar ID after OAuth calendar link';


-- ============================================================
-- sales_calls — track recording source + dedup Attendee bots
-- ============================================================
ALTER TABLE sales_calls
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS attendee_bot_id TEXT UNIQUE;

COMMENT ON COLUMN sales_calls.source
    IS 'How the call was captured: manual (upload) or attendee (bot)';

COMMENT ON COLUMN sales_calls.attendee_bot_id
    IS 'Attendee.dev bot ID — UNIQUE constraint prevents duplicate '
       'ingestion if the webhook fires more than once';

ALTER TABLE sales_calls
    ADD CONSTRAINT valid_source CHECK (source IN ('manual', 'attendee'));


-- ============================================================
-- webhook_idempotency_keys — deduplicate webhook deliveries
-- ============================================================
CREATE TABLE IF NOT EXISTS webhook_idempotency_keys (
    key         TEXT PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE webhook_idempotency_keys
    IS 'Tracks processed Attendee webhook delivery keys to prevent '
       'double-ingestion on retries';
