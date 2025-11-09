-- =====================================================================
-- Migration: 014_create_enhanced_materialized_views.sql
-- Description: Create enhanced materialized views for complex aggregations
-- Created: 2025-11-09
-- 
-- Creates:
-- - mv_agent_performance (materialized view + 4 indexes)
-- - mv_workspace_metrics (materialized view + 4 indexes)
-- - mv_top_agents_enhanced (materialized view + 2 indexes)
-- - mv_error_summary (materialized view + 4 indexes)
-- - v_materialized_view_status (view)
-- - analytics.refresh_all_materialized_views() (function)
-- 
-- Rollback: See 014_rollback_enhanced_materialized_views.sql
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Materialized View: mv_agent_performance
-- Description: Agent performance summary from agent_runs
-- Refresh: Daily
-- Dependencies: analytics.agent_runs
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_agent_performance AS
SELECT
    ar.agent_id,
    ar.workspace_id,
    DATE(ar.started_at) as run_date,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE ar.status = 'completed') as successful_runs,
    AVG(ar.runtime_seconds) as avg_runtime,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ar.runtime_seconds) as median_runtime,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ar.runtime_seconds) as p95_runtime,
    SUM(ar.credits_consumed) as total_credits
FROM analytics.agent_runs ar
WHERE ar.started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ar.agent_id, ar.workspace_id, DATE(ar.started_at);

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_agent_performance_unique
    ON analytics.mv_agent_performance(agent_id, workspace_id, run_date);

-- Additional indexes for performance
CREATE INDEX idx_mv_agent_performance_workspace
    ON analytics.mv_agent_performance(workspace_id, run_date DESC);
CREATE INDEX idx_mv_agent_performance_date
    ON analytics.mv_agent_performance(run_date DESC);
CREATE INDEX idx_mv_agent_performance_runs
    ON analytics.mv_agent_performance(total_runs DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_agent_performance IS 'Agent performance metrics aggregated from agent_runs - last 30 days';

-- =====================================================================
-- Materialized View: mv_workspace_metrics
-- Description: Workspace-level metrics summary
-- Refresh: Daily
-- Dependencies: analytics.agent_runs
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_workspace_metrics AS
WITH workspace_stats AS (
    SELECT
        workspace_id,
        user_id,
        agent_id,
        COUNT(*) as total_runs,
        AVG(CASE WHEN status = 'completed' THEN 100.0 ELSE 0 END) as success_rate,
        SUM(credits_consumed) as credits_consumed,
        MAX(started_at) as last_activity
    FROM analytics.agent_runs
    WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workspace_id, user_id, agent_id
)
SELECT
    workspace_id,
    COUNT(DISTINCT user_id) as total_users,
    COUNT(DISTINCT agent_id) as total_agents,
    SUM(total_runs) as total_executions,
    AVG(success_rate) as avg_success_rate,
    SUM(credits_consumed) as total_credits_consumed,
    MAX(last_activity) as last_activity_at
FROM workspace_stats
GROUP BY workspace_id;

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_workspace_metrics_unique
    ON analytics.mv_workspace_metrics(workspace_id);

-- Additional indexes
CREATE INDEX idx_mv_workspace_metrics_executions
    ON analytics.mv_workspace_metrics(total_executions DESC);
CREATE INDEX idx_mv_workspace_metrics_credits
    ON analytics.mv_workspace_metrics(total_credits_consumed DESC);
CREATE INDEX idx_mv_workspace_metrics_activity
    ON analytics.mv_workspace_metrics(last_activity_at DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_workspace_metrics IS 'Workspace-level aggregated metrics from agent runs - last 30 days';

-- =====================================================================
-- Materialized View: mv_top_agents_enhanced
-- Description: Enhanced top agents ranking with additional metrics
-- Refresh: Daily
-- Dependencies: analytics.mv_agent_performance
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_top_agents_enhanced AS
WITH agent_metrics AS (
    SELECT
        agent_id,
        workspace_id,
        SUM(total_runs) as total_runs,
        SUM(successful_runs) as successful_runs,
        AVG(avg_runtime) as avg_runtime,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_runtime) as overall_median_runtime,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY p95_runtime) as overall_p95_runtime,
        SUM(total_credits) as total_credits,
        COUNT(DISTINCT run_date) as active_days
    FROM analytics.mv_agent_performance
    WHERE run_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY agent_id, workspace_id
)
SELECT
    agent_id,
    workspace_id,
    total_runs,
    successful_runs,
    COALESCE(
        (successful_runs::NUMERIC / NULLIF(total_runs, 0)) * 100,
        0
    ) as success_rate,
    avg_runtime,
    overall_median_runtime as median_runtime,
    overall_p95_runtime as p95_runtime,
    total_credits,
    active_days,
    RANK() OVER (ORDER BY total_runs DESC) as rank_by_runs,
    RANK() OVER (ORDER BY successful_runs DESC) as rank_by_success,
    RANK() OVER (ORDER BY total_credits DESC) as rank_by_credits
