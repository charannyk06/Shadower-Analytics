-- Migration: Create Resource Utilization Materialized Views
-- Description: Aggregated views for fast resource analytics queries
-- Author: Claude Agent
-- Date: 2025-11-13

-- ============================================================================
-- 1. Daily Resource Utilization Summary
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_resource_utilization AS
SELECT
    workspace_id,
    agent_id,
    DATE(created_at) as usage_date,

    -- Execution counts
    COUNT(DISTINCT execution_id) as execution_count,

    -- Compute metrics
    SUM(cpu_seconds) as total_cpu_seconds,
    AVG(cpu_average_percent) as avg_cpu_percent,
    MAX(cpu_peak_percent) as max_cpu_percent,
    SUM(memory_mb_seconds) as total_memory_mb_seconds,
    AVG(memory_average_mb) as avg_memory_mb,
    MAX(memory_peak_mb) as max_memory_mb,
    SUM(COALESCE(gpu_compute_units, 0)) as total_gpu_units,

    -- Token metrics
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    AVG(context_window_used) as avg_context_window_used,
    SUM(prompt_cache_hits) as total_cache_hits,

    -- API metrics
    SUM(external_api_calls) as total_api_calls,
    SUM(api_rate_limit_hits) as total_rate_limit_hits,
    SUM(api_error_count) as total_api_errors,

    -- Network metrics
    SUM(network_bytes_sent) as total_bytes_sent,
    SUM(network_bytes_received) as total_bytes_received,

    -- Storage metrics
    AVG(temp_storage_mb) as avg_temp_storage_mb,
    AVG(persistent_storage_mb) as avg_persistent_storage_mb,
    AVG(cache_size_mb) as avg_cache_size_mb,
    SUM(database_operations) as total_db_operations,

    -- Cost metrics
    SUM(compute_cost_usd) as total_compute_cost,
    SUM(token_cost_usd) as total_token_cost,
    SUM(api_cost_usd) as total_api_cost,
    SUM(storage_cost_usd) as total_storage_cost,
    SUM(network_cost_usd) as total_network_cost,
    SUM(total_cost_usd) as total_cost,

    -- Performance metrics
    AVG(execution_duration_ms) as avg_execution_duration_ms,
    AVG(queue_wait_time_ms) as avg_queue_wait_ms,

    -- Efficiency metrics
    CASE WHEN SUM(total_cost_usd) > 0
        THEN SUM(total_tokens)::DECIMAL / SUM(total_cost_usd)
        ELSE 0
    END as tokens_per_dollar,
    CASE WHEN SUM(total_cost_usd) > 0
        THEN COUNT(DISTINCT execution_id)::DECIMAL / SUM(total_cost_usd)
        ELSE 0
    END as executions_per_dollar

FROM analytics.resource_utilization_metrics
GROUP BY workspace_id, agent_id, DATE(created_at);

-- Indexes for daily summary
CREATE UNIQUE INDEX idx_daily_resource_unique ON analytics.daily_resource_utilization
    (workspace_id, agent_id, usage_date);
CREATE INDEX idx_daily_resource_date ON analytics.daily_resource_utilization
    USING BRIN (usage_date);
CREATE INDEX idx_daily_resource_cost ON analytics.daily_resource_utilization (total_cost DESC);

