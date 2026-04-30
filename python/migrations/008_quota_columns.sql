-- Migration 008: Add quota tracking columns to organizations.

-- ============================================================
-- Schema changes
-- ============================================================

-- minutes_analysed: cumulative minutes of call analysis used by this org.
--   Incremented when a call moves to 'processing'. Never decremented.
--   Append-only — if a call fails mid-pipeline, cost was already incurred.
--
-- seats_used: cached count of manager + rep rows for this org.
--   Incremented on invite acceptance, decremented on member removal.
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS minutes_analysed INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS seats_used       INTEGER NOT NULL DEFAULT 0;

-- ============================================================
-- Backfill
-- ============================================================

-- Backfill minutes_analysed from existing call history.
-- Calls with NULL duration_seconds (recorded before this migration)
-- contribute 0 — existing users get a grace period on past usage.
UPDATE organizations o
SET minutes_analysed = COALESCE((
  SELECT FLOOR(SUM(duration_seconds) / 60.0)
  FROM   sales_calls
  WHERE  org_id = o.id
    AND  status IN ('processing', 'completed')
    AND  duration_seconds IS NOT NULL
), 0);

-- Backfill seats_used from current user_profiles.
UPDATE organizations o
SET seats_used = (
  SELECT COUNT(*)
  FROM   user_profiles
  WHERE  org_id = o.id
    AND  role IN ('manager', 'rep')
);
