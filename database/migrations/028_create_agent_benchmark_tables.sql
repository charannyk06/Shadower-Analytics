-- =====================================================================
-- Migration: 028_create_agent_benchmark_tables.sql
-- Description: Create comprehensive agent benchmarking and performance testing tables
-- Created: 2025-11-13
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: benchmark_suites
-- Description: Define benchmark test suites with categories and configurations
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.benchmark_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL CHECK (
        category IN ('speed', 'accuracy', 'cost', 'reliability', 'scalability', 'comprehensive')
    ),
    description TEXT,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',

    -- Suite configuration
    suite_config JSONB DEFAULT '{}',
    baseline_agent_id UUID,

    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (
        status IN ('active', 'deprecated', 'archived', 'draft')
    ),

    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Benchmark Suites Indexes
CREATE INDEX idx_benchmark_suites_category
    ON analytics.benchmark_suites(category, status);
CREATE INDEX idx_benchmark_suites_status
    ON analytics.benchmark_suites(status, created_at DESC);

-- Comments
COMMENT ON TABLE analytics.benchmark_suites IS 'Define benchmark test suites with categories and configurations';
COMMENT ON COLUMN analytics.benchmark_suites.suite_config IS 'Configuration including weights, thresholds, and scoring rules';

-- =====================================================================
-- Table: benchmark_definitions
-- Description: Individual benchmark test definitions within suites
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.benchmark_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES analytics.benchmark_suites(id) ON DELETE CASCADE,
    benchmark_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Test configuration
    test_type VARCHAR(50) NOT NULL CHECK (
        test_type IN ('synthetic', 'real_world', 'stress', 'edge_case', 'regression')
    ),
    metrics_measured TEXT[] DEFAULT ARRAY['accuracy', 'speed', 'efficiency', 'cost', 'reliability'],

    -- Dataset configuration
    dataset_size INTEGER,
    dataset_complexity VARCHAR(20) CHECK (
        dataset_complexity IN ('low', 'medium', 'high', 'extreme')
    ),
    dataset_source TEXT,
    test_data JSONB,

    -- Constraints
    time_limit_ms INTEGER,
    memory_limit_mb INTEGER,
    token_limit INTEGER,
    cost_limit_usd NUMERIC(10,4),

    -- Expected outputs and scoring
    expected_outputs JSONB,
    scoring_rubric JSONB NOT NULL,

    -- Execution settings
    num_runs INTEGER DEFAULT 5,
    warmup_runs INTEGER DEFAULT 3,
    parallel_execution BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_benchmark_name_suite UNIQUE(suite_id, benchmark_name)
);

-- Benchmark Definitions Indexes
CREATE INDEX idx_benchmark_defs_suite
    ON analytics.benchmark_definitions(suite_id, created_at DESC);
CREATE INDEX idx_benchmark_defs_type
    ON analytics.benchmark_definitions(test_type);

-- Comments
COMMENT ON TABLE analytics.benchmark_definitions IS 'Individual benchmark test definitions within suites';
COMMENT ON COLUMN analytics.benchmark_definitions.scoring_rubric IS 'Rules for calculating benchmark scores';
COMMENT ON COLUMN analytics.benchmark_definitions.test_data IS 'Input data for benchmark execution';

