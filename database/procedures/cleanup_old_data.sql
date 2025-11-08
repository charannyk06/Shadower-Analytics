-- =====================================================================
-- Procedure: cleanup_old_data.sql
-- Description: Clean up old analytics data based on retention policy
-- Usage: psql -f database/procedures/cleanup_old_data.sql
-- =====================================================================

SET search_path TO analytics, public;

-- Run cleanup
DO $$
BEGIN
    RAISE NOTICE 'Starting data cleanup...';
    RAISE NOTICE 'Retention policy:';
    RAISE NOTICE '  - user_activity: 90 days';
    RAISE NOTICE '  - hourly_metrics: 30 days';
    RAISE NOTICE '  - alert_history: 180 days';
END $$;

-- Execute cleanup and display results
SELECT
    table_name,
    rows_deleted,
    pg_size_pretty(rows_deleted * 1024::BIGINT) as estimated_space_freed
FROM analytics.cleanup_old_data()
ORDER BY rows_deleted DESC;

-- Display current table sizes
SELECT
    'user_activity' as table_name,
    pg_size_pretty(pg_total_relation_size('analytics.user_activity')) as total_size,
    (SELECT COUNT(*) FROM analytics.user_activity) as row_count
UNION ALL
SELECT
    'hourly_metrics',
    pg_size_pretty(pg_total_relation_size('analytics.hourly_metrics')),
    (SELECT COUNT(*) FROM analytics.hourly_metrics)
UNION ALL
SELECT
    'alert_history',
    pg_size_pretty(pg_total_relation_size('analytics.alert_history')),
    (SELECT COUNT(*) FROM analytics.alert_history);
