-- =====================================================================
-- Procedure: refresh_materialized_views.sql
-- Description: Refresh all analytics materialized views
-- Usage: psql -f database/procedures/refresh_materialized_views.sql
-- =====================================================================

SET search_path TO analytics, public;

-- Refresh all materialized views concurrently
SELECT analytics.refresh_all_materialized_views();

-- Display refresh completion time
SELECT
    'mv_active_users' as view_name,
    pg_size_pretty(pg_total_relation_size('analytics.mv_active_users')) as size,
    (SELECT COUNT(*) FROM analytics.mv_active_users) as row_count
UNION ALL
SELECT
    'mv_top_agents',
    pg_size_pretty(pg_total_relation_size('analytics.mv_top_agents')),
    (SELECT COUNT(*) FROM analytics.mv_top_agents)
UNION ALL
SELECT
    'mv_workspace_summary',
    pg_size_pretty(pg_total_relation_size('analytics.mv_workspace_summary')),
    (SELECT COUNT(*) FROM analytics.mv_workspace_summary)
UNION ALL
SELECT
    'mv_error_trends',
    pg_size_pretty(pg_total_relation_size('analytics.mv_error_trends')),
    (SELECT COUNT(*) FROM analytics.mv_error_trends)
UNION ALL
SELECT
    'mv_agent_usage_trends',
    pg_size_pretty(pg_total_relation_size('analytics.mv_agent_usage_trends')),
    (SELECT COUNT(*) FROM analytics.mv_agent_usage_trends);
