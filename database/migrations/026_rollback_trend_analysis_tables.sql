-- Migration: 026_rollback_trend_analysis_tables.sql
-- Rollback Migration for Trend Analysis Tables
-- Reverses changes made in 024_create_trend_analysis_tables.sql

-- Drop trigger first
DROP TRIGGER IF EXISTS trend_analysis_updated_at ON analytics.trend_analysis_cache;

-- Drop functions
DROP FUNCTION IF EXISTS analytics.cleanup_expired_trend_analysis();
DROP FUNCTION IF EXISTS analytics.update_trend_analysis_updated_at();

-- Drop indexes on analytics schema
DROP INDEX IF EXISTS analytics.idx_trend_analysis_data;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_calculated;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_expiry;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_workspace_user;

-- Drop composite indexes on source tables
DROP INDEX IF EXISTS public.idx_agent_executions_workspace_time;
DROP INDEX IF EXISTS public.idx_credit_transactions_workspace_time;
DROP INDEX IF EXISTS public.idx_transactions_workspace_time;

-- Drop table
DROP TABLE IF EXISTS analytics.trend_analysis_cache;

-- Log rollback
DO $$
BEGIN
    RAISE NOTICE 'Rolled back trend analysis tables migration';
END $$;
