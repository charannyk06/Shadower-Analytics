-- =====================================================================
-- Migration: 009_create_workspace_analytics_tables.sql
-- Description: Create tables for workspace-level analytics and comparison
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: workspace_metrics_daily
-- Description: Daily aggregated metrics per workspace for comprehensive analytics
-- =====================================================================

CREATE TABLE analytics.workspace_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    metric_date DATE NOT NULL,

    -- Member metrics
    total_members INTEGER DEFAULT 0,
    active_members INTEGER DEFAULT 0,
    new_members INTEGER DEFAULT 0,
    pending_invites INTEGER DEFAULT 0,
    member_growth_rate NUMERIC(5,2) DEFAULT 0,

    -- Member breakdown by role
    owner_count INTEGER DEFAULT 0,
    admin_count INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 0,
    viewer_count INTEGER DEFAULT 0,

    -- Activity metrics
    total_activity INTEGER DEFAULT 0,
    unique_active_users INTEGER DEFAULT 0,
    avg_activity_per_user NUMERIC(10,2) DEFAULT 0,
    activity_trend VARCHAR(20) DEFAULT 'stable',

    -- Agent metrics
    total_agents INTEGER DEFAULT 0,
    active_agents INTEGER DEFAULT 0,
    total_agent_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    avg_success_rate NUMERIC(5,2) DEFAULT 0,
    avg_runtime_seconds NUMERIC(10,2) DEFAULT 0,

    -- Resource metrics
    credits_allocated NUMERIC(15,2) DEFAULT 0,
    credits_consumed NUMERIC(15,2) DEFAULT 0,
    credits_remaining NUMERIC(15,2) DEFAULT 0,
    credit_utilization_rate NUMERIC(5,2) DEFAULT 0,

    -- Storage metrics
    storage_used_bytes BIGINT DEFAULT 0,
    storage_limit_bytes BIGINT DEFAULT 10737418240, -- 10GB default
    storage_utilization_rate NUMERIC(5,2) DEFAULT 0,

    -- API metrics
    total_api_calls INTEGER DEFAULT 0,
    api_rate_limit INTEGER DEFAULT 0,
    api_utilization_rate NUMERIC(5,2) DEFAULT 0,

    -- Health metrics
    health_score INTEGER DEFAULT 0,
    activity_score INTEGER DEFAULT 0,
    engagement_score INTEGER DEFAULT 0,
    efficiency_score INTEGER DEFAULT 0,
    reliability_score INTEGER DEFAULT 0,

    -- Workspace status
    workspace_status VARCHAR(20) DEFAULT 'active',
    days_active INTEGER DEFAULT 0,

    -- Billing metrics
    current_plan VARCHAR(50),
    billing_status VARCHAR(20) DEFAULT 'active',
    current_month_cost NUMERIC(10,2) DEFAULT 0,
    projected_month_cost NUMERIC(10,2) DEFAULT 0,

    -- Consumption breakdown (JSONB for flexibility)
    consumption_by_model JSONB DEFAULT '{}',
    storage_breakdown JSONB DEFAULT '{}',
    api_by_endpoint JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_workspace_daily UNIQUE(workspace_id, metric_date),
    CONSTRAINT valid_workspace_status CHECK (
        workspace_status IN ('active', 'idle', 'at_risk', 'churned')
    ),
    CONSTRAINT valid_activity_trend CHECK (
        activity_trend IN ('increasing', 'stable', 'decreasing')
    ),
    CONSTRAINT valid_billing_status CHECK (
        billing_status IN ('active', 'trial', 'past_due', 'cancelled')
    )
);

-- Indexes for workspace_metrics_daily
CREATE INDEX idx_workspace_metrics_workspace_date
    ON analytics.workspace_metrics_daily(workspace_id, metric_date DESC);

CREATE INDEX idx_workspace_metrics_date
    ON analytics.workspace_metrics_daily(metric_date DESC);

CREATE INDEX idx_workspace_metrics_health_score
    ON analytics.workspace_metrics_daily(health_score DESC);

CREATE INDEX idx_workspace_metrics_status
    ON analytics.workspace_metrics_daily(workspace_status, metric_date DESC);

CREATE INDEX idx_workspace_metrics_activity
    ON analytics.workspace_metrics_daily(total_activity DESC);

-- BRIN index for time-series queries
CREATE INDEX idx_workspace_metrics_date_brin
    ON analytics.workspace_metrics_daily USING brin(metric_date);

-- GIN indexes for JSONB columns
CREATE INDEX idx_workspace_metrics_consumption_model
    ON analytics.workspace_metrics_daily USING gin(consumption_by_model);

CREATE INDEX idx_workspace_metrics_storage_breakdown
    ON analytics.workspace_metrics_daily USING gin(storage_breakdown);

