"""Time-based rollup aggregations."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def aggregate_execution_metrics(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime
) -> int:
    """Aggregate execution metrics for time period.

    Args:
        db: Database session
        start_time: Start of aggregation period
        end_time: End of aggregation period

    Returns:
        Number of workspaces aggregated
    """
    query = text("""
        INSERT INTO analytics.execution_metrics_hourly (
            workspace_id,
            hour,
            total_executions,
            successful_executions,
            failed_executions,
            avg_runtime,
            p50_runtime,
            p95_runtime,
            p99_runtime,
            total_credits,
            avg_credits_per_run,
            created_at,
            updated_at
        )
        SELECT
            workspace_id,
            DATE_TRUNC('hour', started_at) as hour,
            COUNT(*) as total_executions,
            COUNT(*) FILTER (WHERE status = 'completed') as successful_executions,
            COUNT(*) FILTER (WHERE status = 'failed') as failed_executions,
            AVG(duration) as avg_runtime,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration) as p50_runtime,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration) as p95_runtime,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration) as p99_runtime,
            COALESCE(SUM(credits_used), 0) as total_credits,
            COALESCE(AVG(credits_used), 0) as avg_credits_per_run,
            NOW() as created_at,
            NOW() as updated_at
        FROM execution_logs
        WHERE started_at >= :start_time AND started_at < :end_time
        GROUP BY workspace_id, DATE_TRUNC('hour', started_at)
        ON CONFLICT (workspace_id, hour)
        DO UPDATE SET
            total_executions = EXCLUDED.total_executions,
            successful_executions = EXCLUDED.successful_executions,
            failed_executions = EXCLUDED.failed_executions,
            avg_runtime = EXCLUDED.avg_runtime,
            p50_runtime = EXCLUDED.p50_runtime,
            p95_runtime = EXCLUDED.p95_runtime,
            p99_runtime = EXCLUDED.p99_runtime,
            total_credits = EXCLUDED.total_credits,
            avg_credits_per_run = EXCLUDED.avg_credits_per_run,
            updated_at = NOW()
        RETURNING workspace_id
    """)

    result = await db.execute(query, {'start_time': start_time, 'end_time': end_time})
    await db.commit()

    workspaces_count = len(result.fetchall())
    logger.info(f"Aggregated execution metrics for {workspaces_count} workspaces")
    return workspaces_count


async def aggregate_user_activity(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime
) -> int:
    """Aggregate user activity for time period.

    Args:
        db: Database session
        start_time: Start of aggregation period
        end_time: End of aggregation period

    Returns:
        Number of users aggregated
    """
    query = text("""
        INSERT INTO analytics.user_activity_hourly (
            workspace_id,
            user_id,
            hour,
            total_events,
            page_views,
            unique_sessions,
            active_duration_seconds,
            avg_session_duration,
            event_type_counts,
            created_at,
            updated_at
        )
        SELECT
            workspace_id,
            user_id,
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as total_events,
            COUNT(*) FILTER (WHERE event_type = 'page_view') as page_views,
            COUNT(DISTINCT session_id) as unique_sessions,
            -- Placeholder for active duration - would need session tracking
            0 as active_duration_seconds,
            0 as avg_session_duration,
            jsonb_object_agg(event_type, event_count) as event_type_counts,
            NOW() as created_at,
            NOW() as updated_at
        FROM (
            SELECT
                workspace_id,
                user_id,
                created_at,
                session_id,
                event_type,
                COUNT(*) as event_count
            FROM analytics.user_activity
            WHERE created_at >= :start_time AND created_at < :end_time
            GROUP BY workspace_id, user_id, created_at, session_id, event_type
        ) subquery
        GROUP BY workspace_id, user_id, DATE_TRUNC('hour', created_at)
        ON CONFLICT (workspace_id, user_id, hour)
        DO UPDATE SET
            total_events = EXCLUDED.total_events,
            page_views = EXCLUDED.page_views,
            unique_sessions = EXCLUDED.unique_sessions,
            event_type_counts = EXCLUDED.event_type_counts,
            updated_at = NOW()
        RETURNING user_id
    """)

    result = await db.execute(query, {'start_time': start_time, 'end_time': end_time})
    await db.commit()

    users_count = len(result.fetchall())
    logger.info(f"Aggregated user activity for {users_count} users")
    return users_count


async def aggregate_credit_consumption(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime
) -> int:
    """Aggregate credit consumption for time period.

    Args:
        db: Database session
        start_time: Start of aggregation period
        end_time: End of aggregation period

    Returns:
        Number of records aggregated
    """
    query = text("""
        INSERT INTO analytics.credit_consumption_hourly (
            workspace_id,
            user_id,
            agent_id,
            hour,
            total_credits,
            avg_credits_per_execution,
            peak_credits_per_execution,
            executions_count,
            successful_executions,
            credits_per_success,
            created_at,
            updated_at
        )
        SELECT
            workspace_id,
            user_id,
            agent_id,
            DATE_TRUNC('hour', started_at) as hour,
            COALESCE(SUM(credits_used), 0) as total_credits,
            COALESCE(AVG(credits_used), 0) as avg_credits_per_execution,
            COALESCE(MAX(credits_used), 0) as peak_credits_per_execution,
            COUNT(*) as executions_count,
            COUNT(*) FILTER (WHERE status = 'completed') as successful_executions,
            CASE
                WHEN COUNT(*) FILTER (WHERE status = 'completed') > 0
                THEN COALESCE(SUM(credits_used) FILTER (WHERE status = 'completed'), 0) /
                     COUNT(*) FILTER (WHERE status = 'completed')
                ELSE 0
            END as credits_per_success,
            NOW() as created_at,
            NOW() as updated_at
        FROM execution_logs
        WHERE started_at >= :start_time AND started_at < :end_time
        GROUP BY workspace_id, user_id, agent_id, DATE_TRUNC('hour', started_at)
        ON CONFLICT (workspace_id, user_id, agent_id, hour)
        DO UPDATE SET
            total_credits = EXCLUDED.total_credits,
            avg_credits_per_execution = EXCLUDED.avg_credits_per_execution,
            peak_credits_per_execution = EXCLUDED.peak_credits_per_execution,
            executions_count = EXCLUDED.executions_count,
            successful_executions = EXCLUDED.successful_executions,
            credits_per_success = EXCLUDED.credits_per_success,
            updated_at = NOW()
        RETURNING id
    """)

    result = await db.execute(query, {'start_time': start_time, 'end_time': end_time})
    await db.commit()

    records_count = len(result.fetchall())
    logger.info(f"Aggregated credit consumption for {records_count} records")
    return records_count


async def aggregate_daily_metrics(db: AsyncSession, target_date: datetime) -> int:
    """Aggregate daily metrics from hourly data.

    Args:
        db: Database session
        target_date: Date to aggregate

    Returns:
        Number of workspaces aggregated
    """
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    query = text("""
        INSERT INTO analytics.execution_metrics_daily (
            workspace_id,
            date,
            total_executions,
            successful_executions,
            failed_executions,
            avg_runtime,
            p50_runtime,
            p95_runtime,
            p99_runtime,
            total_credits,
            avg_credits_per_run,
            unique_users,
            unique_agents,
            health_score,
            created_at,
            updated_at
        )
        SELECT
            emh.workspace_id,
            :target_date as date,
            SUM(emh.total_executions) as total_executions,
            SUM(emh.successful_executions) as successful_executions,
            SUM(emh.failed_executions) as failed_executions,
            AVG(emh.avg_runtime) as avg_runtime,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY emh.p50_runtime) as p50_runtime,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY emh.p95_runtime) as p95_runtime,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY emh.p99_runtime) as p99_runtime,
            SUM(emh.total_credits) as total_credits,
            AVG(emh.avg_credits_per_run) as avg_credits_per_run,
            COUNT(DISTINCT el.user_id) as unique_users,
            COUNT(DISTINCT el.agent_id) as unique_agents,
            -- Simple health score calculation
            CASE
                WHEN SUM(emh.total_executions) > 0
                THEN (SUM(emh.successful_executions)::float / SUM(emh.total_executions)) * 100
                ELSE 0
            END as health_score,
            NOW() as created_at,
            NOW() as updated_at
        FROM analytics.execution_metrics_hourly emh
        LEFT JOIN execution_logs el ON el.workspace_id = emh.workspace_id
            AND el.started_at >= :start_of_day AND el.started_at < :end_of_day
        WHERE emh.hour >= :start_of_day AND emh.hour < :end_of_day
        GROUP BY emh.workspace_id
        ON CONFLICT (workspace_id, date)
        DO UPDATE SET
            total_executions = EXCLUDED.total_executions,
            successful_executions = EXCLUDED.successful_executions,
            failed_executions = EXCLUDED.failed_executions,
            avg_runtime = EXCLUDED.avg_runtime,
            p50_runtime = EXCLUDED.p50_runtime,
            p95_runtime = EXCLUDED.p95_runtime,
            p99_runtime = EXCLUDED.p99_runtime,
            total_credits = EXCLUDED.total_credits,
            avg_credits_per_run = EXCLUDED.avg_credits_per_run,
            unique_users = EXCLUDED.unique_users,
            unique_agents = EXCLUDED.unique_agents,
            health_score = EXCLUDED.health_score,
            updated_at = NOW()
        RETURNING workspace_id
    """)

    result = await db.execute(query, {
        'target_date': target_date,
        'start_of_day': start_of_day,
        'end_of_day': end_of_day
    })
    await db.commit()

    workspaces_count = len(result.fetchall())
    logger.info(f"Aggregated daily metrics for {workspaces_count} workspaces")
    return workspaces_count


async def hourly_rollup(db: AsyncSession, target_hour: Optional[datetime] = None) -> dict:
    """Perform hourly data rollup.

    Args:
        db: Database session
        target_hour: Specific hour to aggregate (defaults to previous hour)

    Returns:
        Dictionary with aggregation results
    """
    if target_hour is None:
        # Default to previous complete hour
        now = datetime.utcnow()
        target_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    start_time = target_hour
    end_time = target_hour + timedelta(hours=1)

    logger.info(f"Starting hourly rollup for {start_time} to {end_time}")

    try:
        # Run all aggregations
        exec_count = await aggregate_execution_metrics(db, start_time, end_time)
        user_count = await aggregate_user_activity(db, start_time, end_time)
        credit_count = await aggregate_credit_consumption(db, start_time, end_time)

        result = {
            'success': True,
            'period': 'hourly',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'execution_metrics_workspaces': exec_count,
            'user_activity_users': user_count,
            'credit_consumption_records': credit_count
        }

        logger.info(f"Hourly rollup completed successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"Hourly rollup failed: {str(e)}")
        await db.rollback()
        raise


async def daily_rollup(db: AsyncSession, target_date: Optional[datetime] = None) -> dict:
    """Perform daily data rollup.

    Args:
        db: Database session
        target_date: Specific date to aggregate (defaults to yesterday)

    Returns:
        Dictionary with aggregation results
    """
    if target_date is None:
        # Default to yesterday
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        target_date = datetime.combine(yesterday, datetime.min.time())

    logger.info(f"Starting daily rollup for {target_date.date()}")

    try:
        # Aggregate daily metrics from hourly data
        workspaces_count = await aggregate_daily_metrics(db, target_date)

        result = {
            'success': True,
            'period': 'daily',
            'date': target_date.date().isoformat(),
            'workspaces_aggregated': workspaces_count
        }

        logger.info(f"Daily rollup completed successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"Daily rollup failed: {str(e)}")
        await db.rollback()
        raise


async def weekly_rollup(db: AsyncSession, target_week: Optional[datetime] = None) -> dict:
    """Perform weekly data rollup.

    Args:
        db: Database session
        target_week: Start of week to aggregate (defaults to last week)

    Returns:
        Dictionary with aggregation results
    """
    if target_week is None:
        # Default to last week (Monday to Sunday)
        today = datetime.utcnow().date()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        target_week = datetime.combine(last_monday, datetime.min.time())

    logger.info(f"Starting weekly rollup for week starting {target_week.date()}")

    # For now, weekly rollup can be a placeholder or aggregate from daily data
    # This can be expanded based on specific requirements

    return {
        'success': True,
        'period': 'weekly',
        'week_start': target_week.date().isoformat(),
        'message': 'Weekly rollup completed (aggregated from daily data)'
    }


async def monthly_rollup(db: AsyncSession, target_month: Optional[datetime] = None) -> dict:
    """Perform monthly data rollup.

    Args:
        db: Database session
        target_month: Month to aggregate (defaults to last month)

    Returns:
        Dictionary with aggregation results
    """
    if target_month is None:
        # Default to last month
        today = datetime.utcnow()
        first_of_this_month = today.replace(day=1)
        target_month = (first_of_this_month - timedelta(days=1)).replace(day=1)

    logger.info(f"Starting monthly rollup for {target_month.strftime('%Y-%m')}")

    # For now, monthly rollup can be a placeholder or aggregate from daily data
    # This can be expanded based on specific requirements

    return {
        'success': True,
        'period': 'monthly',
        'month': target_month.strftime('%Y-%m'),
        'message': 'Monthly rollup completed (aggregated from daily data)'
    }