-- =====================================================================
-- Table: benchmark_executions
-- Description: Detailed records of benchmark test executions
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.benchmark_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES analytics.benchmark_suites(id),
    benchmark_id UUID NOT NULL REFERENCES analytics.benchmark_definitions(id),
    agent_id UUID NOT NULL,
    agent_version VARCHAR(50),
    workspace_id UUID NOT NULL,

    -- Execution context
    execution_environment JSONB,
    model_configuration JSONB,
    run_number INTEGER DEFAULT 1,

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    total_duration_ms INTEGER,

    -- Core performance metrics (0-100 scale)
    accuracy_score NUMERIC(5,2) CHECK (accuracy_score BETWEEN 0 AND 100),
    speed_score NUMERIC(5,2) CHECK (speed_score BETWEEN 0 AND 100),
    efficiency_score NUMERIC(5,2) CHECK (efficiency_score BETWEEN 0 AND 100),
    cost_score NUMERIC(5,2) CHECK (cost_score BETWEEN 0 AND 100),
    reliability_score NUMERIC(5,2) CHECK (reliability_score BETWEEN 0 AND 100),
    overall_score NUMERIC(5,2) CHECK (overall_score BETWEEN 0 AND 100),

    -- Detailed metrics
    tokens_used INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    memory_peak_mb NUMERIC(10,2),
    cpu_usage_percent NUMERIC(5,2),

    -- Quality metrics
    output_correctness NUMERIC(5,2) CHECK (output_correctness BETWEEN 0 AND 100),
    output_completeness NUMERIC(5,2) CHECK (output_completeness BETWEEN 0 AND 100),
    output_relevance NUMERIC(5,2) CHECK (output_relevance BETWEEN 0 AND 100),

    -- Comparative metrics
    percentile_rank NUMERIC(5,2) CHECK (percentile_rank BETWEEN 0 AND 100),
    deviation_from_baseline NUMERIC(10,2),

    -- Results
    actual_output JSONB,
    validation_results JSONB,
    detailed_metrics JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled')
    ),
    error_details TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Benchmark Executions Indexes
CREATE INDEX idx_benchmark_exec_agent ON analytics.benchmark_executions(agent_id, created_at DESC);
CREATE INDEX idx_benchmark_exec_suite ON analytics.benchmark_executions(suite_id, benchmark_id);
CREATE INDEX idx_benchmark_exec_workspace ON analytics.benchmark_executions(workspace_id, created_at DESC);
CREATE INDEX idx_benchmark_exec_scores ON analytics.benchmark_executions(overall_score DESC, accuracy_score DESC);
CREATE INDEX idx_benchmark_exec_status ON analytics.benchmark_executions(status, start_time DESC);
CREATE INDEX idx_benchmark_exec_time_brin ON analytics.benchmark_executions USING brin(start_time);

-- Comments
COMMENT ON TABLE analytics.benchmark_executions IS 'Detailed records of benchmark test executions with performance metrics';
COMMENT ON COLUMN analytics.benchmark_executions.execution_environment IS 'Hardware specs, runtime config, environment variables';
COMMENT ON COLUMN analytics.benchmark_executions.detailed_metrics IS 'Granular metrics specific to the benchmark type';

-- =====================================================================
-- Table: benchmark_comparisons
-- Description: Store results of agent-to-agent comparisons
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.benchmark_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES analytics.benchmark_suites(id),
    workspace_id UUID NOT NULL,

    -- Agents being compared
    agent_ids UUID[] NOT NULL,
    agent_count INTEGER NOT NULL,

    -- Comparison type
    comparison_type VARCHAR(50) NOT NULL CHECK (
        comparison_type IN ('head_to_head', 'multi_agent', 'time_series', 'regression')
    ),

    -- Comparison results
    overall_winner UUID,
    category_winners JSONB,
    detailed_metrics JSONB NOT NULL,
    statistical_significance JSONB,

    -- Recommendations
    recommendations JSONB,
    insights JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Benchmark Comparisons Indexes
CREATE INDEX idx_benchmark_comparisons_suite ON analytics.benchmark_comparisons(suite_id, created_at DESC);
CREATE INDEX idx_benchmark_comparisons_workspace ON analytics.benchmark_comparisons(workspace_id, created_at DESC);
CREATE INDEX idx_benchmark_comparisons_agents ON analytics.benchmark_comparisons USING gin(agent_ids);

-- Comments
COMMENT ON TABLE analytics.benchmark_comparisons IS 'Store results of agent-to-agent benchmark comparisons';
COMMENT ON COLUMN analytics.benchmark_comparisons.statistical_significance IS 'P-values and confidence intervals for metric differences';