FROM agent_metrics
WHERE total_runs > 0
ORDER BY total_runs DESC;

-- Unique index for concurrent refresh (include workspace_id for multi-tenancy)
CREATE UNIQUE INDEX idx_mv_top_agents_enhanced_unique
    ON analytics.mv_top_agents_enhanced(agent_id, workspace_id);

-- Additional indexes
CREATE INDEX idx_mv_top_agents_enhanced_workspace
    ON analytics.mv_top_agents_enhanced(workspace_id, total_runs DESC);
CREATE INDEX idx_mv_top_agents_enhanced_success_rate
    ON analytics.mv_top_agents_enhanced(success_rate DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_top_agents_enhanced IS 'Enhanced top agents with rankings by multiple criteria - last 30 days';

-- =====================================================================
-- Materialized View: mv_error_summary
-- Description: Error summary and patterns
-- Refresh: Hourly
-- Dependencies: analytics.agent_errors
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_error_summary AS
SELECT
    DATE(ae.created_at) as error_date,
    ae.workspace_id,
    ae.agent_id,
    ae.error_type,
    ae.error_category,
    ae.error_severity,
    COUNT(*) as error_count,
    -- Get affected users from agent_runs via agent_run_id
    COUNT(DISTINCT ar.user_id) FILTER (WHERE ar.user_id IS NOT NULL) as affected_users,
    COUNT(DISTINCT ae.agent_id) as affected_agents,
    ARRAY_AGG(DISTINCT ae.error_message ORDER BY ae.error_message)
        FILTER (WHERE ae.error_message IS NOT NULL)
        [1:5] as sample_messages,
    MIN(ae.created_at) as first_occurrence,
    MAX(ae.created_at) as last_occurrence
FROM analytics.agent_errors ae
LEFT JOIN analytics.agent_runs ar ON ae.agent_run_id = ar.id
WHERE ae.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
    DATE(ae.created_at),
    ae.workspace_id,
    ae.agent_id,
    ae.error_type,
    ae.error_category,
    ae.error_severity
ORDER BY error_date DESC, error_count DESC;

-- Unique index for concurrent refresh
-- Using partial index to exclude NULLs since source table has NOT NULL constraints
CREATE UNIQUE INDEX idx_mv_error_summary_unique
    ON analytics.mv_error_summary(
        error_date,
        workspace_id,
        agent_id,
        error_type,
        error_category,
        error_severity
    )
    WHERE workspace_id IS NOT NULL 
        AND agent_id IS NOT NULL 
        AND error_type IS NOT NULL 
        AND error_category IS NOT NULL 
        AND error_severity IS NOT NULL;

-- Additional indexes
CREATE INDEX idx_mv_error_summary_date
    ON analytics.mv_error_summary(error_date DESC);
CREATE INDEX idx_mv_error_summary_workspace
    ON analytics.mv_error_summary(workspace_id, error_date DESC);
CREATE INDEX idx_mv_error_summary_agent
    ON analytics.mv_error_summary(agent_id, error_date DESC);
CREATE INDEX idx_mv_error_summary_severity
    ON analytics.mv_error_summary(error_severity, error_count DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_error_summary IS 'Error summary with patterns and severity levels - last 30 days';

-- =====================================================================
-- View for Materialized View Metadata
-- Description: Track all materialized views and their refresh status
-- =====================================================================

CREATE OR REPLACE VIEW analytics.v_materialized_view_status AS
SELECT
    schemaname,
    matviewname as view_name,
    matviewowner as owner,
    tablespace,
    hasindexes,
    ispopulated,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||matviewname)) as data_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname) -
                   pg_relation_size(schemaname||'.'||matviewname)) as index_size,
    obj_description((schemaname||'.'||matviewname)::regclass, 'pg_class') as description
FROM pg_matviews
WHERE schemaname = 'analytics'
ORDER BY matviewname;

-- Comments
COMMENT ON VIEW analytics.v_materialized_view_status IS 'Metadata and status of all materialized views in analytics schema';

