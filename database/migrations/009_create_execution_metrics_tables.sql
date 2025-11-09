-- =====================================================================
-- Migration: 009_create_execution_metrics_tables.sql
-- Description: Create execution metrics tracking tables and views
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: execution_metrics_minute
-- Description: Minute-level aggregated execution metrics
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.execution_metrics_minute (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR(255) NOT NULL,
    minute TIMESTAMPTZ NOT NULL,

    -- Throughput metrics
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    cancelled_executions INTEGER DEFAULT 0,

    -- Latency metrics (in milliseconds)
    avg_queue_latency INTEGER,
    p50_queue_latency INTEGER,
    p75_queue_latency INTEGER,
    p90_queue_latency INTEGER,
    p95_queue_latency INTEGER,
    p99_queue_latency INTEGER,

    avg_execution_latency INTEGER,
    p50_execution_latency INTEGER,
    p75_execution_latency INTEGER,
    p90_execution_latency INTEGER,
    p95_execution_latency INTEGER,
    p99_execution_latency INTEGER,

    avg_e2e_latency INTEGER,
    p50_e2e_latency INTEGER,
    p75_e2e_latency INTEGER,
    p90_e2e_latency INTEGER,
    p95_e2e_latency INTEGER,
    p99_e2e_latency INTEGER,

    -- Queue metrics
    max_queue_depth INTEGER DEFAULT 0,
    avg_queue_depth NUMERIC(10,2),
    avg_queue_wait_time NUMERIC(10,2),

    -- System metrics
    avg_cpu_usage NUMERIC(5,2),
    avg_memory_usage NUMERIC(5,2),
    active_workers INTEGER,

    -- Capacity metrics
    capacity_utilization NUMERIC(5,2),
    peak_throughput INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_execution_minute UNIQUE(workspace_id, minute)
);

-- Indexes for execution_metrics_minute
CREATE INDEX idx_execution_metrics_workspace_minute
    ON analytics.execution_metrics_minute(workspace_id, minute DESC);
CREATE INDEX idx_execution_metrics_minute_only
    ON analytics.execution_metrics_minute(minute DESC);

-- Comments
COMMENT ON TABLE analytics.execution_metrics_minute IS 'Minute-level aggregated execution metrics for real-time monitoring';
COMMENT ON COLUMN analytics.execution_metrics_minute.avg_queue_latency IS 'Average queue wait time in milliseconds';
COMMENT ON COLUMN analytics.execution_metrics_minute.capacity_utilization IS 'Percentage of system capacity being utilized';

-- =====================================================================
-- Table: execution_queue
-- Description: Track queued executions for queue depth metrics
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.execution_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_id VARCHAR(255) UNIQUE NOT NULL,
    workspace_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'queued',
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_start_time TIMESTAMPTZ,
    estimated_runtime NUMERIC(10,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_queue_status CHECK (
        status IN ('queued', 'processing', 'completed', 'cancelled', 'failed')
    )
);

-- Indexes for execution_queue
CREATE INDEX idx_execution_queue_workspace_status
    ON analytics.execution_queue(workspace_id, status) WHERE status = 'queued';
CREATE INDEX idx_execution_queue_queued_at
    ON analytics.execution_queue(queued_at DESC);
CREATE INDEX idx_execution_queue_agent_id
    ON analytics.execution_queue(agent_id);
CREATE INDEX idx_execution_queue_priority
    ON analytics.execution_queue(priority DESC, queued_at ASC) WHERE status = 'queued';

-- Comments
COMMENT ON TABLE analytics.execution_queue IS 'Tracks queued executions for queue depth and wait time metrics';
COMMENT ON COLUMN analytics.execution_queue.priority IS 'Higher number = higher priority';

-- =====================================================================
-- Table: execution_patterns
-- Description: Store detected execution patterns and anomalies
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.execution_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    severity VARCHAR(20) DEFAULT 'low',
    description TEXT,
    metadata JSONB DEFAULT '{}',

    -- Pattern-specific metrics
    peak_executions INTEGER,
    total_executions INTEGER,
    impact VARCHAR(20),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_pattern_type CHECK (
        pattern_type IN ('burst', 'spike', 'drop', 'failure_surge', 'anomaly')
    ),
    CONSTRAINT valid_severity CHECK (
        severity IN ('low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT valid_impact CHECK (
        impact IN ('low', 'medium', 'high')
    )
);

-- Indexes for execution_patterns
CREATE INDEX idx_execution_patterns_workspace_detected
    ON analytics.execution_patterns(workspace_id, detected_at DESC);
CREATE INDEX idx_execution_patterns_type
    ON analytics.execution_patterns(pattern_type, detected_at DESC);
CREATE INDEX idx_execution_patterns_severity
    ON analytics.execution_patterns(severity, detected_at DESC) WHERE severity IN ('high', 'critical');

