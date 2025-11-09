-- =====================================================================
-- Migration: 009_create_agent_analytics_tables.sql
-- Description: Create comprehensive agent analytics tables
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: agent_runs
-- Description: Detailed individual agent execution logs
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Execution details
    status VARCHAR(20) NOT NULL CHECK (status IN ('completed', 'failed', 'cancelled', 'timeout')),
    runtime_seconds NUMERIC(10,2),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,

    -- Resource usage
    credits_consumed NUMERIC(10,2) DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    model_name VARCHAR(100),

    -- Concurrency tracking
    concurrent_runs INTEGER DEFAULT 1,

    -- Error details (if failed)
    error_type VARCHAR(100),
    error_message TEXT,
    error_stack TEXT,

    -- User feedback
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_runtime CHECK (
        (status = 'completed' AND runtime_seconds IS NOT NULL) OR
        (status != 'completed')
    )
);

-- Agent Runs Indexes
CREATE INDEX idx_agent_runs_agent_time
    ON analytics.agent_runs(agent_id, started_at DESC);
CREATE INDEX idx_agent_runs_workspace_time
    ON analytics.agent_runs(workspace_id, started_at DESC);
CREATE INDEX idx_agent_runs_user
    ON analytics.agent_runs(user_id, started_at DESC);
CREATE INDEX idx_agent_runs_status
    ON analytics.agent_runs(status, started_at DESC);
CREATE INDEX idx_agent_runs_runtime
    ON analytics.agent_runs(runtime_seconds) WHERE runtime_seconds IS NOT NULL;
CREATE INDEX idx_agent_runs_created_brin
    ON analytics.agent_runs USING brin(started_at);

-- Comments
COMMENT ON TABLE analytics.agent_runs IS 'Individual agent execution records for detailed analytics';
COMMENT ON COLUMN analytics.agent_runs.concurrent_runs IS 'Number of concurrent executions at run time';
COMMENT ON COLUMN analytics.agent_runs.metadata IS 'Additional execution context and parameters';

-- =====================================================================
-- Table: agent_errors
-- Description: Categorized agent error tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    agent_run_id UUID REFERENCES analytics.agent_runs(id) ON DELETE CASCADE,

    -- Error classification
    error_type VARCHAR(100) NOT NULL,
    error_category VARCHAR(50) NOT NULL CHECK (
        error_category IN (
            'timeout', 'rate_limit', 'validation', 'model_error',
            'network', 'auth', 'resource', 'user_error', 'unknown'
        )
    ),
    error_severity VARCHAR(20) NOT NULL CHECK (
        error_severity IN ('low', 'medium', 'high', 'critical')
    ),

    -- Error details
    error_message TEXT NOT NULL,
    error_stack TEXT,
    error_context JSONB DEFAULT '{}',

    -- Recovery information
    auto_recovered BOOLEAN DEFAULT FALSE,
    recovery_time_seconds NUMERIC(10,2),
    recovery_attempts INTEGER DEFAULT 0,

    -- Impact
    affected_users INTEGER DEFAULT 1,
    business_impact VARCHAR(20) CHECK (business_impact IN ('low', 'medium', 'high')),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Errors Indexes
CREATE INDEX idx_agent_errors_agent_time
    ON analytics.agent_errors(agent_id, created_at DESC);
CREATE INDEX idx_agent_errors_type
    ON analytics.agent_errors(error_type, created_at DESC);
CREATE INDEX idx_agent_errors_category
    ON analytics.agent_errors(error_category, error_severity);
CREATE INDEX idx_agent_errors_workspace
    ON analytics.agent_errors(workspace_id, created_at DESC);
CREATE INDEX idx_agent_errors_run
    ON analytics.agent_errors(agent_run_id) WHERE agent_run_id IS NOT NULL;

-- Comments
COMMENT ON TABLE analytics.agent_errors IS 'Categorized agent error tracking with recovery metrics';
COMMENT ON COLUMN analytics.agent_errors.auto_recovered IS 'Whether the error was automatically recovered from';
COMMENT ON COLUMN analytics.agent_errors.error_context IS 'Additional context about the error (input params, state, etc.)';

-- =====================================================================
-- Table: agent_performance_hourly
-- Description: Hourly aggregated agent performance metrics
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_performance_hourly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    metric_hour TIMESTAMPTZ NOT NULL,

    -- Execution metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    cancelled_runs INTEGER DEFAULT 0,

    -- Performance metrics
    avg_runtime_seconds NUMERIC(10,2),
    p50_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),

    -- Resource metrics
    total_credits NUMERIC(15,2) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- User metrics
    unique_users INTEGER DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    sum_ratings INTEGER DEFAULT 0,

    -- Error metrics
    total_errors INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_agent_hour UNIQUE(agent_id, metric_hour)
);

-- Hourly Performance Indexes
CREATE INDEX idx_agent_perf_hourly_agent_time
    ON analytics.agent_performance_hourly(agent_id, metric_hour DESC);
CREATE INDEX idx_agent_perf_hourly_workspace
    ON analytics.agent_performance_hourly(workspace_id, metric_hour DESC);

