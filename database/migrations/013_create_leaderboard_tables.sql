-- Leaderboards Tables Migration
-- Creates tables for competitive rankings and leaderboards

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================================================
-- AGENT LEADERBOARD TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,

    -- Ranking information
    rank INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change VARCHAR(10) CHECK (rank_change IN ('up', 'down', 'same', 'new')),

    -- Timeframe and criteria
    timeframe VARCHAR(20) NOT NULL CHECK (timeframe IN ('24h', '7d', '30d', '90d', 'all')),
    criteria VARCHAR(50) NOT NULL CHECK (criteria IN ('runs', 'success_rate', 'speed', 'efficiency', 'popularity')),

    -- Agent metrics (snapshot)
    total_runs INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    avg_runtime DECIMAL(10,2) DEFAULT 0,
    credits_per_run DECIMAL(10,2) DEFAULT 0,
    unique_users INTEGER DEFAULT 0,

    -- Score and percentile
    score DECIMAL(10,4) NOT NULL,
    percentile DECIMAL(5,2),
    badge VARCHAR(20) CHECK (badge IN ('gold', 'silver', 'bronze')),

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique entries per timeframe and criteria
    CONSTRAINT unique_agent_leaderboard UNIQUE(workspace_id, agent_id, timeframe, criteria)
);

-- ===================================================================
-- USER LEADERBOARD TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.user_leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Ranking information
    rank INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change VARCHAR(10) CHECK (rank_change IN ('up', 'down', 'same', 'new')),

    -- Timeframe and criteria
    timeframe VARCHAR(20) NOT NULL CHECK (timeframe IN ('24h', '7d', '30d', '90d', 'all')),
    criteria VARCHAR(50) NOT NULL CHECK (criteria IN ('activity', 'efficiency', 'contribution', 'savings')),

    -- User metrics (snapshot)
    total_actions INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    credits_used DECIMAL(12,2) DEFAULT 0,
    credits_saved DECIMAL(12,2) DEFAULT 0,
    agents_used INTEGER DEFAULT 0,

    -- Score and percentile
    score DECIMAL(10,4) NOT NULL,
    percentile DECIMAL(5,2),

    -- Achievements stored as JSON array
    achievements JSONB DEFAULT '[]'::JSONB,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique entries per timeframe and criteria
    CONSTRAINT unique_user_leaderboard UNIQUE(workspace_id, user_id, timeframe, criteria)
);

-- ===================================================================
-- WORKSPACE LEADERBOARD TABLE
-- ===================================================================
CREATE TABLE IF NOT EXISTS analytics.workspace_leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,

    -- Ranking information
    rank INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change VARCHAR(10) CHECK (rank_change IN ('up', 'down', 'same', 'new')),

    -- Timeframe and criteria
    timeframe VARCHAR(20) NOT NULL CHECK (timeframe IN ('24h', '7d', '30d', '90d', 'all')),
    criteria VARCHAR(50) NOT NULL CHECK (criteria IN ('activity', 'efficiency', 'growth', 'innovation')),

    -- Workspace metrics (snapshot)
    total_activity INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    agent_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    health_score DECIMAL(5,2) DEFAULT 0,

    -- Score and tier
    score DECIMAL(10,4) NOT NULL,
    tier VARCHAR(20) CHECK (tier IN ('platinum', 'gold', 'silver', 'bronze')),

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique entries per timeframe and criteria
    CONSTRAINT unique_workspace_leaderboard UNIQUE(workspace_id, timeframe, criteria)
);

-- ===================================================================
-- INDEXES FOR PERFORMANCE
-- ===================================================================

-- Agent Leaderboard Indexes
CREATE INDEX IF NOT EXISTS idx_agent_leaderboard_workspace_timeframe
    ON analytics.agent_leaderboard(workspace_id, timeframe, criteria, rank);

CREATE INDEX IF NOT EXISTS idx_agent_leaderboard_rank
    ON analytics.agent_leaderboard(timeframe, criteria, rank)
    WHERE rank <= 100;

