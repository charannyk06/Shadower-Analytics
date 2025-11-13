-- =====================================================================
-- Migration: 030_create_advanced_error_analytics.sql
-- Description: Create advanced error analytics tables for ML-powered RCA,
--              recovery strategies, cascading failure detection,
--              and business impact analysis
-- Created: 2025-11-13
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: error_patterns_enhanced
-- Description: Enhanced error pattern analysis with ML features
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_patterns_enhanced (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name VARCHAR(255) NOT NULL,
    pattern_signature TEXT NOT NULL, -- Regex or pattern matching rule
    category VARCHAR(50) NOT NULL,

    -- Pattern metrics
    occurrence_count INTEGER DEFAULT 0,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ,
    affected_agents UUID[],
    affected_workspaces UUID[],

    -- Resolution information
    known_fixes JSONB DEFAULT '[]',
    auto_recoverable BOOLEAN DEFAULT FALSE,
    recovery_strategy TEXT,
    avg_resolution_time_ms INTEGER,

    -- ML pattern detection
    ml_confidence_score FLOAT DEFAULT 0.0,
    feature_vector FLOAT[],
    cluster_id INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_pattern_signature UNIQUE(pattern_signature)
);

-- Indexes for error_patterns_enhanced
CREATE INDEX idx_error_patterns_enhanced_category
    ON analytics.error_patterns_enhanced(category);
CREATE INDEX idx_error_patterns_enhanced_cluster
    ON analytics.error_patterns_enhanced(cluster_id) WHERE cluster_id IS NOT NULL;
CREATE INDEX idx_error_patterns_enhanced_last_seen
    ON analytics.error_patterns_enhanced(last_seen DESC NULLS LAST);

COMMENT ON TABLE analytics.error_patterns_enhanced IS
    'Enhanced error pattern database with ML-powered detection and resolution strategies';

