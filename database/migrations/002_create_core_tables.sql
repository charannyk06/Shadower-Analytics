-- =====================================================================
-- Migration: 002_create_core_tables.sql
-- Description: Create core analytics tables (user_activity, metrics rollups)
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: user_activity
-- Description: Track all user activity events for detailed analytics
-- =====================================================================

CREATE TABLE analytics.user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    workspace_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_name VARCHAR(100),
    page_path VARCHAR(255),
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'page_view', 'agent_run', 'login', 'logout',
            'workspace_switch', 'feature_use', 'error',
            'api_call', 'export', 'report_view'
        )
    )
);

-- User Activity Indexes
CREATE INDEX idx_user_activity_user_time
    ON analytics.user_activity(user_id, created_at DESC);
CREATE INDEX idx_user_activity_workspace_time
    ON analytics.user_activity(workspace_id, created_at DESC) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_user_activity_event_type
    ON analytics.user_activity(event_type, created_at DESC);
CREATE INDEX idx_user_activity_session
    ON analytics.user_activity(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_user_activity_metadata
    ON analytics.user_activity USING gin(metadata);
CREATE INDEX idx_user_activity_created_at_brin
    ON analytics.user_activity USING brin(created_at);

-- Comments
COMMENT ON TABLE analytics.user_activity IS 'Tracks all user activity events for detailed behavioral analytics';
COMMENT ON COLUMN analytics.user_activity.event_type IS 'Type of event: page_view, agent_run, login, etc.';
COMMENT ON COLUMN analytics.user_activity.metadata IS 'Additional event-specific data stored as JSON';

-- =====================================================================
-- Table: daily_metrics
-- Description: Daily aggregated metrics for performance and analysis
-- =====================================================================

CREATE TABLE analytics.daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL,
    workspace_id UUID,

    -- User metrics
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,

    -- Session metrics
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration_seconds NUMERIC(10,2),
    bounce_rate NUMERIC(5,2),

    -- Execution metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    cancelled_runs INTEGER DEFAULT 0,
    avg_runtime_seconds NUMERIC(10,2),
    median_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),
    p99_runtime_seconds NUMERIC(10,2),

    -- Credit metrics
    total_credits_consumed NUMERIC(15,2) DEFAULT 0,
    avg_credits_per_run NUMERIC(10,2),
    credits_by_model JSONB DEFAULT '{}',

    -- Agent metrics
    unique_agents_run INTEGER DEFAULT 0,
    top_agents JSONB DEFAULT '[]',

    -- Error metrics
    total_errors INTEGER DEFAULT 0,
    error_rate NUMERIC(5,2),
    errors_by_type JSONB DEFAULT '{}',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_daily_metric UNIQUE(metric_date, workspace_id)
);

-- Daily Metrics Indexes
CREATE INDEX idx_daily_metrics_date
    ON analytics.daily_metrics(metric_date DESC);
CREATE INDEX idx_daily_metrics_workspace
    ON analytics.daily_metrics(workspace_id, metric_date DESC) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_daily_metrics_date_brin
    ON analytics.daily_metrics USING brin(metric_date);

-- Comments
COMMENT ON TABLE analytics.daily_metrics IS 'Daily aggregated metrics for overall system performance';
COMMENT ON COLUMN analytics.daily_metrics.credits_by_model IS 'JSON object with credits consumed per AI model';
COMMENT ON COLUMN analytics.daily_metrics.top_agents IS 'JSON array of top performing agents for the day';

-- =====================================================================
-- Table: hourly_metrics
-- Description: Hourly metrics for real-time monitoring
-- =====================================================================

CREATE TABLE analytics.hourly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_hour TIMESTAMPTZ NOT NULL,
    workspace_id UUID,

    -- Real-time counters
    active_users INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    total_credits NUMERIC(10,2) DEFAULT 0,

    -- Performance
    avg_response_time_ms INTEGER,
    p95_response_time_ms INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_hourly_metric UNIQUE(metric_hour, workspace_id)
);

-- Hourly Metrics Indexes
CREATE INDEX idx_hourly_metrics_hour
    ON analytics.hourly_metrics(metric_hour DESC);
CREATE INDEX idx_hourly_metrics_workspace
    ON analytics.hourly_metrics(workspace_id, metric_hour DESC) WHERE workspace_id IS NOT NULL;

-- Comments
COMMENT ON TABLE analytics.hourly_metrics IS 'Hourly aggregated metrics for real-time monitoring and alerting';

-- =====================================================================
-- Table: agent_performance
-- Description: Detailed performance metrics per agent
-- =====================================================================

CREATE TABLE analytics.agent_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    metric_date DATE NOT NULL,
    workspace_id UUID,

    -- Execution stats
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    cancelled_runs INTEGER DEFAULT 0,

    -- Performance metrics
    avg_runtime_seconds NUMERIC(10,2),
    min_runtime_seconds NUMERIC(10,2),
    max_runtime_seconds NUMERIC(10,2),
    p50_runtime_seconds NUMERIC(10,2),
    p75_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),
    p99_runtime_seconds NUMERIC(10,2),

    -- Resource usage
    total_credits NUMERIC(15,2) DEFAULT 0,
    avg_credits_per_run NUMERIC(10,2),
    total_tokens_used BIGINT DEFAULT 0,
    avg_tokens_per_run INTEGER,

    -- User interaction
    unique_users INTEGER DEFAULT 0,
    avg_user_rating NUMERIC(3,2),
    total_feedback_count INTEGER DEFAULT 0,

    -- Error tracking
    error_types JSONB DEFAULT '{}',
    common_failure_reasons JSONB DEFAULT '[]',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_agent_performance UNIQUE(agent_id, metric_date)
);

-- Agent Performance Indexes
CREATE INDEX idx_agent_performance_agent
    ON analytics.agent_performance(agent_id, metric_date DESC);
CREATE INDEX idx_agent_performance_date
    ON analytics.agent_performance(metric_date DESC);
CREATE INDEX idx_agent_performance_workspace
    ON analytics.agent_performance(workspace_id, metric_date DESC) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_agent_performance_composite
    ON analytics.agent_performance(workspace_id, metric_date DESC, total_runs DESC);

-- Comments
COMMENT ON TABLE analytics.agent_performance IS 'Daily performance metrics for individual agents';
COMMENT ON COLUMN analytics.agent_performance.error_types IS 'JSON object with count of each error type';
COMMENT ON COLUMN analytics.agent_performance.common_failure_reasons IS 'JSON array of common reasons for failures';
