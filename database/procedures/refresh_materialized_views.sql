-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_user_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_agent_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_execution_stats;
END;
$$ LANGUAGE plpgsql;
