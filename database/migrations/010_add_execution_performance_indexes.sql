-- =====================================================================
-- Migration: 010_add_execution_performance_indexes.sql
-- Description: Add composite indexes for execution metrics performance
-- Created: 2025-11-09
-- =====================================================================

-- =====================================================================
-- Performance Indexes for execution_logs
-- =====================================================================

-- Composite index for realtime metrics query (workspace_id, status, completed_at)
-- This optimizes queries that filter on running executions
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_status_active
    ON execution_logs(workspace_id, status)
    WHERE completed_at IS NULL;

-- Composite index for completed executions with duration (for latency metrics)
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_started_duration
    ON execution_logs(workspace_id, started_at DESC, duration)
    WHERE status IN ('success', 'failure', 'failed', 'error', 'completed')
    AND duration IS NOT NULL;

-- Composite index for status filtering with started_at (for performance metrics)
CREATE INDEX IF NOT EXISTS idx_execution_logs_workspace_started_status
    ON execution_logs(workspace_id, started_at DESC, status);

-- Comments
COMMENT ON INDEX idx_execution_logs_workspace_status_active IS
    'Partial index for active executions (running/processing) - optimizes realtime metrics';
COMMENT ON INDEX idx_execution_logs_workspace_started_duration IS
    'Composite index for latency percentile calculations';
COMMENT ON INDEX idx_execution_logs_workspace_started_status IS
    'Composite index for performance metrics and throughput calculations';

-- =====================================================================
-- ROLLBACK SCRIPT
-- =====================================================================
-- To rollback this migration, run the following SQL:
--
-- DROP INDEX IF EXISTS idx_execution_logs_workspace_status_active;
-- DROP INDEX IF EXISTS idx_execution_logs_workspace_started_duration;
-- DROP INDEX IF EXISTS idx_execution_logs_workspace_started_status;
--
-- =====================================================================
