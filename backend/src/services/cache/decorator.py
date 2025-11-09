"""Cache decorator for automatic function result caching."""

from functools import wraps
from typing import Optional, Callable, Any, List
import asyncio
import logging

from .keys import CacheKeys
from ...core.redis import get_redis_client

logger = logging.getLogger(__name__)


def cached(
    key_func: Callable[..., str],
    ttl: int = CacheKeys.TTL_MEDIUM,
    skip_cache: bool = False,
    invalidate_on: Optional[List[str]] = None,
):
    """
    Decorator for automatic caching of async function results.

    Args:
        key_func: Function to generate cache key from function arguments
        ttl: Time to live in seconds (default: 5 minutes)
        skip_cache: If True, always bypass cache (for testing)
        invalidate_on: List of event types that should invalidate this cache

    Returns:
        Decorated function with caching capabilities

    Example:
        >>> @cached(
        ...     key_func=lambda workspace_id, timeframe, **_:
        ...         CacheKeys.executive_dashboard(workspace_id, timeframe),
        ...     ttl=CacheKeys.TTL_LONG
        ... )
        ... async def get_executive_metrics(workspace_id: str, timeframe: str):
        ...     # Expensive database query
        ...     return await db.fetch_metrics(workspace_id, timeframe)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Allow cache bypass via parameter
            if skip_cache or kwargs.get("skip_cache", False):
                logger.debug(f"Cache bypass requested for {func.__name__}")
                return await func(*args, **kwargs)

            # Generate cache key from function arguments
            try:
                cache_key = key_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Failed to generate cache key for {func.__name__}: {e}")
                # If key generation fails, execute function without caching
                return await func(*args, **kwargs)

            # Get Redis client
            try:
                redis_client = await get_redis_client()
            except Exception as e:
                logger.error(f"Failed to get Redis client: {e}")
                # If Redis is unavailable, execute function without caching
                return await func(*args, **kwargs)

            # Try to get from cache
            try:
                cached_value = await redis_client.get(cache_key)

                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key} (function: {func.__name__})")
                    return cached_value
            except Exception as e:
                logger.error(f"Cache read error for {cache_key}: {e}")
                # Continue to fetch from source on cache read error

            # Cache miss - fetch from source
            logger.debug(f"Cache miss: {cache_key} (function: {func.__name__})")
            result = await func(*args, **kwargs)

            # Store in cache (don't fail if caching fails)
            try:
                await redis_client.set(cache_key, result, expire=ttl)
                logger.debug(f"Cached result: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.error(f"Cache write error for {cache_key}: {e}")
                # Return result even if caching fails

            return result

        # Add cache invalidation method to decorated function
        async def invalidate(*args, **kwargs):
            """Invalidate cache for this function with given arguments."""
            try:
                cache_key = key_func(*args, **kwargs)
                redis_client = await get_redis_client()
                await redis_client.delete(cache_key)
                logger.info(f"Invalidated cache: {cache_key} (function: {func.__name__})")
            except Exception as e:
                logger.error(f"Failed to invalidate cache for {func.__name__}: {e}")

        # Add invalidate method to wrapper
        wrapper.invalidate = invalidate

        # Store metadata for introspection
        wrapper._cache_metadata = {
            "key_func": key_func,
            "ttl": ttl,
            "invalidate_on": invalidate_on or [],
        }

        return wrapper

    return decorator


def cache_many(
    key_func: Callable[..., List[str]],
    ttl: int = CacheKeys.TTL_MEDIUM,
):
    """
    Decorator for caching multiple results (batch operations).

    Args:
        key_func: Function that returns list of cache keys
        ttl: Time to live in seconds

    Returns:
        Decorated function with batch caching

    Example:
        >>> @cache_many(
        ...     key_func=lambda agent_ids, **_:
        ...         [CacheKeys.agent_analytics(id, '7d') for id in agent_ids],
        ...     ttl=CacheKeys.TTL_LONG
        ... )
        ... async def get_agents_metrics(agent_ids: List[str]):
        ...     return await db.fetch_agents_metrics(agent_ids)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Allow cache bypass
            if kwargs.get("skip_cache", False):
                return await func(*args, **kwargs)

            try:
                redis_client = await get_redis_client()
                cache_keys = key_func(*args, **kwargs)

                # Get all cached values
                cached_results = {}
                for key in cache_keys:
                    value = await redis_client.get(key)
                    if value is not None:
                        cached_results[key] = value

                # If all results are cached, return them
                if len(cached_results) == len(cache_keys):
                    logger.debug(f"Cache hit for all {len(cache_keys)} items")
                    return list(cached_results.values())

                # Otherwise, fetch from source
                logger.debug(f"Cache miss for some items, fetching from source")
                result = await func(*args, **kwargs)

                # Cache the results
                for key, value in zip(cache_keys, result):
                    try:
                        await redis_client.set(key, value, expire=ttl)
                    except Exception as e:
                        logger.error(f"Failed to cache result for {key}: {e}")

                return result

            except Exception as e:
                logger.error(f"Batch cache error: {e}")
                return await func(*args, **kwargs)

        return wrapper

    return decorator


async def invalidate_pattern(pattern: str):
    """
    Utility function to invalidate all keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., 'agent:*:123:*')

    Returns:
        Number of keys deleted
    """
    try:
        redis_client = await get_redis_client()
        deleted = await redis_client.flush_pattern(pattern)
        logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")
        return deleted
    except Exception as e:
        logger.error(f"Failed to invalidate pattern {pattern}: {e}")
        return 0


async def warm_cache(func: Callable, *args, **kwargs):
    """
    Warm up cache by executing a cached function.

    Args:
        func: Cached function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function (which will be cached)
    """
    try:
        logger.info(f"Warming cache for {func.__name__}")
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Failed to warm cache for {func.__name__}: {e}")
        return None
