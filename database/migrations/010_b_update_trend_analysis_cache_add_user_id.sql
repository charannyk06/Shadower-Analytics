-- Update trend analysis cache table to add user_id for proper scoping
-- Migration: 010_b_update_trend_analysis_cache_add_user_id.sql
--
-- IMPORTANT: This migration clears existing cache to prevent information leakage.
-- Cache entries will be regenerated on next request with proper user_id scoping.

-- Step 1: Add user_id column (nullable initially)
ALTER TABLE analytics.trend_analysis_cache
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;

-- Step 2: Clear existing cache entries (safest approach since this is a cache table)
-- This prevents NULL user_id entries and ensures all future cache is properly scoped
DELETE FROM analytics.trend_analysis_cache;

-- Step 3: Make user_id NOT NULL to enforce data integrity
ALTER TABLE analytics.trend_analysis_cache
ALTER COLUMN user_id SET NOT NULL;

-- Step 4: Update the unique constraint to include user_id
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