-- Comments
COMMENT ON TABLE analytics.execution_patterns IS 'Stores detected execution patterns, bursts, and anomalies';
COMMENT ON COLUMN analytics.execution_patterns.pattern_type IS 'Type of pattern: burst, spike, drop, failure_surge, anomaly';

-- =====================================================================
-- View: v_current_executions
-- Description: Real-time view of currently running executions
-- =====================================================================

CREATE OR REPLACE VIEW analytics.v_current_executions AS
SELECT
    el.execution_id as run_id,
    el.agent_id,
    'Agent ' || el.agent_id as agent_name,  -- Placeholder, replace with actual join if agents table exists
    el.user_id,
    el.workspace_id,
    el.started_at,
    EXTRACT(EPOCH FROM (NOW() - el.started_at)) as elapsed_time,
    COALESCE(el.duration, 0) as estimated_runtime,
    el.status,
    el.metadata
FROM execution_logs el
WHERE el.status IN ('running', 'processing', 'pending')
    AND el.completed_at IS NULL
ORDER BY el.started_at DESC;

COMMENT ON VIEW analytics.v_current_executions IS 'Real-time view of currently running executions';

-- =====================================================================
-- View: v_execution_latency_distribution
-- Description: Pre-calculated latency distribution buckets
-- =====================================================================

CREATE OR REPLACE VIEW analytics.v_execution_latency_distribution AS
SELECT
    workspace_id,
    DATE_TRUNC('hour', started_at) as hour,
    CASE
        WHEN duration < 1 THEN '0-1s'
        WHEN duration < 5 THEN '1-5s'
        WHEN duration < 10 THEN '5-10s'
        WHEN duration < 30 THEN '10-30s'
        WHEN duration < 60 THEN '30-60s'
        ELSE '60s+'
    END as bucket,
    COUNT(*) as count
FROM execution_logs
WHERE completed_at IS NOT NULL
GROUP BY workspace_id, DATE_TRUNC('hour', started_at), bucket
ORDER BY hour DESC, bucket;

COMMENT ON VIEW analytics.v_execution_latency_distribution IS 'Latency distribution grouped into time buckets';

-- =====================================================================
-- Function: aggregate_execution_metrics_minute
-- Description: Aggregate execution metrics by minute
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.aggregate_execution_metrics_minute(
    p_workspace_id VARCHAR,
    p_minute TIMESTAMPTZ
) RETURNS void AS $$
DECLARE
    v_total_executions INTEGER;
    v_successful_executions INTEGER;
    v_failed_executions INTEGER;
    v_cancelled_executions INTEGER;
BEGIN
    -- Calculate execution counts
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'success'),
        COUNT(*) FILTER (WHERE status IN ('failure', 'error', 'failed')),
        COUNT(*) FILTER (WHERE status = 'cancelled')
    INTO v_total_executions, v_successful_executions, v_failed_executions, v_cancelled_executions
    FROM execution_logs
    WHERE workspace_id = p_workspace_id
        AND started_at >= p_minute
        AND started_at < p_minute + INTERVAL '1 minute';

    -- Insert or update metrics
    INSERT INTO analytics.execution_metrics_minute (
        workspace_id,
        minute,
        total_executions,
        successful_executions,
        failed_executions,
        cancelled_executions,
        updated_at
    ) VALUES (
        p_workspace_id,
        p_minute,
        v_total_executions,
        v_successful_executions,
        v_failed_executions,
        v_cancelled_executions,
        NOW()
    )
    ON CONFLICT (workspace_id, minute)
    DO UPDATE SET
        total_executions = EXCLUDED.total_executions,
        successful_executions = EXCLUDED.successful_executions,
        failed_executions = EXCLUDED.failed_executions,
        cancelled_executions = EXCLUDED.cancelled_executions,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.aggregate_execution_metrics_minute IS 'Aggregates execution metrics for a specific workspace and minute';

-- =====================================================================
-- Grants
-- =====================================================================

-- Grant appropriate permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON analytics.execution_metrics_minute TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.execution_queue TO PUBLIC;
GRANT SELECT, INSERT ON analytics.execution_patterns TO PUBLIC;
GRANT SELECT ON analytics.v_current_executions TO PUBLIC;
GRANT SELECT ON analytics.v_execution_latency_distribution TO PUBLIC;
GRANT EXECUTE ON FUNCTION analytics.aggregate_execution_metrics_minute TO PUBLIC;

-- =====================================================================
-- Sample Data (optional, for testing)
-- =====================================================================

-- Uncomment below to insert sample data for testing
/*
INSERT INTO analytics.execution_queue (queue_id, workspace_id, agent_id, user_id, priority, status)
VALUES
    ('q1', 'ws1', 'agent1', 'user1', 10, 'queued'),
    ('q2', 'ws1', 'agent2', 'user1', 5, 'queued'),
    ('q3', 'ws1', 'agent3', 'user2', 8, 'queued');
*/