-- =====================================================================
-- Table: benchmark_regressions
-- Description: Track performance regressions detected across versions
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.benchmark_regressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    benchmark_id UUID NOT NULL REFERENCES analytics.benchmark_definitions(id),

    -- Version information
    baseline_version VARCHAR(50),
    current_version VARCHAR(50),
    baseline_execution_id UUID REFERENCES analytics.benchmark_executions(id),
    current_execution_id UUID REFERENCES analytics.benchmark_executions(id),

    -- Regression details
    metric_name VARCHAR(100) NOT NULL,
    baseline_value NUMERIC(10,2),
    current_value NUMERIC(10,2),
    regression_percentage NUMERIC(10,2),

    -- Classification
    severity VARCHAR(20) NOT NULL CHECK (
        severity IN ('minor', 'moderate', 'major', 'critical')
    ),
    regression_type VARCHAR(50) CHECK (
        regression_type IN ('performance', 'accuracy', 'cost', 'reliability', 'pattern')
    ),

    -- Impact analysis
    impact_analysis JSONB,
    affected_users_estimate INTEGER,
    business_impact VARCHAR(20) CHECK (business_impact IN ('low', 'medium', 'high', 'critical')),

    -- Status
    status VARCHAR(20) DEFAULT 'detected' CHECK (
        status IN ('detected', 'investigating', 'confirmed', 'resolved', 'false_positive')
    ),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    detected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Benchmark Regressions Indexes
CREATE INDEX idx_benchmark_regressions_agent ON analytics.benchmark_regressions(agent_id, detected_at DESC);
CREATE INDEX idx_benchmark_regressions_status ON analytics.benchmark_regressions(status, severity, detected_at DESC);
CREATE INDEX idx_benchmark_regressions_benchmark ON analytics.benchmark_regressions(benchmark_id, detected_at DESC);

-- Comments
COMMENT ON TABLE analytics.benchmark_regressions IS 'Track performance regressions detected across agent versions';
COMMENT ON COLUMN analytics.benchmark_regressions.impact_analysis IS 'Detailed analysis of regression impact on users and business';

-- =====================================================================
-- Table: stress_test_results
-- Description: Results from stress testing and load testing
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.stress_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Test configuration
    test_scenario VARCHAR(100) NOT NULL CHECK (
        test_scenario IN ('high_load', 'sustained_load', 'spike_load', 'memory_pressure',
                          'concurrent_requests', 'large_inputs', 'rate_limiting', 'failure_recovery')
    ),
    test_parameters JSONB NOT NULL,

    -- Test execution
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Results
    max_throughput_rps NUMERIC(10,2),
    avg_response_time_ms NUMERIC(10,2),
    p95_response_time_ms NUMERIC(10,2),
    p99_response_time_ms NUMERIC(10,2),
    error_rate_percent NUMERIC(5,2),

    -- Breaking points
    broke BOOLEAN DEFAULT FALSE,
    breaking_point_description TEXT,
    max_concurrent_requests INTEGER,
    max_memory_mb NUMERIC(10,2),

    -- Resource usage at peak
    peak_cpu_percent NUMERIC(5,2),
    peak_memory_mb NUMERIC(10,2),
    peak_io_operations INTEGER,

    -- Resilience metrics
    recovery_time_seconds NUMERIC(10,2),
    failure_count INTEGER DEFAULT 0,
    auto_recovery_success BOOLEAN,

    -- Overall assessment
    resilience_score NUMERIC(5,2) CHECK (resilience_score BETWEEN 0 AND 100),
    scaling_limit_description TEXT,
    recommendations JSONB,

    status VARCHAR(20) DEFAULT 'completed' CHECK (
        status IN ('running', 'completed', 'failed', 'aborted')
    ),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stress Test Results Indexes
