-- =====================================================================
-- Migration: 027_create_notification_tables.sql
-- Description: Create comprehensive notification system tables
-- Created: 2025-11-12
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: notification_preferences
-- Description: User notification preferences per workspace and type
-- =====================================================================

CREATE TABLE analytics.notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    frequency VARCHAR(20) DEFAULT 'immediate', -- 'immediate', 'hourly', 'daily', 'weekly'
    schedule_time TIME, -- For scheduled digests
    schedule_timezone VARCHAR(50) DEFAULT 'UTC',
    filter_rules JSONB DEFAULT '{}', -- Custom filtering conditions
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_notification_pref UNIQUE(user_id, workspace_id, notification_type, channel),
    CONSTRAINT valid_channel CHECK (
        channel IN ('in_app', 'email', 'slack', 'teams', 'discord', 'webhook')
    ),
    CONSTRAINT valid_frequency CHECK (
        frequency IN ('immediate', 'hourly', 'daily', 'weekly')
    )
);

-- Indexes for notification_preferences
CREATE INDEX idx_notification_prefs_user
    ON analytics.notification_preferences(user_id, workspace_id);

CREATE INDEX idx_notification_prefs_type
    ON analytics.notification_preferences(notification_type, is_enabled);

CREATE INDEX idx_notification_prefs_enabled
    ON analytics.notification_preferences(is_enabled, channel);

-- GIN index for filter_rules
CREATE INDEX idx_notification_prefs_filter_rules
    ON analytics.notification_preferences USING gin(filter_rules);

-- Comments
COMMENT ON TABLE analytics.notification_preferences IS 'User notification preferences per workspace and notification type';
COMMENT ON COLUMN analytics.notification_preferences.frequency IS 'Notification frequency: immediate, hourly, daily, or weekly';
COMMENT ON COLUMN analytics.notification_preferences.filter_rules IS 'JSON filtering conditions for notifications';

-- =====================================================================
-- Table: notification_templates
-- Description: Notification templates for different channels
-- =====================================================================

CREATE TABLE analytics.notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(255) NOT NULL UNIQUE,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    subject_template TEXT,
    body_template TEXT NOT NULL,
    variables JSONB NOT NULL DEFAULT '[]', -- Required variables
    preview_data JSONB, -- Sample data for preview
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_template_channel CHECK (
        channel IN ('in_app', 'email', 'slack', 'teams', 'discord', 'webhook')
    )
);

-- Indexes for notification_templates
CREATE INDEX idx_notification_templates_type
    ON analytics.notification_templates(notification_type, channel, is_active);

CREATE INDEX idx_notification_templates_active
    ON analytics.notification_templates(is_active);

-- GIN indexes for JSONB columns
CREATE INDEX idx_notification_templates_variables
    ON analytics.notification_templates USING gin(variables);

-- Comments
COMMENT ON TABLE analytics.notification_templates IS 'Notification templates for different channels and types';
COMMENT ON COLUMN analytics.notification_templates.variables IS 'Required template variables in JSON array format';
COMMENT ON COLUMN analytics.notification_templates.preview_data IS 'Sample data for template preview';

-- =====================================================================
-- Table: notification_queue
-- Description: Queue for pending and scheduled notifications
-- =====================================================================

CREATE TABLE analytics.notification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_type VARCHAR(100) NOT NULL,
    recipient_id UUID NOT NULL,
    recipient_email VARCHAR(255),
    channel VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    payload JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_for TIMESTAMPTZ DEFAULT NOW(),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_queue_channel CHECK (
        channel IN ('in_app', 'email', 'slack', 'teams', 'discord', 'webhook')
    ),
    CONSTRAINT valid_queue_priority CHECK (
        priority IN ('low', 'normal', 'high', 'urgent')
    ),
    CONSTRAINT valid_queue_status CHECK (
        status IN ('pending', 'processing', 'delivered', 'failed', 'cancelled')
    )
);

-- Indexes for notification_queue
CREATE INDEX idx_notification_queue_status
    ON analytics.notification_queue(status, scheduled_for) WHERE status IN ('pending', 'processing');

