-- =====================================================================
-- Migration: 003_create_specialized_tables.sql
-- Description: Create specialized analytics tables (cohorts, alerts)
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: user_cohorts
-- Description: Track user cohorts and retention over time
-- =====================================================================

CREATE TABLE analytics.user_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_period VARCHAR(20) NOT NULL,
    cohort_date DATE NOT NULL,
    workspace_id UUID,

    -- Cohort data
    initial_users INTEGER NOT NULL,
    retention_data JSONB NOT NULL,

    -- Metrics
    ltv_estimate NUMERIC(10,2),
    avg_revenue_per_user NUMERIC(10,2),
    churn_rate NUMERIC(5,2),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_cohort UNIQUE(cohort_period, cohort_date, workspace_id),
    CONSTRAINT valid_cohort_period CHECK (cohort_period IN ('daily', 'weekly', 'monthly'))
);

-- User Cohorts Indexes
CREATE INDEX idx_user_cohorts_date
    ON analytics.user_cohorts(cohort_date DESC);
CREATE INDEX idx_user_cohorts_workspace
    ON analytics.user_cohorts(workspace_id, cohort_date DESC) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_user_cohorts_period
    ON analytics.user_cohorts(cohort_period, cohort_date DESC);

-- Comments
COMMENT ON TABLE analytics.user_cohorts IS 'User cohort analysis for retention and lifetime value tracking';
COMMENT ON COLUMN analytics.user_cohorts.cohort_period IS 'Cohort grouping: daily, weekly, or monthly';
COMMENT ON COLUMN analytics.user_cohorts.retention_data IS 'JSON object with retention rates: {"day_1": 95, "day_7": 80, ...}';
COMMENT ON COLUMN analytics.user_cohorts.ltv_estimate IS 'Estimated lifetime value of users in this cohort';

-- =====================================================================
-- Table: alert_rules
-- Description: Configuration for analytics alerts and monitoring
-- =====================================================================

CREATE TABLE analytics.alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,

    -- Rule configuration
    metric_type VARCHAR(50) NOT NULL,
    condition VARCHAR(20) NOT NULL,
    threshold_value NUMERIC(10,2) NOT NULL,
    evaluation_window_minutes INTEGER DEFAULT 5,

    -- Notification settings
    notification_channels JSONB DEFAULT '[]',
    notification_recipients JSONB DEFAULT '[]',

    -- State tracking
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,

    CONSTRAINT valid_condition CHECK (
        condition IN ('greater_than', 'less_than', 'equals', 'not_equals', 'between')
    ),
    CONSTRAINT valid_metric_type CHECK (
        metric_type IN (
            'error_rate', 'response_time', 'active_users', 'failed_runs',
            'credits_consumed', 'agent_failures', 'user_signups', 'session_duration'
        )
    )
);

-- Alert Rules Indexes
CREATE INDEX idx_alert_rules_workspace
    ON analytics.alert_rules(workspace_id) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_alert_rules_active
    ON analytics.alert_rules(is_active) WHERE is_active = true;
CREATE INDEX idx_alert_rules_metric_type
    ON analytics.alert_rules(metric_type, is_active);

-- Comments
COMMENT ON TABLE analytics.alert_rules IS 'Alert rule configurations for monitoring system metrics';
COMMENT ON COLUMN analytics.alert_rules.metric_type IS 'Type of metric to monitor';
COMMENT ON COLUMN analytics.alert_rules.condition IS 'Comparison operator for threshold evaluation';
COMMENT ON COLUMN analytics.alert_rules.notification_channels IS 'Array of notification channels: ["email", "slack", "webhook"]';
COMMENT ON COLUMN analytics.alert_rules.notification_recipients IS 'Array of recipient configurations';

-- =====================================================================
-- Table: alert_history
-- Description: History of triggered alerts
-- =====================================================================

CREATE TABLE analytics.alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id UUID REFERENCES analytics.alert_rules(id) ON DELETE CASCADE,
    workspace_id UUID,

    -- Alert details
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    metric_value NUMERIC(10,2),
    threshold_value NUMERIC(10,2),
    evaluation_context JSONB DEFAULT '{}',

    -- Notification details
    notifications_sent JSONB DEFAULT '[]',
    notification_status VARCHAR(20) DEFAULT 'pending',

    -- Resolution
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    notes TEXT,

    CONSTRAINT valid_notification_status CHECK (
        notification_status IN ('pending', 'sent', 'failed', 'acknowledged')
    )
);

-- Alert History Indexes
CREATE INDEX idx_alert_history_rule
    ON analytics.alert_history(alert_rule_id, triggered_at DESC);
CREATE INDEX idx_alert_history_workspace
    ON analytics.alert_history(workspace_id, triggered_at DESC) WHERE workspace_id IS NOT NULL;
CREATE INDEX idx_alert_history_triggered_at
    ON analytics.alert_history(triggered_at DESC);
CREATE INDEX idx_alert_history_status
    ON analytics.alert_history(notification_status, triggered_at DESC);

-- Comments
COMMENT ON TABLE analytics.alert_history IS 'Historical record of all triggered alerts';
COMMENT ON COLUMN analytics.alert_history.evaluation_context IS 'Additional context about the alert trigger';
COMMENT ON COLUMN analytics.alert_history.notifications_sent IS 'Array of notification delivery records';
