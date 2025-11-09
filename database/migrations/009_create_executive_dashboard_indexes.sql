-- =====================================================================
-- Migration: 009_create_executive_dashboard_indexes.sql
-- Description: Create performance indexes for executive dashboard queries
-- Created: 2025-11-09
-- Purpose: Optimize queries for DAU/WAU/MAU, execution metrics, and KPIs
-- =====================================================================

-- =====================================================================
-- Execution Logs Indexes for Dashboard Queries
-- =====================================================================

-- Composite index for workspace + time range queries (DAU/WAU/MAU)
-- Used in: _calculate_daily_active_users, _calculate_weekly_active_users, _calculate_monthly_active_users
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_started_at
    ON execution_logs(workspace_id, started_at DESC)
    WHERE workspace_id IS NOT NULL;

-- Index for counting unique active users by time range
-- Used in: DAU/WAU/MAU calculations
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_time_user
    ON execution_logs(workspace_id, started_at DESC, user_id)
    WHERE workspace_id IS NOT NULL AND started_at IS NOT NULL;

-- Index for execution status queries (success rate calculations)
-- Used in: _calculate_success_rate
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_time_status
    ON execution_logs(workspace_id, started_at DESC, status)
    WHERE workspace_id IS NOT NULL AND started_at IS NOT NULL;

-- Index for duration calculations (avg execution time)
-- Used in: _calculate_avg_execution_time
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_time_duration
    ON execution_logs(workspace_id, started_at DESC, duration)
    WHERE workspace_id IS NOT NULL AND duration IS NOT NULL;

-- Index for credits aggregation
-- Used in: _calculate_total_credits
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_time_credits
    ON execution_logs(workspace_id, started_at DESC, credits_used)
    WHERE workspace_id IS NOT NULL AND credits_used IS NOT NULL;

-- Index for active agents calculation
-- Used in: _calculate_active_agents
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_agent_recent
    ON execution_logs(workspace_id, started_at DESC, agent_id)
    WHERE workspace_id IS NOT NULL AND started_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Covering index for comprehensive execution queries
-- Includes commonly selected columns to avoid table lookups
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_comprehensive
    ON execution_logs(workspace_id, started_at DESC)
    INCLUDE (user_id, agent_id, status, duration, credits_used)
    WHERE workspace_id IS NOT NULL;

-- =====================================================================
-- Workspace Metrics Indexes
-- =====================================================================

-- Composite index for workspace metrics time series
CREATE INDEX IF NOT EXISTS idx_workspace_metrics_workspace_date
    ON workspace_metrics(workspace_id, metric_date DESC)
    WHERE workspace_id IS NOT NULL;

-- Covering index for workspace metrics summary
CREATE INDEX IF NOT EXISTS idx_workspace_metrics_summary
    ON workspace_metrics(workspace_id, metric_date DESC)
    INCLUDE (total_users, active_users, total_agents, total_executions, credits_used);

-- =====================================================================
-- User Metrics Indexes
-- =====================================================================

-- Composite index for user-level metrics
CREATE INDEX IF NOT EXISTS idx_user_metrics_user_date
    ON user_metrics(user_id, metric_date DESC)
    WHERE user_id IS NOT NULL;

-- Index for aggregating user activity
CREATE INDEX IF NOT EXISTS idx_user_metrics_date
    ON user_metrics(metric_date DESC)
    INCLUDE (sessions_count, executions_count, active_duration);

-- =====================================================================
-- Agent Metrics Indexes
-- =====================================================================

-- Composite index for agent-level metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_date
    ON agent_metrics(agent_id, metric_date DESC)
    WHERE agent_id IS NOT NULL;

-- Covering index for agent performance summary
CREATE INDEX IF NOT EXISTS idx_agent_metrics_summary
    ON agent_metrics(agent_id, metric_date DESC)
    INCLUDE (total_executions, successful_executions, failed_executions, avg_duration);

-- =====================================================================
-- Partial Indexes for Common Filters
-- =====================================================================

