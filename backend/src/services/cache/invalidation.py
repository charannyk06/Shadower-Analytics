"""Cache invalidation strategies."""

from typing import List
from redis.asyncio import Redis
import logging
from .metrics import record_cache_invalidation

logger = logging.getLogger(__name__)


async def _scan_and_delete(redis: Redis, pattern: str) -> int:
    """Scan and delete keys matching pattern using SCAN (production-safe).

    Args:
        redis: Redis client instance
        pattern: Key pattern to match

    Returns:
        Number of keys deleted

    Note: Uses SCAN instead of KEYS for production safety. There is a potential
    race condition where keys created during SCAN iteration might be missed.
    This is acceptable for cache invalidation use cases.
    """
    cursor = 0
    deleted_count = 0

    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)

        if keys:
            await redis.delete(*keys)
            deleted_count += len(keys)

        if cursor == 0:
            break

    if deleted_count > 0:
        record_cache_invalidation(pattern)

    return deleted_count


async def invalidate_metric_cache(
    redis: Redis,
    metric_type: str,
):
    """Invalidate cache for specific metric type."""
    pattern = f"metric:{metric_type}:*"
    deleted_count = await _scan_and_delete(redis, pattern)
    if deleted_count > 0:
        logger.info(f"Invalidated {deleted_count} cache entries for metric: {metric_type}")


async def invalidate_user_cache(
    redis: Redis,
    user_id: str,
):
    """Invalidate cache for specific user."""
    patterns = [
        f"user:{user_id}:*",
        f"user_metrics:{user_id}:*",
    ]

    total_deleted = 0
    for pattern in patterns:
        deleted_count = await _scan_and_delete(redis, pattern)
        total_deleted += deleted_count

    if total_deleted > 0:
        logger.info(f"Invalidated {total_deleted} cache entries for user: {user_id}")


async def invalidate_agent_cache(
    redis: Redis,
    agent_id: str,
):
    """Invalidate cache for specific agent."""
    pattern = f"agent:{agent_id}:*"
    deleted_count = await _scan_and_delete(redis, pattern)
    if deleted_count > 0:
        logger.info(f"Invalidated {deleted_count} cache entries for agent: {agent_id}")


async def invalidate_all_metrics(redis: Redis):
    """Invalidate all metric caches."""
    pattern = "metric:*"
    deleted_count = await _scan_and_delete(redis, pattern)
    if deleted_count > 0:
        logger.info(f"Invalidated {deleted_count} metric cache entries")
