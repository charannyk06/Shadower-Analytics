-- =====================================================================
-- Migration: 004_create_materialized_views.sql
-- Description: Create materialized views for performance optimization
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Materialized View: mv_active_users
-- Description: Active users summary (DAU, WAU, MAU)
-- Refresh: Daily
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_active_users AS
WITH user_activity_combined AS (
    -- From analytics.user_activity table
    SELECT
        DATE(created_at) as activity_date,
        user_id,
        workspace_id
    FROM analytics.user_activity
    WHERE created_at >= NOW() - INTERVAL '90 days'
)
SELECT
    activity_date,
    workspace_id,
    COUNT(DISTINCT user_id) as daily_active_users,
    COUNT(DISTINCT user_id) FILTER (
        WHERE activity_date >= CURRENT_DATE - INTERVAL '7 days'
    ) as weekly_active_users,
    COUNT(DISTINCT user_id) FILTER (
        WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days'
    ) as monthly_active_users
FROM user_activity_combined
GROUP BY activity_date, workspace_id;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_active_users
    ON analytics.mv_active_users(activity_date, COALESCE(workspace_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_active_users IS 'Active users by day/week/month - refresh daily';

-- =====================================================================
-- Materialized View: mv_top_agents
-- Description: Top performing agents over last 30 days
-- Refresh: Daily
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_top_agents AS
SELECT
    ap.agent_id,
    ap.workspace_id,
    SUM(ap.total_runs) as total_runs_30d,
    SUM(ap.successful_runs) as successful_runs_30d,
    SUM(ap.failed_runs) as failed_runs_30d,
    COALESCE(
        (SUM(ap.successful_runs)::NUMERIC / NULLIF(SUM(ap.total_runs), 0)) * 100,
        0
    ) as success_rate,
    AVG(ap.avg_runtime_seconds) as avg_runtime,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ap.p50_runtime_seconds) as median_runtime,
    SUM(ap.total_credits) as total_credits_30d,
    SUM(ap.unique_users) as unique_users_30d,
    MAX(ap.metric_date) as last_active_date
FROM analytics.agent_performance ap
WHERE ap.metric_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ap.agent_id, ap.workspace_id
ORDER BY total_runs_30d DESC;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_top_agents
    ON analytics.mv_top_agents(agent_id);

-- Additional indexes
CREATE INDEX idx_mv_top_agents_workspace
    ON analytics.mv_top_agents(workspace_id, total_runs_30d DESC);
CREATE INDEX idx_mv_top_agents_success_rate
    ON analytics.mv_top_agents(success_rate DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_top_agents IS 'Top performing agents by runs, success rate, and credits - last 30 days';

-- =====================================================================
-- Materialized View: mv_workspace_summary
-- Description: Workspace-level summary metrics
-- Refresh: Daily
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_workspace_summary AS
WITH workspace_stats AS (
    SELECT
        dm.workspace_id,
        COUNT(DISTINCT dm.metric_date) as days_active,
        SUM(dm.total_users) as total_users,
        AVG(dm.active_users) as avg_daily_active_users,
        SUM(dm.total_runs) as total_runs_30d,
        SUM(dm.successful_runs) as successful_runs_30d,
        SUM(dm.failed_runs) as failed_runs_30d,
        SUM(dm.total_credits_consumed) as total_credits_30d,
        AVG(dm.avg_runtime_seconds) as avg_runtime_30d,
        AVG(dm.error_rate) as avg_error_rate
    FROM analytics.daily_metrics dm
    WHERE dm.metric_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY dm.workspace_id
),
agent_count AS (
    SELECT
        workspace_id,
        COUNT(DISTINCT agent_id) as total_agents
    FROM analytics.agent_performance
    WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workspace_id
)
SELECT
    ws.workspace_id,
    ws.days_active,
    ws.total_users,
    ws.avg_daily_active_users,
    COALESCE(ac.total_agents, 0) as total_agents,
    ws.total_runs_30d,
    ws.successful_runs_30d,
    ws.failed_runs_30d,
    COALESCE(
        (ws.successful_runs_30d::NUMERIC / NULLIF(ws.total_runs_30d, 0)) * 100,
        0
    ) as success_rate,
    ws.total_credits_30d,
    ws.avg_runtime_30d,
    ws.avg_error_rate
FROM workspace_stats ws
LEFT JOIN agent_count ac ON ws.workspace_id = ac.workspace_id;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_workspace_summary
    ON analytics.mv_workspace_summary(COALESCE(workspace_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- Additional indexes
CREATE INDEX idx_mv_workspace_summary_runs
    ON analytics.mv_workspace_summary(total_runs_30d DESC);
CREATE INDEX idx_mv_workspace_summary_credits
    ON analytics.mv_workspace_summary(total_credits_30d DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_workspace_summary IS 'Workspace-level summary statistics for last 30 days';

-- =====================================================================
-- Materialized View: mv_error_trends
-- Description: Error trends and patterns
-- Refresh: Hourly/Daily
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_error_trends AS
WITH error_events AS (
    SELECT
        DATE(created_at) as error_date,
        workspace_id,
        event_name,
        metadata->>'error_type' as error_type,
        metadata->>'error_message' as error_message,
        COUNT(*) as error_count
    FROM analytics.user_activity
    WHERE event_type = 'error'
        AND created_at >= NOW() - INTERVAL '30 days'
    GROUP BY
        DATE(created_at),
        workspace_id,
        event_name,
        metadata->>'error_type',
        metadata->>'error_message'
)
SELECT
    error_date,
    workspace_id,
    error_type,
    event_name,
    SUM(error_count) as total_errors,
    COUNT(DISTINCT error_message) as unique_error_messages,
    ARRAY_AGG(DISTINCT error_message ORDER BY error_message) FILTER (WHERE error_message IS NOT NULL) as sample_messages
FROM error_events
GROUP BY error_date, workspace_id, error_type, event_name
ORDER BY error_date DESC, total_errors DESC;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_error_trends
    ON analytics.mv_error_trends(
        error_date,
        COALESCE(workspace_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(error_type, 'unknown'),
        COALESCE(event_name, 'unknown')
    );

-- Additional indexes
CREATE INDEX idx_mv_error_trends_date
    ON analytics.mv_error_trends(error_date DESC);
CREATE INDEX idx_mv_error_trends_workspace
    ON analytics.mv_error_trends(workspace_id, error_date DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_error_trends IS 'Error trends and patterns for debugging and monitoring';

-- =====================================================================
-- Materialized View: mv_agent_usage_trends
-- Description: Agent usage trends over time
-- Refresh: Daily
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_agent_usage_trends AS
WITH daily_agent_stats AS (
    SELECT
        metric_date,
        agent_id,
        workspace_id,
        total_runs,
        successful_runs,
        failed_runs,
        avg_runtime_seconds,
        total_credits,
        unique_users,
        LAG(total_runs, 7) OVER (PARTITION BY agent_id ORDER BY metric_date) as runs_7d_ago,
        LAG(successful_runs, 7) OVER (PARTITION BY agent_id ORDER BY metric_date) as success_7d_ago
    FROM analytics.agent_performance
    WHERE metric_date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    metric_date,
    agent_id,
    workspace_id,
    total_runs,
    successful_runs,
    failed_runs,
    COALESCE((successful_runs::NUMERIC / NULLIF(total_runs, 0)) * 100, 0) as success_rate,
    avg_runtime_seconds,
    total_credits,
    unique_users,
    -- Week-over-week growth
    CASE
        WHEN runs_7d_ago IS NOT NULL AND runs_7d_ago > 0
        THEN ((total_runs - runs_7d_ago)::NUMERIC / runs_7d_ago) * 100
        ELSE NULL
    END as wow_growth_rate,
    CASE
        WHEN total_runs > COALESCE(runs_7d_ago, 0) THEN 'growing'
        WHEN total_runs < COALESCE(runs_7d_ago, 0) THEN 'declining'
        ELSE 'stable'
    END as trend_direction
FROM daily_agent_stats
WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY metric_date DESC, total_runs DESC;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_agent_usage_trends
    ON analytics.mv_agent_usage_trends(metric_date, agent_id);

-- Additional indexes
CREATE INDEX idx_mv_agent_usage_trends_agent
    ON analytics.mv_agent_usage_trends(agent_id, metric_date DESC);
CREATE INDEX idx_mv_agent_usage_trends_workspace
    ON analytics.mv_agent_usage_trends(workspace_id, metric_date DESC);
CREATE INDEX idx_mv_agent_usage_trends_growth
    ON analytics.mv_agent_usage_trends(wow_growth_rate DESC NULLS LAST);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_agent_usage_trends IS 'Agent usage trends with week-over-week growth metrics';
