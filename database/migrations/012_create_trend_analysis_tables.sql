-- Trend Analysis Tables Migration
-- Creates tables for caching trend analysis results

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create trend analysis cache table
CREATE TABLE IF NOT EXISTS analytics.trend_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    metric VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,

    -- Analysis results stored as JSONB for flexibility
    analysis_data JSONB NOT NULL,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique cache entries per workspace, metric, and timeframe
    CONSTRAINT unique_trend_analysis UNIQUE(workspace_id, metric, timeframe)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_trend_analysis_workspace
    ON analytics.trend_analysis_cache(workspace_id, metric);

CREATE INDEX IF NOT EXISTS idx_trend_analysis_expiry
    ON analytics.trend_analysis_cache(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_trend_analysis_calculated
    ON analytics.trend_analysis_cache(calculated_at DESC);

-- Create GIN index for JSONB data
CREATE INDEX IF NOT EXISTS idx_trend_analysis_data
    ON analytics.trend_analysis_cache USING GIN(analysis_data);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION analytics.update_trend_analysis_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS trend_analysis_updated_at ON analytics.trend_analysis_cache;
CREATE TRIGGER trend_analysis_updated_at
    BEFORE UPDATE ON analytics.trend_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- Create function to clean up expired cache entries
CREATE OR REPLACE FUNCTION analytics.cleanup_expired_trend_analysis()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics.trend_analysis_cache
    WHERE expires_at IS NOT NULL
    AND expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add composite indexes on source tables for efficient trend queries
-- These indexes support queries that filter by workspace_id and created_at
CREATE INDEX IF NOT EXISTS idx_agent_executions_workspace_time
    ON public.agent_executions(workspace_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_credit_transactions_workspace_time
    ON public.credit_transactions(workspace_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_workspace_time
    ON public.transactions(workspace_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE analytics.trend_analysis_cache IS 'Cache table for trend analysis results to improve performance';
COMMENT ON COLUMN analytics.trend_analysis_cache.workspace_id IS 'Reference to the workspace this analysis belongs to';
COMMENT ON COLUMN analytics.trend_analysis_cache.metric IS 'The metric being analyzed (e.g., executions, users, credits)';
COMMENT ON COLUMN analytics.trend_analysis_cache.timeframe IS 'The timeframe for the analysis (e.g., 7d, 30d, 90d, 1y)';
COMMENT ON COLUMN analytics.trend_analysis_cache.analysis_data IS 'Complete trend analysis results stored as JSONB';
COMMENT ON COLUMN analytics.trend_analysis_cache.expires_at IS 'When this cache entry should expire and be recalculated';
