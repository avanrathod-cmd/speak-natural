-- Migration: Create coaching_sessions table
-- Description: Stores coaching session metadata (replaces JSON file storage)
-- Created: 2026-01-22

-- Create coaching_sessions table
CREATE TABLE IF NOT EXISTS coaching_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coaching_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL,
    audio_filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',

    -- Directory paths (stored as JSONB for flexibility)
    directories JSONB,

    -- Voice mapping for speaker -> voice_id (JSONB)
    voice_mapping JSONB,

    -- Progress and error tracking
    progress TEXT,
    error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Create index on coaching_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_coaching_id ON coaching_sessions(coaching_id);

-- Create index on user_id for listing user sessions
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_user_id ON coaching_sessions(user_id);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_status ON coaching_sessions(status);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_created_at ON coaching_sessions(created_at DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_coaching_sessions_updated_at
    BEFORE UPDATE ON coaching_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE coaching_sessions IS 'Stores metadata for all coaching sessions';
COMMENT ON COLUMN coaching_sessions.coaching_id IS 'Unique session identifier (e.g., coach_abc123)';
COMMENT ON COLUMN coaching_sessions.user_id IS 'User who created this session (from JWT)';
COMMENT ON COLUMN coaching_sessions.status IS 'Processing status: pending, processing, completed, failed';
COMMENT ON COLUMN coaching_sessions.directories IS 'JSON object containing local directory paths';
COMMENT ON COLUMN coaching_sessions.voice_mapping IS 'JSON object mapping speaker labels to ElevenLabs voice IDs';
