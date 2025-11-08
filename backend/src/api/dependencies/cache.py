"""Cache dependencies."""

from typing import Optional
from redis.asyncio import Redis

from ...core.redis import get_redis_client


async def get_cache() -> Optional[Redis]:
    """Get Redis cache client."""
    return await get_redis_client()
