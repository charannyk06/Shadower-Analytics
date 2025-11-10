-- Migration: 019_rollback_trend_analysis_cache_user_id.sql
-- Rollback migration for 018_update_trend_analysis_cache_add_user_id.sql
-- This script reverts the user_id changes to the trend_analysis_cache table
--
-- WARNING: This rollback will clear the cache and remove user-scoped security.
-- Only use this if the migration causes critical issues in production.

-- Step 1: Clear cache (since entries with user_id can't exist in old schema)
DELETE FROM analytics.trend_analysis_cache;

-- Step 2: Drop new indexes
DROP INDEX IF EXISTS analytics.idx_trend_analysis_lookup;
DROP INDEX IF EXISTS analytics.idx_trend_analysis_workspace_user;

-- Step 3: Restore original indexes
CREATE INDEX idx_trend_analysis_workspace
    ON analytics.trend_analysis_cache(workspace_id, metric);

CREATE INDEX idx_trend_analysis_lookup
    ON analytics.trend_analysis_cache(workspace_id, metric, timeframe)
    WHERE expires_at > NOW();

-- Step 4: Drop new unique constraint
ALTER TABLE analytics.trend_analysis_cache
DROP CONSTRAINT IF EXISTS unique_trend_analysis;

-- Step 5: Restore original unique constraint
ALTER TABLE analytics.trend_analysis_cache
ADD CONSTRAINT unique_trend_analysis UNIQUE(workspace_id, metric, timeframe);

-- Step 6: Drop user_id column
ALTER TABLE analytics.trend_analysis_cache
DROP COLUMN IF EXISTS user_id;

-- Add comment documenting the rollback
COMMENT ON TABLE analytics.trend_analysis_cache IS
    'Cache table for trend analysis results (rolled back to version without user_id scoping). ' ||
    'WARNING: This version does not prevent information leakage between users in shared workspaces.';
