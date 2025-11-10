-- =====================================================================
-- Migration: 016_create_workspace_analytics_tables.sql
-- Description: Create workspace analytics tables, indexes, and materialized views
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Workspace Analytics Tables
-- =====================================================================

-- Workspace daily metrics summary
CREATE TABLE IF NOT EXISTS analytics.workspace_metrics_daily (
    id BIGSERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL,
    metric_date DATE NOT NULL,
    total_members INTEGER DEFAULT 0,
    active_members INTEGER DEFAULT 0,
    total_activity INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    total_credits DECIMAL(12, 2) DEFAULT 0,
    avg_runtime_seconds DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workspace_id, metric_date)
);

-- Workspace member activity summary
CREATE TABLE IF NOT EXISTS analytics.workspace_member_activity (
    id BIGSERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    metric_date DATE NOT NULL,
    activity_count INTEGER DEFAULT 0,
    agent_runs INTEGER DEFAULT 0,
    credits_consumed DECIMAL(12, 2) DEFAULT 0,
    last_activity_at TIMESTAMP,
    engagement_level VARCHAR(20), -- 'high', 'medium', 'low'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workspace_id, user_id, metric_date)
);

-- Workspace health score history
CREATE TABLE IF NOT EXISTS analytics.workspace_health_scores (
    id BIGSERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL,
    metric_date DATE NOT NULL,
    overall_score DECIMAL(5, 2) DEFAULT 0,
    success_rate_score DECIMAL(5, 2) DEFAULT 0,
    activity_score DECIMAL(5, 2) DEFAULT 0,
    engagement_score DECIMAL(5, 2) DEFAULT 0,
    efficiency_score DECIMAL(5, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workspace_id, metric_date)
);

-- =====================================================================
-- Performance Indexes
-- =====================================================================

-- Workspace members indexes (for access control)
CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace_user
    ON public.workspace_members(workspace_id, user_id)
    WHERE workspace_id IS NOT NULL AND user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workspace_members_last_active
    ON public.workspace_members(workspace_id, last_active_at DESC)
    WHERE workspace_id IS NOT NULL AND last_active_at IS NOT NULL;

-- User activity indexes (for member analytics)
CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_time
    ON analytics.user_activity(workspace_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_activity_workspace_user_time
    ON analytics.user_activity(workspace_id, user_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

-- Agent runs indexes (for workspace analytics)
CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace_time
    ON analytics.agent_runs(workspace_id, started_at DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace_status_time
    ON analytics.agent_runs(workspace_id, status, started_at DESC)
    WHERE workspace_id IS NOT NULL;

-- Workspace metrics daily indexes
CREATE INDEX IF NOT EXISTS idx_workspace_metrics_daily_workspace_date
    ON analytics.workspace_metrics_daily(workspace_id, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_workspace_metrics_daily_date
    ON analytics.workspace_metrics_daily(metric_date DESC);

-- Workspace member activity indexes
CREATE INDEX IF NOT EXISTS idx_workspace_member_activity_workspace_date
    ON analytics.workspace_member_activity(workspace_id, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_workspace_member_activity_user_date
    ON analytics.workspace_member_activity(user_id, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_workspace_member_activity_engagement
    ON analytics.workspace_member_activity(workspace_id, engagement_level, metric_date DESC)
    WHERE engagement_level IS NOT NULL;

-- Workspace health scores indexes
CREATE INDEX IF NOT EXISTS idx_workspace_health_scores_workspace_date
    ON analytics.workspace_health_scores(workspace_id, metric_date DESC);

-- =====================================================================
-- Materialized Views for Comparison Queries
-- =====================================================================

-- Workspace comparison view (for comparing workspaces)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.workspace_comparison_mv AS
SELECT
    workspace_id,
    AVG(overall_score) as avg_health_score,
    AVG(success_rate_score) as avg_success_rate,
    AVG(activity_score) as avg_activity_score,
    AVG(engagement_score) as avg_engagement_score,
    COUNT(DISTINCT metric_date) as days_tracked,
    MAX(metric_date) as last_updated
FROM analytics.workspace_health_scores
WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY workspace_id;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_workspace_comparison_mv_workspace
    ON analytics.workspace_comparison_mv(workspace_id);

-- Workspace activity trends view (for trend analysis)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.workspace_activity_trends_mv AS
SELECT
    workspace_id,
    DATE_TRUNC('week', metric_date) as week_start,
    AVG(active_members) as avg_active_members,
    AVG(total_activity) as avg_total_activity,
    AVG(successful_runs) as avg_successful_runs,
    SUM(total_credits) as total_credits,
    COUNT(*) as days_in_period
FROM analytics.workspace_metrics_daily
WHERE metric_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY workspace_id, DATE_TRUNC('week', metric_date);

-- Create index on activity trends view
CREATE INDEX IF NOT EXISTS idx_workspace_activity_trends_mv_workspace_week
    ON analytics.workspace_activity_trends_mv(workspace_id, week_start DESC);

-- =====================================================================
-- Functions for Materialized View Refresh
-- =====================================================================

-- Function to refresh workspace comparison view
CREATE OR REPLACE FUNCTION analytics.refresh_workspace_comparison_mv()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.workspace_comparison_mv;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh workspace activity trends view
CREATE OR REPLACE FUNCTION analytics.refresh_workspace_activity_trends_mv()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.workspace_activity_trends_mv;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh all workspace analytics views
CREATE OR REPLACE FUNCTION analytics.refresh_all_workspace_analytics_mv()
RETURNS void AS $$
BEGIN
    PERFORM analytics.refresh_workspace_comparison_mv();
    PERFORM analytics.refresh_workspace_activity_trends_mv();
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Comments for Documentation
-- =====================================================================

COMMENT ON TABLE analytics.workspace_metrics_daily IS 'Daily aggregated metrics for each workspace';
COMMENT ON TABLE analytics.workspace_member_activity IS 'Daily member activity tracking per workspace';
COMMENT ON TABLE analytics.workspace_health_scores IS 'Historical workspace health scores';
COMMENT ON MATERIALIZED VIEW analytics.workspace_comparison_mv IS 'Workspace comparison metrics for last 30 days';
COMMENT ON MATERIALIZED VIEW analytics.workspace_activity_trends_mv IS 'Weekly activity trends for workspaces (last 90 days)';

-- =====================================================================
-- Grant Permissions
-- =====================================================================

-- Grant SELECT on tables to analytics role (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_reader') THEN
        GRANT SELECT ON analytics.workspace_metrics_daily TO analytics_reader;
        GRANT SELECT ON analytics.workspace_member_activity TO analytics_reader;
        GRANT SELECT ON analytics.workspace_health_scores TO analytics_reader;
        GRANT SELECT ON analytics.workspace_comparison_mv TO analytics_reader;
        GRANT SELECT ON analytics.workspace_activity_trends_mv TO analytics_reader;
    END IF;
END $$;

-- =====================================================================
-- Migration Complete
-- =====================================================================

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 010_create_workspace_analytics_tables.sql completed successfully';
END $$;
