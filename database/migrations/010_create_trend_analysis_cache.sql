-- Trend analysis cache table for improved performance
-- Migration: 010_create_trend_analysis_cache.sql

-- Create trend analysis cache table
CREATE TABLE IF NOT EXISTS analytics.trend_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    metric VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,

    -- Analysis results stored as JSONB for flexibility
    analysis_data JSONB NOT NULL,

    -- Metadata for cache management
    calculated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,

    -- Audit timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Ensure unique cache entries per workspace, metric, and timeframe
    CONSTRAINT unique_trend_analysis UNIQUE(workspace_id, metric, timeframe)
);

-- Indexes for performance
CREATE INDEX idx_trend_analysis_workspace
    ON analytics.trend_analysis_cache(workspace_id, metric);

CREATE INDEX idx_trend_analysis_expires
    ON analytics.trend_analysis_cache(expires_at);

CREATE INDEX idx_trend_analysis_calculated
    ON analytics.trend_analysis_cache(calculated_at DESC);

-- Composite index for common query patterns
CREATE INDEX idx_trend_analysis_lookup
    ON analytics.trend_analysis_cache(workspace_id, metric, timeframe)
    WHERE expires_at > NOW();

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION analytics.update_trend_analysis_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at on row modification
CREATE TRIGGER trend_analysis_updated_at
    BEFORE UPDATE ON analytics.trend_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_trend_analysis_updated_at();

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION analytics.cleanup_expired_trend_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics.trend_analysis_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add comment for documentation
COMMENT ON TABLE analytics.trend_analysis_cache IS
    'Cache table for trend analysis results to improve performance. ' ||
    'Stores comprehensive trend analysis data including decomposition, patterns, and forecasts.';

COMMENT ON COLUMN analytics.trend_analysis_cache.analysis_data IS
    'JSONB containing full trend analysis results including overview, time series, decomposition, patterns, forecasts, and insights';

COMMENT ON COLUMN analytics.trend_analysis_cache.expires_at IS
    'Expiration timestamp for cache invalidation. Expired entries should be recalculated or removed.';
