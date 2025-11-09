-- =====================================================================
-- Rollback Migration: 014_rollback_enhanced_materialized_views.sql
-- Description: Rollback enhanced materialized views created in 014
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Revoke Grants
-- =====================================================================

REVOKE SELECT ON analytics.mv_agent_performance FROM authenticated;
REVOKE SELECT ON analytics.mv_workspace_metrics FROM authenticated;
REVOKE SELECT ON analytics.mv_top_agents_enhanced FROM authenticated;
REVOKE SELECT ON analytics.mv_error_summary FROM authenticated;
REVOKE SELECT ON analytics.v_materialized_view_status FROM authenticated;
REVOKE EXECUTE ON FUNCTION analytics.refresh_all_materialized_views FROM service_role, postgres;

-- =====================================================================
-- Note: RLS Policies and RLS on Materialized Views
-- =====================================================================
-- PostgreSQL does not support Row-Level Security (RLS) on materialized views.
-- The secure views (v_*_secure) created in migration 015 are regular views
-- that filter by workspace_id. These will be dropped in migration 015 rollback.
-- No RLS policies exist on materialized views themselves.

-- =====================================================================
-- Drop Utility Function
-- =====================================================================

DROP FUNCTION IF EXISTS analytics.refresh_all_materialized_views(BOOLEAN) CASCADE;

-- =====================================================================
-- Drop Metadata View
-- =====================================================================

DROP VIEW IF EXISTS analytics.v_materialized_view_status CASCADE;

-- =====================================================================
-- Drop Materialized Views (in reverse dependency order)
-- =====================================================================

-- Drop views that depend on other materialized views first
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_top_agents_enhanced CASCADE;

-- Drop independent materialized views
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_error_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_workspace_metrics CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_agent_performance CASCADE;

-- =====================================================================
-- Rollback Complete
-- =====================================================================

-- Note: This rollback script removes only the materialized views and functions
-- created in migration 014. Other materialized views from migration 004
-- (mv_active_users, mv_top_agents, mv_workspace_summary, mv_error_trends,
-- mv_agent_usage_trends) are not affected by this rollback.
