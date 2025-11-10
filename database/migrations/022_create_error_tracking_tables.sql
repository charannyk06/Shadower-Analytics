-- =====================================================================
-- Migration: 022_create_error_tracking_tables.sql
-- Description: Create comprehensive error tracking tables
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: errors
-- Description: Main error tracking table with grouping and resolution
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.errors (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint VARCHAR(32) NOT NULL,
    workspace_id UUID NOT NULL,

    -- Error details
    error_type VARCHAR(100) NOT NULL,
    message TEXT,
    severity VARCHAR(20) DEFAULT 'medium' CHECK (
        severity IN ('low', 'medium', 'high', 'critical')
    ),
    status VARCHAR(20) DEFAULT 'new' CHECK (
        status IN ('new', 'acknowledged', 'investigating', 'resolved', 'ignored')
    ),

    -- Occurrence tracking
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,

    -- Technical details
    stack_trace TEXT,
    context JSONB DEFAULT '{}',

    -- Impact
    users_affected TEXT[] DEFAULT '{}',
    agents_affected TEXT[] DEFAULT '{}',
    executions_affected INTEGER DEFAULT 0,
    credits_lost NUMERIC(10,2) DEFAULT 0,
    cascading_failures INTEGER DEFAULT 0,

    -- Resolution
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,
    resolution TEXT,
    root_cause TEXT,
    preventive_measures TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_error_fingerprint UNIQUE(fingerprint, workspace_id)
);

-- Indexes for errors table
CREATE INDEX idx_errors_workspace_status
    ON analytics.errors(workspace_id, status);

CREATE INDEX idx_errors_severity_last_seen
    ON analytics.errors(severity, last_seen DESC);

CREATE INDEX idx_errors_fingerprint
    ON analytics.errors(fingerprint);

CREATE INDEX idx_errors_workspace_time
    ON analytics.errors(workspace_id, last_seen DESC);

CREATE INDEX idx_errors_status
    ON analytics.errors(status, last_seen DESC);

-- Comments
COMMENT ON TABLE analytics.errors IS 'Main error tracking with grouping, categorization, and resolution';
COMMENT ON COLUMN analytics.errors.fingerprint IS 'MD5 hash for grouping similar errors';
COMMENT ON COLUMN analytics.errors.occurrence_count IS 'Total number of times this error occurred';
COMMENT ON COLUMN analytics.errors.cascading_failures IS 'Number of errors caused by this error';

-- =====================================================================
-- Table: error_occurrences
-- Description: Individual error instances for detailed tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID NOT NULL REFERENCES analytics.errors(error_id) ON DELETE CASCADE,

    -- Occurrence details
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,
    agent_id UUID,
    run_id UUID,

    -- Additional context
    metadata JSONB DEFAULT '{}',
    environment VARCHAR(50),
    version VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_occurrences
CREATE INDEX idx_error_occurrences_error
    ON analytics.error_occurrences(error_id, occurred_at DESC);

CREATE INDEX idx_error_occurrences_user
    ON analytics.error_occurrences(user_id, occurred_at DESC) WHERE user_id IS NOT NULL;

CREATE INDEX idx_error_occurrences_agent
    ON analytics.error_occurrences(agent_id, occurred_at DESC) WHERE agent_id IS NOT NULL;

CREATE INDEX idx_error_occurrences_time
    ON analytics.error_occurrences(occurred_at DESC);

-- Comments
COMMENT ON TABLE analytics.error_occurrences IS 'Individual error occurrences for detailed tracking and analysis';

-- =====================================================================
-- Table: error_timeline
-- Description: Time-series error metrics for spike detection
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Time bucket
    time_bucket TIMESTAMPTZ NOT NULL,
    bucket_size VARCHAR(20) DEFAULT 'hourly' CHECK (
        bucket_size IN ('minute', 'hourly', 'daily')
    ),

    -- Metrics
    error_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    unique_errors INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_workspace_bucket UNIQUE(workspace_id, time_bucket, bucket_size)
);

-- Indexes for error_timeline
CREATE INDEX idx_error_timeline_workspace_time
    ON analytics.error_timeline(workspace_id, time_bucket DESC);

CREATE INDEX idx_error_timeline_bucket_size
    ON analytics.error_timeline(bucket_size, time_bucket DESC);

-- Comments
COMMENT ON TABLE analytics.error_timeline IS 'Time-series error metrics for spike detection and pattern analysis';

-- =====================================================================
-- Table: error_spikes
-- Description: Detected error spikes for alerting
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_spikes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Spike details
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    peak_errors INTEGER NOT NULL,
    total_errors INTEGER NOT NULL,
    primary_cause VARCHAR(255),

    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_spikes
