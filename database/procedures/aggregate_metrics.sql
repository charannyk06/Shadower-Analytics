-- =====================================================================
-- Procedure: aggregate_metrics.sql
-- Description: Aggregate daily and hourly metrics
-- Usage: psql -f database/procedures/aggregate_metrics.sql
-- =====================================================================

SET search_path TO analytics, public;

-- Aggregate metrics for yesterday (daily)
DO $$
DECLARE
    target_date DATE := CURRENT_DATE - 1;
BEGIN
    RAISE NOTICE 'Aggregating daily metrics for %', target_date;
    PERFORM analytics.aggregate_daily_metrics(target_date, NULL);
END $$;

-- Aggregate metrics for the last hour (hourly)
DO $$
DECLARE
    target_hour TIMESTAMPTZ := DATE_TRUNC('hour', NOW() - INTERVAL '1 hour');
BEGIN
    RAISE NOTICE 'Aggregating hourly metrics for %', target_hour;
    PERFORM analytics.aggregate_hourly_metrics(target_hour, NULL);
END $$;

-- Display summary
SELECT
    'Daily metrics aggregated for: ' || (CURRENT_DATE - 1)::TEXT as message
UNION ALL
SELECT
    'Hourly metrics aggregated for: ' || DATE_TRUNC('hour', NOW() - INTERVAL '1 hour')::TEXT;
