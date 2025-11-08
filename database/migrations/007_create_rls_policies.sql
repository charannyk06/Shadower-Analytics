-- =====================================================================
-- Migration: 007_create_rls_policies.sql
-- Description: Implement Row-Level Security for multi-tenancy
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Enable Row-Level Security on Analytics Tables
-- =====================================================================

ALTER TABLE analytics.user_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.hourly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.agent_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.user_cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.alert_history ENABLE ROW LEVEL SECURITY;

-- =====================================================================
-- Helper Function: Get User's Workspaces
-- Description: Returns workspace IDs the current user has access to
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.get_user_workspaces()
RETURNS TABLE (workspace_id UUID)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    -- This assumes a workspace_members table exists in the public schema
    -- Adjust based on your actual schema structure
    SELECT wm.workspace_id
    FROM public.workspace_members wm
    WHERE wm.user_id = auth.uid();
$$;

COMMENT ON FUNCTION analytics.get_user_workspaces IS 'Get all workspace IDs accessible by current user';

-- =====================================================================
-- RLS Policies: user_activity
-- =====================================================================

-- Policy: Users can view activity in their workspaces
CREATE POLICY user_activity_select_policy ON analytics.user_activity
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR user_id = auth.uid()  -- Users can always see their own activity
    );

-- Policy: Users can insert their own activity
CREATE POLICY user_activity_insert_policy ON analytics.user_activity
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND (
            workspace_id IN (SELECT analytics.get_user_workspaces())
            OR workspace_id IS NULL
        )
    );

-- Policy: Service role has full access
CREATE POLICY user_activity_service_policy ON analytics.user_activity
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: daily_metrics
-- =====================================================================

-- Policy: Users can view metrics for their workspaces
CREATE POLICY daily_metrics_select_policy ON analytics.daily_metrics
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL  -- Global metrics visible to all authenticated users
    );

-- Policy: Only service role can insert/update daily metrics
CREATE POLICY daily_metrics_service_policy ON analytics.daily_metrics
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: hourly_metrics
-- =====================================================================

-- Policy: Users can view metrics for their workspaces
CREATE POLICY hourly_metrics_select_policy ON analytics.hourly_metrics
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL
    );

-- Policy: Only service role can insert/update hourly metrics
CREATE POLICY hourly_metrics_service_policy ON analytics.hourly_metrics
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: agent_performance
-- =====================================================================

-- Policy: Users can view performance for agents in their workspaces
CREATE POLICY agent_performance_select_policy ON analytics.agent_performance
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL
    );

-- Policy: Only service role can insert/update agent performance
CREATE POLICY agent_performance_service_policy ON analytics.agent_performance
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: user_cohorts
-- =====================================================================

-- Policy: Users can view cohorts for their workspaces
CREATE POLICY user_cohorts_select_policy ON analytics.user_cohorts
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL
    );

-- Policy: Only service role can insert/update cohorts
CREATE POLICY user_cohorts_service_policy ON analytics.user_cohorts
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: alert_rules
-- =====================================================================

-- Policy: Users can view alert rules for their workspaces
CREATE POLICY alert_rules_select_policy ON analytics.alert_rules
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL
    );

-- Policy: Users can create alert rules for their workspaces
CREATE POLICY alert_rules_insert_policy ON analytics.alert_rules
    FOR INSERT
    WITH CHECK (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        AND created_by = auth.uid()
    );

-- Policy: Users can update their own alert rules
CREATE POLICY alert_rules_update_policy ON analytics.alert_rules
    FOR UPDATE
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        AND created_by = auth.uid()
    );

-- Policy: Users can delete their own alert rules
CREATE POLICY alert_rules_delete_policy ON analytics.alert_rules
    FOR DELETE
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        AND created_by = auth.uid()
    );

-- Policy: Service role has full access
CREATE POLICY alert_rules_service_policy ON analytics.alert_rules
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: alert_history
-- =====================================================================

-- Policy: Users can view alert history for their workspaces
CREATE POLICY alert_history_select_policy ON analytics.alert_history
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR workspace_id IS NULL
    );

-- Policy: Users can update alert history (for acknowledgments)
CREATE POLICY alert_history_update_policy ON analytics.alert_history
    FOR UPDATE
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
    )
    WITH CHECK (
        workspace_id IN (SELECT analytics.get_user_workspaces())
    );

-- Policy: Service role has full access
CREATE POLICY alert_history_service_policy ON analytics.alert_history
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- Grant Permissions
-- =====================================================================

-- Grant select on materialized views to authenticated users
GRANT SELECT ON analytics.mv_active_users TO authenticated;
GRANT SELECT ON analytics.mv_top_agents TO authenticated;
GRANT SELECT ON analytics.mv_workspace_summary TO authenticated;
GRANT SELECT ON analytics.mv_error_trends TO authenticated;
GRANT SELECT ON analytics.mv_agent_usage_trends TO authenticated;

-- Grant execute on functions to authenticated users
GRANT EXECUTE ON FUNCTION analytics.get_workspace_metrics TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.get_agent_insights TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.get_user_workspaces TO authenticated;

-- Grant all on functions to service_role
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA analytics TO service_role;

-- Grant usage on schema
GRANT USAGE ON SCHEMA analytics TO authenticated;
GRANT ALL ON SCHEMA analytics TO service_role;

-- Grant access to tables for service_role
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO service_role;

-- Grant select access to authenticated users (RLS will filter)
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO authenticated;

-- Grant insert on user_activity to authenticated users
GRANT INSERT ON analytics.user_activity TO authenticated;

-- Grant update on alert_history to authenticated users (for acknowledgments)
GRANT UPDATE ON analytics.alert_history TO authenticated;

-- Grant full CRUD on alert_rules to authenticated users (RLS will filter)
GRANT INSERT, UPDATE, DELETE ON analytics.alert_rules TO authenticated;

-- =====================================================================
-- Comments
-- =====================================================================

COMMENT ON POLICY user_activity_select_policy ON analytics.user_activity IS
    'Users can view activity in their workspaces or their own activity';

COMMENT ON POLICY daily_metrics_select_policy ON analytics.daily_metrics IS
    'Users can view metrics for their workspaces';

COMMENT ON POLICY alert_rules_select_policy ON analytics.alert_rules IS
    'Users can view alert rules for their workspaces';

COMMENT ON POLICY alert_history_update_policy ON analytics.alert_history IS
    'Users can acknowledge alerts for their workspaces';
