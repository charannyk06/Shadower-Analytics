-- =====================================================================
-- Migration: 014_create_enhanced_materialized_views.sql
-- Description: Create enhanced materialized views for complex aggregations
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Materialized View: mv_agent_performance
-- Description: Agent performance summary from agent_runs
-- Refresh: Daily
-- Dependencies: public.agent_runs
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
FROM public.agent_runs ar
WHERE ar.started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ar.agent_id, ar.workspace_id, DATE(ar.started_at);

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_agent_performance_unique
    ON analytics.mv_agent_performance(agent_id, run_date);

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
-- Dependencies: public.agent_runs
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
    FROM public.agent_runs
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

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_mv_top_agents_enhanced_unique
    ON analytics.mv_top_agents_enhanced(agent_id);

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
-- Dependencies: public.agent_errors
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
    COUNT(DISTINCT ae.user_id) as affected_users,
    COUNT(DISTINCT ae.agent_id) as affected_agents,
    ARRAY_AGG(DISTINCT ae.error_message ORDER BY ae.error_message)
        FILTER (WHERE ae.error_message IS NOT NULL)
        [1:5] as sample_messages,
    MIN(ae.created_at) as first_occurrence,
    MAX(ae.created_at) as last_occurrence
FROM public.agent_errors ae
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
CREATE UNIQUE INDEX idx_mv_error_summary_unique
    ON analytics.mv_error_summary(
        error_date,
        COALESCE(workspace_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(agent_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(error_type, 'unknown'),
        COALESCE(error_category, 'unknown'),
        COALESCE(error_severity, 'unknown')
    );

-- Additional indexes
CREATE INDEX idx_mv_error_summary_date
    ON analytics.mv_error_summary(error_date DESC);
CREATE INDEX idx_mv_error_summary_workspace
    ON analytics.mv_error_summary(workspace_id, error_date DESC);
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
            -- Build refresh command
            v_refresh_command := 'REFRESH MATERIALIZED VIEW ' ||
                CASE WHEN concurrent_mode THEN 'CONCURRENTLY ' ELSE '' END ||
                'analytics.' || v_view.matviewname;

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
-- =====================================================================

-- Populate all new materialized views
REFRESH MATERIALIZED VIEW analytics.mv_agent_performance;
REFRESH MATERIALIZED VIEW analytics.mv_workspace_metrics;
REFRESH MATERIALIZED VIEW analytics.mv_top_agents_enhanced;
REFRESH MATERIALIZED VIEW analytics.mv_error_summary;

-- =====================================================================
-- Grants
-- =====================================================================

-- Grant SELECT on all materialized views to analytics users
GRANT SELECT ON analytics.mv_agent_performance TO PUBLIC;
GRANT SELECT ON analytics.mv_workspace_metrics TO PUBLIC;
GRANT SELECT ON analytics.mv_top_agents_enhanced TO PUBLIC;
GRANT SELECT ON analytics.mv_error_summary TO PUBLIC;
GRANT SELECT ON analytics.v_materialized_view_status TO PUBLIC;

-- Grant EXECUTE on refresh function (restrict to admin roles in production)
GRANT EXECUTE ON FUNCTION analytics.refresh_all_materialized_views TO PUBLIC;

-- =====================================================================
-- Migration Complete
-- =====================================================================
