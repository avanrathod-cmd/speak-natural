-- Migration: Sales Call Analyzer tables
-- Description: Adds all tables for the sales call analyzer MVP
-- Created: 2026-03-04

-- ============================================================
-- organizations
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE organizations
    IS 'Company or team account grouping managers and reps';


-- ============================================================
-- user_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY
        REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id),
    role TEXT NOT NULL DEFAULT 'rep',
    full_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_role CHECK (role IN ('manager', 'rep'))
);

-- Index on org_id for filtering user profiles by org.
CREATE INDEX IF NOT EXISTS idx_user_profiles_org_id
    ON user_profiles(org_id);

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE user_profiles
    IS 'Extends auth.users with org membership and role';


-- ============================================================
-- products
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    description TEXT,
    customer_profile TEXT,
    talking_points TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_org_id
    ON products(org_id);

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE products
    IS 'Product/service context uploaded by managers or reps';
COMMENT ON COLUMN products.customer_profile
    IS 'Target customer persona description';
COMMENT ON COLUMN products.talking_points
    IS 'Key selling points and pitch notes';


-- ============================================================
-- sales_scripts
-- ============================================================
CREATE TABLE IF NOT EXISTS sales_scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    product_id UUID REFERENCES products(id),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    script_content TEXT NOT NULL,
    key_phrases TEXT[],
    objection_handlers JSONB,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_script_status
        CHECK (status IN ('active', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_sales_scripts_org_id
    ON sales_scripts(org_id);
CREATE INDEX IF NOT EXISTS idx_sales_scripts_product_id
    ON sales_scripts(product_id);

CREATE TRIGGER update_sales_scripts_updated_at
    BEFORE UPDATE ON sales_scripts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE sales_scripts
    IS 'AI-generated scripts linked to a product context';
COMMENT ON COLUMN sales_scripts.key_phrases
    IS 'Must-say phrases the rep should cover';
COMMENT ON COLUMN sales_scripts.objection_handlers
    IS 'JSON: {objection_text: recommended_response}';


-- ============================================================
-- sales_calls
-- ============================================================
CREATE TABLE IF NOT EXISTS sales_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    rep_id UUID NOT NULL REFERENCES auth.users(id),
    script_id UUID REFERENCES sales_scripts(id),
    product_id UUID REFERENCES products(id),
    call_id TEXT UNIQUE NOT NULL,
    audio_filename TEXT NOT NULL,
    s3_audio_uri TEXT,
    s3_transcript_uri TEXT,
    duration_seconds FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT valid_call_status CHECK (
        status IN (
            'pending', 'processing', 'completed', 'failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_sales_calls_org_id
    ON sales_calls(org_id);
CREATE INDEX IF NOT EXISTS idx_sales_calls_rep_id
    ON sales_calls(rep_id);
CREATE INDEX IF NOT EXISTS idx_sales_calls_status
    ON sales_calls(status);
CREATE INDEX IF NOT EXISTS idx_sales_calls_created_at
    ON sales_calls(created_at DESC);

CREATE TRIGGER update_sales_calls_updated_at
    BEFORE UPDATE ON sales_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE sales_calls
    IS 'Sales call recordings and their processing status';
COMMENT ON COLUMN sales_calls.call_id
    IS 'Unique job identifier (e.g., call_abc123)';


-- ============================================================
-- call_analyses
-- ============================================================
CREATE TABLE IF NOT EXISTS call_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT NOT NULL REFERENCES sales_calls(call_id),
    org_id UUID NOT NULL REFERENCES organizations(id),

    -- Speaker identification
    -- One sales rep per call; multiple customer reps possible
    salesperson_speaker_label TEXT,
    customer_speaker_labels TEXT[],

    -- Rep performance scores (0-100)
    overall_rep_score INTEGER,
    script_adherence_score INTEGER,
    communication_score INTEGER,
    objection_handling_score INTEGER,
    closing_score INTEGER,

    -- Rep performance details (AI output)
    rep_analysis JSONB,

    -- Customer / lead scores
    lead_score INTEGER,
    engagement_level TEXT,
    customer_sentiment TEXT,

    -- Customer behavior details (AI output)
    customer_analysis JSONB,

    -- Vocal metrics from audio pipeline
    vocal_metrics JSONB,

    -- Speaker-labeled full transcript
    full_transcript JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_engagement CHECK (
        engagement_level IN ('high', 'medium', 'low')
    ),
    CONSTRAINT valid_sentiment CHECK (
        customer_sentiment IN (
            'positive', 'neutral', 'negative'
        )
    ),
    CONSTRAINT valid_rep_score CHECK (
        overall_rep_score BETWEEN 0 AND 100
    ),
    CONSTRAINT valid_lead_score CHECK (
        lead_score BETWEEN 0 AND 100
    )
);

CREATE INDEX IF NOT EXISTS idx_call_analyses_call_id
    ON call_analyses(call_id);
CREATE INDEX IF NOT EXISTS idx_call_analyses_org_id
    ON call_analyses(org_id);

COMMENT ON TABLE call_analyses
    IS 'AI analysis results for each completed sales call';
COMMENT ON COLUMN call_analyses.rep_analysis
    IS 'JSON: strengths, improvements, key_moments, coaching';
COMMENT ON COLUMN call_analyses.customer_analysis
    IS 'JSON: interests, objections, buying_signals, next_steps';
COMMENT ON COLUMN call_analyses.vocal_metrics
    IS 'JSON: pace_wpm, filler_ratio, pitch_variation, energy';
COMMENT ON COLUMN call_analyses.full_transcript
    IS 'JSON: [{speaker_role, text, start_time, end_time}]';


-- ============================================================
-- manager_chat_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS manager_chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    manager_id UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_manager_id
    ON manager_chat_sessions(manager_id);

COMMENT ON TABLE manager_chat_sessions
    IS 'AI chat sessions started by a manager';


-- ============================================================
-- manager_chat_messages
-- ============================================================
CREATE TABLE IF NOT EXISTS manager_chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID NOT NULL
        REFERENCES manager_chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
    ON manager_chat_messages(chat_session_id);

COMMENT ON TABLE manager_chat_messages
    IS 'Individual messages in a manager AI chat session';
COMMENT ON COLUMN manager_chat_messages.role
    IS 'user | assistant';
