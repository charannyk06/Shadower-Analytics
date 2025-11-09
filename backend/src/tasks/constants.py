"""Shared constants for aggregation jobs."""

# Retention settings
DEFAULT_RETENTION_DAYS = 90

# Backfill limits
MAX_BACKFILL_PERIODS = 1000

# Whitelisted tables for maintenance operations
ALLOWED_VACUUM_TABLES = {
    'analytics.execution_metrics_hourly',
    'analytics.execution_metrics_daily',
    'analytics.user_activity_hourly',
    'analytics.credit_consumption_hourly',
}

ALLOWED_SCHEMAS = {'analytics'}

# Whitelisted materialized views that are safe to refresh
ALLOWED_MATERIALIZED_VIEWS = {
    "analytics.mv_daily_user_metrics",
    "analytics.mv_daily_agent_metrics",
    "analytics.mv_hourly_execution_stats",
    "analytics.mv_workspace_summary",
}
