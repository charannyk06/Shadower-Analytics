"""Celery tasks package."""

from src.tasks.aggregation import (
    hourly_rollup_task,
    daily_rollup_task,
    weekly_rollup_task,
    monthly_rollup_task,
    refresh_materialized_views_task,
    backfill_aggregations_task,
)
from src.tasks.maintenance import (
    cleanup_old_data_task,
    health_check_task,
    vacuum_tables_task,
    rebuild_indices_task,
)

__all__ = [
    'hourly_rollup_task',
    'daily_rollup_task',
    'weekly_rollup_task',
    'monthly_rollup_task',
    'refresh_materialized_views_task',
    'backfill_aggregations_task',
    'cleanup_old_data_task',
    'health_check_task',
    'vacuum_tables_task',
    'rebuild_indices_task',
]
