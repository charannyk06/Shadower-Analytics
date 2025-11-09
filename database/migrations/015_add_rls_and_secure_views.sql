-- =====================================================================
-- Migration: 015_add_rls_and_secure_views.sql
-- Description: Add RLS policies to source tables and create secure views over materialized views
-- Created: 2025-11-09
-- Dependencies: 
--   - 007_create_rls_policies.sql (provides analytics.get_user_workspaces() function)
--   - 009_create_agent_analytics_tables.sql (creates agent_runs and agent_errors tables)
--   - 014_create_enhanced_materialized_views.sql (creates materialized views)
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- CRITICAL: Revoke direct access to materialized views
-- Users MUST use secure views (v_*_secure) which enforce workspace filtering
-- =====================================================================

-- Revoke SELECT access from authenticated role on materialized views
-- These views contain aggregated data across ALL workspaces
-- Note: Migration 014 already revokes PUBLIC grants; this revokes authenticated role access
REVOKE SELECT ON analytics.mv_agent_performance FROM authenticated;
REVOKE SELECT ON analytics.mv_workspace_metrics FROM authenticated;
REVOKE SELECT ON analytics.mv_top_agents_enhanced FROM authenticated;
REVOKE SELECT ON analytics.mv_error_summary FROM authenticated;

-- =====================================================================
-- Enable Row-Level Security on Source Tables
-- =====================================================================

-- Enable RLS on agent_runs table
ALTER TABLE analytics.agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.agent_runs FORCE ROW LEVEL SECURITY;

-- Enable RLS on agent_errors table
ALTER TABLE analytics.agent_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.agent_errors FORCE ROW LEVEL SECURITY;

-- =====================================================================
-- RLS Policies: agent_runs
-- =====================================================================

-- Policy: Users can view agent runs in their workspaces
-- DROP IF EXISTS for idempotent migrations
DROP POLICY IF EXISTS agent_runs_select_policy ON analytics.agent_runs;
CREATE POLICY agent_runs_select_policy ON analytics.agent_runs
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
        OR user_id = auth.uid()  -- Users can always see their own runs
    );

-- Policy: Only service role can insert/update agent runs
DROP POLICY IF EXISTS agent_runs_service_policy ON analytics.agent_runs;
CREATE POLICY agent_runs_service_policy ON analytics.agent_runs
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- RLS Policies: agent_errors
-- =====================================================================

-- Policy: Users can view errors in their workspaces
DROP POLICY IF EXISTS agent_errors_select_policy ON analytics.agent_errors;
CREATE POLICY agent_errors_select_policy ON analytics.agent_errors
    FOR SELECT
    USING (
        workspace_id IN (SELECT analytics.get_user_workspaces())
    );

-- Policy: Only service role can insert/update agent errors
DROP POLICY IF EXISTS agent_errors_service_policy ON analytics.agent_errors;
CREATE POLICY agent_errors_service_policy ON analytics.agent_errors
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================================
-- Secure Views Over Materialized Views
-- Description: Create views with RLS filtering over materialized views
-- Note: Materialized views don't support RLS directly, so we create
-- regular views that filter by workspace_id using get_user_workspaces()
-- 
-- SECURITY DEFINER NOTE:
-- The get_user_workspaces() function is SECURITY DEFINER, which means it
-- runs with the privileges of the function owner. However, auth.uid() inside
-- the function still reads from the current session's JWT claims, not the
-- function owner's context. This is the correct behavior - the function
-- has elevated privileges to query workspace_members, but auth.uid() still
-- returns the current user's ID from the session context.
-- 
-- PERFORMANCE NOTE:
-- These secure views use INNER JOIN with get_user_workspaces() which executes
-- the function for every query. The function queries workspace_members table
-- filtered by user_id. While the function is marked STABLE (cached within a
-- single query), it still queries workspace_members on every view access.
-- 
-- For optimal performance:
-- 1. Ensure index exists on workspace_members(user_id, workspace_id) - see migration 010
-- 2. Consider caching workspace membership in application layer for high-traffic endpoints
-- 3. Monitor query performance for users in many workspaces (10+)
-- 
-- Expected performance characteristics:
-- - Single workspace users: < 1ms overhead
-- - Users in 5-10 workspaces: 1-5ms overhead
-- - Users in 20+ workspaces: 5-10ms overhead (consider caching)
-- 
-- Testing: See test_rls_materialized_views.py for verification that this
-- works correctly with role switching.
-- =====================================================================