-- Comments
COMMENT ON TABLE analytics.workspace_metrics_daily IS 'Daily aggregated metrics per workspace for comprehensive analytics';
COMMENT ON COLUMN analytics.workspace_metrics_daily.health_score IS 'Overall workspace health score (0-100)';
COMMENT ON COLUMN analytics.workspace_metrics_daily.activity_trend IS 'Activity trend: increasing, stable, or decreasing';
COMMENT ON COLUMN analytics.workspace_metrics_daily.workspace_status IS 'Workspace status: active, idle, at_risk, or churned';
COMMENT ON COLUMN analytics.workspace_metrics_daily.consumption_by_model IS 'Credits consumed per AI model';
COMMENT ON COLUMN analytics.workspace_metrics_daily.storage_breakdown IS 'Storage usage by category';

-- =====================================================================
-- Table: workspace_member_activity
-- Description: Detailed member activity metrics within workspaces
-- =====================================================================

CREATE TABLE analytics.workspace_member_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    metric_date DATE NOT NULL,

    -- Member info
    user_role VARCHAR(20),

    -- Activity metrics
    activity_count INTEGER DEFAULT 0,
    agent_runs INTEGER DEFAULT 0,
    success_rate NUMERIC(5,2) DEFAULT 0,
    credits_used NUMERIC(10,2) DEFAULT 0,

    -- Engagement
    days_active INTEGER DEFAULT 0,
    last_active_at TIMESTAMPTZ,
    engagement_level VARCHAR(20) DEFAULT 'low',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_workspace_member_daily UNIQUE(workspace_id, user_id, metric_date),
    CONSTRAINT valid_user_role CHECK (
        user_role IN ('owner', 'admin', 'member', 'viewer')
    ),
    CONSTRAINT valid_engagement_level CHECK (
        engagement_level IN ('high', 'medium', 'low', 'inactive')
    )
);

-- Indexes for workspace_member_activity
CREATE INDEX idx_workspace_member_workspace
    ON analytics.workspace_member_activity(workspace_id, metric_date DESC);

CREATE INDEX idx_workspace_member_user
    ON analytics.workspace_member_activity(user_id, metric_date DESC);

CREATE INDEX idx_workspace_member_engagement
    ON analytics.workspace_member_activity(workspace_id, engagement_level);

CREATE INDEX idx_workspace_member_last_active
    ON analytics.workspace_member_activity(workspace_id, last_active_at DESC);

-- Comments
COMMENT ON TABLE analytics.workspace_member_activity IS 'Daily activity metrics for workspace members';
COMMENT ON COLUMN analytics.workspace_member_activity.engagement_level IS 'Member engagement: high, medium, low, or inactive';

-- =====================================================================
-- Materialized View: mv_workspace_comparison
-- Description: Pre-computed workspace comparison data for benchmarking
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_workspace_comparison AS
WITH recent_metrics AS (
    SELECT
        workspace_id,
        AVG(health_score) as avg_health_score,
        AVG(total_activity) as avg_activity,
        AVG(credits_consumed) as avg_credits,
        AVG(avg_success_rate) as avg_efficiency,
        AVG(total_members) as avg_members,
        AVG(active_members) as avg_active_members,
        AVG(credit_utilization_rate) as avg_credit_utilization
    FROM analytics.workspace_metrics_daily
    WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workspace_id
),
global_averages AS (
    SELECT
        AVG(avg_health_score) as global_avg_health,
        AVG(avg_activity) as global_avg_activity,
        AVG(avg_credits) as global_avg_credits,
        AVG(avg_efficiency) as global_avg_efficiency,
        COUNT(DISTINCT workspace_id) as total_workspaces
    FROM recent_metrics
)
SELECT
    rm.workspace_id,
    rm.avg_health_score,
    rm.avg_activity,
    rm.avg_credits,
    rm.avg_efficiency,
    rm.avg_members,
    rm.avg_active_members,
    rm.avg_credit_utilization,

    -- Rankings
    RANK() OVER (ORDER BY rm.avg_health_score DESC) as health_rank,
    RANK() OVER (ORDER BY rm.avg_activity DESC) as activity_rank,
    RANK() OVER (ORDER BY rm.avg_efficiency DESC) as efficiency_rank,
    RANK() OVER (ORDER BY rm.avg_credits ASC) as cost_efficiency_rank,

    -- Percentiles
    PERCENT_RANK() OVER (ORDER BY rm.avg_health_score) * 100 as health_percentile,
    PERCENT_RANK() OVER (ORDER BY rm.avg_activity) * 100 as activity_percentile,
    PERCENT_RANK() OVER (ORDER BY rm.avg_efficiency) * 100 as efficiency_percentile,

    -- Benchmarks vs global average
    CASE
        WHEN ga.global_avg_activity > 0 THEN
            ROUND(((rm.avg_activity - ga.global_avg_activity) / ga.global_avg_activity * 100)::numeric, 2)
        ELSE 0
    END as activity_vs_avg_pct,

    CASE
        WHEN ga.global_avg_efficiency > 0 THEN
            ROUND(((rm.avg_efficiency - ga.global_avg_efficiency) / ga.global_avg_efficiency * 100)::numeric, 2)
        ELSE 0
    END as efficiency_vs_avg_pct,

    CASE
        WHEN ga.global_avg_credits > 0 THEN
            ROUND(((rm.avg_credits - ga.global_avg_credits) / ga.global_avg_credits * 100)::numeric, 2)
        ELSE 0
    END as cost_vs_avg_pct,

    ga.total_workspaces