CREATE INDEX idx_error_spikes_workspace
    ON analytics.error_spikes(workspace_id, start_time DESC);

CREATE INDEX idx_error_spikes_resolved
    ON analytics.error_spikes(resolved, start_time DESC);

-- Comments
COMMENT ON TABLE analytics.error_spikes IS 'Detected error spikes for alerting and analysis';

-- =====================================================================
-- Table: error_patterns
-- Description: Detected error patterns and correlations
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Pattern details
    pattern VARCHAR(255) NOT NULL,
    frequency INTEGER DEFAULT 0,
    last_occurrence TIMESTAMPTZ,
    correlation VARCHAR(255),

    -- Pattern type
    pattern_type VARCHAR(50) CHECK (
        pattern_type IN ('temporal', 'user', 'agent', 'cascade', 'environment')
    ),

    -- Metadata
    confidence NUMERIC(3,2) DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_patterns
CREATE INDEX idx_error_patterns_workspace
    ON analytics.error_patterns(workspace_id, frequency DESC);

CREATE INDEX idx_error_patterns_type
    ON analytics.error_patterns(pattern_type, last_occurrence DESC);

-- Comments
COMMENT ON TABLE analytics.error_patterns IS 'Detected error patterns for proactive issue resolution';

-- =====================================================================
-- Table: error_recovery_attempts
-- Description: Track recovery attempts and methods
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_recovery_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID NOT NULL REFERENCES analytics.errors(error_id) ON DELETE CASCADE,
    occurrence_id UUID REFERENCES analytics.error_occurrences(id) ON DELETE SET NULL,

    -- Recovery details
    recovery_method VARCHAR(100) NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT NOW(),
    succeeded BOOLEAN DEFAULT FALSE,
    recovery_time_seconds NUMERIC(10,2),

    -- Failure details
    failure_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_recovery_attempts
CREATE INDEX idx_error_recovery_error
    ON analytics.error_recovery_attempts(error_id, attempted_at DESC);

CREATE INDEX idx_error_recovery_method
    ON analytics.error_recovery_attempts(recovery_method, succeeded);

-- Comments
COMMENT ON TABLE analytics.error_recovery_attempts IS 'Track error recovery attempts and effectiveness';

-- =====================================================================
-- Materialized View: error_summary
-- Description: Pre-aggregated error metrics for dashboard
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.error_summary AS
SELECT
    e.workspace_id,
    DATE_TRUNC('day', e.last_seen) as metric_date,

    -- Error counts
    COUNT(*) as total_unique_errors,
    SUM(e.occurrence_count) as total_occurrences,

    -- By severity
    COUNT(*) FILTER (WHERE e.severity = 'critical') as critical_errors,
    COUNT(*) FILTER (WHERE e.severity = 'high') as high_errors,
    COUNT(*) FILTER (WHERE e.severity = 'medium') as medium_errors,
    COUNT(*) FILTER (WHERE e.severity = 'low') as low_errors,

    -- By status
    COUNT(*) FILTER (WHERE e.status = 'new') as new_errors,
    COUNT(*) FILTER (WHERE e.status = 'acknowledged') as acknowledged_errors,
    COUNT(*) FILTER (WHERE e.status = 'investigating') as investigating_errors,
    COUNT(*) FILTER (WHERE e.status = 'resolved') as resolved_errors,
    COUNT(*) FILTER (WHERE e.status = 'ignored') as ignored_errors,

    -- Impact
    (
        SELECT COUNT(DISTINCT user_id)
        FROM (
            SELECT UNNEST(e2.users_affected) AS user_id
            FROM analytics.errors e2
            WHERE e2.workspace_id = e.workspace_id
              AND DATE_TRUNC('day', e2.last_seen) = DATE_TRUNC('day', e.last_seen)
        ) AS all_users
    ) as total_users_affected,
    SUM(e.executions_affected) as total_executions_affected,
    SUM(e.credits_lost) as total_credits_lost,
    SUM(e.cascading_failures) as total_cascading_failures,

    -- Recovery
    AVG(
        CASE WHEN e.resolved_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (e.resolved_at - e.first_seen))
        ELSE NULL END
    ) as avg_resolution_time_seconds

FROM analytics.errors e
WHERE e.last_seen >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY e.workspace_id, DATE_TRUNC('day', e.last_seen);

