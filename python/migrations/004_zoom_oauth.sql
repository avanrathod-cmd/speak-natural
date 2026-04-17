-- Migration 004: Zoom OAuth connection storage
-- Run against your Supabase project via the SQL editor or psql.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS zoom_connection_id TEXT;

COMMENT ON COLUMN user_profiles.zoom_connection_id
    IS 'Attendee zoom_oauth_connection ID — required for bots to '
       'join Zoom meetings on behalf of this user';
