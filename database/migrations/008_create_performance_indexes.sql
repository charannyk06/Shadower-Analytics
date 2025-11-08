-- =====================================================================
-- Migration: 008_create_performance_indexes.sql
-- Description: Create additional performance indexes and optimizations
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Composite Indexes for Common Query Patterns
-- =====================================================================

-- User activity composite indexes
CREATE INDEX idx_user_activity_workspace_user_time
    ON analytics.user_activity(workspace_id, user_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX idx_user_activity_event_workspace_time
    ON analytics.user_activity(event_type, workspace_id, created_at DESC)
    WHERE workspace_id IS NOT NULL;

-- Daily metrics composite indexes for trending queries
CREATE INDEX idx_daily_metrics_workspace_date_runs
    ON analytics.daily_metrics(workspace_id, metric_date DESC, total_runs DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX idx_daily_metrics_workspace_date_credits
    ON analytics.daily_metrics(workspace_id, metric_date DESC, total_credits_consumed DESC)
    WHERE workspace_id IS NOT NULL;

-- Agent performance composite for leaderboards
CREATE INDEX idx_agent_performance_workspace_success
    ON analytics.agent_performance(workspace_id, metric_date DESC, successful_runs DESC)
    WHERE workspace_id IS NOT NULL;

CREATE INDEX idx_agent_performance_workspace_credits
    ON analytics.agent_performance(workspace_id, metric_date DESC, total_credits DESC)
    WHERE workspace_id IS NOT NULL;

-- =====================================================================
-- Partial Indexes for Specific Conditions
-- =====================================================================

-- Index for recent activity (last 30 days) - most common query
CREATE INDEX idx_user_activity_recent
    ON analytics.user_activity(workspace_id, created_at DESC)
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';

-- Index for active alert rules only
CREATE INDEX idx_alert_rules_active_workspace
    ON analytics.alert_rules(workspace_id, metric_type)
    WHERE is_active = true;

-- Index for unacknowledged alerts
CREATE INDEX idx_alert_history_pending
    ON analytics.alert_history(workspace_id, triggered_at DESC)
    WHERE acknowledged_by IS NULL;

-- Index for failed runs in agent performance
CREATE INDEX idx_agent_performance_failures
    ON analytics.agent_performance(agent_id, metric_date DESC, failed_runs DESC)
    WHERE failed_runs > 0;

-- Index for error events
CREATE INDEX idx_user_activity_errors
    ON analytics.user_activity(workspace_id, created_at DESC, event_name)
    WHERE event_type = 'error';

-- =====================================================================
-- JSONB Indexes for Metadata Queries
-- =====================================================================

-- GIN index for metadata searching (already created in 002, but ensuring coverage)
-- This allows queries like: WHERE metadata @> '{"key": "value"}'
CREATE INDEX IF NOT EXISTS idx_user_activity_metadata_gin
    ON analytics.user_activity USING gin(metadata jsonb_path_ops);

-- Index for specific JSON fields commonly queried
CREATE INDEX idx_daily_metrics_credits_by_model
    ON analytics.daily_metrics USING gin(credits_by_model);

CREATE INDEX idx_daily_metrics_errors_by_type
    ON analytics.daily_metrics USING gin(errors_by_type);

CREATE INDEX idx_agent_performance_error_types
    ON analytics.agent_performance USING gin(error_types);

-- =====================================================================
-- Covering Indexes for Performance
-- =====================================================================

-- Covering index for workspace summary queries
CREATE INDEX idx_daily_metrics_workspace_summary
    ON analytics.daily_metrics(workspace_id, metric_date DESC)
    INCLUDE (total_runs, successful_runs, failed_runs, total_credits_consumed, active_users);

-- Covering index for agent performance summary
CREATE INDEX idx_agent_performance_summary
    ON analytics.agent_performance(agent_id, metric_date DESC)
    INCLUDE (total_runs, successful_runs, avg_runtime_seconds, total_credits);

-- =====================================================================
-- Expression Indexes for Calculated Values
-- =====================================================================

-- Index on success rate calculation (commonly used in WHERE clauses)
CREATE INDEX idx_daily_metrics_success_rate
    ON analytics.daily_metrics(
        workspace_id,
        metric_date DESC,
        (CASE WHEN total_runs > 0 THEN (successful_runs::NUMERIC / total_runs) * 100 ELSE 0 END)
    )
    WHERE total_runs > 0;

-- Index on error rate for alerting
CREATE INDEX idx_daily_metrics_error_rate_high
    ON analytics.daily_metrics(workspace_id, metric_date DESC, error_rate)
    WHERE error_rate > 5.0;  -- Only index high error rates

-- =====================================================================
-- Hash Indexes for Equality Searches
-- =====================================================================

-- Hash index for session_id lookups (exact matches only)
CREATE INDEX idx_user_activity_session_hash
    ON analytics.user_activity USING hash(session_id)
    WHERE session_id IS NOT NULL;

-- Hash index for alert rule lookups by ID
CREATE INDEX idx_alert_history_rule_hash
    ON analytics.alert_history USING hash(alert_rule_id);

-- =====================================================================
-- Text Search Indexes
-- =====================================================================

-- Full-text search on alert rule names and descriptions
CREATE INDEX idx_alert_rules_search
    ON analytics.alert_rules
    USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- =====================================================================
-- Statistics and Maintenance
-- =====================================================================

-- Update statistics for better query planning
ANALYZE analytics.user_activity;
ANALYZE analytics.daily_metrics;
ANALYZE analytics.hourly_metrics;
ANALYZE analytics.agent_performance;
ANALYZE analytics.user_cohorts;
ANALYZE analytics.alert_rules;
ANALYZE analytics.alert_history;

-- =====================================================================
-- Index Comments
-- =====================================================================

COMMENT ON INDEX analytics.idx_user_activity_workspace_user_time IS
    'Composite index for user activity filtered by workspace and user';

COMMENT ON INDEX analytics.idx_daily_metrics_workspace_summary IS
    'Covering index for workspace summary queries including key metrics';

COMMENT ON INDEX analytics.idx_user_activity_recent IS
    'Partial index for recent activity (last 30 days) - most common query pattern';

COMMENT ON INDEX analytics.idx_alert_rules_active_workspace IS
    'Partial index for active alert rules only';

COMMENT ON INDEX analytics.idx_agent_performance_failures IS
    'Partial index for agents with failures, used in error analysis';

COMMENT ON INDEX analytics.idx_daily_metrics_success_rate IS
    'Expression index on calculated success rate for efficient filtering';

COMMENT ON INDEX analytics.idx_alert_rules_search IS
    'Full-text search index for alert rule names and descriptions';

-- =====================================================================
-- Additional Optimizations
-- =====================================================================

-- Set statistics target higher for frequently queried columns
ALTER TABLE analytics.user_activity
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN user_id SET STATISTICS 1000,
    ALTER COLUMN event_type SET STATISTICS 500;

ALTER TABLE analytics.daily_metrics
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN metric_date SET STATISTICS 1000;

ALTER TABLE analytics.agent_performance
    ALTER COLUMN agent_id SET STATISTICS 1000,
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN metric_date SET STATISTICS 1000;

-- Set fill factor for tables with frequent updates
ALTER TABLE analytics.daily_metrics SET (fillfactor = 90);
ALTER TABLE analytics.hourly_metrics SET (fillfactor = 90);
ALTER TABLE analytics.agent_performance SET (fillfactor = 90);

-- Enable auto-vacuum tuning for high-traffic tables
ALTER TABLE analytics.user_activity SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE analytics.hourly_metrics SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);
