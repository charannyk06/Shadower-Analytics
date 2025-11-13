"""Enhanced multi-layer cache service with local and Redis caching."""

from typing import Optional, Any, Dict, Callable, Awaitable
import hashlib
import json
import pickle
import logging
from datetime import timedelta
from functools import wraps

from ...core.redis import RedisClient, get_redis_client

logger = logging.getLogger(__name__)


class MultiLayerCacheService:
    """Multi-layer cache service with local memory cache and Redis distributed cache."""

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize multi-layer cache service.

        Args:
            redis_client: Optional RedisClient instance
        """
        self.redis_client = redis_client
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_maxsize = 1000  # Max items in local cache
        self._local_cache_hits = 0
        self._local_cache_misses = 0
        self._redis_cache_hits = 0
        self._redis_cache_misses = 0

    def _generate_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters.

        Args:
            prefix: Cache key prefix
            params: Parameters to include in key

        Returns:
            Generated cache key
        """
        # Sort params for consistent key generation
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{hash_str}"

    async def get(
        self,
        key: str,
        default: Optional[Any] = None
    ) -> Optional[Any]:
        """Get value from cache (local first, then Redis).

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        # Check local cache first
        if key in self.local_cache:
            self._local_cache_hits += 1
            logger.debug(f"Local cache hit: {key}")
            return self.local_cache[key]

        self._local_cache_misses += 1

        # Check Redis cache
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value is not None:
                    self._redis_cache_hits += 1
                    logger.debug(f"Redis cache hit: {key}")
                    # Update local cache
                    self._update_local_cache(key, value)
                    return value

                self._redis_cache_misses += 1
            except Exception as e:
                logger.error(f"Redis cache get error: {e}")

        return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 3600
    ):
        """Set value in both local and Redis cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        # Set in local cache
        self._update_local_cache(key, value)

        # Set in Redis cache
        if self.redis_client:
            try:
                await self.redis_client.set(key, value, expire=ttl)
                logger.debug(f"Cached in Redis: {key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"Redis cache set error: {e}")

    async def delete(self, pattern: str):
        """Delete keys matching pattern from both caches.

        Args:
            pattern: Key pattern to match
        """
        # Delete from local cache
        keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.local_cache[key]

        logger.debug(f"Deleted {len(keys_to_delete)} keys from local cache")

        # Delete from Redis
        if self.redis_client:
            try:
                deleted = await self.redis_client.flush_pattern(pattern)
                logger.debug(f"Deleted {deleted} keys from Redis")
            except Exception as e:
                logger.error(f"Redis cache delete error: {e}")

    async def increment(
        self,
        key: str,
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """Increment counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment
            ttl: Time to live in seconds

        Returns:
            New value after increment
        """
        if self.redis_client:
            try:
                value = await self.redis_client.redis.incrby(key, amount)
                if ttl:
                    await self.redis_client.expire(key, ttl)
                return value
            except Exception as e:
                logger.error(f"Redis increment error: {e}")

        # Fallback to local cache
        current = self.local_cache.get(key, 0)
        new_value = current + amount
        self.local_cache[key] = new_value
        return new_value

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Awaitable[Any]],
        ttl: int = 3600
    ) -> Any:
        """Get from cache or compute and cache the result.

        Args:
            key: Cache key
            compute_func: Async function to compute value
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Check cache
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # Compute value
        logger.debug(f"Cache miss, computing value for: {key}")
        value = await compute_func()

        # Cache result
        await self.set(key, value, ttl)

        return value

    def _update_local_cache(self, key: str, value: Any):
        """Update local cache with size limit.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Implement simple LRU by removing oldest items
        if len(self.local_cache) >= self.local_cache_maxsize:
            # Remove the first item (oldest)
            oldest_key = next(iter(self.local_cache))
            del self.local_cache[oldest_key]
            logger.debug(f"Evicted from local cache: {oldest_key}")

        self.local_cache[key] = value

    def clear_local_cache(self):
        """Clear local cache."""
        self.local_cache.clear()
        logger.info("Local cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_local = self._local_cache_hits + self._local_cache_misses
        local_hit_rate = (
            (self._local_cache_hits / total_local * 100)
            if total_local > 0
            else 0
        )

        total_redis = self._redis_cache_hits + self._redis_cache_misses
        redis_hit_rate = (
            (self._redis_cache_hits / total_redis * 100)
            if total_redis > 0
            else 0
        )

        return {
            "local_cache": {
                "size": len(self.local_cache),
                "max_size": self.local_cache_maxsize,
                "hits": self._local_cache_hits,
                "misses": self._local_cache_misses,
                "hit_rate_percent": round(local_hit_rate, 2),
            },
            "redis_cache": {
                "hits": self._redis_cache_hits,
                "misses": self._redis_cache_misses,
                "hit_rate_percent": round(redis_hit_rate, 2),
                "connected": self.redis_client is not None,
            },
        }


# Singleton instance
_cache_service: Optional[MultiLayerCacheService] = None


async def get_cache_service() -> MultiLayerCacheService:
    """Get cache service instance.

    Returns:
        MultiLayerCacheService: Singleton cache service instance
    """
    global _cache_service

    if _cache_service is None:
        redis_client = await get_redis_client()
        _cache_service = MultiLayerCacheService(redis_client)

    return _cache_service


def cached(
    prefix: str,
    ttl: int = 3600,
    key_params: Optional[list[str]] = None
):
    """Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_params: List of parameter names to include in cache key

    Returns:
        Decorated function

    Example:
        @cached(prefix="user_metrics", ttl=300, key_params=["user_id", "timeframe"])
        async def get_user_metrics(user_id: str, timeframe: str):
            # Expensive computation
            return compute_metrics(user_id, timeframe)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service
            cache_service = await get_cache_service()

            # Generate cache key
            cache_params = {}
            if key_params:
                # Extract specified parameters
                for i, param_name in enumerate(key_params):
                    if i < len(args):
                        cache_params[param_name] = args[i]
                    elif param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]

            cache_key = cache_service._generate_key(prefix, cache_params)

            # Try to get from cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)

            # Cache result
            await cache_service.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
