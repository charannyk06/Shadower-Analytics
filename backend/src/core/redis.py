"""Redis connection management."""

from redis.asyncio import Redis, ConnectionPool
from typing import Optional
from .config import settings
import logging

logger = logging.getLogger(__name__)

redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


async def get_redis_client() -> Optional[Redis]:
    """Get Redis client instance."""
    global redis_pool, redis_client

    if redis_client is None:
        try:
            redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=10,
            )
            redis_client = Redis(connection_pool=redis_pool)
            # Test connection
            await redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None

    return redis_client


async def close_redis():
    """Close Redis connection."""
    global redis_client, redis_pool

    if redis_client:
        await redis_client.close()
        redis_client = None

    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None

    logger.info("Redis connection closed")
