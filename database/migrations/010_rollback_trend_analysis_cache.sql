-- Rollback migration for trend analysis cache
-- This script safely removes the trend analysis cache infrastructure

-- Drop trigger first
DROP TRIGGER IF EXISTS trend_analysis_updated_at
    ON analytics.trend_analysis_cache;

-- Drop trigger function
DROP FUNCTION IF EXISTS analytics.update_trend_analysis_updated_at();

-- Drop cleanup function
DROP FUNCTION IF EXISTS analytics.cleanup_expired_trend_cache();

-- Drop indexes
DROP INDEX IF EXISTS analytics.idx_trend_analysis_lookup;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_calculated;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_expires;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_workspace;

-- Drop the main table
DROP TABLE IF EXISTS analytics.trend_analysis_cache;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Trend analysis cache infrastructure successfully removed';
END $$;