CREATE INDEX idx_notification_queue_recipient
    ON analytics.notification_queue(recipient_id, status);

CREATE INDEX idx_notification_queue_scheduled
    ON analytics.notification_queue(scheduled_for) WHERE status = 'pending';

CREATE INDEX idx_notification_queue_priority
    ON analytics.notification_queue(priority DESC, scheduled_for) WHERE status = 'pending';

CREATE INDEX idx_notification_queue_created
    ON analytics.notification_queue(created_at DESC);

-- GIN index for payload
CREATE INDEX idx_notification_queue_payload
    ON analytics.notification_queue USING gin(payload);

-- Comments
COMMENT ON TABLE analytics.notification_queue IS 'Queue for pending and scheduled notifications';
COMMENT ON COLUMN analytics.notification_queue.priority IS 'Priority level: low, normal, high, or urgent';
COMMENT ON COLUMN analytics.notification_queue.status IS 'Queue status: pending, processing, delivered, failed, or cancelled';

-- =====================================================================
-- Table: notification_log
-- Description: Historical log of all sent notifications
-- =====================================================================

CREATE TABLE analytics.notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES analytics.notification_queue(id) ON DELETE SET NULL,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    subject TEXT,
    preview TEXT,
    full_content TEXT,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    delivery_status VARCHAR(20) NOT NULL,
    tracking_data JSONB DEFAULT '{}',

    CONSTRAINT valid_log_channel CHECK (
        channel IN ('in_app', 'email', 'slack', 'teams', 'discord', 'webhook')
    ),
    CONSTRAINT valid_log_delivery_status CHECK (
        delivery_status IN ('sent', 'delivered', 'bounced', 'failed', 'read', 'clicked')
    )
);

-- Indexes for notification_log
CREATE INDEX idx_notification_log_user
    ON analytics.notification_log(user_id, sent_at DESC);

CREATE INDEX idx_notification_log_workspace
    ON analytics.notification_log(workspace_id, notification_type, sent_at DESC);

CREATE INDEX idx_notification_log_type
    ON analytics.notification_log(notification_type, sent_at DESC);

CREATE INDEX idx_notification_log_channel
    ON analytics.notification_log(channel, sent_at DESC);

CREATE INDEX idx_notification_log_status
    ON analytics.notification_log(delivery_status, sent_at DESC);

CREATE INDEX idx_notification_log_unread
    ON analytics.notification_log(user_id, read_at) WHERE read_at IS NULL AND channel = 'in_app';

-- BRIN index for time-series queries
CREATE INDEX idx_notification_log_sent_at_brin
    ON analytics.notification_log USING brin(sent_at);

-- GIN index for tracking_data
CREATE INDEX idx_notification_log_tracking_data
    ON analytics.notification_log USING gin(tracking_data);

-- Comments
COMMENT ON TABLE analytics.notification_log IS 'Historical log of all sent notifications with tracking data';
COMMENT ON COLUMN analytics.notification_log.delivery_status IS 'Delivery status: sent, delivered, bounced, failed, read, or clicked';
COMMENT ON COLUMN analytics.notification_log.tracking_data IS 'Additional tracking and metadata in JSON format';

-- =====================================================================
-- Table: digest_queue
-- Description: Queue for periodic digest notifications
-- =====================================================================

CREATE TABLE analytics.digest_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    digest_type VARCHAR(50) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    events JSONB NOT NULL DEFAULT '[]',
    summary_stats JSONB DEFAULT '{}',
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    notification_id UUID REFERENCES analytics.notification_queue(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_digest_type CHECK (
        digest_type IN ('daily', 'weekly', 'monthly', 'custom')
    ),
    CONSTRAINT valid_digest_period CHECK (period_end > period_start)
);

-- Indexes for digest_queue
CREATE INDEX idx_digest_queue_pending
    ON analytics.digest_queue(is_sent, period_end) WHERE is_sent = FALSE;