-- Comments
COMMENT ON TABLE analytics.agent_performance_hourly IS 'Hourly aggregated metrics for real-time agent monitoring';

-- =====================================================================
-- Table: agent_optimization_suggestions
-- Description: Store optimization recommendations for agents
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_optimization_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Suggestion details
    suggestion_type VARCHAR(20) NOT NULL CHECK (
        suggestion_type IN ('performance', 'cost', 'reliability', 'user_experience')
    ),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    estimated_impact TEXT,
    effort_level VARCHAR(20) NOT NULL CHECK (effort_level IN ('low', 'medium', 'high')),

    -- Priority
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (
        status IN ('active', 'implemented', 'dismissed', 'archived')
    ),
    implemented_at TIMESTAMPTZ,

    -- Impact tracking
    baseline_metrics JSONB,
    post_implementation_metrics JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optimization Suggestions Indexes
CREATE INDEX idx_agent_opt_suggestions_agent
    ON analytics.agent_optimization_suggestions(agent_id, status, priority DESC);
CREATE INDEX idx_agent_opt_suggestions_workspace
    ON analytics.agent_optimization_suggestions(workspace_id, status);
CREATE INDEX idx_agent_opt_suggestions_type
    ON analytics.agent_optimization_suggestions(suggestion_type, status);

-- Comments
COMMENT ON TABLE analytics.agent_optimization_suggestions IS 'AI-generated optimization recommendations for agents';
COMMENT ON COLUMN analytics.agent_optimization_suggestions.baseline_metrics IS 'Metrics before implementation';
COMMENT ON COLUMN analytics.agent_optimization_suggestions.post_implementation_metrics IS 'Metrics after implementation';

-- =====================================================================
-- Table: agent_user_feedback
-- Description: Detailed user feedback and ratings
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    agent_run_id UUID REFERENCES analytics.agent_runs(id) ON DELETE SET NULL,

    -- Rating
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),

    -- Feedback
    comment TEXT,
    feedback_category VARCHAR(50) CHECK (
        feedback_category IN (
            'speed', 'accuracy', 'reliability', 'usability',
            'cost', 'documentation', 'other'
        )
    ),

    -- Sentiment analysis
    sentiment VARCHAR(20) CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    sentiment_score NUMERIC(3,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Feedback Indexes
CREATE INDEX idx_agent_feedback_agent_time
    ON analytics.agent_user_feedback(agent_id, created_at DESC);
CREATE INDEX idx_agent_feedback_user
    ON analytics.agent_user_feedback(user_id, created_at DESC);
CREATE INDEX idx_agent_feedback_rating
    ON analytics.agent_user_feedback(rating, created_at DESC);
CREATE INDEX idx_agent_feedback_workspace
    ON analytics.agent_user_feedback(workspace_id, created_at DESC);

-- Comments
COMMENT ON TABLE analytics.agent_user_feedback IS 'User ratings and feedback for agent executions';
COMMENT ON COLUMN analytics.agent_user_feedback.sentiment_score IS 'Automated sentiment analysis score (-1 to 1)';

-- =====================================================================
-- Table: agent_model_usage
-- Description: Track model usage per agent for cost analysis
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_model_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    metric_date DATE NOT NULL,

    -- Model details
    model_name VARCHAR(100) NOT NULL,
    model_provider VARCHAR(50),

    -- Usage metrics
    total_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_credits NUMERIC(15,2) DEFAULT 0,

    -- Cost breakdown
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_agent_model_date UNIQUE(agent_id, model_name, metric_date)
);

-- Model Usage Indexes
CREATE INDEX idx_agent_model_usage_agent_date
    ON analytics.agent_model_usage(agent_id, metric_date DESC);
CREATE INDEX idx_agent_model_usage_workspace
    ON analytics.agent_model_usage(workspace_id, metric_date DESC);
CREATE INDEX idx_agent_model_usage_model
    ON analytics.agent_model_usage(model_name, metric_date DESC);

-- Comments
COMMENT ON TABLE analytics.agent_model_usage IS 'Track AI model usage per agent for cost optimization';

