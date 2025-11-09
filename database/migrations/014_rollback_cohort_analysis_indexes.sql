-- =====================================================================
-- Rollback Migration: 014_rollback_cohort_analysis_indexes.sql
-- Description: Rollback indexes created for cohort analysis feature
-- Rollback for: 014_create_cohort_analysis_indexes.sql
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Drop UserActivity Indexes
-- =====================================================================

DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_workspace_created;
DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_user_workspace;
DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_workspace_user_created;
DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_session_created;
DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_workspace_event_type;
DROP INDEX CONCURRENTLY IF EXISTS analytics.idx_user_activity_workspace_device;

-- =====================================================================
-- Drop ExecutionLog Indexes
-- =====================================================================

DROP INDEX CONCURRENTLY IF EXISTS public.idx_execution_log_workspace_user;
DROP INDEX CONCURRENTLY IF EXISTS public.idx_execution_log_workspace_credits;
DROP INDEX CONCURRENTLY IF EXISTS public.idx_execution_log_user_credits;

-- =====================================================================
-- Reset Statistics to Defaults
-- =====================================================================

ALTER TABLE analytics.user_activity
    ALTER COLUMN workspace_id SET STATISTICS 100,
    ALTER COLUMN user_id SET STATISTICS 100,
    ALTER COLUMN created_at SET STATISTICS 100;

ALTER TABLE public.execution_logs
    ALTER COLUMN workspace_id SET STATISTICS 100,
    ALTER COLUMN user_id SET STATISTICS 100;

-- =====================================================================
-- Refresh Statistics
-- =====================================================================

ANALYZE analytics.user_activity;
ANALYZE public.execution_logs;

-- =====================================================================
-- Verification
-- =====================================================================

-- Verify indexes were dropped:
--
-- SELECT indexname
-- FROM pg_indexes
-- WHERE schemaname IN ('analytics', 'public')
--   AND (indexname LIKE 'idx_user_activity_%' OR indexname LIKE 'idx_execution_log_%');
--
-- Expected: Should not show the dropped indexes