CREATE INDEX idx_stress_test_agent ON analytics.stress_test_results(agent_id, created_at DESC);
CREATE INDEX idx_stress_test_scenario ON analytics.stress_test_results(test_scenario, created_at DESC);
CREATE INDEX idx_stress_test_workspace ON analytics.stress_test_results(workspace_id, created_at DESC);

-- Comments
COMMENT ON TABLE analytics.stress_test_results IS 'Results from stress testing and load testing scenarios';
COMMENT ON COLUMN analytics.stress_test_results.test_parameters IS 'Concurrent requests, duration, request rate, etc.';

-- =====================================================================
-- Table: cost_performance_analysis
-- Description: Cost efficiency analysis for agents
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.cost_performance_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    analysis_date DATE NOT NULL,

    -- Cost metrics
    total_cost_usd NUMERIC(15,4) DEFAULT 0,
    cost_per_task NUMERIC(10,4),
    cost_per_success NUMERIC(10,4),

    -- Performance metrics
    avg_performance_score NUMERIC(5,2),
    performance_per_dollar NUMERIC(10,4),

    -- Efficiency analysis
    token_efficiency NUMERIC(5,2),
    resource_efficiency NUMERIC(5,2),
    time_efficiency NUMERIC(5,2),
    overall_efficiency NUMERIC(5,2),

    -- Optimal configurations
    optimal_configurations JSONB,
    current_configuration JSONB,
    estimated_savings_usd NUMERIC(10,4),

    -- Optimization opportunities
    optimization_opportunities JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_agent_analysis_date UNIQUE(agent_id, analysis_date)
);

-- Cost Performance Analysis Indexes
CREATE INDEX idx_cost_perf_agent_date ON analytics.cost_performance_analysis(agent_id, analysis_date DESC);
CREATE INDEX idx_cost_perf_workspace ON analytics.cost_performance_analysis(workspace_id, analysis_date DESC);
CREATE INDEX idx_cost_perf_efficiency ON analytics.cost_performance_analysis(overall_efficiency DESC, analysis_date DESC);

-- Comments
COMMENT ON TABLE analytics.cost_performance_analysis IS 'Cost efficiency and performance-per-dollar analysis for agents';
COMMENT ON COLUMN analytics.cost_performance_analysis.performance_per_dollar IS 'Performance score divided by cost';

-- =====================================================================
-- Materialized View: benchmark_leaderboard
-- Description: Dynamic leaderboard showing agent rankings across benchmarks
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.benchmark_leaderboard AS
WITH latest_benchmarks AS (
    SELECT
        agent_id,
        benchmark_id,
        suite_id,
        workspace_id,
        accuracy_score,
        speed_score,
        efficiency_score,
        cost_score,
        reliability_score,
        overall_score,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY agent_id, benchmark_id ORDER BY created_at DESC) as rn
    FROM analytics.benchmark_executions
    WHERE status = 'completed'
        AND created_at > NOW() - INTERVAL '30 days'
),
benchmark_aggregates AS (
    SELECT
        lb.agent_id,
        lb.workspace_id,
        bs.category as benchmark_category,
        AVG(lb.accuracy_score) as avg_accuracy,
        AVG(lb.speed_score) as avg_speed,
        AVG(lb.efficiency_score) as avg_efficiency,
        AVG(lb.cost_score) as avg_cost,
        AVG(lb.reliability_score) as avg_reliability,
        AVG(lb.overall_score) as avg_overall,
        COUNT(DISTINCT lb.benchmark_id) as benchmarks_completed,
        MAX(lb.created_at) as last_benchmark_date
    FROM latest_benchmarks lb
    JOIN analytics.benchmark_suites bs ON lb.suite_id = bs.id
    WHERE lb.rn = 1
    GROUP BY lb.agent_id, lb.workspace_id, bs.category
),
category_rankings AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_accuracy DESC) as accuracy_rank,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_speed DESC) as speed_rank,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_efficiency DESC) as efficiency_rank,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_cost DESC) as cost_rank,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_reliability DESC) as reliability_rank,
        RANK() OVER (PARTITION BY benchmark_category ORDER BY avg_overall DESC) as overall_rank
    FROM benchmark_aggregates
)
SELECT
    agent_id,
    workspace_id,
    benchmark_category,
    ROUND(avg_accuracy, 2) as avg_accuracy,
    ROUND(avg_speed, 2) as avg_speed,
    ROUND(avg_efficiency, 2) as avg_efficiency,
    ROUND(avg_cost, 2) as avg_cost,
    ROUND(avg_reliability, 2) as avg_reliability,
    ROUND(avg_overall, 2) as avg_overall,
    accuracy_rank,
    speed_rank,
    efficiency_rank,
    cost_rank,
    reliability_rank,
    overall_rank,
    benchmarks_completed,
    last_benchmark_date,
    LEAST(accuracy_rank, speed_rank, efficiency_rank, cost_rank, reliability_rank) as best_ranking
