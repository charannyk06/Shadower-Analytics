-- Funnel Analysis Tables Migration
-- Creates tables for conversion funnel tracking and analysis

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================================================
-- FUNNEL DEFINITION TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.funnel_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,

    -- Funnel metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),

    -- Funnel configuration stored as JSON
    -- Format: [{"stepId": "...", "stepName": "...", "event": "...", "filters": {...}}]
    steps JSONB NOT NULL,

    -- Analysis settings
    timeframe VARCHAR(20) DEFAULT '30d' CHECK (timeframe IN ('24h', '7d', '30d', '90d')),
    segment_by VARCHAR(50), -- Optional: user_type, subscription_tier, etc.

    -- Metadata
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_funnel_name UNIQUE(workspace_id, name)
);

-- ===================================================================
-- FUNNEL ANALYSIS RESULTS TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.funnel_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    funnel_id UUID NOT NULL REFERENCES analytics.funnel_definitions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,

    -- Analysis timeframe
    analysis_start TIMESTAMPTZ NOT NULL,
    analysis_end TIMESTAMPTZ NOT NULL,

    -- Step results stored as JSON array
    -- Format: [{"stepId": "...", "stepName": "...", "totalUsers": 100, "uniqueUsers": 95, ...}]
    step_results JSONB NOT NULL,

    -- Overall funnel metrics
    total_entered INTEGER NOT NULL DEFAULT 0,
    total_completed INTEGER NOT NULL DEFAULT 0,
    overall_conversion_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_time_to_complete DECIMAL(10,2), -- in seconds
    biggest_drop_off_step VARCHAR(255),
    biggest_drop_off_rate DECIMAL(5,2),

    -- Segment analysis (if segmented)
    segment_name VARCHAR(100),
    segment_results JSONB, -- Format: [{"segmentName": "...", "conversionRate": 75.5, "performance": "above"}]

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_funnel_analysis UNIQUE(funnel_id, analysis_start, analysis_end, segment_name)
);

-- ===================================================================
-- FUNNEL STEP PERFORMANCE TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.funnel_step_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    funnel_id UUID NOT NULL REFERENCES analytics.funnel_definitions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,

    -- Step identification
    step_id VARCHAR(100) NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_order INTEGER NOT NULL,
    event_name VARCHAR(255) NOT NULL,

    -- Time period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,

    -- Step metrics
    total_users INTEGER NOT NULL DEFAULT 0,
    unique_users INTEGER NOT NULL DEFAULT 0,
    users_from_previous_step INTEGER NOT NULL DEFAULT 0,
    conversion_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    drop_off_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_time_from_previous DECIMAL(10,2), -- in seconds
    median_time_from_previous DECIMAL(10,2),

    -- Drop-off analysis
    drop_off_reasons JSONB, -- Format: [{"reason": "...", "count": 50, "percentage": 25.0}]

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_funnel_step_period UNIQUE(funnel_id, step_id, period_start, period_end)
);

-- ===================================================================
-- USER FUNNEL JOURNEY TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.user_funnel_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    funnel_id UUID NOT NULL REFERENCES analytics.funnel_definitions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Journey tracking
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    last_step_reached VARCHAR(100),
    last_step_order INTEGER,
    status VARCHAR(20) NOT NULL CHECK (status IN ('in_progress', 'completed', 'abandoned')),

    -- Journey path (array of step IDs with timestamps)
    -- Format: [{"stepId": "...", "stepName": "...", "timestamp": "..."}]
    journey_path JSONB NOT NULL DEFAULT '[]'::JSONB,

    -- Time metrics
    total_time_spent DECIMAL(10,2), -- in seconds
    time_per_step JSONB, -- Format: {"step1": 120.5, "step2": 85.3}

    -- User segment
    user_segment VARCHAR(100),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_user_funnel_journey UNIQUE(funnel_id, user_id, started_at)
);

-- ===================================================================
-- INDEXES FOR PERFORMANCE
-- ===================================================================