-- =====================================================================
-- Table: error_root_causes
-- Description: Root cause analysis results
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_root_causes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID NOT NULL REFERENCES analytics.errors(error_id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL,

    -- Root cause analysis
    immediate_cause TEXT NOT NULL,
    root_causes JSONB DEFAULT '[]', -- Array of {cause, probability, evidence, remediation}
    contributing_factors JSONB DEFAULT '[]',

    -- Correlation analysis
    correlated_changes JSONB DEFAULT '[]', -- Recent deployments, config changes, etc.
    similar_errors UUID[], -- IDs of similar errors

    -- Advanced RCA
    dependency_chain JSONB DEFAULT '[]',
    temporal_correlation JSONB DEFAULT '{}',
    environmental_factors JSONB DEFAULT '{}',

    -- Remediation
    remediation_suggestions JSONB DEFAULT '[]',
    auto_remediation_possible BOOLEAN DEFAULT FALSE,

    -- Analysis metadata
    analysis_confidence FLOAT DEFAULT 0.0,
    analysis_version VARCHAR(50),
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_root_causes
CREATE INDEX idx_error_root_causes_error
    ON analytics.error_root_causes(error_id);
CREATE INDEX idx_error_root_causes_workspace
    ON analytics.error_root_causes(workspace_id, analyzed_at DESC);
CREATE INDEX idx_error_root_causes_auto_remediation
    ON analytics.error_root_causes(auto_remediation_possible) WHERE auto_remediation_possible = TRUE;

COMMENT ON TABLE analytics.error_root_causes IS
    'Automated root cause analysis results with ML-powered insights';

-- =====================================================================
-- Table: recovery_strategies
-- Description: Recovery strategy performance tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.recovery_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id VARCHAR(100) NOT NULL UNIQUE,
    strategy_name VARCHAR(255) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL CHECK (
        strategy_type IN ('retry', 'fallback', 'circuit_breaker', 'graceful_degradation', 'manual', 'rollback', 'scale', 'reset')
    ),

    -- Performance metrics
    total_invocations INTEGER DEFAULT 0,
    successful_recoveries INTEGER DEFAULT 0,
    failed_recoveries INTEGER DEFAULT 0,
    partial_recoveries INTEGER DEFAULT 0,

    success_rate FLOAT DEFAULT 0.0,
    avg_recovery_time_ms INTEGER DEFAULT 0,
    p95_recovery_time_ms INTEGER DEFAULT 0,
    resource_overhead FLOAT DEFAULT 0.0,
    user_impact_score FLOAT DEFAULT 0.0,

    -- Cost analysis
    recovery_cost_per_incident NUMERIC(10,2) DEFAULT 0.0,
    saved_revenue_estimate NUMERIC(10,2) DEFAULT 0.0,
    roi FLOAT DEFAULT 0.0,

    -- Strategy configuration
    config JSONB DEFAULT '{}',
    applicable_error_types TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for recovery_strategies
CREATE INDEX idx_recovery_strategies_type
    ON analytics.recovery_strategies(strategy_type);
CREATE INDEX idx_recovery_strategies_success_rate
    ON analytics.recovery_strategies(success_rate DESC);

COMMENT ON TABLE analytics.recovery_strategies IS
    'Recovery strategy performance metrics and configuration';

-- =====================================================================
-- Table: error_recovery_executions
-- Description: Detailed recovery execution logs
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_recovery_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID NOT NULL REFERENCES analytics.errors(error_id) ON DELETE CASCADE,
    strategy_id VARCHAR(100) NOT NULL REFERENCES analytics.recovery_strategies(strategy_id),
    occurrence_id UUID REFERENCES analytics.error_occurrences(id) ON DELETE SET NULL,

    -- Execution details
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'running' CHECK (
        status IN ('running', 'success', 'failed', 'partial', 'timeout', 'cancelled')
    ),

    -- Performance
    recovery_time_ms INTEGER,
    resource_usage JSONB DEFAULT '{}',

    -- Result
    steps_executed JSONB DEFAULT '[]', -- Array of {step, status, result, timestamp}
    final_result TEXT,
    failure_reason TEXT,

    -- Context
    execution_context JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_recovery_executions
CREATE INDEX idx_error_recovery_executions_error
    ON analytics.error_recovery_executions(error_id, started_at DESC);
CREATE INDEX idx_error_recovery_executions_strategy
    ON analytics.error_recovery_executions(strategy_id, started_at DESC);
CREATE INDEX idx_error_recovery_executions_status
    ON analytics.error_recovery_executions(status, started_at DESC);

COMMENT ON TABLE analytics.error_recovery_executions IS
    'Detailed tracking of recovery strategy executions';

-- =====================================================================
-- Table: error_cascades
-- Description: Cascading failure detection and tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_cascades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Cascade identification
    initial_error_id UUID NOT NULL REFERENCES analytics.errors(error_id),
    cascade_chain UUID[], -- Ordered array of error IDs in cascade

    -- Metrics
    cascade_start TIMESTAMPTZ NOT NULL,
    cascade_end TIMESTAMPTZ,
    cascade_duration_seconds INTEGER,

    affected_agents_count INTEGER DEFAULT 0,
    affected_users_count INTEGER DEFAULT 0,
    total_errors_in_cascade INTEGER DEFAULT 0,

    -- Severity classification
    cascade_severity VARCHAR(50) DEFAULT 'isolated' CHECK (
        cascade_severity IN ('isolated', 'minor_cascade', 'moderate_cascade', 'major_cascade', 'critical_cascade')
    ),

    -- Analysis
    root_cause_identified BOOLEAN DEFAULT FALSE,
    root_cause TEXT,
    preventable BOOLEAN DEFAULT NULL,
    prevention_strategy TEXT,

    -- Impact
    business_impact JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_cascades
CREATE INDEX idx_error_cascades_workspace
    ON analytics.error_cascades(workspace_id, cascade_start DESC);
CREATE INDEX idx_error_cascades_initial_error
    ON analytics.error_cascades(initial_error_id);
CREATE INDEX idx_error_cascades_severity
    ON analytics.error_cascades(cascade_severity, cascade_start DESC);

COMMENT ON TABLE analytics.error_cascades IS
    'Cascading failure detection and analysis';

-- =====================================================================
-- Table: error_business_impact
-- Description: Business impact analysis for errors
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_business_impact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID NOT NULL REFERENCES analytics.errors(error_id) ON DELETE CASCADE,
    cascade_id UUID REFERENCES analytics.error_cascades(id) ON DELETE SET NULL,
    workspace_id UUID NOT NULL,

    -- Financial impact
    lost_revenue NUMERIC(12,2) DEFAULT 0.0,
    additional_costs NUMERIC(12,2) DEFAULT 0.0,
    credit_refunds NUMERIC(12,2) DEFAULT 0.0,
    total_financial_impact NUMERIC(12,2) DEFAULT 0.0,

    -- Operational impact
    downtime_minutes INTEGER DEFAULT 0,
    affected_workflows TEXT[],
    manual_intervention_hours FLOAT DEFAULT 0.0,
    sla_violations INTEGER DEFAULT 0,

    -- User impact
    affected_users_count INTEGER DEFAULT 0,
    user_satisfaction_impact FLOAT DEFAULT 0.0, -- Score -1.0 to 0.0
    churn_risk FLOAT DEFAULT 0.0, -- Probability 0.0 to 1.0
    support_tickets_generated INTEGER DEFAULT 0,

    -- Reputation impact
    reputation_severity_score FLOAT DEFAULT 0.0,
    public_visibility BOOLEAN DEFAULT FALSE,
    recovery_time_expectation_minutes INTEGER,

    -- Analysis metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    calculation_version VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_business_impact
CREATE INDEX idx_error_business_impact_error
    ON analytics.error_business_impact(error_id);
CREATE INDEX idx_error_business_impact_workspace
    ON analytics.error_business_impact(workspace_id, calculated_at DESC);
CREATE INDEX idx_error_business_impact_financial
    ON analytics.error_business_impact(total_financial_impact DESC);

COMMENT ON TABLE analytics.error_business_impact IS
    'Comprehensive business impact analysis for errors and cascades';

-- =====================================================================
-- Table: error_predictions
-- Description: Predictive error analytics
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.error_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    agent_id UUID,

    -- Prediction
    prediction_date DATE NOT NULL,
    error_probability FLOAT NOT NULL, -- 0.0 to 1.0
    risk_level VARCHAR(50) NOT NULL CHECK (
        risk_level IN ('low', 'medium', 'high', 'critical')
    ),

    -- Risk factors
    top_risk_factors JSONB DEFAULT '[]',
    predicted_error_types TEXT[],

    -- Prevention
    prevention_actions JSONB DEFAULT '[]',
    prevention_priority INTEGER DEFAULT 0,

    -- Model metadata
    model_version VARCHAR(50),
    confidence_score FLOAT DEFAULT 0.0,

    -- Outcome (filled after prediction date)
    actual_errors_occurred INTEGER,
    prediction_accuracy FLOAT,

    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for error_predictions
CREATE INDEX idx_error_predictions_workspace
    ON analytics.error_predictions(workspace_id, prediction_date DESC);
CREATE INDEX idx_error_predictions_agent
    ON analytics.error_predictions(agent_id, prediction_date DESC) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_error_predictions_risk_level
    ON analytics.error_predictions(risk_level, prediction_date DESC);

COMMENT ON TABLE analytics.error_predictions IS
    'ML-powered predictive error analytics and prevention recommendations';

-- =====================================================================
-- Table: auto_resolution_rules
-- Description: Automated error resolution rules and playbooks
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.auto_resolution_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(255) NOT NULL,
    workspace_id UUID, -- NULL means global rule
    agent_id UUID, -- NULL means applies to all agents

    -- Rule matching
    error_pattern TEXT NOT NULL, -- Regex pattern
    error_categories TEXT[],
    severity_levels TEXT[],
    condition_expression TEXT, -- JavaScript expression

    -- Actions
    actions JSONB NOT NULL, -- Array of {action_type, parameters, max_attempts, backoff_strategy}
    success_criteria TEXT,
    fallback_action TEXT,

    -- Limits and safety
    max_auto_resolutions_per_hour INTEGER DEFAULT 10,
    max_retry_attempts INTEGER DEFAULT 3,
    require_approval_for TEXT[], -- Error categories requiring manual approval

    -- Status and metrics
    enabled BOOLEAN DEFAULT TRUE,
    times_triggered INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Indexes for auto_resolution_rules
CREATE INDEX idx_auto_resolution_rules_workspace
    ON analytics.auto_resolution_rules(workspace_id) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_auto_resolution_rules_agent
    ON analytics.auto_resolution_rules(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_auto_resolution_rules_enabled
    ON analytics.auto_resolution_rules(enabled) WHERE enabled = TRUE;

COMMENT ON TABLE analytics.auto_resolution_rules IS
    'Automated error resolution rules and playbooks';

-- =====================================================================
-- Materialized View: error_correlation_matrix
-- Description: Error correlation analysis
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.error_correlation_matrix AS
WITH error_pairs AS (
    SELECT
        e1.error_type as error_type_1,
        e2.error_type as error_type_2,
        e1.workspace_id,
        COUNT(*) as co_occurrence_count,
        AVG(EXTRACT(EPOCH FROM (e2.last_seen - e1.first_seen))) as avg_time_diff_seconds
    FROM analytics.error_occurrences eo1
    JOIN analytics.errors e1 ON eo1.error_id = e1.error_id
    JOIN analytics.error_occurrences eo2 ON eo1.agent_id = eo2.agent_id
    JOIN analytics.errors e2 ON eo2.error_id = e2.error_id
    WHERE e1.error_id != e2.error_id
        AND eo2.occurred_at >= eo1.occurred_at
        AND eo2.occurred_at <= eo1.occurred_at + INTERVAL '5 minutes'
        AND e1.created_at >= NOW() - INTERVAL '90 days'
    GROUP BY e1.error_type, e2.error_type, e1.workspace_id
    HAVING COUNT(*) > 5
)
SELECT
    workspace_id,
    error_type_1,
    error_type_2,
    co_occurrence_count,
    avg_time_diff_seconds,
    co_occurrence_count::float / NULLIF((
        SELECT COUNT(*)
        FROM analytics.errors
        WHERE error_type = error_type_1
            AND workspace_id = error_pairs.workspace_id
    ), 0) as conditional_probability,
    CASE
        WHEN avg_time_diff_seconds < 10 THEN 'immediate'
        WHEN avg_time_diff_seconds < 60 THEN 'quick'
        WHEN avg_time_diff_seconds < 300 THEN 'delayed'
        ELSE 'long_delayed'
    END as correlation_timing
FROM error_pairs
ORDER BY workspace_id, co_occurrence_count DESC;

-- Index on materialized view
CREATE INDEX idx_error_correlation_matrix_workspace
    ON analytics.error_correlation_matrix(workspace_id, co_occurrence_count DESC);

COMMENT ON MATERIALIZED VIEW analytics.error_correlation_matrix IS
    'Error correlation analysis for identifying cascading failures';

-- =====================================================================
-- Materialized View: cascading_failure_analysis
-- Description: Comprehensive cascading failure view
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.cascading_failure_analysis AS
WITH error_cascade AS (
    SELECT
        e1.error_id as initial_error_id,
        e1.workspace_id,
        e1.error_type as initial_error_type,
        e1.first_seen as cascade_start,
        ARRAY_AGG(
            e2.error_id ORDER BY e2.first_seen
        ) as cascade_chain,
        COUNT(DISTINCT e2.error_id) as cascade_length,
        COUNT(DISTINCT UNNEST(e2.agents_affected)) as affected_agents,
        COUNT(DISTINCT UNNEST(e2.users_affected)) as affected_users,
        MAX(e2.last_seen) as cascade_end,
        EXTRACT(EPOCH FROM (MAX(e2.last_seen) - e1.first_seen)) as cascade_duration_seconds,
        SUM(e2.occurrence_count) as total_errors,
        SUM(e2.credits_lost) as total_credits_lost
    FROM analytics.errors e1
    JOIN analytics.errors e2
        ON e2.workspace_id = e1.workspace_id
        AND e2.first_seen > e1.first_seen
        AND e2.first_seen < e1.first_seen + INTERVAL '30 minutes'
        AND (
            e2.context->>'parent_error_id' = e1.error_id::text
            OR e2.context->'related_error_ids' ? e1.error_id::text
        )
    WHERE e1.severity IN ('critical', 'high')
        AND e1.first_seen >= NOW() - INTERVAL '90 days'
    GROUP BY e1.error_id, e1.workspace_id, e1.error_type, e1.first_seen
)
SELECT
    *,
    CASE
        WHEN affected_agents > 10 THEN 'major_cascade'
        WHEN affected_agents > 5 THEN 'moderate_cascade'
        WHEN affected_agents > 2 THEN 'minor_cascade'
        ELSE 'isolated'
    END as cascade_severity,
    CASE
        WHEN total_credits_lost > 1000 THEN 'critical'
        WHEN total_credits_lost > 500 THEN 'high'
        WHEN total_credits_lost > 100 THEN 'medium'
        ELSE 'low'
    END as business_impact_severity
FROM error_cascade
WHERE cascade_length > 1
ORDER BY cascade_start DESC;

-- Index on materialized view
CREATE INDEX idx_cascading_failure_analysis_workspace
    ON analytics.cascading_failure_analysis(workspace_id, cascade_start DESC);
CREATE INDEX idx_cascading_failure_analysis_severity
    ON analytics.cascading_failure_analysis(cascade_severity, cascade_start DESC);

COMMENT ON MATERIALIZED VIEW analytics.cascading_failure_analysis IS
    'Comprehensive cascading failure detection and analysis';

-- =====================================================================
-- Materialized View: error_trend_analysis
-- Description: Error trending and forecasting
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.error_trend_analysis AS
WITH hourly_errors AS (
    SELECT
        DATE_TRUNC('hour', et.time_bucket) as hour,
        et.workspace_id,
        e.error_type,
        e.category,
        SUM(et.error_count) as error_count,
        AVG(EXTRACT(EPOCH FROM (e.resolved_at - e.first_seen))) as avg_resolution_time,
        COUNT(DISTINCT UNNEST(e.users_affected)) as affected_users
    FROM analytics.error_timeline et
    JOIN analytics.errors e ON e.workspace_id = et.workspace_id
        AND e.last_seen >= et.time_bucket
        AND e.last_seen < et.time_bucket + INTERVAL '1 hour'
    WHERE et.time_bucket > NOW() - INTERVAL '30 days'
        AND et.bucket_size = 'hourly'
    GROUP BY DATE_TRUNC('hour', et.time_bucket), et.workspace_id, e.error_type, e.category
),
trend_calculation AS (
    SELECT
        workspace_id,
        error_type,
        category,
        REGR_SLOPE(error_count, EXTRACT(EPOCH FROM hour)) as error_trend,
        REGR_R2(error_count, EXTRACT(EPOCH FROM hour)) as trend_confidence,
        AVG(error_count) as avg_hourly_errors,
        STDDEV(error_count) as error_volatility,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY error_count) as p95_errors,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY error_count) as median_errors,
        MIN(error_count) as min_errors,
        MAX(error_count) as max_errors
    FROM hourly_errors
    GROUP BY workspace_id, error_type, category
)
SELECT
    *,
    CASE
        WHEN error_trend > 0 AND trend_confidence > 0.7 THEN 'increasing'
        WHEN error_trend < 0 AND trend_confidence > 0.7 THEN 'decreasing'
        ELSE 'stable'
    END as trend_direction,
    CASE
        WHEN error_volatility / NULLIF(avg_hourly_errors, 0) > 1 THEN 'high'
        WHEN error_volatility / NULLIF(avg_hourly_errors, 0) > 0.5 THEN 'medium'
        ELSE 'low'
    END as volatility_level,
    CASE
        WHEN avg_hourly_errors > p95_errors * 1.5 THEN 'anomalous'
        WHEN avg_hourly_errors > median_errors * 2 THEN 'elevated'
        ELSE 'normal'
    END as current_state
