-- =====================================================================
-- Migration: 021_create_credit_consumption_tables.sql
-- Description: Create comprehensive credit consumption tracking tables
-- Created: 2025-11-09
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: credit_consumption
-- Description: Track all credit consumption events with detailed context
-- =====================================================================

CREATE TABLE analytics.credit_consumption (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Consumption details
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    credits_consumed NUMERIC(15,2) NOT NULL,
    tokens_used INTEGER,

    -- Context
    agent_id UUID,
    user_id UUID,
    run_id UUID,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    consumed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for credit_consumption
CREATE INDEX idx_credit_consumption_workspace_time
    ON analytics.credit_consumption(workspace_id, consumed_at DESC);
CREATE INDEX idx_credit_consumption_model
    ON analytics.credit_consumption(model, consumed_at DESC);
CREATE INDEX idx_credit_consumption_agent
    ON analytics.credit_consumption(agent_id, consumed_at DESC) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_credit_consumption_user
    ON analytics.credit_consumption(user_id, consumed_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_credit_consumption_provider
    ON analytics.credit_consumption(provider, consumed_at DESC);
CREATE INDEX idx_credit_consumption_consumed_at_brin
    ON analytics.credit_consumption USING brin(consumed_at);

-- Comments
COMMENT ON TABLE analytics.credit_consumption IS 'Detailed tracking of all credit consumption events';
COMMENT ON COLUMN analytics.credit_consumption.provider IS 'AI provider: openai, anthropic, google, other';
COMMENT ON COLUMN analytics.credit_consumption.metadata IS 'Additional context like API endpoint, parameters, etc.';

-- =====================================================================
-- Table: credit_consumption_daily
-- Description: Daily aggregated credit consumption metrics
-- =====================================================================

CREATE TABLE analytics.credit_consumption_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    date DATE NOT NULL,

    -- Totals
    total_credits NUMERIC(15,2) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,

    -- Breakdown by model (JSONB for flexibility)
    model_breakdown JSONB DEFAULT '{}',

    -- Breakdown by agent
    agent_breakdown JSONB DEFAULT '{}',

    -- Breakdown by user
    user_breakdown JSONB DEFAULT '{}',

    -- Breakdown by provider
    provider_breakdown JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_credit_daily UNIQUE(workspace_id, date)
);

-- Indexes for credit_consumption_daily
CREATE INDEX idx_credit_consumption_daily_workspace
    ON analytics.credit_consumption_daily(workspace_id, date DESC);
CREATE INDEX idx_credit_consumption_daily_date
    ON analytics.credit_consumption_daily(date DESC);

-- Comments
COMMENT ON TABLE analytics.credit_consumption_daily IS 'Daily aggregated credit consumption for efficient querying';
COMMENT ON COLUMN analytics.credit_consumption_daily.model_breakdown IS 'JSON: {model_name: {credits, tokens, calls}}';
COMMENT ON COLUMN analytics.credit_consumption_daily.agent_breakdown IS 'JSON: {agent_id: {credits, runs}}';

-- =====================================================================
-- Table: workspace_credits
-- Description: Track credit allocation and budgets per workspace
-- =====================================================================

CREATE TABLE public.workspace_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL UNIQUE,

    -- Credit allocation
    allocated_credits NUMERIC(15,2) DEFAULT 0,
    consumed_credits NUMERIC(15,2) DEFAULT 0,

    -- Budget period
    period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_end TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days',

    -- Budget settings
    monthly_budget NUMERIC(15,2),
    weekly_budget NUMERIC(15,2),
    daily_limit NUMERIC(15,2),

    -- Alert thresholds
    alert_threshold_50 BOOLEAN DEFAULT true,
    alert_threshold_75 BOOLEAN DEFAULT true,
    alert_threshold_90 BOOLEAN DEFAULT true,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for workspace_credits
CREATE INDEX idx_workspace_credits_workspace
    ON public.workspace_credits(workspace_id);
CREATE INDEX idx_workspace_credits_period
    ON public.workspace_credits(period_start, period_end);

-- Comments
COMMENT ON TABLE public.workspace_credits IS 'Credit allocation and budget management per workspace';
COMMENT ON COLUMN public.workspace_credits.allocated_credits IS 'Total credits allocated for current period';
COMMENT ON COLUMN public.workspace_credits.consumed_credits IS 'Credits consumed in current period';

-- =====================================================================
-- Table: credit_budget_alerts
-- Description: Track budget alerts and notifications
-- =====================================================================

CREATE TABLE analytics.credit_budget_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,

    -- Alert details
    alert_type VARCHAR(50) NOT NULL,
    threshold NUMERIC(15,2) NOT NULL,
    current_value NUMERIC(15,2) NOT NULL,
    message TEXT NOT NULL,

    -- Status
    is_acknowledged BOOLEAN DEFAULT false,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID,

    triggered_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_alert_type CHECK (
        alert_type IN ('approaching_limit', 'exceeded_limit', 'unusual_spike', 'daily_limit', 'weekly_limit', 'monthly_limit')
    )
);

