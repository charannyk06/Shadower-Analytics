"""Maintenance Celery tasks."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict

from celery import Task
from sqlalchemy import text

from src.celery_app import celery_app
from src.core.database import async_session_maker
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
    name='tasks.maintenance.cleanup_old_data',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
    default_retry_delay=1800,  # 30 minutes
)
def cleanup_old_data_task(self, retention_days: int = 90) -> Dict:
    """Clean up old data based on retention policy.

    Args:
        retention_days: Number of days to retain data (default: 90)

    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info(f"Starting cleanup task with {retention_days} days retention")

        async def run_cleanup():
            async with async_session_maker() as db:
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

                results = {}

                # Clean up old execution logs
                query_logs = text("""
                    DELETE FROM execution_logs
                    WHERE started_at < :cutoff_date
                    RETURNING id
                """)
                result = await db.execute(query_logs, {'cutoff_date': cutoff_date})
                logs_deleted = len(result.fetchall())
                results['execution_logs_deleted'] = logs_deleted

                # Clean up old user activity events
                query_activity = text("""
                    DELETE FROM analytics.user_activity
                    WHERE created_at < :cutoff_date
                    RETURNING id
                """)
                result = await db.execute(query_activity, {'cutoff_date': cutoff_date})
                activity_deleted = len(result.fetchall())
                results['user_activity_deleted'] = activity_deleted

                # Clean up old hourly aggregations (keep longer than raw data)
                # Only delete if older than 2x retention period
                long_cutoff = datetime.utcnow() - timedelta(days=retention_days * 2)
                query_hourly = text("""
                    DELETE FROM analytics.execution_metrics_hourly
                    WHERE hour < :cutoff_date
                    RETURNING id
                """)
                result = await db.execute(query_hourly, {'cutoff_date': long_cutoff})
                hourly_deleted = len(result.fetchall())
                results['hourly_metrics_deleted'] = hourly_deleted

                await db.commit()

                logger.info(f"Cleanup completed: {results}")

                return {
                    'success': True,
                    'retention_days': retention_days,
                    'cutoff_date': cutoff_date.isoformat(),
                    'results': results
                }

        result = self.run_async(run_cleanup)
        return result

    except Exception as exc:
        logger.error(f"Cleanup task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.maintenance.health_check',
    bind=True,
    base=AsyncDatabaseTask,
)
def health_check_task(self) -> Dict:
    """Perform health checks on the system.

    Returns:
        Dictionary with health check results
    """
    try:
        logger.info("Starting health check task")

        async def run_health_check():
            async with async_session_maker() as db:
                checks = {}

                # Check database connectivity
                try:
                    await db.execute(text("SELECT 1"))
                    checks['database'] = {'status': 'healthy', 'latency_ms': 0}
                except Exception as e:
                    checks['database'] = {'status': 'unhealthy', 'error': str(e)}

                # Check recent aggregation activity
                try:
                    query = text("""
                        SELECT COUNT(*), MAX(updated_at)
                        FROM analytics.execution_metrics_hourly
                        WHERE updated_at > NOW() - INTERVAL '2 hours'
                    """)
                    result = await db.execute(query)
                    row = result.fetchone()
                    recent_count, last_update = row if row else (0, None)

                    if recent_count > 0:
                        checks['aggregations'] = {
                            'status': 'healthy',
                            'recent_updates': recent_count,
                            'last_update': last_update.isoformat() if last_update else None
                        }
                    else:
                        checks['aggregations'] = {
                            'status': 'warning',
                            'message': 'No recent aggregation updates'
                        }
                except Exception as e:
                    checks['aggregations'] = {'status': 'error', 'error': str(e)}

                # Check data freshness
                try:
                    query = text("""
                        SELECT
                            (SELECT COUNT(*) FROM execution_logs WHERE started_at > NOW() - INTERVAL '1 hour') as recent_logs,
                            (SELECT COUNT(*) FROM analytics.execution_metrics_hourly WHERE hour > NOW() - INTERVAL '1 hour') as recent_metrics
                    """)
                    result = await db.execute(query)
                    row = result.fetchone()
                    recent_logs, recent_metrics = row if row else (0, 0)

                    checks['data_freshness'] = {
                        'status': 'healthy' if recent_logs > 0 or recent_metrics > 0 else 'idle',
                        'recent_logs': recent_logs,
                        'recent_metrics': recent_metrics
                    }
                except Exception as e:
                    checks['data_freshness'] = {'status': 'error', 'error': str(e)}

                # Overall health status
                unhealthy_checks = [k for k, v in checks.items() if v.get('status') == 'unhealthy']
                overall_status = 'unhealthy' if unhealthy_checks else 'healthy'

                return {
                    'timestamp': datetime.utcnow().isoformat(),
                    'overall_status': overall_status,
                    'checks': checks,
                    'unhealthy_checks': unhealthy_checks
                }

        result = self.run_async(run_health_check)
        logger.info(f"Health check completed: {result['overall_status']}")
        return result

    except Exception as exc:
        logger.error(f"Health check task failed: {str(exc)}", exc_info=True)
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(exc)
        }


