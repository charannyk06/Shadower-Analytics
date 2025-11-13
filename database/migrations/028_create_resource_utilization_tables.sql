-- Migration: Create Resource Utilization Analytics Tables
-- Description: Comprehensive tracking of computational resources, API calls, token usage, and infrastructure costs
-- Author: Claude Agent
-- Date: 2025-11-13

-- ============================================================================
-- 1. Resource Utilization Metrics Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.resource_utilization_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Compute metrics
    cpu_seconds DECIMAL(10,2),
    cpu_average_percent DECIMAL(5,2),
    cpu_peak_percent DECIMAL(5,2),
    memory_mb_seconds DECIMAL(12,2),
    memory_average_mb DECIMAL(10,2),
    memory_peak_mb DECIMAL(10,2),
    memory_allocation_mb DECIMAL(10,2),
    gpu_compute_units DECIMAL(10,2),
    gpu_utilization_percent DECIMAL(5,2),
    gpu_memory_mb DECIMAL(10,2),

    -- Network metrics
    network_bytes_sent BIGINT DEFAULT 0,
    network_bytes_received BIGINT DEFAULT 0,
    network_api_calls INTEGER DEFAULT 0,

    -- Token metrics
    model_provider VARCHAR(50),
    model_name VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    embedding_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens + embedding_tokens) STORED,
    context_window_used INTEGER DEFAULT 0,
    prompt_cache_hits INTEGER DEFAULT 0,

    -- API metrics
    external_api_calls INTEGER DEFAULT 0,
    api_rate_limit_hits INTEGER DEFAULT 0,
    api_error_count INTEGER DEFAULT 0,

    -- Storage metrics
    temp_storage_mb DECIMAL(10,2) DEFAULT 0,
    persistent_storage_mb DECIMAL(10,2) DEFAULT 0,
    cache_size_mb DECIMAL(10,2) DEFAULT 0,
    database_operations INTEGER DEFAULT 0,

    -- Cost metrics (in USD)
    compute_cost_usd DECIMAL(10,6) DEFAULT 0,
    token_cost_usd DECIMAL(10,6) DEFAULT 0,
    api_cost_usd DECIMAL(10,6) DEFAULT 0,
    storage_cost_usd DECIMAL(10,6) DEFAULT 0,
    network_cost_usd DECIMAL(10,6) DEFAULT 0,
    total_cost_usd DECIMAL(10,6) GENERATED ALWAYS AS (
        compute_cost_usd + token_cost_usd + api_cost_usd + storage_cost_usd + network_cost_usd
    ) STORED,

    -- Time metrics
    execution_duration_ms INTEGER,
    queue_wait_time_ms INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for resource utilization metrics
CREATE INDEX idx_resource_util_agent_time ON analytics.resource_utilization_metrics
    USING BRIN (agent_id, created_at);
CREATE INDEX idx_resource_util_workspace_time ON analytics.resource_utilization_metrics
    USING BRIN (workspace_id, created_at);
CREATE INDEX idx_resource_util_execution ON analytics.resource_utilization_metrics (execution_id);
CREATE INDEX idx_resource_util_cost ON analytics.resource_utilization_metrics (total_cost_usd DESC);
CREATE INDEX idx_resource_util_tokens ON analytics.resource_utilization_metrics (total_tokens DESC);
CREATE INDEX idx_resource_util_created_at ON analytics.resource_utilization_metrics
    USING BRIN (created_at);

-- ============================================================================
-- 2. API Usage Tracking Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.api_usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    api_provider VARCHAR(100),

    -- Call statistics
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    rate_limited_calls INTEGER DEFAULT 0,
    timeout_calls INTEGER DEFAULT 0,

    -- Latency metrics (in milliseconds)
    avg_latency_ms DECIMAL(10,2),
    p50_latency_ms DECIMAL(10,2),
    p95_latency_ms DECIMAL(10,2),
    p99_latency_ms DECIMAL(10,2),
    min_latency_ms DECIMAL(10,2),
    max_latency_ms DECIMAL(10,2),

    -- Cost metrics
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    cost_per_call DECIMAL(10,6),
    wasted_cost_failed_calls DECIMAL(10,6) DEFAULT 0,

    -- Rate limiting info
    rate_limit_current INTEGER,
    rate_limit_max INTEGER,
    rate_limit_reset_time TIMESTAMP WITH TIME ZONE,
    throttle_incidents INTEGER DEFAULT 0,

    -- Error analysis
    error_types JSONB DEFAULT '{}'::jsonb,
    error_rate DECIMAL(5,4),
    retry_success_rate DECIMAL(5,4),

    -- Time period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for API usage metrics