FROM category_rankings;

-- Index on materialized view
CREATE INDEX idx_benchmark_leaderboard_category
    ON analytics.benchmark_leaderboard(benchmark_category, overall_rank);
CREATE INDEX idx_benchmark_leaderboard_agent
    ON analytics.benchmark_leaderboard(agent_id, benchmark_category);
CREATE INDEX idx_benchmark_leaderboard_workspace
    ON analytics.benchmark_leaderboard(workspace_id, overall_rank);
CREATE INDEX idx_benchmark_leaderboard_overall
    ON analytics.benchmark_leaderboard(overall_rank, avg_overall DESC);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.benchmark_leaderboard IS 'Dynamic leaderboard showing agent rankings across benchmark categories (30-day window)';

-- =====================================================================
-- Materialized View: agent_comparison_matrix
-- Description: Pre-computed agent comparison matrix for fast lookups
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.agent_comparison_matrix AS
WITH latest_benchmarks AS (
    SELECT
        agent_id,
        benchmark_id,
        accuracy_score,
        speed_score,
        efficiency_score,
        cost_score,
        reliability_score,
        overall_score,
        ROW_NUMBER() OVER (PARTITION BY agent_id, benchmark_id ORDER BY created_at DESC) as rn
    FROM analytics.benchmark_executions
    WHERE status = 'completed'
),
benchmark_aggregates AS (
    SELECT
        agent_id,
        AVG(accuracy_score) as avg_accuracy,
        AVG(speed_score) as avg_speed,
        AVG(efficiency_score) as avg_efficiency,
        AVG(cost_score) as avg_cost,
        AVG(reliability_score) as avg_reliability,
        AVG(overall_score) as avg_overall,
        COUNT(DISTINCT benchmark_id) as benchmarks_completed,
        STDDEV(accuracy_score) as stddev_accuracy,
        STDDEV(speed_score) as stddev_speed
    FROM latest_benchmarks
    WHERE rn = 1
    GROUP BY agent_id
),
rankings AS (
    SELECT
        agent_id,
        avg_accuracy,
        avg_speed,
        avg_efficiency,
        avg_cost,
        avg_reliability,
        avg_overall,
        benchmarks_completed,
        RANK() OVER (ORDER BY avg_accuracy DESC) as accuracy_rank,
        RANK() OVER (ORDER BY avg_speed DESC) as speed_rank,
        RANK() OVER (ORDER BY avg_efficiency DESC) as efficiency_rank,
        RANK() OVER (ORDER BY avg_cost DESC) as cost_rank,
        RANK() OVER (ORDER BY avg_reliability DESC) as reliability_rank,
        RANK() OVER (ORDER BY avg_overall DESC) as overall_rank,
        -- Composite score with weighted metrics
        (avg_accuracy * 0.3 + avg_speed * 0.2 + avg_efficiency * 0.2 +
         avg_cost * 0.15 + avg_reliability * 0.15) as composite_score
    FROM benchmark_aggregates
)
SELECT
    agent_id,
    ROUND(avg_accuracy, 2) as avg_accuracy,
    ROUND(avg_speed, 2) as avg_speed,
    ROUND(avg_efficiency, 2) as avg_efficiency,
    ROUND(avg_cost, 2) as avg_cost,
    ROUND(avg_reliability, 2) as avg_reliability,
    ROUND(avg_overall, 2) as avg_overall,
    ROUND(composite_score, 2) as composite_score,
    accuracy_rank,
    speed_rank,
    efficiency_rank,
    cost_rank,
    reliability_rank,
    overall_rank,
    benchmarks_completed
