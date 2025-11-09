"""Materialized view refresh logic."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def refresh_materialized_view(
    db: AsyncSession,
    view_name: str,
    concurrently: bool = True
) -> Dict[str, Any]:
    """Refresh a specific materialized view.

    Args:
        db: Database session
        view_name: Name of the materialized view to refresh
        concurrently: If True, use CONCURRENTLY to avoid locking

    Returns:
        Dictionary with refresh status
    """
    try:
        # Validate view_name against known materialized views to prevent SQL injection
        valid_views = [
            "analytics.mv_daily_user_metrics",
            "analytics.mv_daily_agent_metrics",
            "analytics.mv_hourly_execution_stats",
            "analytics.mv_workspace_summary",
        ]
        if view_name not in valid_views:
            raise ValueError(f"Invalid materialized view name: {view_name}")
        
        concurrent_str = "CONCURRENTLY" if concurrently else ""
        query = text(f"REFRESH MATERIALIZED VIEW {concurrent_str} {view_name}")

        logger.info(f"Refreshing materialized view: {view_name}")
        await db.execute(query)
        await db.commit()

        logger.info(f"Successfully refreshed materialized view: {view_name}")
        return {
            'view_name': view_name,
            'success': True,
            'concurrent': concurrently
        }

    except Exception as e:
        logger.error(f"Failed to refresh materialized view {view_name}: {str(e)}")
        await db.rollback()
        return {
            'view_name': view_name,
            'success': False,
            'error': str(e),
            'concurrent': concurrently
        }


async def refresh_all_materialized_views(db: AsyncSession) -> Dict[str, Any]:
    """Refresh all materialized views.

    Args:
        db: Database session

    Returns:
        Dictionary with refresh results for all views
    """
    # Define materialized views to refresh
    # Note: These would need to be created via migrations
    views = [
        "analytics.mv_daily_user_metrics",
        "analytics.mv_daily_agent_metrics",
        "analytics.mv_hourly_execution_stats",
        "analytics.mv_workspace_summary",
    ]

    results = []
    success_count = 0
    failure_count = 0

    logger.info(f"Starting refresh of {len(views)} materialized views")

    for view in views:
        result = await refresh_materialized_view(db, view, concurrently=True)
        results.append(result)

        if result['success']:
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        f"Materialized view refresh completed: "
        f"{success_count} succeeded, {failure_count} failed"
    )

    return {
        'total_views': len(views),
        'success_count': success_count,
        'failure_count': failure_count,
        'results': results
    }


async def create_materialized_views(db: AsyncSession) -> Dict[str, Any]:
    """Create materialized views if they don't exist.

    This should be called during initial setup or migrations.

    Args:
        db: Database session

    Returns:
        Dictionary with creation status
    """
    try:
        # Example materialized view for daily user metrics
        query_daily_user = text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_daily_user_metrics AS
            SELECT
                user_id,
                workspace_id,
                DATE(hour) as date,
                SUM(total_events) as total_events,
                SUM(page_views) as page_views,
                SUM(unique_sessions) as unique_sessions,
                AVG(active_duration_seconds) as avg_active_duration
            FROM analytics.user_activity_hourly
            GROUP BY user_id, workspace_id, DATE(hour)
            WITH DATA
        """)

        # Example materialized view for hourly execution stats
        query_hourly_exec = text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_hourly_execution_stats AS
            SELECT
                workspace_id,
                hour,
                total_executions,
                successful_executions,
                failed_executions,
                CASE
                    WHEN total_executions > 0
                    THEN (successful_executions::float / total_executions * 100)
                    ELSE 0
                END as success_rate,
                avg_runtime,
                p95_runtime,
                total_credits
            FROM analytics.execution_metrics_hourly
            WITH DATA
        """)

        # Example materialized view for workspace summary
        query_workspace_summary = text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_workspace_summary AS
            SELECT
                workspace_id,
                COUNT(DISTINCT hour) as active_hours,
                SUM(total_executions) as total_executions,
                SUM(successful_executions) as successful_executions,
                SUM(total_credits) as total_credits_used,
                AVG(avg_runtime) as avg_runtime,
                MAX(p95_runtime) as max_p95_runtime
            FROM analytics.execution_metrics_hourly
            GROUP BY workspace_id
            WITH DATA
        """)

        # Create indexes on materialized views
        index_queries = [
            text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_user_metrics ON analytics.mv_daily_user_metrics (user_id, workspace_id, date)"),
            text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_exec_stats ON analytics.mv_hourly_execution_stats (workspace_id, hour)"),
            text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_workspace_summary ON analytics.mv_workspace_summary (workspace_id)")
        ]

        logger.info("Creating materialized views...")

        await db.execute(query_daily_user)
        await db.execute(query_hourly_exec)
        await db.execute(query_workspace_summary)

        for index_query in index_queries:
            await db.execute(index_query)

        await db.commit()

        logger.info("Successfully created materialized views")
        return {'success': True, 'views_created': 3}

    except Exception as e:
        logger.error(f"Failed to create materialized views: {str(e)}")
        await db.rollback()
        return {'success': False, 'error': str(e)}
