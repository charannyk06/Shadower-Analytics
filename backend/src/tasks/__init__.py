"""Celery tasks package."""

from src.tasks.aggregation import (
    hourly_rollup_task,
    daily_rollup_task,
    weekly_rollup_task,
    refresh_materialized_views_task,
)
from src.tasks.maintenance import (
    cleanup_old_data_task,
    health_check_task,
)

__all__ = [
    'hourly_rollup_task',
    'daily_rollup_task',
    'weekly_rollup_task',
    'refresh_materialized_views_task',
    'cleanup_old_data_task',
    'health_check_task',
]