-- Funnel Definitions Indexes
CREATE INDEX IF NOT EXISTS idx_funnel_definitions_workspace
    ON analytics.funnel_definitions(workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_funnel_definitions_created
    ON analytics.funnel_definitions(created_at DESC);

-- Funnel Analysis Results Indexes
CREATE INDEX IF NOT EXISTS idx_funnel_results_funnel
    ON analytics.funnel_analysis_results(funnel_id, analysis_start DESC);

CREATE INDEX IF NOT EXISTS idx_funnel_results_workspace_time
    ON analytics.funnel_analysis_results(workspace_id, analysis_start, analysis_end);

CREATE INDEX IF NOT EXISTS idx_funnel_results_calculated
    ON analytics.funnel_analysis_results(calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_funnel_results_segment
    ON analytics.funnel_analysis_results(funnel_id, segment_name)
    WHERE segment_name IS NOT NULL;

-- Funnel Step Performance Indexes
CREATE INDEX IF NOT EXISTS idx_funnel_step_performance_funnel
    ON analytics.funnel_step_performance(funnel_id, step_order, period_start);

CREATE INDEX IF NOT EXISTS idx_funnel_step_performance_period
    ON analytics.funnel_step_performance(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_funnel_step_performance_conversion
    ON analytics.funnel_step_performance(funnel_id, conversion_rate DESC);

-- User Funnel Journeys Indexes
CREATE INDEX IF NOT EXISTS idx_user_journeys_funnel_status
    ON analytics.user_funnel_journeys(funnel_id, status, started_at);

CREATE INDEX IF NOT EXISTS idx_user_journeys_user
    ON analytics.user_funnel_journeys(user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_journeys_workspace
    ON analytics.user_funnel_journeys(workspace_id, started_at);

CREATE INDEX IF NOT EXISTS idx_user_journeys_segment
    ON analytics.user_funnel_journeys(funnel_id, user_segment)
    WHERE user_segment IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_journeys_path
    ON analytics.user_funnel_journeys USING GIN(journey_path);

-- ===================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- ===================================================================

-- Funnel Definitions Trigger
DROP TRIGGER IF EXISTS funnel_definitions_updated_at ON analytics.funnel_definitions;
CREATE TRIGGER funnel_definitions_updated_at
    BEFORE UPDATE ON analytics.funnel_definitions
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- Funnel Step Performance Trigger
DROP TRIGGER IF EXISTS funnel_step_performance_updated_at ON analytics.funnel_step_performance;
CREATE TRIGGER funnel_step_performance_updated_at
    BEFORE UPDATE ON analytics.funnel_step_performance
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- User Funnel Journeys Trigger
DROP TRIGGER IF EXISTS user_funnel_journeys_updated_at ON analytics.user_funnel_journeys;
CREATE TRIGGER user_funnel_journeys_updated_at
    BEFORE UPDATE ON analytics.user_funnel_journeys
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- ===================================================================
-- HELPER FUNCTIONS
-- ===================================================================

-- Function to calculate conversion rate
CREATE OR REPLACE FUNCTION analytics.calculate_conversion_rate(
    completed_count INTEGER,
    total_count INTEGER
)
RETURNS DECIMAL AS $$
BEGIN
    IF total_count = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND(((completed_count::NUMERIC / total_count::NUMERIC) * 100.0), 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate drop-off rate
CREATE OR REPLACE FUNCTION analytics.calculate_drop_off_rate(
    current_step_users INTEGER,
    previous_step_users INTEGER
)
RETURNS DECIMAL AS $$
BEGIN
    IF previous_step_users = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((((previous_step_users - current_step_users)::NUMERIC / previous_step_users::NUMERIC) * 100.0), 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to identify biggest drop-off step
CREATE OR REPLACE FUNCTION analytics.find_biggest_drop_off(
    step_results JSONB
)
RETURNS TABLE(step_name VARCHAR, drop_off_rate DECIMAL) AS $$
DECLARE
    max_drop_off DECIMAL := 0;
    result_step VARCHAR;
    result_rate DECIMAL;
BEGIN
    SELECT
        (step->>'stepName')::VARCHAR,
        (step->>'dropOffRate')::DECIMAL
    INTO result_step, result_rate
    FROM jsonb_array_elements(step_results) AS step
    WHERE (step->>'dropOffRate')::DECIMAL IS NOT NULL
    ORDER BY (step->>'dropOffRate')::DECIMAL DESC
    LIMIT 1;

    RETURN QUERY SELECT result_step, result_rate;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate funnel health score (0-100)
CREATE OR REPLACE FUNCTION analytics.calculate_funnel_health_score(
    overall_conversion DECIMAL,
    avg_drop_off DECIMAL,
    step_count INTEGER
)
RETURNS DECIMAL AS $$
DECLARE
    health_score DECIMAL;
BEGIN
    -- Health score formula:
    -- - 60% weight on overall conversion rate
    -- - 30% weight on drop-off consistency (lower is better)
    -- - 10% weight on funnel complexity (fewer steps is better for conversion)

    health_score := (
        (overall_conversion * 0.6) +
        ((100 - LEAST(avg_drop_off, 100)) * 0.3) +
        ((100 - LEAST(step_count * 5, 50)) * 0.1)
    );

    RETURN ROUND(GREATEST(LEAST(health_score, 100), 0), 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ===================================================================
-- MATERIALIZED VIEW FOR FUNNEL OVERVIEW
-- ===================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_funnel_overview AS
SELECT
    fd.id AS funnel_id,
    fd.workspace_id,
    fd.name AS funnel_name,
    fd.status,
    jsonb_array_length(fd.steps) AS step_count,

    -- Latest analysis results
    far.overall_conversion_rate,
    far.avg_time_to_complete,
    far.biggest_drop_off_step,
    far.biggest_drop_off_rate,
    far.total_entered,
    far.total_completed,

    -- Calculate health score
    analytics.calculate_funnel_health_score(
        COALESCE(far.overall_conversion_rate, 0),
        COALESCE(far.biggest_drop_off_rate, 0),
        jsonb_array_length(fd.steps)
    ) AS health_score,

    -- User journeys summary
    (SELECT COUNT(*) FROM analytics.user_funnel_journeys WHERE funnel_id = fd.id AND status = 'completed') AS total_completions,
    (SELECT COUNT(*) FROM analytics.user_funnel_journeys WHERE funnel_id = fd.id AND status = 'abandoned') AS total_abandonments,
    (SELECT COUNT(*) FROM analytics.user_funnel_journeys WHERE funnel_id = fd.id AND status = 'in_progress') AS in_progress_count,

    far.calculated_at AS last_analyzed_at,
    fd.created_at,
    fd.updated_at
FROM analytics.funnel_definitions fd
LEFT JOIN LATERAL (
    SELECT *
    FROM analytics.funnel_analysis_results
    WHERE funnel_id = fd.id
    ORDER BY calculated_at DESC
    LIMIT 1
) far ON true
WHERE fd.status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_funnel_overview_pk
    ON analytics.mv_funnel_overview(funnel_id);

CREATE INDEX IF NOT EXISTS idx_mv_funnel_overview_workspace
    ON analytics.mv_funnel_overview(workspace_id, health_score DESC);

CREATE INDEX IF NOT EXISTS idx_mv_funnel_overview_conversion
    ON analytics.mv_funnel_overview(overall_conversion_rate DESC);

-- ===================================================================
-- COMMENTS FOR DOCUMENTATION
-- ===================================================================

COMMENT ON TABLE analytics.funnel_definitions IS 'Stores conversion funnel definitions with steps and configuration';
COMMENT ON TABLE analytics.funnel_analysis_results IS 'Stores aggregated funnel analysis results for reporting';
COMMENT ON TABLE analytics.funnel_step_performance IS 'Tracks performance metrics for individual funnel steps';
COMMENT ON TABLE analytics.user_funnel_journeys IS 'Records individual user journeys through funnels';

COMMENT ON COLUMN analytics.funnel_definitions.steps IS 'JSON array of funnel steps with event names and filters';
COMMENT ON COLUMN analytics.funnel_analysis_results.step_results IS 'JSON array of per-step metrics and analysis';
COMMENT ON COLUMN analytics.user_funnel_journeys.journey_path IS 'JSON array tracking user path through funnel steps';

COMMENT ON FUNCTION analytics.calculate_conversion_rate IS 'Calculates conversion rate as percentage';
COMMENT ON FUNCTION analytics.calculate_drop_off_rate IS 'Calculates drop-off rate between funnel steps';
COMMENT ON FUNCTION analytics.find_biggest_drop_off IS 'Identifies the step with highest drop-off rate';
COMMENT ON FUNCTION analytics.calculate_funnel_health_score IS 'Calculates overall funnel health score (0-100)';