-- Index for recent executions (last 90 days) - common executive dashboard timeframe
CREATE INDEX IF NOT EXISTS idx_execution_logs_recent_90d
    ON execution_logs(workspace_id, started_at DESC, status)
    WHERE started_at >= CURRENT_TIMESTAMP - INTERVAL '90 days'
    AND workspace_id IS NOT NULL;

-- Index for successful executions only
CREATE INDEX IF NOT EXISTS idx_execution_logs_successful
    ON execution_logs(workspace_id, started_at DESC)
    WHERE status = 'success' AND workspace_id IS NOT NULL;

-- Index for failed executions (for error analysis)
CREATE INDEX IF NOT EXISTS idx_execution_logs_failed
    ON execution_logs(workspace_id, started_at DESC)
    WHERE status IN ('failed', 'error') AND workspace_id IS NOT NULL;

-- =====================================================================
-- Statistics and Maintenance
-- =====================================================================

-- Update statistics for better query planning
ANALYZE execution_logs;
ANALYZE workspace_metrics;
ANALYZE user_metrics;
ANALYZE agent_metrics;

-- =====================================================================
-- Index Comments for Documentation
-- =====================================================================

COMMENT ON INDEX idx_execution_logs_workspace_started_at IS
    'Primary index for executive dashboard time-range queries on execution logs';

COMMENT ON INDEX idx_execution_logs_workspace_time_user IS
    'Optimizes DAU/WAU/MAU calculations by workspace and time range';

COMMENT ON INDEX idx_execution_logs_workspace_time_status IS
    'Optimizes success rate calculations filtered by status';

COMMENT ON INDEX idx_execution_logs_workspace_comprehensive IS
    'Covering index to avoid table lookups for common dashboard queries';

COMMENT ON INDEX idx_execution_logs_recent_90d IS
    'Partial index for recent 90-day queries - most common executive dashboard timeframe';

COMMENT ON INDEX idx_workspace_metrics_summary IS
    'Covering index for workspace-level KPI aggregations';

-- =====================================================================
-- Performance Tuning for Executive Dashboard Tables
-- =====================================================================

-- Set higher statistics target for frequently queried columns
ALTER TABLE execution_logs
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN started_at SET STATISTICS 1000,
    ALTER COLUMN user_id SET STATISTICS 500,
    ALTER COLUMN agent_id SET STATISTICS 500,
    ALTER COLUMN status SET STATISTICS 500;

ALTER TABLE workspace_metrics
    ALTER COLUMN workspace_id SET STATISTICS 1000,
    ALTER COLUMN metric_date SET STATISTICS 1000;

ALTER TABLE user_metrics
    ALTER COLUMN user_id SET STATISTICS 500,
    ALTER COLUMN metric_date SET STATISTICS 1000;

ALTER TABLE agent_metrics
    ALTER COLUMN agent_id SET STATISTICS 500,
    ALTER COLUMN metric_date SET STATISTICS 1000;

-- Set fill factor for tables with frequent updates
-- Lower fill factor leaves room for updates without page splits
ALTER TABLE execution_logs SET (fillfactor = 90);
ALTER TABLE workspace_metrics SET (fillfactor = 90);
ALTER TABLE user_metrics SET (fillfactor = 90);
ALTER TABLE agent_metrics SET (fillfactor = 90);

-- Enable auto-vacuum tuning for high-traffic tables
ALTER TABLE execution_logs SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE workspace_metrics SET (
    autovacuum_vacuum_scale_factor = 0.15,
    autovacuum_analyze_scale_factor = 0.1
);

-- =====================================================================
-- Verification
-- =====================================================================

-- Verify indexes were created
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO index_count
    FROM pg_indexes
    WHERE schemaname = current_schema()
    AND indexname LIKE 'idx_execution_logs%'
    OR indexname LIKE 'idx_workspace_metrics%'
    OR indexname LIKE 'idx_user_metrics%'
    OR indexname LIKE 'idx_agent_metrics%';

    RAISE NOTICE 'Created % indexes for executive dashboard performance', index_count;
END $$;