CREATE INDEX idx_api_usage_agent_time ON analytics.api_usage_metrics
    USING BRIN (agent_id, period_start);
CREATE INDEX idx_api_usage_workspace_time ON analytics.api_usage_metrics
    USING BRIN (workspace_id, period_start);
CREATE INDEX idx_api_usage_endpoint ON analytics.api_usage_metrics (api_endpoint);
CREATE INDEX idx_api_usage_provider ON analytics.api_usage_metrics (api_provider);
CREATE INDEX idx_api_usage_error_rate ON analytics.api_usage_metrics (error_rate DESC);

-- ============================================================================
-- 3. Token Budget Management Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.token_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    agent_id UUID,

    -- Budget allocations
    daily_token_budget INTEGER,
    weekly_token_budget INTEGER,
    monthly_token_budget INTEGER,

    -- Cost budgets
    daily_cost_budget_usd DECIMAL(10,2),
    weekly_cost_budget_usd DECIMAL(10,2),
    monthly_cost_budget_usd DECIMAL(10,2),

    -- Alert thresholds (percentages)
    warning_threshold_percent INTEGER DEFAULT 80,
    critical_threshold_percent INTEGER DEFAULT 90,

    -- Budget period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    budget_type VARCHAR(20) NOT NULL CHECK (budget_type IN ('daily', 'weekly', 'monthly')),

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(workspace_id, agent_id, budget_type, period_start)
);

-- Indexes for token budgets
CREATE INDEX idx_token_budgets_workspace ON analytics.token_budgets (workspace_id);
CREATE INDEX idx_token_budgets_agent ON analytics.token_budgets (agent_id);
CREATE INDEX idx_token_budgets_period ON analytics.token_budgets (period_start, period_end);
CREATE INDEX idx_token_budgets_active ON analytics.token_budgets (is_active) WHERE is_active = true;

-- ============================================================================
-- 4. Resource Optimization Recommendations Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.resource_optimization_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Recommendation details
    optimization_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'compute', 'tokens', 'api', 'storage', 'network', 'cost', 'general'
    )),
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),

    -- Impact analysis
    current_value DECIMAL(15,4),
    recommended_value DECIMAL(15,4),
    estimated_savings_usd DECIMAL(10,2),
    estimated_savings_percent DECIMAL(5,2),

    -- Implementation
    implementation_effort VARCHAR(20) CHECK (implementation_effort IN ('low', 'medium', 'high')),
    implementation_steps JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'implemented', 'rejected', 'expired'
    )),

    -- Recommendation text
    title VARCHAR(255) NOT NULL,
    description TEXT,
    reasoning TEXT,

    -- Validity period
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,

    -- Tracking
    applied_at TIMESTAMP WITH TIME ZONE,
    applied_by UUID,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimization recommendations
CREATE INDEX idx_resource_opt_agent ON analytics.resource_optimization_recommendations (agent_id);
CREATE INDEX idx_resource_opt_workspace ON analytics.resource_optimization_recommendations (workspace_id);
CREATE INDEX idx_resource_opt_status ON analytics.resource_optimization_recommendations (status);
CREATE INDEX idx_resource_opt_priority ON analytics.resource_optimization_recommendations (priority);
CREATE INDEX idx_resource_opt_category ON analytics.resource_optimization_recommendations (category);
CREATE INDEX idx_resource_opt_savings ON analytics.resource_optimization_recommendations (estimated_savings_usd DESC);

-- ============================================================================
-- 5. Resource Waste Detection Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.resource_waste_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    execution_id UUID,
    workspace_id UUID NOT NULL,

    -- Waste details
    waste_type VARCHAR(50) NOT NULL CHECK (waste_type IN (
        'idle_resources', 'oversized_instances', 'redundant_api_calls',
        'inefficient_prompts', 'unused_cache', 'failed_execution_costs',
        'rate_limit_waste', 'token_overflow'
    )),
    waste_category VARCHAR(50) NOT NULL,

    -- Quantification
    waste_amount DECIMAL(15,4),
    waste_unit VARCHAR(50),
    waste_cost_usd DECIMAL(10,6),

    -- Detection
    detection_method VARCHAR(100),
    confidence_score DECIMAL(3,2),

    -- Description
    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Resolution
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,

    -- Time period
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    waste_period_start TIMESTAMP WITH TIME ZONE,
    waste_period_end TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for waste detection
