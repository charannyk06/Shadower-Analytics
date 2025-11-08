-- Daily user metrics materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_user_metrics AS
SELECT
    DATE(metric_date) as date,
    COUNT(DISTINCT user_id) as total_users,
    SUM(sessions_count) as total_sessions,
    SUM(executions_count) as total_executions,
    AVG(active_duration) as avg_active_duration
FROM user_metrics
GROUP BY DATE(metric_date);

CREATE UNIQUE INDEX ON mv_daily_user_metrics (date);

-- Daily agent metrics materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_agent_metrics AS
SELECT
    DATE(metric_date) as date,
    agent_id,
    SUM(total_executions) as total_executions,
    SUM(successful_executions) as successful_executions,
    SUM(failed_executions) as failed_executions,
    AVG(avg_duration) as avg_duration,
    CASE
        WHEN SUM(total_executions) > 0
        THEN (SUM(successful_executions)::FLOAT / SUM(total_executions)::FLOAT) * 100
        ELSE 0
    END as success_rate
FROM agent_metrics
GROUP BY DATE(metric_date), agent_id;

CREATE UNIQUE INDEX ON mv_daily_agent_metrics (date, agent_id);

-- Hourly execution stats materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_execution_stats AS
SELECT
    DATE_TRUNC('hour', started_at) as hour,
    COUNT(*) as total_executions,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'failure' THEN 1 END) as failed,
    AVG(duration) as avg_duration,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration) as p95_duration,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration) as p99_duration
FROM execution_logs
WHERE completed_at IS NOT NULL
GROUP BY DATE_TRUNC('hour', started_at);

CREATE UNIQUE INDEX ON mv_hourly_execution_stats (hour);