-- =====================================================================
-- Function: Refresh all materialized views
-- Description: Utility function to refresh all materialized views
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_all_materialized_views(
    concurrent_mode BOOLEAN DEFAULT TRUE
)
RETURNS TABLE(
    view_name TEXT,
    refresh_started_at TIMESTAMPTZ,
    refresh_completed_at TIMESTAMPTZ,
    duration_seconds NUMERIC,
    success BOOLEAN,
    error_message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_view RECORD;
    v_start_time TIMESTAMPTZ;
    v_end_time TIMESTAMPTZ;
    v_refresh_command TEXT;
BEGIN
    -- Refresh each materialized view
    FOR v_view IN
        SELECT matviewname
        FROM pg_matviews
        WHERE schemaname = 'analytics'
        ORDER BY matviewname
    LOOP
        v_start_time := clock_timestamp();

        BEGIN
            -- Build refresh command using format() with %I for identifier escaping
            -- This prevents SQL injection if pg_matviews metadata is compromised
            -- Use separate format() calls to ensure both schema and view name are escaped
            IF concurrent_mode THEN
                v_refresh_command := format(
                    'REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I',
                    'analytics',
                    v_view.matviewname
                );
            ELSE
                v_refresh_command := format(
                    'REFRESH MATERIALIZED VIEW %I.%I',
                    'analytics',
                    v_view.matviewname
                );
            END IF;

            -- Execute refresh
            EXECUTE v_refresh_command;

            v_end_time := clock_timestamp();

            -- Return success record
            RETURN QUERY SELECT
                v_view.matviewname::TEXT,
                v_start_time,
                v_end_time,
                EXTRACT(EPOCH FROM (v_end_time - v_start_time))::NUMERIC,
                TRUE,
                NULL::TEXT;

        EXCEPTION WHEN OTHERS THEN
            v_end_time := clock_timestamp();

            -- Return error record
            RETURN QUERY SELECT
                v_view.matviewname::TEXT,
                v_start_time,
                v_end_time,
                EXTRACT(EPOCH FROM (v_end_time - v_start_time))::NUMERIC,
                FALSE,
                SQLERRM::TEXT;
        END;
    END LOOP;
END;
$$;

-- Comments
COMMENT ON FUNCTION analytics.refresh_all_materialized_views IS
    'Refresh all materialized views in analytics schema with error handling and timing';

-- =====================================================================
-- Initial population of materialized views
-- NOTE: Commented out to prevent migration timeouts on large datasets.
-- Run these manually after migration completes:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_agent_performance;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_workspace_metrics;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_top_agents_enhanced;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_error_summary;
-- =====================================================================

-- REFRESH MATERIALIZED VIEW analytics.mv_agent_performance;
-- REFRESH MATERIALIZED VIEW analytics.mv_workspace_metrics;
-- REFRESH MATERIALIZED VIEW analytics.mv_top_agents_enhanced;
-- REFRESH MATERIALIZED VIEW analytics.mv_error_summary;

-- =====================================================================
-- Grants
-- =====================================================================

-- Note: PostgreSQL does not support RLS directly on materialized views.
-- RLS policies and secure views are created in migration 015_add_rls_and_secure_views.sql

-- Revoke any existing PUBLIC grants (defense in depth)
REVOKE ALL ON analytics.mv_agent_performance FROM PUBLIC;
REVOKE ALL ON analytics.mv_workspace_metrics FROM PUBLIC;
REVOKE ALL ON analytics.mv_top_agents_enhanced FROM PUBLIC;
REVOKE ALL ON analytics.mv_error_summary FROM PUBLIC;
REVOKE ALL ON analytics.v_materialized_view_status FROM PUBLIC;
REVOKE ALL ON FUNCTION analytics.refresh_all_materialized_views FROM PUBLIC;

-- Grant SELECT on all materialized views to authenticated users only
-- Note: Direct access to materialized views should be restricted.
-- Use secure views (v_*_secure) created in migration 015 for workspace-filtered access.
GRANT SELECT ON analytics.mv_agent_performance TO authenticated;
GRANT SELECT ON analytics.mv_workspace_metrics TO authenticated;
GRANT SELECT ON analytics.mv_top_agents_enhanced TO authenticated;
GRANT SELECT ON analytics.mv_error_summary TO authenticated;
GRANT SELECT ON analytics.v_materialized_view_status TO authenticated;

-- Grant EXECUTE on refresh function only to service_role
-- Admin API endpoints will use service_role connection for refresh operations
GRANT EXECUTE ON FUNCTION analytics.refresh_all_materialized_views TO service_role;

-- =====================================================================
-- Migration Complete
-- =====================================================================