-- Indexes for credit_budget_alerts
CREATE INDEX idx_credit_alerts_workspace
    ON analytics.credit_budget_alerts(workspace_id, triggered_at DESC);
CREATE INDEX idx_credit_alerts_type
    ON analytics.credit_budget_alerts(alert_type, triggered_at DESC);
CREATE INDEX idx_credit_alerts_unacknowledged
    ON analytics.credit_budget_alerts(workspace_id, is_acknowledged) WHERE is_acknowledged = false;

-- Comments
COMMENT ON TABLE analytics.credit_budget_alerts IS 'Budget alerts and notifications for credit consumption';

-- =====================================================================
-- Table: agent_credit_limits
-- Description: Credit limits and restrictions per agent
-- =====================================================================

CREATE TABLE public.agent_credit_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL UNIQUE,
    workspace_id UUID NOT NULL,

    -- Limits
    daily_limit NUMERIC(15,2),
    weekly_limit NUMERIC(15,2),
    monthly_limit NUMERIC(15,2),
    per_run_limit NUMERIC(15,2),

    -- Current consumption tracking
    consumed_today NUMERIC(15,2) DEFAULT 0,
    consumed_this_week NUMERIC(15,2) DEFAULT 0,
    consumed_this_month NUMERIC(15,2) DEFAULT 0,

    -- Status
    is_enabled BOOLEAN DEFAULT true,
    is_paused BOOLEAN DEFAULT false,

    -- Timestamps for reset tracking
    last_daily_reset TIMESTAMPTZ DEFAULT NOW(),
    last_weekly_reset TIMESTAMPTZ DEFAULT NOW(),
    last_monthly_reset TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for agent_credit_limits
CREATE INDEX idx_agent_credit_limits_agent
    ON public.agent_credit_limits(agent_id);
CREATE INDEX idx_agent_credit_limits_workspace
    ON public.agent_credit_limits(workspace_id);

-- Comments
COMMENT ON TABLE public.agent_credit_limits IS 'Credit limits and consumption tracking per agent';

