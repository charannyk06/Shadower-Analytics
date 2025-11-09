"""Redis connection management and client wrapper."""

import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle
from .config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Enhanced Redis client with advanced caching capabilities."""

    def __init__(self, url: str):
        """Initialize Redis client with connection pooling."""
        self.redis = redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=False,  # Handle bytes for complex objects
            max_connections=50,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic deserialization."""
        try:
            value = await self.redis.get(key)
            if value:
                try:
                    # Try JSON first (faster and more common)
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Fall back to pickle for complex objects
                    return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration and automatic serialization."""
        try:
            # Try JSON serialization first (faster and more portable)
            try:
                serialized = json.dumps(value)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                serialized = pickle.dumps(value)

            if expire:
                return await self.redis.setex(key, expire, serialized)
            return await self.redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key."""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Get time to live for key in seconds. Returns -1 if no TTL, -2 if key doesn't exist."""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache get_ttl error for key {key}: {e}")
            return -2

    async def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern using SCAN (production-safe).
        Returns number of keys deleted.
        """
        try:
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)

                if keys:
                    deleted += await self.redis.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
            return deleted
        except Exception as e:
            logger.error(f"Cache flush_pattern error for pattern {pattern}: {e}")
            return 0

    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        try:
            await self.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get or create global Redis client instance."""
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = RedisClient(settings.REDIS_URL)
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    return _redis_client


async def close_redis():
    """Close global Redis connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