-- ============================================================================
-- 2. Token Budget Tracking View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.token_budget_tracking AS
WITH daily_usage AS (
    SELECT
        workspace_id,
        agent_id,
        DATE(created_at) as usage_date,
        SUM(total_tokens) as daily_tokens,
        SUM(token_cost_usd) as daily_token_cost,
        COUNT(DISTINCT execution_id) as execution_count
    FROM analytics.resource_utilization_metrics
    GROUP BY workspace_id, agent_id, DATE(created_at)
),
budget_allocation AS (
    SELECT
        workspace_id,
        agent_id,
        daily_token_budget,
        weekly_token_budget,
        monthly_token_budget,
        daily_cost_budget_usd,
        weekly_cost_budget_usd,
        monthly_cost_budget_usd,
        warning_threshold_percent,
        critical_threshold_percent
    FROM analytics.token_budgets
    WHERE is_active = true
    AND budget_type = 'daily'
)
SELECT
    du.workspace_id,
    du.agent_id,
    du.usage_date,
    du.daily_tokens,
    du.daily_token_cost,
    du.execution_count,

    -- Budget info
    ba.daily_token_budget,
    ba.monthly_token_budget,
    ba.daily_cost_budget_usd,
    ba.warning_threshold_percent,
    ba.critical_threshold_percent,

    -- Budget usage percentages
    CASE
        WHEN ba.daily_token_budget > 0
        THEN (du.daily_tokens::DECIMAL / ba.daily_token_budget) * 100
        ELSE 0
    END as daily_budget_usage_pct,

    CASE
        WHEN ba.daily_cost_budget_usd > 0
        THEN (du.daily_token_cost::DECIMAL / ba.daily_cost_budget_usd) * 100
        ELSE 0
    END as daily_cost_budget_usage_pct,

    -- Rolling windows
    SUM(du.daily_tokens) OVER (
        PARTITION BY du.workspace_id, du.agent_id
        ORDER BY du.usage_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as rolling_7d_tokens,

    SUM(du.daily_tokens) OVER (
        PARTITION BY du.workspace_id, du.agent_id
        ORDER BY du.usage_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as rolling_30d_tokens,

    SUM(du.daily_token_cost) OVER (
        PARTITION BY du.workspace_id, du.agent_id
        ORDER BY du.usage_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as rolling_30d_cost,

    -- Budget status
    CASE
        WHEN ba.daily_token_budget IS NULL THEN 'no_budget'
        WHEN du.daily_tokens > ba.daily_token_budget THEN 'over_budget'
        WHEN du.daily_tokens > ba.daily_token_budget * (ba.critical_threshold_percent::DECIMAL / 100) THEN 'critical'
        WHEN du.daily_tokens > ba.daily_token_budget * (ba.warning_threshold_percent::DECIMAL / 100) THEN 'warning'
        ELSE 'within_budget'
    END as budget_status

FROM daily_usage du
LEFT JOIN budget_allocation ba ON du.workspace_id = ba.workspace_id
    AND (du.agent_id = ba.agent_id OR ba.agent_id IS NULL);

-- Indexes for token budget tracking
CREATE UNIQUE INDEX idx_token_budget_tracking_unique ON analytics.token_budget_tracking
    (workspace_id, agent_id, usage_date);
CREATE INDEX idx_token_budget_tracking_status ON analytics.token_budget_tracking (budget_status)
    WHERE budget_status IN ('over_budget', 'critical', 'warning');

-- ============================================================================
-- 3. Infrastructure Cost Allocation View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.infrastructure_cost_allocation AS
WITH resource_costs AS (
    SELECT
        workspace_id,
        agent_id,
        DATE_TRUNC('day', created_at) as cost_date,

        -- Compute costs (based on standard cloud pricing)
        SUM(cpu_seconds * 0.0000166) as cpu_cost, -- $0.06/hour
        SUM(memory_mb_seconds * 0.0000000046) as memory_cost, -- $0.004/GB-hour
        SUM(COALESCE(gpu_compute_units, 0) * 0.0001) as gpu_cost,

        -- Storage costs
        SUM(storage_cost_usd) as storage_cost,

        -- Network costs (estimated at $0.01/GB)
        SUM((network_bytes_sent + network_bytes_received) * 0.00000001) as network_cost,

        -- API and token costs (from actual metrics)
        SUM(token_cost_usd) as token_cost,
        SUM(api_cost_usd) as api_cost,

        -- Execution metrics
        COUNT(DISTINCT execution_id) as execution_count,
        AVG(execution_duration_ms) as avg_duration_ms

    FROM analytics.resource_utilization_metrics
    GROUP BY workspace_id, agent_id, DATE_TRUNC('day', created_at)
)
SELECT
    workspace_id,
    agent_id,
    cost_date::DATE as cost_date,

    -- Cost breakdown
    cpu_cost,
    memory_cost,
    gpu_cost,
    storage_cost,
    network_cost,
    token_cost,
    api_cost,

    -- Total daily cost
    (cpu_cost + memory_cost + gpu_cost + storage_cost +
     network_cost + token_cost + api_cost) as total_daily_cost,

    -- Execution metrics
    execution_count,
    avg_duration_ms,

    -- Cost per execution
    CASE
        WHEN execution_count > 0
        THEN (cpu_cost + memory_cost + gpu_cost + storage_cost +
              network_cost + token_cost + api_cost) / execution_count
        ELSE 0
    END as cost_per_execution,

    -- Rolling costs
    SUM(cpu_cost + memory_cost + gpu_cost + storage_cost +
        network_cost + token_cost + api_cost) OVER (
        PARTITION BY workspace_id, agent_id
        ORDER BY cost_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as rolling_7d_cost,

    SUM(cpu_cost + memory_cost + gpu_cost + storage_cost +
        network_cost + token_cost + api_cost) OVER (
        PARTITION BY workspace_id, agent_id
        ORDER BY cost_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as rolling_30d_cost,

    -- Cost distribution percentages
    CASE
        WHEN (cpu_cost + memory_cost + gpu_cost + storage_cost +
              network_cost + token_cost + api_cost) > 0
        THEN (token_cost / (cpu_cost + memory_cost + gpu_cost + storage_cost +
                           network_cost + token_cost + api_cost)) * 100
        ELSE 0
    END as token_cost_percent,

    CASE
        WHEN (cpu_cost + memory_cost + gpu_cost + storage_cost +
              network_cost + token_cost + api_cost) > 0
        THEN ((cpu_cost + memory_cost + gpu_cost) /
              (cpu_cost + memory_cost + gpu_cost + storage_cost +
               network_cost + token_cost + api_cost)) * 100
        ELSE 0
    END as compute_cost_percent

FROM resource_costs;

-- Indexes for cost allocation
CREATE UNIQUE INDEX idx_cost_allocation_unique ON analytics.infrastructure_cost_allocation
    (workspace_id, agent_id, cost_date);
CREATE INDEX idx_cost_allocation_date ON analytics.infrastructure_cost_allocation
    USING BRIN (cost_date);
CREATE INDEX idx_cost_allocation_total ON analytics.infrastructure_cost_allocation (total_daily_cost DESC);

-- ============================================================================
-- 4. API Usage Summary View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.api_usage_summary AS
SELECT
    workspace_id,
    agent_id,
    api_endpoint,
    api_provider,
    DATE_TRUNC('day', period_start) as usage_date,

    -- Call statistics
    SUM(total_calls) as total_calls,
    SUM(successful_calls) as successful_calls,
    SUM(failed_calls) as failed_calls,
    SUM(rate_limited_calls) as rate_limited_calls,

    -- Error rate
    CASE
        WHEN SUM(total_calls) > 0
        THEN (SUM(failed_calls)::DECIMAL / SUM(total_calls)) * 100
        ELSE 0
    END as error_rate_percent,

    -- Latency metrics
    AVG(avg_latency_ms) as avg_latency_ms,
    AVG(p95_latency_ms) as p95_latency_ms,
    AVG(p99_latency_ms) as p99_latency_ms,

    -- Cost metrics
    SUM(total_cost_usd) as total_cost,
    AVG(cost_per_call) as avg_cost_per_call,
    SUM(wasted_cost_failed_calls) as wasted_cost,

    -- Rate limiting
    SUM(throttle_incidents) as throttle_incidents

FROM analytics.api_usage_metrics
GROUP BY workspace_id, agent_id, api_endpoint, api_provider, DATE_TRUNC('day', period_start);

-- Indexes for API usage summary
CREATE UNIQUE INDEX idx_api_usage_summary_unique ON analytics.api_usage_summary
    (workspace_id, agent_id, api_endpoint, usage_date);
CREATE INDEX idx_api_usage_summary_date ON analytics.api_usage_summary
    USING BRIN (usage_date);
CREATE INDEX idx_api_usage_summary_error_rate ON analytics.api_usage_summary (error_rate_percent DESC);

-- ============================================================================
-- 5. Resource Waste Summary View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.resource_waste_summary AS
SELECT
    workspace_id,
    agent_id,
    waste_type,
    waste_category,
    DATE(detected_at) as detection_date,

    -- Waste quantification
    COUNT(*) as waste_event_count,
    SUM(waste_cost_usd) as total_waste_cost,
    AVG(waste_cost_usd) as avg_waste_cost_per_event,
    MAX(waste_cost_usd) as max_waste_cost,

    -- Resolution tracking
    COUNT(*) FILTER (WHERE is_resolved = true) as resolved_count,
    COUNT(*) FILTER (WHERE is_resolved = false) as unresolved_count,

    -- Confidence
    AVG(confidence_score) as avg_confidence_score

FROM analytics.resource_waste_events
GROUP BY workspace_id, agent_id, waste_type, waste_category, DATE(detected_at);

-- Indexes for waste summary
CREATE UNIQUE INDEX idx_waste_summary_unique ON analytics.resource_waste_summary
    (workspace_id, agent_id, waste_type, detection_date);
CREATE INDEX idx_waste_summary_date ON analytics.resource_waste_summary
    USING BRIN (detection_date);
CREATE INDEX idx_waste_summary_cost ON analytics.resource_waste_summary (total_waste_cost DESC);

-- ============================================================================
-- 6. Agent Efficiency Scorecard View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.agent_efficiency_scorecard AS
WITH recent_metrics AS (
    SELECT
        workspace_id,
        agent_id,
        SUM(total_tokens) as total_tokens,
        SUM(total_cost_usd) as total_cost,
        COUNT(DISTINCT execution_id) as total_executions,
        AVG(execution_duration_ms) as avg_duration_ms
    FROM analytics.resource_utilization_metrics
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workspace_id, agent_id
),
waste_metrics AS (
    SELECT
        workspace_id,
        agent_id,
        SUM(waste_cost_usd) as total_waste_cost
    FROM analytics.resource_waste_events
    WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
    AND is_resolved = false
    GROUP BY workspace_id, agent_id
)
SELECT
    rm.workspace_id,
    rm.agent_id,

    -- Efficiency metrics
    CASE WHEN rm.total_cost > 0
        THEN rm.total_tokens::DECIMAL / rm.total_cost
        ELSE 0
    END as tokens_per_dollar,

    CASE WHEN rm.total_cost > 0
        THEN rm.total_executions::DECIMAL / rm.total_cost
        ELSE 0
    END as executions_per_dollar,

    CASE WHEN rm.total_executions > 0
        THEN 1000000.0 / rm.avg_duration_ms
        ELSE 0
    END as throughput_score,

    -- Cost efficiency
    rm.total_cost as total_30d_cost,
    COALESCE(wm.total_waste_cost, 0) as total_30d_waste,
    CASE WHEN rm.total_cost > 0
        THEN (1 - COALESCE(wm.total_waste_cost, 0) / rm.total_cost) * 100
        ELSE 100
    END as cost_efficiency_percent,

    -- Overall efficiency score (0-100)
    (
        -- Tokens per dollar (normalized, weight: 30%)
        LEAST((CASE WHEN rm.total_cost > 0 THEN rm.total_tokens::DECIMAL / rm.total_cost ELSE 0 END) / 1000, 1) * 30 +
        -- Executions per dollar (normalized, weight: 30%)
        LEAST((CASE WHEN rm.total_cost > 0 THEN rm.total_executions::DECIMAL / rm.total_cost ELSE 0 END) / 10, 1) * 30 +
        -- Throughput (normalized, weight: 20%)
        LEAST((CASE WHEN rm.total_executions > 0 THEN 1000000.0 / rm.avg_duration_ms ELSE 0 END) / 100, 1) * 20 +
        -- Waste reduction (weight: 20%)
        (CASE WHEN rm.total_cost > 0 THEN (1 - COALESCE(wm.total_waste_cost, 0) / rm.total_cost) ELSE 1 END) * 20
    ) as overall_efficiency_score,

    -- Metadata
    rm.total_tokens,
    rm.total_executions,
    rm.avg_duration_ms

FROM recent_metrics rm
LEFT JOIN waste_metrics wm ON rm.workspace_id = wm.workspace_id AND rm.agent_id = wm.agent_id;

-- Indexes for efficiency scorecard
CREATE UNIQUE INDEX idx_efficiency_scorecard_unique ON analytics.agent_efficiency_scorecard
    (workspace_id, agent_id);
CREATE INDEX idx_efficiency_scorecard_score ON analytics.agent_efficiency_scorecard
    (overall_efficiency_score DESC);

-- ============================================================================
-- 7. Comments for documentation
-- ============================================================================
COMMENT ON MATERIALIZED VIEW analytics.daily_resource_utilization IS
    'Daily aggregated resource utilization metrics per agent';
COMMENT ON MATERIALIZED VIEW analytics.token_budget_tracking IS
    'Token budget tracking with alerts and rolling windows';
COMMENT ON MATERIALIZED VIEW analytics.infrastructure_cost_allocation IS
    'Detailed cost breakdown and allocation per agent';
COMMENT ON MATERIALIZED VIEW analytics.api_usage_summary IS
    'Aggregated API usage statistics per endpoint';
COMMENT ON MATERIALIZED VIEW analytics.resource_waste_summary IS
    'Summary of detected resource waste by type';
COMMENT ON MATERIALIZED VIEW analytics.agent_efficiency_scorecard IS
    'Comprehensive efficiency scoring for agents';

-- ============================================================================
-- 8. Refresh functions for materialized views
-- ============================================================================
CREATE OR REPLACE FUNCTION analytics.refresh_resource_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.daily_resource_utilization;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.token_budget_tracking;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.infrastructure_cost_allocation;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.api_usage_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.resource_waste_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.agent_efficiency_scorecard;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_resource_materialized_views IS
    'Refresh all resource analytics materialized views concurrently';