FROM rankings
ORDER BY composite_score DESC;

-- Index on materialized view
CREATE UNIQUE INDEX idx_agent_comparison_matrix_agent
    ON analytics.agent_comparison_matrix(agent_id);
CREATE INDEX idx_agent_comparison_matrix_composite
    ON analytics.agent_comparison_matrix(composite_score DESC);
CREATE INDEX idx_agent_comparison_matrix_overall
    ON analytics.agent_comparison_matrix(overall_rank);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.agent_comparison_matrix IS 'Pre-computed agent comparison matrix with rankings and composite scores';

-- =====================================================================
-- Refresh Functions
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_benchmark_leaderboard()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.benchmark_leaderboard;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analytics.refresh_agent_comparison_matrix()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.agent_comparison_matrix;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_benchmark_leaderboard() IS 'Refresh benchmark leaderboard materialized view';
COMMENT ON FUNCTION analytics.refresh_agent_comparison_matrix() IS 'Refresh agent comparison matrix materialized view';

-- =====================================================================
-- Helper Functions
-- =====================================================================

-- Function to calculate percentile rank for a benchmark execution
CREATE OR REPLACE FUNCTION analytics.calculate_percentile_rank(
    p_benchmark_id UUID,
    p_score NUMERIC
)
RETURNS NUMERIC AS $$
DECLARE
    v_rank NUMERIC;
BEGIN
    SELECT PERCENT_RANK() OVER (ORDER BY overall_score)
    INTO v_rank
    FROM (
        SELECT overall_score
        FROM analytics.benchmark_executions
        WHERE benchmark_id = p_benchmark_id
            AND status = 'completed'
            AND overall_score IS NOT NULL
        UNION ALL
        SELECT p_score
    ) scores
    WHERE overall_score = p_score;

    RETURN ROUND(v_rank * 100, 2);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.calculate_percentile_rank IS 'Calculate percentile rank for a benchmark execution score';

