-- =====================================================================
-- Migration: 014_create_cohort_analysis_indexes.sql
-- Description: Create indexes for cohort analysis and retention tracking
-- Created: 2025-11-09
-- Related: Cohort Analysis Feature (PR #XX)
-- =====================================================================

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locks
-- This requires running outside a transaction block

SET search_path TO analytics, public;

-- =====================================================================
-- UserActivity Indexes for Cohort Analysis
-- =====================================================================

-- Composite index for workspace + created_at queries (cohort date filtering)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_workspace_created
ON analytics.user_activity (workspace_id, created_at);

-- Composite index for user + workspace queries (user cohort identification)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user_workspace
ON analytics.user_activity (user_id, workspace_id);

-- Composite index for workspace + user + created_at (cohort retention queries)
-- This is the most critical index for retention calculations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_workspace_user_created
ON analytics.user_activity (workspace_id, user_id, created_at);

-- Index for session-based queries (engagement tracking)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_session_created
ON analytics.user_activity (session_id, created_at)
WHERE session_id IS NOT NULL;

-- Index for event type filtering (activation cohorts)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_workspace_event_type
ON analytics.user_activity (workspace_id, event_type);

-- Index for device type segmentation (behavioral analysis)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_workspace_device
ON analytics.user_activity (workspace_id, device_type)
WHERE device_type IS NOT NULL;

-- =====================================================================
-- ExecutionLog Indexes for LTV Calculations
-- =====================================================================

-- Composite index for workspace + user (LTV calculations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_log_workspace_user
ON public.execution_logs (workspace_id, user_id)
WHERE workspace_id IS NOT NULL AND user_id IS NOT NULL;

-- Index for credits_used aggregations (revenue calculations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_log_workspace_credits
ON public.execution_logs (workspace_id, credits_used)
WHERE workspace_id IS NOT NULL;

-- Composite index for user revenue queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_execution_log_user_credits
ON public.execution_logs (user_id, credits_used)
WHERE user_id IS NOT NULL;

-- =====================================================================
-- Statistics and Maintenance
-- =====================================================================

-- Update statistics for better query planning
ANALYZE analytics.user_activity;
ANALYZE public.execution_logs;

-- =====================================================================
-- Index Comments
-- =====================================================================

COMMENT ON INDEX analytics.idx_user_activity_workspace_created IS
    'Composite index for cohort date filtering by workspace - Target: <3s for 90-day range';

COMMENT ON INDEX analytics.idx_user_activity_user_workspace IS
    'Composite index for user cohort identification - Used in cohort membership queries';

COMMENT ON INDEX analytics.idx_user_activity_workspace_user_created IS
    'Critical index for retention calculations - Enables fast user activity lookups over time';

COMMENT ON INDEX analytics.idx_user_activity_session_created IS
    'Index for session-based engagement tracking in cohort analysis';

COMMENT ON INDEX analytics.idx_user_activity_workspace_event_type IS
    'Index for event type filtering - Supports activation and feature adoption cohorts';

COMMENT ON INDEX analytics.idx_user_activity_workspace_device IS
    'Partial index for device segmentation - Used in behavioral cohort analysis';

COMMENT ON INDEX public.idx_execution_log_workspace_user IS
    'Composite index for LTV calculations - Enables fast per-user credit aggregation';

COMMENT ON INDEX public.idx_execution_log_workspace_credits IS
    'Index for workspace revenue calculations - Used in cohort LTV metrics';

COMMENT ON INDEX public.idx_execution_log_user_credits IS
    'Index for per-user revenue queries - Supports user-level LTV analysis';

-- =====================================================================
-- Performance Tuning
-- =====================================================================

-- Set statistics target higher for frequently queried columns
ALTER TABLE analytics.user_activity
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN user_id SET STATISTICS 1000,
    ALTER COLUMN created_at SET STATISTICS 1000;

ALTER TABLE public.execution_logs
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN user_id SET STATISTICS 1000;

-- =====================================================================
-- Verification Queries
-- =====================================================================

-- To verify indexes were created successfully:
--
-- SELECT
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'analytics'
--   AND tablename = 'user_activity'
--   AND indexname LIKE 'idx_user_activity_%'
-- ORDER BY indexname;
--
-- SELECT
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
--   AND tablename = 'execution_logs'
--   AND indexname LIKE 'idx_execution_log_%'
-- ORDER BY indexname;

-- =====================================================================
-- Expected Performance Targets
-- =====================================================================
--
-- With these indexes in place:
-- - Cohort calculation: <3 seconds (90-day date range)
-- - Retention matrix: <2 seconds (single cohort, all periods)
-- - LTV calculation: <1 second (per cohort)
-- - Segment retention: <1 second (per cohort)
--
-- Monitor using:
-- SELECT * FROM pg_stat_user_indexes
-- WHERE indexrelname LIKE 'idx_user_activity_%'
--    OR indexrelname LIKE 'idx_execution_log_%';
