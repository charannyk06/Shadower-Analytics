-- =====================================================================
-- Migration: 005_create_functions.sql
-- Description: Create analytics functions and procedures
-- Created: 2025-11-08
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Function: refresh_all_materialized_views
-- Description: Refresh all materialized views (use CONCURRENTLY for production)
-- Usage: SELECT analytics.refresh_all_materialized_views();
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.refresh_all_materialized_views()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh all materialized views concurrently
    -- Concurrent refresh requires unique indexes
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_active_users;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_top_agents;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_workspace_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_error_trends;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_agent_usage_trends;

    RAISE NOTICE 'All materialized views refreshed successfully at %', NOW();
END;
$$;

COMMENT ON FUNCTION analytics.refresh_all_materialized_views IS 'Refresh all analytics materialized views concurrently';

-- =====================================================================
-- Function: calculate_percentiles
-- Description: Calculate percentile values from an array of numbers
-- Usage: SELECT analytics.calculate_percentiles(ARRAY[1,2,3,4,5], ARRAY[0.5, 0.95, 0.99]);
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.calculate_percentiles(
    values NUMERIC[],
    percentiles NUMERIC[]
)
RETURNS NUMERIC[]
LANGUAGE plpgsql
AS $$
DECLARE
    result NUMERIC[];
    p NUMERIC;
    sorted_values NUMERIC[];
    array_length INTEGER;
    position INTEGER;
BEGIN
    -- Sort the input values
    sorted_values := ARRAY(SELECT unnest(values) ORDER BY 1);
    array_length := array_length(sorted_values, 1);

    -- Calculate each percentile
    FOREACH p IN ARRAY percentiles LOOP
        IF array_length = 0 THEN
            result := array_append(result, NULL);
        ELSE
            position := CEIL(p * array_length)::INTEGER;
            position := GREATEST(1, LEAST(position, array_length));
            result := array_append(result, sorted_values[position]);
        END IF;
    END LOOP;

    RETURN result;
END;
$$;

COMMENT ON FUNCTION analytics.calculate_percentiles IS 'Calculate percentile values from an array of numbers';

