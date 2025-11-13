"""Resource metrics aggregation and materialized view refresh tasks."""

from celeryconfig import app
from datetime import datetime
import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os

logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/shadower_analytics"
)


async def refresh_resource_materialized_views():
    """Refresh all resource analytics materialized views."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Call the refresh function we created in the migration
            query = text("SELECT analytics.refresh_resource_materialized_views()")
            await session.execute(query)
            await session.commit()

            logger.info("Successfully refreshed all resource materialized views")
            return {"status": "success", "views_refreshed": 6}

        except Exception as e:
            logger.error(f"Error refreshing resource materialized views: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await engine.dispose()


async def calculate_efficiency_scores():
    """Calculate and update efficiency scores for all agents."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Efficiency scores are calculated via the materialized view
            # This just ensures it's up to date
            query = text("""
                REFRESH MATERIALIZED VIEW CONCURRENTLY
                analytics.agent_efficiency_scorecard
            """)
            await session.execute(query)
            await session.commit()

            logger.info("Successfully updated efficiency scores")
            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error calculating efficiency scores: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await engine.dispose()


async def detect_resource_waste():
    """Detect and log resource waste events."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Detect idle resources (low utilization)
            query = text("""
                INSERT INTO analytics.resource_waste_events (
                    agent_id,
                    execution_id,
                    workspace_id,
                    waste_type,
                    waste_category,
                    waste_amount,
                    waste_unit,
                    waste_cost_usd,
                    title,
                    description,
                    detection_method,
                    confidence_score
                )
                SELECT
                    agent_id,
                    execution_id,
                    workspace_id,
                    'idle_resources'::varchar as waste_type,
                    'compute'::varchar as waste_category,
                    (memory_allocation_mb - memory_average_mb) as waste_amount,
                    'MB'::varchar as waste_unit,
                    ((memory_allocation_mb - memory_average_mb) / 1024.0 * 0.004 *
                     execution_duration_ms / 3600000.0) as waste_cost_usd,
                    'Underutilized Memory Allocation'::varchar as title,
                    CONCAT('Memory allocated: ', memory_allocation_mb::text, 'MB, ',
                           'Average used: ', memory_average_mb::text, 'MB') as description,
                    'automated_threshold'::varchar as detection_method,
                    0.85 as confidence_score
                FROM analytics.resource_utilization_metrics
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                    AND memory_allocation_mb > 0
                    AND memory_average_mb > 0
                    AND (memory_average_mb / memory_allocation_mb) < 0.5
                    AND NOT EXISTS (
                        SELECT 1 FROM analytics.resource_waste_events rwe
                        WHERE rwe.execution_id = resource_utilization_metrics.execution_id
                        AND rwe.waste_type = 'idle_resources'
                    )
            """)
            result = await session.execute(query)
            await session.commit()

            waste_events_detected = result.rowcount
            logger.info(f"Detected {waste_events_detected} new resource waste events")

            return {
                "status": "success",
                "waste_events_detected": waste_events_detected
            }

        except Exception as e:
            logger.error(f"Error detecting resource waste: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await engine.dispose()


@app.task
def refresh_resource_views():
    """Celery task to refresh resource analytics materialized views."""
    logger.info("Starting resource metrics materialized view refresh...")

    try:
        result = asyncio.run(refresh_resource_materialized_views())
        logger.info("Resource metrics refresh completed successfully")
        return result

    except Exception as e:
        logger.error(f"Resource metrics refresh failed: {e}")
        raise


@app.task
def update_efficiency_scores():
    """Celery task to update agent efficiency scores."""
    logger.info("Starting efficiency scores calculation...")

    try:
        result = asyncio.run(calculate_efficiency_scores())
        logger.info("Efficiency scores calculation completed successfully")
        return result

    except Exception as e:
        logger.error(f"Efficiency scores calculation failed: {e}")
        raise


@app.task
def detect_waste():
    """Celery task to detect resource waste."""
    logger.info("Starting resource waste detection...")

    try:
        result = asyncio.run(detect_resource_waste())
        logger.info("Resource waste detection completed successfully")
        return result

    except Exception as e:
        logger.error(f"Resource waste detection failed: {e}")
        raise


@app.task
def run_resource_analytics_pipeline():
    """Run complete resource analytics pipeline."""
    logger.info("Starting complete resource analytics pipeline...")

    try:
        # Refresh materialized views
        refresh_result = asyncio.run(refresh_resource_materialized_views())
        logger.info(f"Materialized views refreshed: {refresh_result}")

        # Calculate efficiency scores
        efficiency_result = asyncio.run(calculate_efficiency_scores())
        logger.info(f"Efficiency scores calculated: {efficiency_result}")

        # Detect waste
        waste_result = asyncio.run(detect_resource_waste())
        logger.info(f"Waste detection completed: {waste_result}")

        logger.info("Complete resource analytics pipeline completed successfully")
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "refresh": refresh_result,
            "efficiency": efficiency_result,
            "waste": waste_result,
        }

    except Exception as e:
        logger.error(f"Resource analytics pipeline failed: {e}")
        raise