-- Index on materialized view
CREATE INDEX idx_error_summary_workspace_date
    ON analytics.error_summary(workspace_id, metric_date DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.error_summary IS 'Pre-aggregated error metrics for fast dashboard queries';

-- =====================================================================
-- Functions
-- =====================================================================

-- Function to refresh error summary
CREATE OR REPLACE FUNCTION analytics.refresh_error_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.error_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_error_summary() IS 'Refresh error summary materialized view';

-- Function to update error occurrence
CREATE OR REPLACE FUNCTION analytics.update_error_occurrence()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE analytics.errors
    SET
        occurrence_count = occurrence_count + 1,
        last_seen = NEW.occurred_at,
        updated_at = NOW()
    WHERE error_id = NEW.error_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update error occurrence count
DROP TRIGGER IF EXISTS trigger_update_error_occurrence ON analytics.error_occurrences;
CREATE TRIGGER trigger_update_error_occurrence
    AFTER INSERT ON analytics.error_occurrences
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_error_occurrence();

COMMENT ON FUNCTION analytics.update_error_occurrence() IS 'Update error occurrence count when new occurrence is inserted';

-- Function to update error timeline
CREATE OR REPLACE FUNCTION analytics.update_error_timeline(
    p_workspace_id UUID,
    p_occurred_at TIMESTAMPTZ,
    p_severity VARCHAR(20),
    p_error_id UUID
)
RETURNS void AS $$
DECLARE
    v_hour TIMESTAMPTZ;
BEGIN
    v_hour := DATE_TRUNC('hour', p_occurred_at);

    INSERT INTO analytics.error_timeline (
        workspace_id,
        time_bucket,
        bucket_size,
        error_count,
        critical_count,
        unique_errors
    ) VALUES (
        p_workspace_id,
        v_hour,
        'hourly',
        1,
        CASE WHEN p_severity = 'critical' THEN 1 ELSE 0 END,
        1
    )
    ON CONFLICT (workspace_id, time_bucket, bucket_size)
    DO UPDATE SET
        error_count = analytics.error_timeline.error_count + 1,
        critical_count = analytics.error_timeline.critical_count +
            CASE WHEN p_severity = 'critical' THEN 1 ELSE 0 END;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.update_error_timeline IS 'Update error timeline metrics for spike detection';

-- =====================================================================
-- Sample Data Generation (for development/testing)
-- =====================================================================

-- Function to generate sample errors
CREATE OR REPLACE FUNCTION analytics.generate_sample_errors(
    p_workspace_id UUID,
    p_days_back INTEGER DEFAULT 7,
    p_errors_per_day INTEGER DEFAULT 20
)
RETURNS void AS $$
DECLARE
    v_date DATE;
    v_error_count INTEGER;
    v_error_types TEXT[] := ARRAY[
        'TimeoutError',
        'ValidationError',
        'AuthenticationError',
        'RateLimitError',
        'ModelError',
        'NetworkError',
        'ResourceError'
    ];
    v_severities TEXT[] := ARRAY['low', 'medium', 'high', 'critical'];
    v_error_type TEXT;
    v_severity TEXT;
    v_fingerprint VARCHAR(32);
BEGIN
    FOR i IN 0..p_days_back LOOP
        v_date := CURRENT_DATE - (i || ' days')::INTERVAL;
        v_error_count := p_errors_per_day + FLOOR(RANDOM() * 10 - 5);

        FOR j IN 1..v_error_count LOOP
            v_error_type := v_error_types[1 + FLOOR(RANDOM() * ARRAY_LENGTH(v_error_types, 1))];
            v_severity := v_severities[1 + FLOOR(RANDOM() * ARRAY_LENGTH(v_severities, 1))];
            v_fingerprint := MD5(v_error_type || FLOOR(RANDOM() * 5)::TEXT);

            INSERT INTO analytics.errors (
                fingerprint,
                workspace_id,
                error_type,
                message,
                severity,
                status,
                first_seen,
                last_seen,
                occurrence_count,
                stack_trace,
                users_affected,
                executions_affected,
                credits_lost
            ) VALUES (
                v_fingerprint,
                p_workspace_id,
                v_error_type,
                'Sample error message for ' || v_error_type,
                v_severity,
                CASE
                    WHEN RANDOM() < 0.6 THEN 'new'
                    WHEN RANDOM() < 0.8 THEN 'acknowledged'
                    WHEN RANDOM() < 0.9 THEN 'investigating'
                    ELSE 'resolved'
                END,
                v_date + (RANDOM() * INTERVAL '12 hours'),
                v_date + (RANDOM() * INTERVAL '24 hours'),
                1 + FLOOR(RANDOM() * 10),
                'Sample stack trace',
                ARRAY[gen_random_uuid()::TEXT],
                FLOOR(RANDOM() * 5),
                ROUND((RANDOM() * 10)::NUMERIC, 2)
            )
            ON CONFLICT (fingerprint, workspace_id) DO NOTHING;
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Generated sample errors for % days', p_days_back;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.generate_sample_errors IS 'Generate sample error data for testing';