CREATE INDEX idx_digest_queue_user
    ON analytics.digest_queue(user_id, workspace_id, digest_type);

CREATE INDEX idx_digest_queue_period
    ON analytics.digest_queue(period_start, period_end);

-- Unique constraint to prevent duplicate digests
CREATE UNIQUE INDEX idx_digest_queue_unique
    ON analytics.digest_queue(user_id, workspace_id, digest_type, period_start);

-- GIN indexes for JSONB columns
CREATE INDEX idx_digest_queue_events
    ON analytics.digest_queue USING gin(events);

CREATE INDEX idx_digest_queue_summary
    ON analytics.digest_queue USING gin(summary_stats);

-- Comments
COMMENT ON TABLE analytics.digest_queue IS 'Queue for periodic digest notifications';
COMMENT ON COLUMN analytics.digest_queue.digest_type IS 'Type of digest: daily, weekly, monthly, or custom';
COMMENT ON COLUMN analytics.digest_queue.events IS 'Array of events included in digest';
COMMENT ON COLUMN analytics.digest_queue.summary_stats IS 'Aggregated statistics for digest period';

-- =====================================================================
-- Table: notification_channels
-- Description: Channel configuration per workspace (webhooks, API keys)
-- =====================================================================

CREATE TABLE analytics.notification_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    channel VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    configuration JSONB NOT NULL DEFAULT '{}', -- Webhook URLs, API keys, etc.
    last_test_at TIMESTAMPTZ,
    last_test_status VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_workspace_channel UNIQUE(workspace_id, channel),
    CONSTRAINT valid_notification_channel CHECK (
        channel IN ('email', 'slack', 'teams', 'discord', 'webhook')
    ),
    CONSTRAINT valid_test_status CHECK (
        last_test_status IS NULL OR last_test_status IN ('success', 'failed')
    )
);

-- Indexes for notification_channels
CREATE INDEX idx_notification_channels_workspace
    ON analytics.notification_channels(workspace_id, is_enabled);

-- GIN index for configuration
CREATE INDEX idx_notification_channels_config
    ON analytics.notification_channels USING gin(configuration);

-- Comments
COMMENT ON TABLE analytics.notification_channels IS 'Channel configuration per workspace for external integrations';
COMMENT ON COLUMN analytics.notification_channels.configuration IS 'Channel-specific configuration including webhooks and API keys';

-- =====================================================================
-- Table: notification_subscriptions
-- Description: User subscriptions to specific notification topics
-- =====================================================================

CREATE TABLE analytics.notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    subscription_type VARCHAR(100) NOT NULL,
    is_subscribed BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_subscription UNIQUE(user_id, workspace_id, subscription_type)
);

-- Indexes for notification_subscriptions
CREATE INDEX idx_notification_subscriptions_user
    ON analytics.notification_subscriptions(user_id, workspace_id);

CREATE INDEX idx_notification_subscriptions_type
    ON analytics.notification_subscriptions(subscription_type, is_subscribed);

-- Comments
COMMENT ON TABLE analytics.notification_subscriptions IS 'User subscriptions to specific notification topics';

-- =====================================================================
-- Materialized View: mv_notification_metrics
-- Description: Pre-computed notification performance metrics
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.mv_notification_metrics AS
WITH recent_notifications AS (
    SELECT
        workspace_id,
        notification_type,
        channel,
        COUNT(*) as total_sent,
        COUNT(*) FILTER (WHERE delivery_status = 'delivered') as total_delivered,
        COUNT(*) FILTER (WHERE delivery_status = 'failed') as total_failed,
        COUNT(*) FILTER (WHERE delivery_status = 'bounced') as total_bounced,
        COUNT(*) FILTER (WHERE read_at IS NOT NULL) as total_read,
        COUNT(*) FILTER (WHERE clicked_at IS NOT NULL) as total_clicked,
        AVG(EXTRACT(EPOCH FROM (delivered_at - sent_at))) as avg_delivery_time_seconds
    FROM analytics.notification_log
    WHERE sent_at >= NOW() - INTERVAL '30 days'
    GROUP BY workspace_id, notification_type, channel
)
SELECT
    workspace_id,
    notification_type,
    channel,
    total_sent,
    total_delivered,
    total_failed,
    total_bounced,
    total_read,
    total_clicked,
    ROUND(avg_delivery_time_seconds::numeric, 2) as avg_delivery_time_seconds,
    CASE WHEN total_sent > 0 THEN ROUND((total_delivered::numeric / total_sent * 100), 2) ELSE 0 END as delivery_rate,
    CASE WHEN total_delivered > 0 THEN ROUND((total_read::numeric / total_delivered * 100), 2) ELSE 0 END as open_rate,
    CASE WHEN total_read > 0 THEN ROUND((total_clicked::numeric / total_read * 100), 2) ELSE 0 END as click_through_rate,
    NOW() as last_refreshed