FROM trend_calculation;

-- Index on materialized view
CREATE INDEX idx_error_trend_analysis_workspace
    ON analytics.error_trend_analysis(workspace_id, error_type);
CREATE INDEX idx_error_trend_analysis_trend
    ON analytics.error_trend_analysis(trend_direction, trend_confidence DESC);

COMMENT ON MATERIALIZED VIEW analytics.error_trend_analysis IS
    'Error trending analysis with forecasting indicators';

-- =====================================================================
-- Functions
-- =====================================================================

-- Function to refresh all error analytics materialized views
CREATE OR REPLACE FUNCTION analytics.refresh_error_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.error_correlation_matrix;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.cascading_failure_analysis;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.error_trend_analysis;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.error_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_error_analytics_views() IS
    'Refresh all error analytics materialized views';

-- Function to detect cascading failures
CREATE OR REPLACE FUNCTION analytics.detect_cascading_failure(
    p_error_id UUID,
    p_time_window_minutes INTEGER DEFAULT 30
)
RETURNS TABLE (
    cascade_id UUID,
    cascade_chain UUID[],
    affected_count INTEGER,
    severity VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE error_chain AS (
        -- Base case: the initial error
        SELECT
            e.error_id,
            e.workspace_id,
            ARRAY[e.error_id] as chain,
            1 as depth
        FROM analytics.errors e
        WHERE e.error_id = p_error_id

        UNION ALL

        -- Recursive case: find related errors
        SELECT
            e.error_id,
            e.workspace_id,
            ec.chain || e.error_id,
            ec.depth + 1
        FROM error_chain ec
        JOIN analytics.errors e
            ON e.workspace_id = ec.workspace_id
            AND e.first_seen > (
                SELECT first_seen FROM analytics.errors WHERE error_id = ec.error_id
            )
            AND e.first_seen < (
                SELECT first_seen FROM analytics.errors WHERE error_id = ec.error_id
            ) + (p_time_window_minutes || ' minutes')::INTERVAL
            AND (
                e.context->>'parent_error_id' = ec.error_id::text
                OR e.context->'related_error_ids' ? ec.error_id::text
            )
            AND NOT (e.error_id = ANY(ec.chain)) -- Prevent cycles
        WHERE ec.depth < 10 -- Limit recursion depth
    )
    SELECT
        gen_random_uuid() as cascade_id,
        MAX(chain) as cascade_chain,
        COUNT(DISTINCT error_id) as affected_count,
        CASE
            WHEN COUNT(DISTINCT error_id) > 10 THEN 'major_cascade'
            WHEN COUNT(DISTINCT error_id) > 5 THEN 'moderate_cascade'
            WHEN COUNT(DISTINCT error_id) > 2 THEN 'minor_cascade'
            ELSE 'isolated'
        END as severity
    FROM error_chain
    GROUP BY workspace_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.detect_cascading_failure IS
    'Detect and analyze cascading failures starting from an initial error';

-- Function to calculate business impact
CREATE OR REPLACE FUNCTION analytics.calculate_error_business_impact(
    p_error_id UUID
)
RETURNS JSONB AS $$
DECLARE
    v_impact JSONB;
    v_error RECORD;
BEGIN
    SELECT * INTO v_error FROM analytics.errors WHERE error_id = p_error_id;

    IF v_error IS NULL THEN
        RETURN '{"error": "Error not found"}'::JSONB;
    END IF;

    v_impact := jsonb_build_object(
        'financial_impact', jsonb_build_object(
            'lost_revenue', COALESCE(v_error.credits_lost * 0.01, 0),
            'additional_costs', COALESCE(v_error.credits_lost * 0.02, 0),
            'credit_refunds', COALESCE(v_error.credits_lost, 0),
            'total_financial_impact', COALESCE(v_error.credits_lost * 1.03, 0)
        ),
        'operational_impact', jsonb_build_object(
            'downtime_minutes', COALESCE(
                EXTRACT(EPOCH FROM (v_error.resolved_at - v_error.first_seen)) / 60,
                0
            ),
            'affected_workflows', COALESCE(ARRAY_LENGTH(v_error.agents_affected, 1), 0),
            'manual_intervention_hours', 0.5,
            'sla_violations', CASE WHEN v_error.severity = 'critical' THEN 1 ELSE 0 END
        ),
        'user_impact', jsonb_build_object(
            'affected_users', COALESCE(ARRAY_LENGTH(v_error.users_affected, 1), 0),
            'user_satisfaction_impact', -0.1 * COALESCE(ARRAY_LENGTH(v_error.users_affected, 1), 0),
            'churn_risk', CASE
                WHEN v_error.severity = 'critical' THEN 0.3
                WHEN v_error.severity = 'high' THEN 0.1
                ELSE 0.01
            END,
            'support_tickets_generated', COALESCE(ARRAY_LENGTH(v_error.users_affected, 1), 0) / 2
        ),
        'reputation_impact', jsonb_build_object(
            'severity_score', CASE
                WHEN v_error.severity = 'critical' THEN 10
                WHEN v_error.severity = 'high' THEN 7
                WHEN v_error.severity = 'medium' THEN 4
                ELSE 1
            END,
            'public_visibility', FALSE,
            'recovery_time_expectation', 60
        )
    );

    RETURN v_impact;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.calculate_error_business_impact IS
    'Calculate comprehensive business impact for an error';

-- =====================================================================
-- Initial Data
-- =====================================================================

-- Insert default recovery strategies
INSERT INTO analytics.recovery_strategies (strategy_id, strategy_name, strategy_type, config, applicable_error_types) VALUES
('retry_exponential', 'Exponential Backoff Retry', 'retry',
 '{"max_attempts": 3, "initial_delay_ms": 1000, "multiplier": 2}'::JSONB,
 ARRAY['TimeoutError', 'NetworkError', 'RateLimitError']),

('circuit_breaker', 'Circuit Breaker Pattern', 'circuit_breaker',
 '{"failure_threshold": 5, "timeout_duration_seconds": 60, "half_open_requests": 3}'::JSONB,
 ARRAY['ServiceUnavailable', 'NetworkError']),

('fallback_default', 'Fallback to Default', 'fallback',
 '{"default_response": "cached", "cache_duration_minutes": 10}'::JSONB,
 ARRAY['ModelError', 'APIError']),

('graceful_degradation', 'Graceful Degradation', 'graceful_degradation',
 '{"reduced_functionality": true, "notify_user": true}'::JSONB,
 ARRAY['ResourceError', 'OverloadError']),

('rollback_state', 'State Rollback', 'rollback',
 '{"checkpoint_enabled": true, "rollback_depth": 1}'::JSONB,
 ARRAY['ValidationError', 'StateError'])
ON CONFLICT (strategy_id) DO NOTHING;

-- =====================================================================
-- Grants and Permissions
-- =====================================================================

-- Grant SELECT on all new tables and views to appropriate roles
-- (Assuming standard roles exist: analytics_read, analytics_write, analytics_admin)

-- Note: Adjust these grants based on your actual role structure
-- GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_read;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO analytics_write;
-- GRANT ALL ON ALL TABLES IN SCHEMA analytics TO analytics_admin;