-- =====================================================================
-- Function: aggregate_daily_credit_consumption
-- Description: Aggregate credit consumption into daily rollup table
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.aggregate_daily_credit_consumption(
    p_workspace_id UUID,
    p_date DATE
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    v_model_breakdown JSONB;
    v_agent_breakdown JSONB;
    v_user_breakdown JSONB;
    v_provider_breakdown JSONB;
    v_total_credits NUMERIC;
    v_total_tokens INTEGER;
    v_total_calls INTEGER;
BEGIN
    -- Aggregate by model
    SELECT jsonb_object_agg(
        model,
        jsonb_build_object(
            'credits', SUM(credits_consumed),
            'tokens', SUM(COALESCE(tokens_used, 0)),
            'calls', COUNT(*)
        )
    )
    INTO v_model_breakdown
    FROM analytics.credit_consumption
    WHERE workspace_id = p_workspace_id
        AND DATE(consumed_at) = p_date
    GROUP BY model;

    -- Aggregate by agent
    SELECT jsonb_object_agg(
        agent_id::text,
        jsonb_build_object(
            'credits', SUM(credits_consumed),
            'runs', COUNT(DISTINCT run_id)
        )
    )
    INTO v_agent_breakdown
    FROM analytics.credit_consumption
    WHERE workspace_id = p_workspace_id
        AND DATE(consumed_at) = p_date
        AND agent_id IS NOT NULL
    GROUP BY agent_id;

    -- Aggregate by user
    SELECT jsonb_object_agg(
        user_id::text,
        jsonb_build_object(
            'credits', SUM(credits_consumed),
            'executions', COUNT(DISTINCT run_id)
        )
    )
    INTO v_user_breakdown
    FROM analytics.credit_consumption
    WHERE workspace_id = p_workspace_id
        AND DATE(consumed_at) = p_date
        AND user_id IS NOT NULL
    GROUP BY user_id;

    -- Aggregate by provider
    SELECT jsonb_object_agg(
        provider,
        jsonb_build_object(
            'credits', SUM(credits_consumed),
            'tokens', SUM(COALESCE(tokens_used, 0)),
            'calls', COUNT(*)
        )
    )
    INTO v_provider_breakdown
    FROM analytics.credit_consumption
    WHERE workspace_id = p_workspace_id
        AND DATE(consumed_at) = p_date
    GROUP BY provider;

    -- Get totals
    SELECT
        COALESCE(SUM(credits_consumed), 0),
        COALESCE(SUM(tokens_used), 0),
        COUNT(*)
    INTO v_total_credits, v_total_tokens, v_total_calls
    FROM analytics.credit_consumption
    WHERE workspace_id = p_workspace_id
        AND DATE(consumed_at) = p_date;

    -- Upsert into daily aggregation table
    INSERT INTO analytics.credit_consumption_daily (
        workspace_id,
        date,
        total_credits,
        total_tokens,
        total_calls,
        model_breakdown,
        agent_breakdown,
        user_breakdown,
        provider_breakdown,
        updated_at
    )
    VALUES (
        p_workspace_id,
        p_date,
        v_total_credits,
        v_total_tokens,
        v_total_calls,
        COALESCE(v_model_breakdown, '{}'::jsonb),
        COALESCE(v_agent_breakdown, '{}'::jsonb),
        COALESCE(v_user_breakdown, '{}'::jsonb),
        COALESCE(v_provider_breakdown, '{}'::jsonb),
        NOW()
    )
    ON CONFLICT (workspace_id, date)
    DO UPDATE SET
        total_credits = EXCLUDED.total_credits,
        total_tokens = EXCLUDED.total_tokens,
        total_calls = EXCLUDED.total_calls,
        model_breakdown = EXCLUDED.model_breakdown,
        agent_breakdown = EXCLUDED.agent_breakdown,
        user_breakdown = EXCLUDED.user_breakdown,
        provider_breakdown = EXCLUDED.provider_breakdown,
        updated_at = NOW();
END;
$$;

COMMENT ON FUNCTION analytics.aggregate_daily_credit_consumption IS 'Aggregates credit consumption data into daily rollup table';

-- =====================================================================
-- Trigger: update_workspace_credits_on_consumption
-- Description: Update workspace consumed credits when new consumption is recorded
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.update_workspace_credits()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE public.workspace_credits
    SET
        consumed_credits = consumed_credits + NEW.credits_consumed,
        updated_at = NOW()
    WHERE workspace_id = NEW.workspace_id;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_update_workspace_credits
    AFTER INSERT ON analytics.credit_consumption
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_workspace_credits();

-- =====================================================================
-- Grant permissions
-- =====================================================================

GRANT SELECT ON analytics.credit_consumption TO analytics_read;
GRANT INSERT ON analytics.credit_consumption TO analytics_write;
GRANT SELECT ON analytics.credit_consumption_daily TO analytics_read;
GRANT SELECT, INSERT, UPDATE ON public.workspace_credits TO analytics_write;
GRANT SELECT ON public.workspace_credits TO analytics_read;