-- Function to detect regressions for an agent
CREATE OR REPLACE FUNCTION analytics.detect_agent_regressions(
    p_agent_id UUID,
    p_current_version VARCHAR(50),
    p_baseline_version VARCHAR(50) DEFAULT NULL,
    p_threshold NUMERIC DEFAULT 10.0
)
RETURNS TABLE (
    benchmark_id UUID,
    metric_name VARCHAR(100),
    baseline_value NUMERIC,
    current_value NUMERIC,
    regression_percentage NUMERIC,
    severity VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    WITH baseline_scores AS (
        SELECT
            be.benchmark_id,
            be.accuracy_score,
            be.speed_score,
            be.efficiency_score,
            be.cost_score,
            be.reliability_score
        FROM analytics.benchmark_executions be
        WHERE be.agent_id = p_agent_id
            AND (p_baseline_version IS NULL OR be.agent_version = p_baseline_version)
            AND be.status = 'completed'
        ORDER BY be.created_at DESC
        LIMIT 1
    ),
    current_scores AS (
        SELECT
            be.benchmark_id,
            be.accuracy_score,
            be.speed_score,
            be.efficiency_score,
            be.cost_score,
            be.reliability_score
        FROM analytics.benchmark_executions be
        WHERE be.agent_id = p_agent_id
            AND be.agent_version = p_current_version
            AND be.status = 'completed'
        ORDER BY be.created_at DESC
        LIMIT 1
    )
    SELECT
        bs.benchmark_id,
        metric::VARCHAR(100) as metric_name,
        baseline_val as baseline_value,
        current_val as current_value,
        ROUND(((baseline_val - current_val) / NULLIF(baseline_val, 0)) * 100, 2) as regression_percentage,
        CASE
            WHEN ABS(((baseline_val - current_val) / NULLIF(baseline_val, 0)) * 100) > 30 THEN 'critical'::VARCHAR(20)
            WHEN ABS(((baseline_val - current_val) / NULLIF(baseline_val, 0)) * 100) > 20 THEN 'major'::VARCHAR(20)
            WHEN ABS(((baseline_val - current_val) / NULLIF(baseline_val, 0)) * 100) > 10 THEN 'moderate'::VARCHAR(20)
            ELSE 'minor'::VARCHAR(20)
        END as severity
    FROM baseline_scores bs
    CROSS JOIN LATERAL (
        VALUES
            ('accuracy', bs.accuracy_score, (SELECT accuracy_score FROM current_scores WHERE benchmark_id = bs.benchmark_id)),
            ('speed', bs.speed_score, (SELECT speed_score FROM current_scores WHERE benchmark_id = bs.benchmark_id)),
            ('efficiency', bs.efficiency_score, (SELECT efficiency_score FROM current_scores WHERE benchmark_id = bs.benchmark_id)),
            ('cost', bs.cost_score, (SELECT cost_score FROM current_scores WHERE benchmark_id = bs.benchmark_id)),
            ('reliability', bs.reliability_score, (SELECT reliability_score FROM current_scores WHERE benchmark_id = bs.benchmark_id))
    ) AS metrics(metric, baseline_val, current_val)
    WHERE ((baseline_val - current_val) / NULLIF(baseline_val, 0)) * 100 > p_threshold;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.detect_agent_regressions IS 'Detect performance regressions for an agent between versions';

-- =====================================================================
-- Sample Data Generation (for development/testing)
-- =====================================================================

-- Function to create sample benchmark suite
CREATE OR REPLACE FUNCTION analytics.create_sample_benchmark_suite()
RETURNS UUID AS $$
DECLARE
    v_suite_id UUID;
    v_benchmark_id UUID;
BEGIN
    -- Create sample suite
    INSERT INTO analytics.benchmark_suites (
        suite_name,
        category,
        description,
        version,
        suite_config
    ) VALUES (
        'Comprehensive Performance Suite',
        'comprehensive',
        'Complete suite testing accuracy, speed, cost, reliability, and scalability',
        '1.0.0',
        '{"weights": {"accuracy": 0.3, "speed": 0.2, "efficiency": 0.2, "cost": 0.15, "reliability": 0.15}}'::JSONB
    ) RETURNING id INTO v_suite_id;

    -- Create sample benchmarks
    INSERT INTO analytics.benchmark_definitions (
        suite_id,
        benchmark_name,
        description,
        test_type,
        dataset_complexity,
        time_limit_ms,
        scoring_rubric
    ) VALUES
    (
        v_suite_id,
        'Response Speed Test',
        'Measure agent response time under normal conditions',
        'synthetic',
        'medium',
        30000,
        '{"accuracy_weight": 0.2, "speed_weight": 0.8}'::JSONB
    ),
    (
        v_suite_id,
        'Accuracy Benchmark',
        'Test output accuracy against known correct answers',
        'real_world',
        'high',
        60000,
        '{"accuracy_weight": 0.9, "completeness_weight": 0.1}'::JSONB
    ),
    (
        v_suite_id,
        'Cost Efficiency Test',
        'Evaluate cost per task completion',
        'synthetic',
        'low',
        20000,
        '{"cost_weight": 0.7, "speed_weight": 0.3}'::JSONB
    );

    RAISE NOTICE 'Created sample benchmark suite with ID: %', v_suite_id;
    RETURN v_suite_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.create_sample_benchmark_suite IS 'Create sample benchmark suite with test definitions';