-- =====================================================================
-- Materialized View: agent_analytics_summary
-- Description: Pre-aggregated agent analytics for fast queries
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.agent_analytics_summary AS
SELECT
    ar.agent_id,
    ar.workspace_id,
    DATE_TRUNC('day', ar.started_at) as metric_date,

    -- Execution counts
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE ar.status = 'completed') as successful_runs,
    COUNT(*) FILTER (WHERE ar.status = 'failed') as failed_runs,
    COUNT(*) FILTER (WHERE ar.status = 'cancelled') as cancelled_runs,

    -- Success rate
    ROUND(
        (COUNT(*) FILTER (WHERE ar.status = 'completed')::NUMERIC /
         NULLIF(COUNT(*), 0) * 100), 2
    ) as success_rate,

    -- Runtime statistics
    ROUND(AVG(ar.runtime_seconds), 2) as avg_runtime,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ar.runtime_seconds), 2) as median_runtime,
    ROUND(MIN(ar.runtime_seconds), 2) as min_runtime,
    ROUND(MAX(ar.runtime_seconds), 2) as max_runtime,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ar.runtime_seconds), 2) as p75_runtime,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY ar.runtime_seconds), 2) as p90_runtime,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ar.runtime_seconds), 2) as p95_runtime,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ar.runtime_seconds), 2) as p99_runtime,
    ROUND(STDDEV(ar.runtime_seconds), 2) as std_dev_runtime,

    -- Resource metrics
    ROUND(SUM(ar.credits_consumed), 2) as total_credits,
    ROUND(AVG(ar.credits_consumed), 2) as avg_credits_per_run,
    SUM(ar.tokens_used) as total_tokens,
    ROUND(AVG(ar.tokens_used), 0) as avg_tokens_per_run,

    -- User metrics
    COUNT(DISTINCT ar.user_id) as unique_users,
    COUNT(ar.user_rating) as total_ratings,
    ROUND(AVG(ar.user_rating), 2) as avg_rating,

    -- Error metrics
    COUNT(*) FILTER (WHERE ar.error_type IS NOT NULL) as total_errors,

    -- Concurrency
    MAX(ar.concurrent_runs) as peak_concurrency,
    ROUND(AVG(ar.concurrent_runs), 2) as avg_concurrency

FROM analytics.agent_runs ar
WHERE ar.started_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY ar.agent_id, ar.workspace_id, DATE_TRUNC('day', ar.started_at);

-- Index on materialized view
CREATE INDEX idx_agent_analytics_summary_agent_date
    ON analytics.agent_analytics_summary(agent_id, metric_date DESC);
CREATE INDEX idx_agent_analytics_summary_workspace
    ON analytics.agent_analytics_summary(workspace_id, metric_date DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.agent_analytics_summary IS 'Pre-aggregated daily agent metrics for fast dashboard queries';

-- =====================================================================
-- Automatic Refresh Function
-- =====================================================================

-- Function to refresh agent analytics summary
CREATE OR REPLACE FUNCTION analytics.refresh_agent_analytics_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.agent_analytics_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_agent_analytics_summary() IS 'Refresh agent analytics summary materialized view';

-- =====================================================================
-- Sample Data Generation (for development/testing)
-- =====================================================================

-- Function to generate sample agent runs
CREATE OR REPLACE FUNCTION analytics.generate_sample_agent_runs(
    p_agent_id UUID,
    p_workspace_id UUID,
    p_days_back INTEGER DEFAULT 30,
    p_runs_per_day INTEGER DEFAULT 50
)
RETURNS void AS $$
DECLARE
    v_date DATE;
    v_run_count INTEGER;
    v_status VARCHAR(20);
    v_runtime NUMERIC;
    v_user_ids UUID[] := ARRAY[
        gen_random_uuid(),
        gen_random_uuid(),
        gen_random_uuid(),
        gen_random_uuid(),
        gen_random_uuid()
    ];
BEGIN
    -- Generate runs for each day
    FOR i IN 0..p_days_back LOOP
        v_date := CURRENT_DATE - (i || ' days')::INTERVAL;

        -- Generate random number of runs for the day
        v_run_count := p_runs_per_day + FLOOR(RANDOM() * 20 - 10);

        FOR j IN 1..v_run_count LOOP
            -- Random status (85% success rate)
            v_status := CASE
                WHEN RANDOM() < 0.85 THEN 'completed'
                WHEN RANDOM() < 0.92 THEN 'failed'
                ELSE 'cancelled'
            END;

            -- Random runtime (normal distribution around 5 seconds)
            v_runtime := GREATEST(0.1, 5.0 + (RANDOM() - 0.5) * 8);

            INSERT INTO analytics.agent_runs (
                agent_id,
                workspace_id,
                user_id,
                status,
                runtime_seconds,
                started_at,
                completed_at,
                credits_consumed,
                tokens_used,
                model_name,
                concurrent_runs,
                user_rating
            ) VALUES (
                p_agent_id,
                p_workspace_id,
                v_user_ids[1 + FLOOR(RANDOM() * 5)],
                v_status,
                CASE WHEN v_status = 'completed' THEN v_runtime ELSE NULL END,
                v_date + (RANDOM() * INTERVAL '24 hours'),
                CASE WHEN v_status = 'completed'
                    THEN v_date + (RANDOM() * INTERVAL '24 hours') + (v_runtime || ' seconds')::INTERVAL
                    ELSE NULL
                END,
                ROUND(v_runtime * 0.5 + RANDOM() * 2, 2),
                FLOOR(500 + RANDOM() * 2000),
                CASE WHEN RANDOM() < 0.5 THEN 'gpt-4' ELSE 'gpt-3.5-turbo' END,
                1 + FLOOR(RANDOM() * 5),
                CASE WHEN v_status = 'completed' AND RANDOM() < 0.3
                    THEN 3 + FLOOR(RANDOM() * 3)
                    ELSE NULL
                END
            );
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Generated sample agent runs for % days', p_days_back;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.generate_sample_agent_runs IS 'Generate sample agent run data for testing';