FROM recent_notifications;

-- Unique index for fast lookups
CREATE UNIQUE INDEX idx_mv_notification_metrics_unique
    ON analytics.mv_notification_metrics(workspace_id, notification_type, channel);

-- Additional indexes
CREATE INDEX idx_mv_notification_metrics_workspace
    ON analytics.mv_notification_metrics(workspace_id);

CREATE INDEX idx_mv_notification_metrics_type
    ON analytics.mv_notification_metrics(notification_type);

-- Comments
COMMENT ON MATERIALIZED VIEW analytics.mv_notification_metrics IS 'Pre-computed notification performance metrics for last 30 days';

-- =====================================================================
-- Function: refresh_notification_metrics
-- Description: Helper function to refresh notification metrics view
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_notification_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_notification_metrics;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.refresh_notification_metrics() IS 'Refreshes the notification metrics materialized view';

-- =====================================================================
-- Function: mark_notification_as_read
-- Description: Mark a notification as read and update tracking
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.mark_notification_as_read(
    p_notification_id UUID,
    p_user_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated BOOLEAN;
BEGIN
    UPDATE analytics.notification_log
    SET
        read_at = CASE WHEN read_at IS NULL THEN NOW() ELSE read_at END,
        delivery_status = CASE WHEN delivery_status = 'delivered' THEN 'read' ELSE delivery_status END,
        tracking_data = tracking_data || jsonb_build_object('last_read_at', NOW())
    WHERE id = p_notification_id
        AND user_id = p_user_id
        AND channel = 'in_app';

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.mark_notification_as_read(UUID, UUID) IS 'Marks an in-app notification as read';

-- =====================================================================
-- Function: get_unread_notification_count
-- Description: Get count of unread in-app notifications for a user
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.get_unread_notification_count(
    p_user_id UUID,
    p_workspace_id UUID DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM analytics.notification_log
    WHERE user_id = p_user_id
        AND channel = 'in_app'
        AND read_at IS NULL
        AND (p_workspace_id IS NULL OR workspace_id = p_workspace_id);

    RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.get_unread_notification_count(UUID, UUID) IS 'Returns count of unread in-app notifications for a user';

-- =====================================================================
-- Function: process_notification_queue
-- Description: Process pending notifications from queue
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.process_notification_queue(
    p_batch_size INTEGER DEFAULT 100
)
RETURNS TABLE (
    notification_id UUID,
    recipient_id UUID,
    channel VARCHAR,
    priority VARCHAR
) AS $$
BEGIN
    -- Update status to processing for selected notifications
    WITH selected AS (
        SELECT id
        FROM analytics.notification_queue
        WHERE status = 'pending'
            AND scheduled_for <= NOW()
            AND attempts < max_attempts
        ORDER BY priority DESC, scheduled_for ASC
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    UPDATE analytics.notification_queue nq
    SET
        status = 'processing',
        last_attempt_at = NOW(),
        attempts = attempts + 1
    FROM selected
    WHERE nq.id = selected.id
    RETURNING nq.id, nq.recipient_id, nq.channel, nq.priority;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.process_notification_queue(INTEGER) IS 'Processes batch of pending notifications from queue';

-- =====================================================================
-- Function: cleanup_old_notifications
-- Description: Archive or delete old notification logs
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.cleanup_old_notifications(
    p_days_to_keep INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM analytics.notification_log
        WHERE sent_at < NOW() - (p_days_to_keep || ' days')::INTERVAL
            AND read_at IS NOT NULL -- Only delete read notifications
        RETURNING id
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.cleanup_old_notifications(INTEGER) IS 'Cleans up old read notifications older than specified days';

-- =====================================================================
-- Trigger: update_notification_preferences_timestamp
-- Description: Auto-update updated_at timestamp
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.update_notification_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_notification_prefs_updated
    BEFORE UPDATE ON analytics.notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_notification_timestamp();

CREATE TRIGGER trg_notification_templates_updated
    BEFORE UPDATE ON analytics.notification_templates
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_notification_timestamp();

CREATE TRIGGER trg_notification_channels_updated
    BEFORE UPDATE ON analytics.notification_channels
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_notification_timestamp();

CREATE TRIGGER trg_notification_subscriptions_updated
    BEFORE UPDATE ON analytics.notification_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_notification_timestamp();

-- =====================================================================
-- Grant Permissions
-- =====================================================================

-- Grant read access to analytics role
GRANT SELECT ON analytics.notification_preferences TO analytics_reader;
GRANT SELECT ON analytics.notification_templates TO analytics_reader;
GRANT SELECT ON analytics.notification_queue TO analytics_reader;
GRANT SELECT ON analytics.notification_log TO analytics_reader;
GRANT SELECT ON analytics.digest_queue TO analytics_reader;
GRANT SELECT ON analytics.notification_channels TO analytics_reader;
GRANT SELECT ON analytics.notification_subscriptions TO analytics_reader;
GRANT SELECT ON analytics.mv_notification_metrics TO analytics_reader;

-- Grant write access to analytics admin
GRANT INSERT, UPDATE, DELETE ON analytics.notification_preferences TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.notification_templates TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.notification_queue TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.notification_log TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.digest_queue TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.notification_channels TO analytics_admin;
GRANT INSERT, UPDATE, DELETE ON analytics.notification_subscriptions TO analytics_admin;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION analytics.refresh_notification_metrics() TO analytics_admin;
GRANT EXECUTE ON FUNCTION analytics.mark_notification_as_read(UUID, UUID) TO analytics_admin;
GRANT EXECUTE ON FUNCTION analytics.get_unread_notification_count(UUID, UUID) TO analytics_reader;
GRANT EXECUTE ON FUNCTION analytics.process_notification_queue(INTEGER) TO analytics_admin;
GRANT EXECUTE ON FUNCTION analytics.cleanup_old_notifications(INTEGER) TO analytics_admin;

-- =====================================================================
-- Initial Data: Default Notification Templates
-- =====================================================================

-- Email template for alert notifications
INSERT INTO analytics.notification_templates (template_name, notification_type, channel, subject_template, body_template, variables, preview_data) VALUES
('alert_critical_email', 'alert_critical', 'email',
 '⚠️ Critical Alert: {{alert_name}}',
 '<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc2626; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }
        .metric { font-size: 24px; font-weight: bold; color: #dc2626; margin: 10px 0; }
        .button { background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
        .footer { color: #6b7280; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>⚠️ Critical Alert</h2>
        </div>
        <div class="content">
            <h3>{{alert_name}}</h3>
            <p>{{alert_description}}</p>
            <div class="metric">
                {{metric_name}}: {{metric_value}}
            </div>
            <p><strong>Threshold:</strong> {{threshold}}</p>
            <p><strong>Time:</strong> {{triggered_at}}</p>
            <a href="{{dashboard_url}}" class="button">View Dashboard</a>
        </div>
        <div class="footer">
            <p>Workspace: {{workspace_name}}</p>
            <p>You received this because you are subscribed to critical alerts.</p>
        </div>
    </div>
</body>
</html>',
 '["alert_name", "alert_description", "metric_name", "metric_value", "threshold", "triggered_at", "dashboard_url", "workspace_name"]'::jsonb,
 '{"alert_name": "High Error Rate", "alert_description": "Error rate exceeded threshold", "metric_name": "Error Rate", "metric_value": "15%", "threshold": "10%", "triggered_at": "2025-11-12 10:30:00", "dashboard_url": "https://app.example.com/dashboard", "workspace_name": "Production"}'::jsonb
);

-- Slack template for alert notifications
INSERT INTO analytics.notification_templates (template_name, notification_type, channel, body_template, variables, preview_data) VALUES
('alert_critical_slack', 'alert_critical', 'slack',
 '{
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Critical Alert: {{alert_name}}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Metric:*\n{{metric_name}}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Value:*\n{{metric_value}}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Threshold:*\n{{threshold}}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Time:*\n{{triggered_at}}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{{alert_description}}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Dashboard"
                    },
                    "url": "{{dashboard_url}}",
                    "style": "primary"
                }
            ]
        }
    ]
}',
 '["alert_name", "metric_name", "metric_value", "threshold", "triggered_at", "alert_description", "dashboard_url"]'::jsonb,
 '{"alert_name": "High Error Rate", "metric_name": "Error Rate", "metric_value": "15%", "threshold": "10%", "triggered_at": "2025-11-12 10:30:00", "alert_description": "Error rate exceeded threshold", "dashboard_url": "https://app.example.com/dashboard"}'::jsonb
);

-- In-app template for alert notifications
INSERT INTO analytics.notification_templates (template_name, notification_type, channel, body_template, variables, preview_data) VALUES
('alert_critical_in_app', 'alert_critical', 'in_app',
 '{"title": "{{alert_name}}", "message": "{{alert_description}}", "severity": "critical", "metric": "{{metric_name}}: {{metric_value}}", "action_url": "{{dashboard_url}}"}',
 '["alert_name", "alert_description", "metric_name", "metric_value", "dashboard_url"]'::jsonb,
 '{"alert_name": "High Error Rate", "alert_description": "Error rate exceeded threshold", "metric_name": "Error Rate", "metric_value": "15%", "dashboard_url": "/dashboard/errors"}'::jsonb
);

-- Email template for daily digest
INSERT INTO analytics.notification_templates (template_name, notification_type, channel, subject_template, body_template, variables, preview_data) VALUES
('digest_daily_email', 'digest_daily', 'email',
 '📊 Daily Analytics Summary - {{workspace_name}}',
 '<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
        .content { background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; }
        .metric-card { background: #f9fafb; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .metric-value { font-size: 28px; font-weight: bold; color: #2563eb; }
        .metric-label { color: #6b7280; font-size: 14px; }
        .change-positive { color: #10b981; }
        .change-negative { color: #ef4444; }
        .button { background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📊 Daily Analytics Summary</h2>
            <p>{{workspace_name}} - {{date}}</p>
        </div>
        <div class="content">
            <div class="metric-card">
                <div class="metric-label">Active Users</div>
                <div class="metric-value">{{active_users}}</div>
                <div class="change-positive">↑ {{active_users_change}}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Executions</div>
                <div class="metric-value">{{total_executions}}</div>
                <div class="change-positive">↑ {{executions_change}}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{{success_rate}}%</div>
            </div>
            <p>{{summary_text}}</p>
            <a href="{{dashboard_url}}" class="button">View Full Dashboard</a>
        </div>
    </div>
</body>
</html>',
 '["workspace_name", "date", "active_users", "active_users_change", "total_executions", "executions_change", "success_rate", "summary_text", "dashboard_url"]'::jsonb,
 '{"workspace_name": "Production", "date": "2025-11-12", "active_users": "1,234", "active_users_change": "12.5", "total_executions": "5,678", "executions_change": "8.3", "success_rate": "98.5", "summary_text": "Great day! Activity is up and performance remains strong.", "dashboard_url": "https://app.example.com/dashboard"}'::jsonb
);
