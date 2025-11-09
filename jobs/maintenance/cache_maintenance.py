"""Cache maintenance tasks for scheduled cleanup and warming."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend/src"))

from celeryconfig import app
from core.redis import get_redis_client
from core.config import settings
from services.cache.keys import CacheKeys

logger = logging.getLogger(__name__)


@app.task(name="maintenance.cache_maintenance.cleanup_expired_cache")
def cleanup_expired_cache():
    """
    Scheduled job to clean up stale cache entries without TTL.
    Runs daily to ensure cache hygiene.
    """
    return asyncio.run(_cleanup_expired_cache())


async def _cleanup_expired_cache():
    """Clean up cache entries that should have TTL but don't."""
    try:
        redis_client = await get_redis_client()

        # Patterns to check for keys without TTL
        patterns_to_check = [
            f"{CacheKeys.EXECUTIVE_PREFIX}:*",
            f"{CacheKeys.AGENT_PREFIX}:*",
            f"{CacheKeys.METRICS_PREFIX}:*",
            f"{CacheKeys.USER_PREFIX}:*",
            f"{CacheKeys.QUERY_PREFIX}:*",
        ]

        total_cleaned = 0
        total_checked = 0

        for pattern in patterns_to_check:
            cursor = 0
            while True:
                cursor, keys = await redis_client.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )

                for key in keys:
                    total_checked += 1
                    ttl = await redis_client.get_ttl(key)

                    # Remove keys without TTL (shouldn't exist for cache entries)
                    if ttl == -1:
                        await redis_client.delete(key)
                        total_cleaned += 1
                        logger.warning(f"Removed cache key without TTL: {key}")

                if cursor == 0:
                    break

        logger.info(
            f"Cache cleanup completed: checked {total_checked} keys, "
            f"cleaned {total_cleaned} stale entries"
        )

        return {"checked": total_checked, "cleaned": total_cleaned}

    except Exception as e:
        logger.error(f"Failed to cleanup expired cache: {e}")
        return {"error": str(e)}


@app.task(name="maintenance.cache_maintenance.refresh_materialized_cache")
def refresh_materialized_cache():
    """
    Refresh cache for frequently accessed data (materialized views).
    Runs hourly to keep hot data fresh.
    """
    return asyncio.run(_refresh_materialized_cache())


async def _refresh_materialized_cache():
    """Refresh cache for active workspaces."""
    try:
        # This would get list of active workspaces from database
        # For now, we'll just log the intention
        logger.info("Starting materialized cache refresh")

        # Implementation notes:
        # 1. Get list of active workspaces (workspaces with activity in last 24h)
        # 2. For each workspace, warm cache for common queries
        # 3. This ensures frequently accessed data is always fresh

        # Placeholder implementation
        refreshed_count = 0

        # Example: refresh top 10 most active workspaces
        # active_workspaces = await get_active_workspaces(limit=10)
        # for workspace in active_workspaces:
        #     await cache_service.warm_cache(workspace.id)
        #     refreshed_count += 1

        logger.info(f"Materialized cache refresh completed: {refreshed_count} workspaces")

        return {"refreshed": refreshed_count}

    except Exception as e:
        logger.error(f"Failed to refresh materialized cache: {e}")
        return {"error": str(e)}


@app.task(name="maintenance.cache_maintenance.cache_health_check")
def cache_health_check():
    """
    Monitor cache health metrics and log warnings.
    Runs every 15 minutes.
    """
    return asyncio.run(_cache_health_check())


async def _cache_health_check():
    """Check cache health and report metrics."""
    try:
        redis_client = await get_redis_client()

        # Get cache statistics
        info = await redis_client.redis.info()

        # Extract key metrics
        used_memory = info.get("used_memory", 0)
        used_memory_peak = info.get("used_memory_peak", 0)
        hit_rate = info.get("keyspace_hits", 0) / max(
            info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
        )
        evicted_keys = info.get("evicted_keys", 0)

        # Log metrics
        logger.info(
            f"Cache health: memory={info.get('used_memory_human')}, "
            f"hit_rate={hit_rate:.2%}, evicted={evicted_keys}"
        )

        # Check for potential issues
        warnings = []

        # Check hit rate (warn if below 80%)
        if hit_rate < 0.8:
            warnings.append(f"Low cache hit rate: {hit_rate:.2%}")

        # Check memory usage (warn if near peak)
        if used_memory > used_memory_peak * 0.9:
            warnings.append("Memory usage near peak")

        # Check evictions (warn if happening)
        if evicted_keys > 0:
            warnings.append(f"Cache evictions detected: {evicted_keys}")

        if warnings:
            for warning in warnings:
                logger.warning(f"Cache health warning: {warning}")

        return {
            "memory_used": info.get("used_memory_human"),
            "hit_rate": hit_rate,
            "evicted_keys": evicted_keys,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(f"Failed to check cache health: {e}")
        return {"error": str(e)}


@app.task(name="maintenance.cache_maintenance.warm_priority_cache")
def warm_priority_cache():
    """
    Warm cache for high-priority data.
    Runs at application start and periodically.
    """
    return asyncio.run(_warm_priority_cache())


async def _warm_priority_cache():
    """Pre-populate cache with priority data."""
    try:
        logger.info("Starting priority cache warming")

        # Implementation notes:
        # 1. Executive dashboards for top workspaces
        # 2. Top agents analytics
        # 3. Common metric aggregations
        # 4. Recent reports

        warmed_count = 0

        # Example implementation:
        # priority_workspaces = await get_priority_workspaces()
        # for workspace in priority_workspaces:
        #     cache_service = CacheService(redis_client)
        #     await cache_service.warm_cache(workspace.id)
        #     warmed_count += 1

        logger.info(f"Priority cache warming completed: {warmed_count} items")

        return {"warmed": warmed_count}

    except Exception as e:
        logger.error(f"Failed to warm priority cache: {e}")
        return {"error": str(e)}