CREATE INDEX IF NOT EXISTS idx_agent_leaderboard_calculated
    ON analytics.agent_leaderboard(calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_leaderboard_agent
    ON analytics.agent_leaderboard(agent_id, timeframe);

-- User Leaderboard Indexes
CREATE INDEX IF NOT EXISTS idx_user_leaderboard_workspace_timeframe
    ON analytics.user_leaderboard(workspace_id, timeframe, criteria, rank);

CREATE INDEX IF NOT EXISTS idx_user_leaderboard_rank
    ON analytics.user_leaderboard(timeframe, criteria, rank)
    WHERE rank <= 100;

CREATE INDEX IF NOT EXISTS idx_user_leaderboard_calculated
    ON analytics.user_leaderboard(calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_leaderboard_user
    ON analytics.user_leaderboard(user_id, timeframe);

CREATE INDEX IF NOT EXISTS idx_user_leaderboard_achievements
    ON analytics.user_leaderboard USING GIN(achievements);

-- Workspace Leaderboard Indexes
CREATE INDEX IF NOT EXISTS idx_workspace_leaderboard_timeframe
    ON analytics.workspace_leaderboard(timeframe, criteria, rank);

CREATE INDEX IF NOT EXISTS idx_workspace_leaderboard_rank
    ON analytics.workspace_leaderboard(timeframe, criteria, rank)
    WHERE rank <= 100;

CREATE INDEX IF NOT EXISTS idx_workspace_leaderboard_calculated
    ON analytics.workspace_leaderboard(calculated_at DESC);

-- ===================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- ===================================================================

-- Agent Leaderboard Trigger
DROP TRIGGER IF EXISTS agent_leaderboard_updated_at ON analytics.agent_leaderboard;
CREATE TRIGGER agent_leaderboard_updated_at
    BEFORE UPDATE ON analytics.agent_leaderboard
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- User Leaderboard Trigger
DROP TRIGGER IF EXISTS user_leaderboard_updated_at ON analytics.user_leaderboard;
CREATE TRIGGER user_leaderboard_updated_at
    BEFORE UPDATE ON analytics.user_leaderboard
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- Workspace Leaderboard Trigger
DROP TRIGGER IF EXISTS workspace_leaderboard_updated_at ON analytics.workspace_leaderboard;
CREATE TRIGGER workspace_leaderboard_updated_at
    BEFORE UPDATE ON analytics.workspace_leaderboard
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- ===================================================================
-- HELPER FUNCTIONS
-- ===================================================================

-- Function to calculate percentile
CREATE OR REPLACE FUNCTION analytics.calculate_percentile(
    score_value DECIMAL,
    total_count INTEGER,
    rank_value INTEGER
)
RETURNS DECIMAL AS $$
BEGIN
    IF total_count = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND(((total_count - rank_value + 1.0) / total_count * 100.0)::NUMERIC, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to determine rank change
CREATE OR REPLACE FUNCTION analytics.determine_rank_change(
    current_rank INTEGER,
    prev_rank INTEGER
)
RETURNS VARCHAR AS $$
BEGIN
    IF prev_rank IS NULL THEN
        RETURN 'new';
    ELSIF current_rank < prev_rank THEN
        RETURN 'up';
    ELSIF current_rank > prev_rank THEN
        RETURN 'down';
    ELSE
        RETURN 'same';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to assign badge based on rank
CREATE OR REPLACE FUNCTION analytics.assign_badge(rank_value INTEGER)
RETURNS VARCHAR AS $$
BEGIN
    CASE
        WHEN rank_value = 1 THEN RETURN 'gold';
        WHEN rank_value = 2 THEN RETURN 'silver';
        WHEN rank_value = 3 THEN RETURN 'bronze';
        ELSE RETURN NULL;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to assign tier based on percentile
CREATE OR REPLACE FUNCTION analytics.assign_tier(percentile_value DECIMAL)
RETURNS VARCHAR AS $$
BEGIN
    CASE
        WHEN percentile_value >= 95 THEN RETURN 'platinum';
        WHEN percentile_value >= 80 THEN RETURN 'gold';
        WHEN percentile_value >= 60 THEN RETURN 'silver';
        ELSE RETURN 'bronze';
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ===================================================================
-- MATERIALIZED VIEWS FOR EFFICIENT RANKING
-- ===================================================================

-- Agent Rankings by Success Rate (7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_agent_rankings_success_7d AS
SELECT
    a.workspace_id,
    a.id AS agent_id,
    a.name AS agent_name,
    a.type AS agent_type,
    COUNT(ae.id) AS total_runs,
    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
    ROUND(AVG(ae.duration), 2) AS avg_runtime,
    ROUND(AVG(ae.credits_used), 2) AS credits_per_run,
    COUNT(DISTINCT ae.user_id) AS unique_users,
    -- Score calculation (weighted formula)
    (
        (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.4) +
        (LEAST(COUNT(ae.id), 1000) / 10.0 * 0.3) +
        (COUNT(DISTINCT ae.user_id) * 2.0 * 0.2) +
        (GREATEST(0, 100 - COALESCE(AVG(ae.duration), 0) / 1000) * 0.1)
    ) AS score
FROM public.agents a
LEFT JOIN public.agent_executions ae ON a.id = ae.agent_id
    AND ae.created_at >= NOW() - INTERVAL '7 days'
    AND ae.deleted_at IS NULL
WHERE a.deleted_at IS NULL
GROUP BY a.workspace_id, a.id, a.name, a.type
HAVING COUNT(ae.id) >= 5; -- Minimum 5 runs to qualify

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_agent_rankings_success_7d_pk
    ON analytics.mv_agent_rankings_success_7d(workspace_id, agent_id);

CREATE INDEX IF NOT EXISTS idx_mv_agent_rankings_success_7d_score
    ON analytics.mv_agent_rankings_success_7d(workspace_id, score DESC);

-- User Rankings by Activity (7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_user_rankings_activity_7d AS
SELECT
    u.workspace_id,
    u.id AS user_id,
    u.name AS user_name,
    u.email AS user_email,
    COUNT(DISTINCT ae.id) AS total_actions,
    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
    COALESCE(SUM(ae.credits_used), 0) AS credits_used,
    COUNT(DISTINCT ae.agent_id) AS agents_used,
    -- Score calculation (weighted formula)
    (
        (COUNT(DISTINCT ae.id) * 1.0) +
        (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.5) +
        (COUNT(DISTINCT ae.agent_id) * 5.0)
    ) AS score
FROM public.users u
LEFT JOIN public.agent_executions ae ON u.id = ae.user_id
    AND ae.created_at >= NOW() - INTERVAL '7 days'
    AND ae.deleted_at IS NULL
WHERE u.deleted_at IS NULL
GROUP BY u.workspace_id, u.id, u.name, u.email
HAVING COUNT(DISTINCT ae.id) >= 1; -- Minimum 1 action to qualify

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_user_rankings_activity_7d_pk
    ON analytics.mv_user_rankings_activity_7d(workspace_id, user_id);

CREATE INDEX IF NOT EXISTS idx_mv_user_rankings_activity_7d_score
    ON analytics.mv_user_rankings_activity_7d(workspace_id, score DESC);

-- Workspace Rankings by Activity (7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_workspace_rankings_activity_7d AS
SELECT
    w.id AS workspace_id,
    w.name AS workspace_name,
    w.plan,
    (SELECT COUNT(*) FROM public.users WHERE workspace_id = w.id AND deleted_at IS NULL) AS member_count,
    COUNT(DISTINCT ae.id) AS total_activity,
    COUNT(DISTINCT ae.user_id) AS active_users,
    COUNT(DISTINCT ae.agent_id) AS agent_count,
    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
    -- Health score (composite metric)
    ROUND(
        (
            (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.4) +
            (LEAST(COUNT(DISTINCT ae.user_id), 100) * 0.5 * 0.3) +
            (LEAST(COUNT(DISTINCT ae.agent_id), 50) * 1.0 * 0.3)
        ), 2
    ) AS health_score,
    -- Score calculation
    (
        (COUNT(DISTINCT ae.id) * 0.1) +
        (COUNT(DISTINCT ae.user_id) * 10.0) +
        (COUNT(DISTINCT ae.agent_id) * 5.0) +
        (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 1.0)
    ) AS score
FROM public.workspaces w
LEFT JOIN public.agent_executions ae ON w.id = ae.workspace_id
    AND ae.created_at >= NOW() - INTERVAL '7 days'
    AND ae.deleted_at IS NULL
WHERE w.deleted_at IS NULL
GROUP BY w.id, w.name, w.plan
HAVING COUNT(DISTINCT ae.id) >= 10; -- Minimum 10 activities to qualify

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_workspace_rankings_activity_7d_pk
    ON analytics.mv_workspace_rankings_activity_7d(workspace_id);

CREATE INDEX IF NOT EXISTS idx_mv_workspace_rankings_activity_7d_score
    ON analytics.mv_workspace_rankings_activity_7d(score DESC);

-- ===================================================================
-- COMMENTS FOR DOCUMENTATION
-- ===================================================================

COMMENT ON TABLE analytics.agent_leaderboard IS 'Competitive rankings for agents based on various performance metrics';
COMMENT ON TABLE analytics.user_leaderboard IS 'Competitive rankings for users based on activity and contribution';
COMMENT ON TABLE analytics.workspace_leaderboard IS 'Competitive rankings for workspaces based on overall performance';

COMMENT ON COLUMN analytics.agent_leaderboard.criteria IS 'Ranking criteria: runs, success_rate, speed, efficiency, popularity';
COMMENT ON COLUMN analytics.user_leaderboard.criteria IS 'Ranking criteria: activity, efficiency, contribution, savings';
COMMENT ON COLUMN analytics.workspace_leaderboard.criteria IS 'Ranking criteria: activity, efficiency, growth, innovation';

COMMENT ON FUNCTION analytics.calculate_percentile IS 'Calculates percentile ranking for a given score and rank';
COMMENT ON FUNCTION analytics.determine_rank_change IS 'Determines rank change direction: up, down, same, or new';
COMMENT ON FUNCTION analytics.assign_badge IS 'Assigns gold, silver, or bronze badge for top 3 ranks';
COMMENT ON FUNCTION analytics.assign_tier IS 'Assigns tier (platinum, gold, silver, bronze) based on percentile';