-- =====================================================================
-- Function: aggregate_daily_metrics
-- Description: Aggregate metrics for a specific date and workspace
-- Usage: SELECT analytics.aggregate_daily_metrics('2025-11-08', NULL);
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.aggregate_daily_metrics(
    target_date DATE,
    target_workspace_id UUID DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    rows_affected INTEGER;
BEGIN
    -- Aggregate data from user_activity into daily_metrics
    INSERT INTO analytics.daily_metrics (
        metric_date,
        workspace_id,
        active_users,
        total_sessions,
        total_errors
    )
    SELECT
        target_date,
        workspace_id,
        COUNT(DISTINCT user_id) as active_users,
        COUNT(DISTINCT session_id) as total_sessions,
        COUNT(*) FILTER (WHERE event_type = 'error') as total_errors
    FROM analytics.user_activity
    WHERE DATE(created_at) = target_date
        AND (target_workspace_id IS NULL OR workspace_id = target_workspace_id)
    GROUP BY workspace_id
    ON CONFLICT (metric_date, workspace_id)
    DO UPDATE SET
        active_users = EXCLUDED.active_users,
        total_sessions = EXCLUDED.total_sessions,
        total_errors = EXCLUDED.total_errors,
        updated_at = NOW();

    GET DIAGNOSTICS rows_affected = ROW_COUNT;

    RAISE NOTICE 'Aggregated daily metrics for % (% rows affected)', target_date, rows_affected;
END;
$$;

COMMENT ON FUNCTION analytics.aggregate_daily_metrics IS 'Aggregate daily metrics from raw activity data';

-- =====================================================================
-- Function: aggregate_hourly_metrics
-- Description: Aggregate metrics for a specific hour
-- Usage: SELECT analytics.aggregate_hourly_metrics('2025-11-08 14:00:00');
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.aggregate_hourly_metrics(
    target_hour TIMESTAMPTZ,
    target_workspace_id UUID DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    hour_start TIMESTAMPTZ;
    hour_end TIMESTAMPTZ;
    rows_affected INTEGER;
BEGIN
    -- Round to hour boundary
    hour_start := DATE_TRUNC('hour', target_hour);
    hour_end := hour_start + INTERVAL '1 hour';

    -- Aggregate hourly data
    INSERT INTO analytics.hourly_metrics (
        metric_hour,
        workspace_id,
        active_users,
        total_runs
    )
    SELECT
        hour_start,
        workspace_id,
        COUNT(DISTINCT user_id) as active_users,
        COUNT(*) FILTER (WHERE event_type = 'agent_run') as total_runs
    FROM analytics.user_activity
    WHERE created_at >= hour_start
        AND created_at < hour_end
        AND (target_workspace_id IS NULL OR workspace_id = target_workspace_id)
    GROUP BY workspace_id
    ON CONFLICT (metric_hour, workspace_id)
    DO UPDATE SET
        active_users = EXCLUDED.active_users,
        total_runs = EXCLUDED.total_runs,
        created_at = NOW();

    GET DIAGNOSTICS rows_affected = ROW_COUNT;

    RAISE NOTICE 'Aggregated hourly metrics for % (% rows affected)', hour_start, rows_affected;
END;
$$;

COMMENT ON FUNCTION analytics.aggregate_hourly_metrics IS 'Aggregate hourly metrics from raw activity data';

-- =====================================================================
-- Function: cleanup_old_data
-- Description: Remove old analytics data based on retention policy
-- Usage: SELECT analytics.cleanup_old_data();
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.cleanup_old_data()
RETURNS TABLE (
    table_name TEXT,
    rows_deleted BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    activity_deleted BIGINT;
    hourly_deleted BIGINT;
    alert_history_deleted BIGINT;
BEGIN
    -- Keep raw activity for 90 days
    DELETE FROM analytics.user_activity
    WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS activity_deleted = ROW_COUNT;

    -- Keep hourly metrics for 30 days
    DELETE FROM analytics.hourly_metrics
    WHERE metric_hour < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS hourly_deleted = ROW_COUNT;

    -- Keep alert history for 180 days
    DELETE FROM analytics.alert_history
    WHERE triggered_at < NOW() - INTERVAL '180 days';
    GET DIAGNOSTICS alert_history_deleted = ROW_COUNT;

    -- Return summary
    RETURN QUERY
    SELECT 'user_activity'::TEXT, activity_deleted
    UNION ALL
    SELECT 'hourly_metrics'::TEXT, hourly_deleted
    UNION ALL
    SELECT 'alert_history'::TEXT, alert_history_deleted;
END;
$$;

COMMENT ON FUNCTION analytics.cleanup_old_data IS 'Clean up old data according to retention policy';

-- =====================================================================
-- Function: get_workspace_metrics
-- Description: Get comprehensive metrics for a workspace
-- Usage: SELECT * FROM analytics.get_workspace_metrics('workspace-uuid');
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.get_workspace_metrics(
    p_workspace_id UUID,
    p_start_date DATE DEFAULT CURRENT_DATE - 30,
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    metric_date DATE,
    active_users INTEGER,
    total_runs INTEGER,
    successful_runs INTEGER,
    failed_runs INTEGER,
    success_rate NUMERIC,
    total_credits NUMERIC,
    avg_runtime NUMERIC,
    unique_agents INTEGER
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dm.metric_date,
        dm.active_users,
        dm.total_runs,
        dm.successful_runs,
        dm.failed_runs,
        COALESCE(
            (dm.successful_runs::NUMERIC / NULLIF(dm.total_runs, 0)) * 100,
            0
        ) as success_rate,
        dm.total_credits_consumed,
        dm.avg_runtime_seconds,
        dm.unique_agents_run
    FROM analytics.daily_metrics dm
    WHERE dm.workspace_id = p_workspace_id
        AND dm.metric_date >= p_start_date
        AND dm.metric_date <= p_end_date
    ORDER BY dm.metric_date DESC;
END;
$$;

COMMENT ON FUNCTION analytics.get_workspace_metrics IS 'Get comprehensive metrics for a workspace over a date range';

-- =====================================================================
-- Function: get_agent_insights
-- Description: Get detailed insights for a specific agent
-- Usage: SELECT * FROM analytics.get_agent_insights('agent-uuid', 30);
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.get_agent_insights(
    p_agent_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_runs BIGINT,
    success_rate NUMERIC,
    avg_runtime NUMERIC,
    p50_runtime NUMERIC,
    p95_runtime NUMERIC,
    p99_runtime NUMERIC,
    total_credits NUMERIC,
    unique_users BIGINT,
    trend_direction TEXT,
    top_error_types JSONB
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    current_period_runs BIGINT;
    previous_period_runs BIGINT;
BEGIN
    RETURN QUERY
    WITH agent_stats AS (
        SELECT
            SUM(ap.total_runs) as total_runs,
            COALESCE(
                (SUM(ap.successful_runs)::NUMERIC / NULLIF(SUM(ap.total_runs), 0)) * 100,
                0
            ) as success_rate,
            AVG(ap.avg_runtime_seconds) as avg_runtime,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ap.p50_runtime_seconds) as p50_runtime,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ap.p95_runtime_seconds) as p95_runtime,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ap.p99_runtime_seconds) as p99_runtime,
            SUM(ap.total_credits) as total_credits,
            SUM(ap.unique_users) as unique_users,
            jsonb_object_agg(
                error_key,
                error_count
            ) FILTER (WHERE error_key IS NOT NULL) as top_error_types
        FROM analytics.agent_performance ap,
             LATERAL (
                 SELECT key as error_key, value::INTEGER as error_count
                 FROM jsonb_each_text(ap.error_types)
                 ORDER BY value::INTEGER DESC
                 LIMIT 5
             ) errors
        WHERE ap.agent_id = p_agent_id
            AND ap.metric_date >= CURRENT_DATE - p_days
    ),
    trend_calc AS (
        SELECT
            SUM(total_runs) FILTER (
                WHERE metric_date >= CURRENT_DATE - (p_days / 2)
            ) as current_runs,
            SUM(total_runs) FILTER (
                WHERE metric_date < CURRENT_DATE - (p_days / 2)
            ) as previous_runs
        FROM analytics.agent_performance
        WHERE agent_id = p_agent_id
            AND metric_date >= CURRENT_DATE - p_days
    )
    SELECT
        stats.total_runs,
        stats.success_rate,
        stats.avg_runtime,
        stats.p50_runtime,
        stats.p95_runtime,
        stats.p99_runtime,
        stats.total_credits,
        stats.unique_users,
        CASE
            WHEN trend.current_runs > trend.previous_runs THEN 'growing'
            WHEN trend.current_runs < trend.previous_runs THEN 'declining'
            ELSE 'stable'
        END as trend_direction,
        COALESCE(stats.top_error_types, '{}'::jsonb) as top_error_types
    FROM agent_stats stats
    CROSS JOIN trend_calc trend;
END;
$$;

COMMENT ON FUNCTION analytics.get_agent_insights IS 'Get detailed performance insights for a specific agent';

-- =====================================================================
-- Function: evaluate_alert_rules
-- Description: Evaluate all active alert rules and trigger alerts
-- Usage: SELECT analytics.evaluate_alert_rules();
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.evaluate_alert_rules()
RETURNS TABLE (
    alert_rule_id UUID,
    triggered BOOLEAN,
    metric_value NUMERIC,
    threshold_value NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    rule RECORD;
    current_value NUMERIC;
    should_trigger BOOLEAN;
BEGIN
    -- Loop through all active alert rules
    FOR rule IN
        SELECT * FROM analytics.alert_rules
        WHERE is_active = true
    LOOP
        -- Get current metric value based on metric type
        -- This is a simplified version - in production, you'd have
        -- specific logic for each metric type
        current_value := 0; -- Placeholder

        -- Evaluate condition
        should_trigger := CASE rule.condition
            WHEN 'greater_than' THEN current_value > rule.threshold_value
            WHEN 'less_than' THEN current_value < rule.threshold_value
            WHEN 'equals' THEN current_value = rule.threshold_value
            WHEN 'not_equals' THEN current_value != rule.threshold_value
            ELSE FALSE
        END;

        -- If triggered, insert into alert history
        IF should_trigger THEN
            INSERT INTO analytics.alert_history (
                alert_rule_id,
                workspace_id,
                metric_value,
                threshold_value,
                triggered_at
            ) VALUES (
                rule.id,
                rule.workspace_id,
                current_value,
                rule.threshold_value,
                NOW()
            );

            -- Update alert rule
            UPDATE analytics.alert_rules
            SET
                last_triggered_at = NOW(),
                trigger_count = trigger_count + 1
            WHERE id = rule.id;
        END IF;

        -- Return result
        RETURN QUERY
        SELECT rule.id, should_trigger, current_value, rule.threshold_value;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION analytics.evaluate_alert_rules IS 'Evaluate all active alert rules and create alert history entries';
