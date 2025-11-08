-- =====================================================================
-- Migration: 006_create_triggers.sql
-- Description: Create triggers for automatic data management
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Trigger Function: update_updated_at
-- Description: Automatically update the updated_at timestamp
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.update_updated_at IS 'Trigger function to automatically update updated_at timestamp';

-- =====================================================================
-- Apply updated_at trigger to tables
-- =====================================================================

CREATE TRIGGER update_daily_metrics_updated_at
    BEFORE UPDATE ON analytics.daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();

CREATE TRIGGER update_agent_performance_updated_at
    BEFORE UPDATE ON analytics.agent_performance
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();

CREATE TRIGGER update_user_cohorts_updated_at
    BEFORE UPDATE ON analytics.user_cohorts
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();

CREATE TRIGGER update_alert_rules_updated_at
    BEFORE UPDATE ON analytics.alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();

-- =====================================================================
-- Trigger Function: validate_alert_rule
-- Description: Validate alert rule configuration before insert/update
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.validate_alert_rule()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate threshold value is positive for certain metric types
    IF NEW.metric_type IN ('error_rate', 'response_time', 'active_users') THEN
        IF NEW.threshold_value < 0 THEN
            RAISE EXCEPTION 'Threshold value must be positive for metric type %', NEW.metric_type;
        END IF;
    END IF;

    -- Validate evaluation window
    IF NEW.evaluation_window_minutes < 1 OR NEW.evaluation_window_minutes > 1440 THEN
        RAISE EXCEPTION 'Evaluation window must be between 1 and 1440 minutes';
    END IF;

    -- Validate notification channels format
    IF NEW.notification_channels IS NOT NULL THEN
        IF jsonb_typeof(NEW.notification_channels) != 'array' THEN
            RAISE EXCEPTION 'notification_channels must be a JSON array';
        END IF;
    END IF;

    -- Validate notification recipients format
    IF NEW.notification_recipients IS NOT NULL THEN
        IF jsonb_typeof(NEW.notification_recipients) != 'array' THEN
            RAISE EXCEPTION 'notification_recipients must be a JSON array';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.validate_alert_rule IS 'Validate alert rule configuration';

CREATE TRIGGER validate_alert_rule_before_insert
    BEFORE INSERT ON analytics.alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_alert_rule();

CREATE TRIGGER validate_alert_rule_before_update
    BEFORE UPDATE ON analytics.alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_alert_rule();

-- =====================================================================
-- Trigger Function: log_alert_trigger
-- Description: Log when an alert is triggered
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.log_alert_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Update the alert rule with last triggered time
    UPDATE analytics.alert_rules
    SET
        last_triggered_at = NEW.triggered_at,
        trigger_count = trigger_count + 1
    WHERE id = NEW.alert_rule_id;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.log_alert_trigger IS 'Update alert rule metadata when alert is triggered';

CREATE TRIGGER log_alert_trigger_after_insert
    AFTER INSERT ON analytics.alert_history
    FOR EACH ROW
    EXECUTE FUNCTION analytics.log_alert_trigger();

-- =====================================================================
-- Trigger Function: validate_cohort_data
-- Description: Validate user cohort data before insert/update
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.validate_cohort_data()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate retention_data is a JSON object
    IF jsonb_typeof(NEW.retention_data) != 'object' THEN
        RAISE EXCEPTION 'retention_data must be a JSON object';
    END IF;

    -- Validate initial_users is positive
    IF NEW.initial_users < 0 THEN
        RAISE EXCEPTION 'initial_users must be a positive number';
    END IF;

    -- Validate cohort_date is not in the future
    IF NEW.cohort_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'cohort_date cannot be in the future';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.validate_cohort_data IS 'Validate user cohort data';

CREATE TRIGGER validate_cohort_data_before_insert
    BEFORE INSERT ON analytics.user_cohorts
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_cohort_data();

CREATE TRIGGER validate_cohort_data_before_update
    BEFORE UPDATE ON analytics.user_cohorts
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_cohort_data();

-- =====================================================================
-- Trigger Function: validate_metric_data
-- Description: Validate metric data before insert/update
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.validate_metric_data()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate metric_date is not in the future
    IF NEW.metric_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'metric_date cannot be in the future';
    END IF;

    -- Validate counts are non-negative
    IF NEW.total_runs < 0 OR NEW.successful_runs < 0 OR NEW.failed_runs < 0 THEN
        RAISE EXCEPTION 'Run counts cannot be negative';
    END IF;

    -- Validate success + fail doesn't exceed total
    IF NEW.successful_runs + NEW.failed_runs > NEW.total_runs THEN
        RAISE EXCEPTION 'Sum of successful and failed runs cannot exceed total runs';
    END IF;

    -- Validate credits are non-negative
    IF NEW.total_credits_consumed < 0 THEN
        RAISE EXCEPTION 'Credits consumed cannot be negative';
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.validate_metric_data IS 'Validate daily metric data';

CREATE TRIGGER validate_daily_metrics_before_insert
    BEFORE INSERT ON analytics.daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_metric_data();

CREATE TRIGGER validate_daily_metrics_before_update
    BEFORE UPDATE ON analytics.daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION analytics.validate_metric_data();

-- =====================================================================
-- Trigger Function: sanitize_user_activity
-- Description: Sanitize user activity data before insert
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.sanitize_user_activity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Ensure metadata is valid JSON
    IF NEW.metadata IS NULL THEN
        NEW.metadata = '{}'::jsonb;
    END IF;

    -- Truncate long text fields to prevent bloat
    IF LENGTH(NEW.user_agent) > 500 THEN
        NEW.user_agent = LEFT(NEW.user_agent, 500);
    END IF;

    IF LENGTH(NEW.referrer) > 500 THEN
        NEW.referrer = LEFT(NEW.referrer, 500);
    END IF;

    IF LENGTH(NEW.page_path) > 255 THEN
        NEW.page_path = LEFT(NEW.page_path, 255);
    END IF;

    -- Set created_at if not provided
    IF NEW.created_at IS NULL THEN
        NEW.created_at = NOW();
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.sanitize_user_activity IS 'Sanitize and normalize user activity data';

CREATE TRIGGER sanitize_user_activity_before_insert
    BEFORE INSERT ON analytics.user_activity
    FOR EACH ROW
    EXECUTE FUNCTION analytics.sanitize_user_activity();

-- =====================================================================
-- Trigger Function: update_alert_history_status
-- Description: Update alert notification status
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.update_alert_history_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- If acknowledged_by is set, update status to acknowledged
    IF NEW.acknowledged_by IS NOT NULL AND OLD.acknowledged_by IS NULL THEN
        NEW.notification_status = 'acknowledged';
        NEW.acknowledged_at = NOW();
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION analytics.update_alert_history_status IS 'Automatically update alert status when acknowledged';

CREATE TRIGGER update_alert_history_status_before_update
    BEFORE UPDATE ON analytics.alert_history
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_alert_history_status();