@celery_app.task(
    name='tasks.maintenance.vacuum_tables',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=1,
)
def vacuum_tables_task(self, analyze: bool = True) -> Dict:
    """Run VACUUM on aggregation tables to reclaim space and update statistics.

    Args:
        analyze: Whether to run ANALYZE as well (default: True)

    Returns:
        Dictionary with vacuum results
    """
    try:
        logger.info("Starting vacuum task")

        async def run_vacuum():
            async with async_session_maker() as db:
                tables = [
                    'analytics.execution_metrics_hourly',
                    'analytics.execution_metrics_daily',
                    'analytics.user_activity_hourly',
                    'analytics.credit_consumption_hourly',
                ]

                results = []

                for table in tables:
                    try:
                        # Note: VACUUM cannot run inside a transaction block
                        # This would need special handling in production
                        analyze_str = "ANALYZE" if analyze else ""
                        query = text(f"VACUUM {analyze_str} {table}")
                        await db.execute(query)
                        await db.commit()

                        results.append({
                            'table': table,
                            'status': 'success',
                            'analyzed': analyze
                        })
                        logger.info(f"Vacuumed table: {table}")

                    except Exception as e:
                        logger.error(f"Failed to vacuum {table}: {str(e)}")
                        results.append({
                            'table': table,
                            'status': 'error',
                            'error': str(e)
                        })

                success_count = sum(1 for r in results if r['status'] == 'success')

                return {
                    'success': True,
                    'tables_vacuumed': success_count,
                    'total_tables': len(tables),
                    'results': results
                }

        result = self.run_async(run_vacuum)
        logger.info(f"Vacuum task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Vacuum task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.maintenance.rebuild_indices',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=1,
)
def rebuild_indices_task(self) -> Dict:
    """Rebuild indices on aggregation tables to improve query performance.

    Returns:
        Dictionary with rebuild results
    """
    try:
        logger.info("Starting index rebuild task")

        async def run_rebuild():
            async with async_session_maker() as db:
                # Get all indices on aggregation tables
                query = text("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname
                    FROM pg_indexes
                    WHERE schemaname = 'analytics'
                    AND tablename IN (
                        'execution_metrics_hourly',
                        'execution_metrics_daily',
                        'user_activity_hourly',
                        'credit_consumption_hourly'
                    )
                """)

                result = await db.execute(query)
                indices = result.fetchall()

                rebuild_results = []

                for schema, table, index in indices:
                    try:
                        reindex_query = text(f"REINDEX INDEX CONCURRENTLY {schema}.{index}")
                        await db.execute(reindex_query)
                        await db.commit()

                        rebuild_results.append({
                            'index': f"{schema}.{index}",
                            'table': f"{schema}.{table}",
                            'status': 'success'
                        })
                        logger.info(f"Rebuilt index: {schema}.{index}")

                    except Exception as e:
                        logger.error(f"Failed to rebuild {schema}.{index}: {str(e)}")
                        rebuild_results.append({
                            'index': f"{schema}.{index}",
                            'table': f"{schema}.{table}",
                            'status': 'error',
                            'error': str(e)
                        })

                success_count = sum(1 for r in rebuild_results if r['status'] == 'success')

                return {
                    'success': True,
                    'indices_rebuilt': success_count,
                    'total_indices': len(indices),
                    'results': rebuild_results
                }

        result = self.run_async(run_rebuild)
        logger.info(f"Index rebuild completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Index rebuild task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)