FROM recent_metrics rm
CROSS JOIN global_averages ga;

-- Unique index for fast lookups
CREATE UNIQUE INDEX idx_mv_workspace_comparison_workspace
    ON analytics.mv_workspace_comparison(workspace_id);

-- Additional indexes for sorting/filtering
CREATE INDEX idx_mv_workspace_comparison_health_rank
    ON analytics.mv_workspace_comparison(health_rank);

CREATE INDEX idx_mv_workspace_comparison_activity_rank
    ON analytics.mv_workspace_comparison(activity_rank);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_workspace_comparison IS 'Pre-computed workspace comparison metrics for admin dashboard';

-- =====================================================================
-- Function: refresh_workspace_comparison
-- Description: Helper function to refresh the materialized view
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_workspace_comparison()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_workspace_comparison;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_workspace_comparison() IS 'Refreshes the workspace comparison materialized view';

-- =====================================================================
-- Function: calculate_workspace_health_score
-- Description: Calculate health score for a workspace
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.calculate_workspace_health_score(
    p_workspace_id UUID,
    p_metric_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    overall_score INTEGER,
    activity_score INTEGER,
    engagement_score INTEGER,
    efficiency_score INTEGER,
    reliability_score INTEGER
) AS $$
DECLARE
    v_activity_score INTEGER;
    v_engagement_score INTEGER;
    v_efficiency_score INTEGER;
    v_reliability_score INTEGER;
    v_overall_score INTEGER;
BEGIN
    -- Calculate activity score (based on active members percentage)
    SELECT LEAST(100, ROUND(
        (CAST(active_members AS NUMERIC) / NULLIF(total_members, 0) * 100)::numeric
    ))
    INTO v_activity_score
    FROM analytics.workspace_metrics_daily
    WHERE workspace_id = p_workspace_id
        AND metric_date = p_metric_date;

    -- Calculate engagement score (based on avg activity per user)
    SELECT LEAST(100, ROUND(
        (avg_activity_per_user / 10 * 100)::numeric
    ))
    INTO v_engagement_score
    FROM analytics.workspace_metrics_daily
    WHERE workspace_id = p_workspace_id
        AND metric_date = p_metric_date;

    -- Calculate efficiency score (based on agent success rate)
    SELECT ROUND(avg_success_rate)
    INTO v_efficiency_score
    FROM analytics.workspace_metrics_daily
    WHERE workspace_id = p_workspace_id
        AND metric_date = p_metric_date;

    -- Calculate reliability score (100 - error rate)
    SELECT LEAST(100, ROUND(
        (100 - (CAST(failed_runs AS NUMERIC) / NULLIF(total_agent_runs, 0) * 100))::numeric
    ))
    INTO v_reliability_score
    FROM analytics.workspace_metrics_daily
    WHERE workspace_id = p_workspace_id
        AND metric_date = p_metric_date;

    -- Calculate overall score (weighted average)
    v_overall_score := ROUND(
        COALESCE(v_activity_score, 0) * 0.3 +
        COALESCE(v_engagement_score, 0) * 0.3 +
        COALESCE(v_efficiency_score, 0) * 0.2 +
        COALESCE(v_reliability_score, 0) * 0.2
    );

    RETURN QUERY SELECT
        v_overall_score,
        COALESCE(v_activity_score, 0),
        COALESCE(v_engagement_score, 0),
        COALESCE(v_efficiency_score, 0),
        COALESCE(v_reliability_score, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.calculate_workspace_health_score(UUID, DATE) IS 'Calculates health score components for a workspace';

-- =====================================================================
-- Grant Permissions
-- =====================================================================

-- Grant read access to analytics role
GRANT SELECT ON analytics.workspace_metrics_daily TO analytics_reader;
GRANT SELECT ON analytics.workspace_member_activity TO analytics_reader;
GRANT SELECT ON analytics.mv_workspace_comparison TO analytics_reader;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION analytics.refresh_workspace_comparison() TO analytics_admin;
GRANT EXECUTE ON FUNCTION analytics.calculate_workspace_health_score(UUID, DATE) TO analytics_reader;
