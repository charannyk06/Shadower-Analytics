-- =====================================================================
-- Migration: 015_add_rls_and_secure_views.sql
-- Description: Add RLS policies to source tables and create secure views over materialized views
-- Created: 2025-11-09
-- Dependencies: 009_create_agent_analytics_tables.sql, 014_create_enhanced_materialized_views.sql
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Enable Row-Level Security on Source Tables
-- =====================================================================

-- Enable RLS on agent_runs table
ALTER TABLE analytics.agent_runs ENABLE ROW LEVEL SECURITY;

-- Enable RLS on agent_errors table
ALTER TABLE analytics.agent_errors ENABLE ROW LEVEL SECURITY;

-- =====================================================================
-- RLS Policies: agent_runs
-- =====================================================================

-- Policy: Users can view agent runs in their workspaces
CREATE POLICY agent_runs_select_policy ON analytics.agent_runs
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR user_id = auth.uid()  -- Users can always see their own runs
    );

-- Policy: Only service role can insert/update agent runs
CREATE POLICY agent_runs_service_policy ON analytics.agent_runs
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: agent_errors
-- =====================================================================

-- Policy: Users can view errors in their workspaces
CREATE POLICY agent_errors_select_policy ON analytics.agent_errors
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
    );

-- Policy: Only service role can insert/update agent errors
CREATE POLICY agent_errors_service_policy ON analytics.agent_errors
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- Secure Views Over Materialized Views
-- Description: Create views with RLS filtering over materialized views
-- Note: Materialized views don't support RLS directly, so we create
-- regular views that filter by workspace_id using get_user_workspaces()
-- =====================================================================

-- Secure view for mv_agent_performance
CREATE OR REPLACE VIEW analytics.v_agent_performance_secure AS
SELECT *
FROM analytics.mv_agent_performance
WHERE workspace_id IN (SELECT analytics.get_user_workspaces());

COMMENT ON VIEW analytics.v_agent_performance_secure IS
    'Secure view over mv_agent_performance with workspace filtering';

-- Secure view for mv_workspace_metrics
CREATE OR REPLACE VIEW analytics.v_workspace_metrics_secure AS
SELECT *
FROM analytics.mv_workspace_metrics
WHERE workspace_id IN (SELECT analytics.get_user_workspaces());

COMMENT ON VIEW analytics.v_workspace_metrics_secure IS
    'Secure view over mv_workspace_metrics with workspace filtering';

-- Secure view for mv_top_agents_enhanced
CREATE OR REPLACE VIEW analytics.v_top_agents_enhanced_secure AS
SELECT *
FROM analytics.mv_top_agents_enhanced
WHERE workspace_id IN (SELECT analytics.get_user_workspaces());

COMMENT ON VIEW analytics.v_top_agents_enhanced_secure IS
    'Secure view over mv_top_agents_enhanced with workspace filtering';

-- Secure view for mv_error_summary
CREATE OR REPLACE VIEW analytics.v_error_summary_secure AS
SELECT *
FROM analytics.mv_error_summary
WHERE workspace_id IN (SELECT analytics.get_user_workspaces());

COMMENT ON VIEW analytics.v_error_summary_secure IS
    'Secure view over mv_error_summary with workspace filtering';

-- =====================================================================
-- Grants for Secure Views
-- =====================================================================

-- Revoke PUBLIC grants on materialized views (will be done in migration 014 fix)
-- Grant SELECT on secure views to authenticated users
GRANT SELECT ON analytics.v_agent_performance_secure TO authenticated;
GRANT SELECT ON analytics.v_workspace_metrics_secure TO authenticated;
GRANT SELECT ON analytics.v_top_agents_enhanced_secure TO authenticated;
GRANT SELECT ON analytics.v_error_summary_secure TO authenticated;

-- Grant SELECT on source tables to authenticated users (RLS will filter)
GRANT SELECT ON analytics.agent_runs TO authenticated;
GRANT SELECT ON analytics.agent_errors TO authenticated;

-- =====================================================================
-- Comments
-- =====================================================================

COMMENT ON POLICY agent_runs_select_policy ON analytics.agent_runs IS
    'Users can view agent runs in their workspaces or their own runs';

COMMENT ON POLICY agent_errors_select_policy ON analytics.agent_errors IS
    'Users can view errors in their workspaces';

-- =====================================================================
-- Migration Complete
-- =====================================================================

