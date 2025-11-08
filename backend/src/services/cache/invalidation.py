"""Cache invalidation strategies."""

from typing import List
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)


async def invalidate_metric_cache(
    redis: Redis,
    metric_type: str,
):
    """Invalidate cache for specific metric type."""
    pattern = f"metric:{metric_type}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
        logger.info(f"Invalidated {len(keys)} cache entries for metric: {metric_type}")


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
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            total_deleted += len(keys)

    logger.info(f"Invalidated {total_deleted} cache entries for user: {user_id}")


async def invalidate_agent_cache(
    redis: Redis,
    agent_id: str,
):
    """Invalidate cache for specific agent."""
    pattern = f"agent:{agent_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
        logger.info(f"Invalidated {len(keys)} cache entries for agent: {agent_id}")


async def invalidate_all_metrics(redis: Redis):
    """Invalidate all metric caches."""
    pattern = "metric:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
        logger.info(f"Invalidated {len(keys)} metric cache entries")
