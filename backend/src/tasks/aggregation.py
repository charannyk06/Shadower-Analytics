"""Aggregation Celery tasks."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict

from celery import Task
from src.celery_app import celery_app
from src.core.database import async_session_maker
from src.services.aggregation.rollup import (
    hourly_rollup,
    daily_rollup,
    weekly_rollup,
    monthly_rollup,
)
from src.services.aggregation.materialized import refresh_all_materialized_views
from src.core.config import settings

logger = logging.getLogger(__name__)


class AsyncDatabaseTask(Task):
    """Base task class that provides async database session handling."""

    def run_async(self, async_func, *args, **kwargs):
        """Run an async function synchronously."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))


@celery_app.task(
    name='tasks.aggregation.hourly_rollup',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def hourly_rollup_task(self, target_hour: Optional[str] = None) -> Dict:
    """Celery task for hourly rollup.

    Args:
        target_hour: ISO format datetime string for specific hour (optional)

    Returns:
        Dictionary with rollup results
    """
    if not settings.HOURLY_ROLLUP_ENABLED:
        logger.info("Hourly rollup is disabled via settings")
        return {'success': False, 'message': 'Hourly rollup disabled'}

    try:
        logger.info("Starting hourly rollup task")

        # Parse target_hour if provided
        target_datetime = None
        if target_hour:
            target_datetime = datetime.fromisoformat(target_hour)

        async def run_rollup():
            async with async_session_maker() as db:
                return await hourly_rollup(db, target_datetime)

        result = self.run_async(run_rollup)
        logger.info(f"Hourly rollup task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Hourly rollup task failed: {str(exc)}", exc_info=True)
        # Retry the task
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.aggregation.daily_rollup',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=600,  # 10 minutes
)
def daily_rollup_task(self, target_date: Optional[str] = None) -> Dict:
    """Celery task for daily rollup.

    Args:
        target_date: ISO format date string for specific date (optional)

    Returns:
        Dictionary with rollup results
    """
    if not settings.DAILY_ROLLUP_ENABLED:
        logger.info("Daily rollup is disabled via settings")
        return {'success': False, 'message': 'Daily rollup disabled'}

    try:
        logger.info("Starting daily rollup task")

        # Parse target_date if provided
        target_datetime = None
        if target_date:
            target_datetime = datetime.fromisoformat(target_date)

        async def run_rollup():
            async with async_session_maker() as db:
                return await daily_rollup(db, target_datetime)

        result = self.run_async(run_rollup)
        logger.info(f"Daily rollup task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Daily rollup task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.aggregation.weekly_rollup',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=900,  # 15 minutes
)
def weekly_rollup_task(self, target_week: Optional[str] = None) -> Dict:
    """Celery task for weekly rollup.

    Args:
        target_week: ISO format date string for week start (optional)

    Returns:
        Dictionary with rollup results
    """
    if not settings.WEEKLY_ROLLUP_ENABLED:
        logger.info("Weekly rollup is disabled via settings")
        return {'success': False, 'message': 'Weekly rollup disabled'}

    try:
        logger.info("Starting weekly rollup task")

        # Parse target_week if provided
        target_datetime = None
        if target_week:
            target_datetime = datetime.fromisoformat(target_week)

        async def run_rollup():
            async with async_session_maker() as db:
                return await weekly_rollup(db, target_datetime)

        result = self.run_async(run_rollup)
        logger.info(f"Weekly rollup task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Weekly rollup task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.aggregation.monthly_rollup',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=1800,  # 30 minutes
)
def monthly_rollup_task(self, target_month: Optional[str] = None) -> Dict:
    """Celery task for monthly rollup.

    Args:
        target_month: ISO format date string for month start (optional)

    Returns:
        Dictionary with rollup results
    """
    if not settings.MONTHLY_ROLLUP_ENABLED:
        logger.info("Monthly rollup is disabled via settings")
        return {'success': False, 'message': 'Monthly rollup disabled'}

    try:
        logger.info("Starting monthly rollup task")

        # Parse target_month if provided
        target_datetime = None
        if target_month:
            target_datetime = datetime.fromisoformat(target_month)

        async def run_rollup():
            async with async_session_maker() as db:
                return await monthly_rollup(db, target_datetime)

        result = self.run_async(run_rollup)
        logger.info(f"Monthly rollup task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Monthly rollup task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.aggregation.refresh_materialized_views',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=120,  # 2 minutes
)
def refresh_materialized_views_task(self) -> Dict:
    """Celery task to refresh materialized views.

    Returns:
        Dictionary with refresh results
    """
    try:
        logger.info("Starting materialized views refresh task")

        async def run_refresh():
            async with async_session_maker() as db:
                return await refresh_all_materialized_views(db)

        result = self.run_async(run_refresh)
        logger.info(f"Materialized views refresh completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Materialized views refresh failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.aggregation.backfill_aggregations',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=1,
)
def backfill_aggregations_task(
    self,
    start_date: str,
    end_date: str,
    granularity: str = 'hourly'
) -> Dict:
    """Backfill aggregations for a date range.

    Useful for historical data or fixing gaps in aggregations.

    Args:
        start_date: ISO format date string for start
        end_date: ISO format date string for end
        granularity: 'hourly' or 'daily'

    Returns:
        Dictionary with backfill results
    """
    try:
        logger.info(f"Starting backfill task: {start_date} to {end_date}, granularity: {granularity}")

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        results = []

        async def run_backfill():
            async with async_session_maker() as db:
                current = start_dt

                if granularity == 'hourly':
                    while current < end_dt:
                        result = await hourly_rollup(db, current)
                        results.append(result)
                        current += timedelta(hours=1)

                elif granularity == 'daily':
                    while current < end_dt:
                        result = await daily_rollup(db, current)
                        results.append(result)
                        current += timedelta(days=1)

                return {
                    'success': True,
                    'granularity': granularity,
                    'start_date': start_date,
                    'end_date': end_date,
                    'periods_processed': len(results),
                    'results': results
                }

        result = self.run_async(run_backfill)
        logger.info(f"Backfill task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Backfill task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)