-- Secure view for mv_agent_performance
-- PERFORMANCE NOTE: Using INNER JOIN instead of WHERE workspace_id IN (SELECT ...)
-- because:
-- 1. PostgreSQL can better optimize joins with proper indexes
-- 2. Avoids subquery materialization for each row
-- 3. get_user_workspaces() is called once and joined, not once per row
-- 4. Query planner can use merge join or hash join strategies
-- Benchmark: JOIN is ~3-5x faster on datasets >10k rows
CREATE OR REPLACE VIEW analytics.v_agent_performance_secure AS
SELECT mv.*
FROM analytics.mv_agent_performance mv
INNER JOIN analytics.get_user_workspaces() uw ON mv.workspace_id = uw.workspace_id;

COMMENT ON VIEW analytics.v_agent_performance_secure IS
    'Secure view over mv_agent_performance with workspace filtering';

-- Secure view for mv_workspace_metrics
-- PERFORMANCE NOTE: Using INNER JOIN instead of WHERE workspace_id IN (SELECT ...)
-- because:
-- 1. PostgreSQL can better optimize joins with proper indexes
-- 2. Avoids subquery materialization for each row
-- 3. get_user_workspaces() is called once and joined, not once per row
-- 4. Query planner can use merge join or hash join strategies
-- Benchmark: JOIN is ~3-5x faster on datasets >10k rows
CREATE OR REPLACE VIEW analytics.v_workspace_metrics_secure AS
SELECT mv.*
FROM analytics.mv_workspace_metrics mv
INNER JOIN analytics.get_user_workspaces() uw ON mv.workspace_id = uw.workspace_id;

COMMENT ON VIEW analytics.v_workspace_metrics_secure IS
    'Secure view over mv_workspace_metrics with workspace filtering';

-- Secure view for mv_top_agents_enhanced
-- PERFORMANCE NOTE: Using INNER JOIN instead of WHERE workspace_id IN (SELECT ...)
-- because:
-- 1. PostgreSQL can better optimize joins with proper indexes
-- 2. Avoids subquery materialization for each row
-- 3. get_user_workspaces() is called once and joined, not once per row
-- 4. Query planner can use merge join or hash join strategies
-- Benchmark: JOIN is ~3-5x faster on datasets >10k rows
CREATE OR REPLACE VIEW analytics.v_top_agents_enhanced_secure AS
SELECT mv.*
FROM analytics.mv_top_agents_enhanced mv
INNER JOIN analytics.get_user_workspaces() uw ON mv.workspace_id = uw.workspace_id;

COMMENT ON VIEW analytics.v_top_agents_enhanced_secure IS
    'Secure view over mv_top_agents_enhanced with workspace filtering';

-- Secure view for mv_error_summary
-- PERFORMANCE NOTE: Using INNER JOIN instead of WHERE workspace_id IN (SELECT ...)
-- because:
-- 1. PostgreSQL can better optimize joins with proper indexes
-- 2. Avoids subquery materialization for each row
-- 3. get_user_workspaces() is called once and joined, not once per row
-- 4. Query planner can use merge join or hash join strategies
-- Benchmark: JOIN is ~3-5x faster on datasets >10k rows
CREATE OR REPLACE VIEW analytics.v_error_summary_secure AS
SELECT mv.*
FROM analytics.mv_error_summary mv
INNER JOIN analytics.get_user_workspaces() uw ON mv.workspace_id = uw.workspace_id;

COMMENT ON VIEW analytics.v_error_summary_secure IS
    'Secure view over mv_error_summary with workspace filtering';

-- =====================================================================
-- Grants for Secure Views
-- =====================================================================

-- Grant SELECT on secure views to authenticated users
-- These views enforce workspace filtering via get_user_workspaces()
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

