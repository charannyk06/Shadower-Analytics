-- Update trend analysis cache table to add user_id for proper scoping
-- Migration: 010_b_update_trend_analysis_cache_add_user_id.sql

-- Add user_id column to trend_analysis_cache table
ALTER TABLE analytics.trend_analysis_cache
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;

-- Update the unique constraint to include user_id
ALTER TABLE analytics.trend_analysis_cache
DROP CONSTRAINT IF EXISTS unique_trend_analysis;

ALTER TABLE analytics.trend_analysis_cache
ADD CONSTRAINT unique_trend_analysis UNIQUE(workspace_id, user_id, metric, timeframe);

-- Update index to include user_id
DROP INDEX IF EXISTS analytics.idx_trend_analysis_workspace;
CREATE INDEX idx_trend_analysis_workspace_user
    ON analytics.trend_analysis_cache(workspace_id, user_id, metric);

-- Update the lookup index to include user_id
DROP INDEX IF EXISTS analytics.idx_trend_analysis_lookup;
CREATE INDEX idx_trend_analysis_lookup
    ON analytics.trend_analysis_cache(workspace_id, user_id, metric, timeframe)
    WHERE expires_at > NOW();

-- Add comment explaining the security improvement
COMMENT ON COLUMN analytics.trend_analysis_cache.user_id IS
    'User ID for cache entry scoping. Prevents information leakage between users in shared workspaces.';