CREATE INDEX idx_resource_waste_agent ON analytics.resource_waste_events (agent_id);
CREATE INDEX idx_resource_waste_workspace ON analytics.resource_waste_events (workspace_id);
CREATE INDEX idx_resource_waste_type ON analytics.resource_waste_events (waste_type);
CREATE INDEX idx_resource_waste_cost ON analytics.resource_waste_events (waste_cost_usd DESC);
CREATE INDEX idx_resource_waste_unresolved ON analytics.resource_waste_events (is_resolved)
    WHERE is_resolved = false;

-- ============================================================================
-- 6. Resource Forecasts Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.resource_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Forecast details
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN (
        'tokens', 'compute', 'api_calls', 'storage', 'cost'
    )),
    forecast_horizon_days INTEGER NOT NULL,

    -- Predictions
    predicted_value DECIMAL(15,4) NOT NULL,
    lower_bound DECIMAL(15,4),
    upper_bound DECIMAL(15,4),
    confidence_level DECIMAL(3,2),

    -- Historical baseline
    historical_average DECIMAL(15,4),
    historical_trend VARCHAR(20),

    -- Time series
    forecast_date DATE NOT NULL,
    forecast_period_start DATE NOT NULL,
    forecast_period_end DATE NOT NULL,

    -- Model info
    model_type VARCHAR(50),
    model_accuracy DECIMAL(5,4),
    training_data_points INTEGER,

    -- Alerts
    exceeds_budget BOOLEAN DEFAULT false,
    alert_threshold_breached BOOLEAN DEFAULT false,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for forecasts
CREATE INDEX idx_resource_forecast_agent ON analytics.resource_forecasts (agent_id);
CREATE INDEX idx_resource_forecast_workspace ON analytics.resource_forecasts (workspace_id);
CREATE INDEX idx_resource_forecast_type ON analytics.resource_forecasts (resource_type);
CREATE INDEX idx_resource_forecast_date ON analytics.resource_forecasts (forecast_date);
CREATE INDEX idx_resource_forecast_alerts ON analytics.resource_forecasts (exceeds_budget)
    WHERE exceeds_budget = true;

-- ============================================================================
-- 7. Comments for documentation
-- ============================================================================
COMMENT ON TABLE analytics.resource_utilization_metrics IS
    'Comprehensive tracking of computational resources, tokens, and costs per agent execution';
COMMENT ON TABLE analytics.api_usage_metrics IS
    'Detailed tracking of external API calls, latency, errors, and rate limiting';
COMMENT ON TABLE analytics.token_budgets IS
    'Token and cost budget allocations and tracking per workspace and agent';
COMMENT ON TABLE analytics.resource_optimization_recommendations IS
    'AI-generated recommendations for optimizing resource usage and reducing costs';
COMMENT ON TABLE analytics.resource_waste_events IS
    'Detection and tracking of resource waste across all categories';
COMMENT ON TABLE analytics.resource_forecasts IS
    'Time series forecasts for resource demand and cost projections';

-- ============================================================================
-- 8. Triggers for updated_at timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION analytics.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_resource_utilization_updated_at
    BEFORE UPDATE ON analytics.resource_utilization_metrics
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();

CREATE TRIGGER update_api_usage_updated_at
    BEFORE UPDATE ON analytics.api_usage_metrics
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();

CREATE TRIGGER update_token_budgets_updated_at
    BEFORE UPDATE ON analytics.token_budgets
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();

CREATE TRIGGER update_resource_opt_updated_at
    BEFORE UPDATE ON analytics.resource_optimization_recommendations
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();

CREATE TRIGGER update_resource_waste_updated_at
    BEFORE UPDATE ON analytics.resource_waste_events
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();

CREATE TRIGGER update_resource_forecasts_updated_at
    BEFORE UPDATE ON analytics.resource_forecasts
    FOR EACH ROW EXECUTE FUNCTION analytics.update_updated_at_column();
