"""Enhanced Redis cache implementation with warming and invalidation."""

import asyncio
import json
import re
from typing import Any, Optional, Callable, Dict
import logging
from .metrics import (
    record_cache_hit,
    record_cache_miss,
    record_cache_error,
    record_cache_invalidation,
    track_cache_operation,
)
from ...core.constants import CACHE_KEY_MAX_LENGTH, CACHE_KEY_PATTERN

from .keys import CacheKeys
from ...core.redis import RedisClient

logger = logging.getLogger(__name__)


class CacheKeyValidationError(ValueError):
    """Exception raised for invalid cache keys."""

    pass


class CacheService:
    """Enhanced Redis cache service with advanced features."""

    def __init__(self, redis_client: RedisClient):
        """
        Initialize cache service.

        Args:
            redis_client: RedisClient instance
        """
        self.redis = redis_client
        self._key_pattern = re.compile(CACHE_KEY_PATTERN)

    def _validate_cache_key(self, key: str) -> None:
        """Validate cache key format and length.

        Args:
            key: Cache key to validate

        Raises:
            CacheKeyValidationError: If key is invalid
        """
        if not key:
            raise CacheKeyValidationError("Cache key cannot be empty")

        if len(key) > CACHE_KEY_MAX_LENGTH:
            raise CacheKeyValidationError(
                f"Cache key exceeds maximum length of {CACHE_KEY_MAX_LENGTH} characters"
            )

        if not self._key_pattern.match(key):
            raise CacheKeyValidationError(
                f"Cache key contains invalid characters. "
                f"Only alphanumeric, colon, underscore, hyphen, and dot are allowed"
            )

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            self._validate_cache_key(key)
            value = await self.redis.get(key)
            if value is not None:
                record_cache_hit("get", self._get_key_pattern(key))
            else:
                record_cache_miss("get", self._get_key_pattern(key))
            return value
        except CacheKeyValidationError as e:
            logger.warning(f"Invalid cache key: {e}")
            record_cache_error("get", "ValidationError")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            record_cache_error("get", type(e).__name__)
            return None

    async def set(self, key: str, value: Any, ttl: int = CacheKeys.TTL_MEDIUM):
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        try:
            self._validate_cache_key(key)
            await self.redis.set(key, value, expire=ttl)
        except CacheKeyValidationError as e:
            logger.warning(f"Invalid cache key: {e}")
            record_cache_error("set", "ValidationError")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            record_cache_error("set", type(e).__name__)

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        try:
            self._validate_cache_key(key)
            result = await self.redis.delete(key)
            return result
        except CacheKeyValidationError as e:
            logger.warning(f"Invalid cache key: {e}")
            record_cache_error("delete", "ValidationError")
            return False
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            record_cache_error("delete", type(e).__name__)
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            self._validate_cache_key(key)
            return await self.redis.exists(key)
        except CacheKeyValidationError as e:
            logger.warning(f"Invalid cache key: {e}")
            record_cache_error("exists", "ValidationError")
            return False
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            record_cache_error("exists", type(e).__name__)
            return False

    async def get_or_compute(
        self, key: str, compute_func: Callable, ttl: int = CacheKeys.TTL_MEDIUM
    ) -> Any:
        """
        Get from cache or compute and cache the result.

        Args:
            key: Cache key
            compute_func: Async function to compute value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Check cache first
        value = await self.get(key)

        if value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return value

        # Cache miss - compute value
        logger.debug(f"Cache miss for key: {key}, computing...")
        value = await compute_func()

        # Cache the result
        await self.set(key, value, ttl=ttl)
        logger.debug(f"Cached computed value for key: {key}")

        return value

    async def invalidate_workspace(self, workspace_id: str) -> int:
        """
        Invalidate all cache entries for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Number of keys deleted
        """
        patterns = CacheKeys.get_workspace_pattern(workspace_id)

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(
            f"Invalidated {total_deleted} cache entries for workspace {workspace_id}"
        )
        return total_deleted

    async def invalidate_agent(self, agent_id: str) -> int:
        """
        Invalidate all cache entries for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of keys deleted
        """
        pattern = CacheKeys.get_agent_pattern(agent_id)
        deleted = await self.clear_pattern(pattern)

        logger.info(f"Invalidated {deleted} cache entries for agent {agent_id}")
        return deleted

    async def invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all cache entries for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of keys deleted
        """
        patterns = CacheKeys.get_user_pattern(user_id)

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
        return total_deleted

    async def warm_cache(self, workspace_id: str) -> int:
        """
        Pre-populate cache with common queries for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Number of successful cache warming operations
        """
        logger.info(f"Starting cache warming for workspace {workspace_id}")

        timeframes = ["24h", "7d", "30d"]
        tasks = []

        for timeframe in timeframes:
            # Warm executive dashboard data
            tasks.append(self._warm_executive_dashboard(workspace_id, timeframe))

            # Warm top agents data
            tasks.append(self._warm_top_agents(workspace_id, timeframe))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(
            f"Cache warming completed for workspace {workspace_id}: "
            f"{successful}/{len(results)} successful"
        )

        return successful

    async def _warm_executive_dashboard(self, workspace_id: str, timeframe: str):
        """
        Warm executive dashboard cache (placeholder - will be implemented with actual service).

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period
        """
        key = CacheKeys.executive_dashboard(workspace_id, timeframe)
        ttl = CacheKeys.get_ttl_for_timeframe(timeframe)

        # This would call the actual metrics service
        # For now, we just create the key structure
        logger.debug(f"Would warm cache for executive dashboard: {key} (TTL: {ttl}s)")

        # Implementation will be added when integrating with metrics service
        return key

    async def _warm_top_agents(self, workspace_id: str, timeframe: str):
        """
        Warm top agents cache (placeholder - will be implemented with actual service).

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period
        """
        key = CacheKeys.agent_top(workspace_id, timeframe)
        ttl = CacheKeys.get_ttl_for_timeframe(timeframe)

        logger.debug(f"Would warm cache for top agents: {key} (TTL: {ttl}s)")

        # Implementation will be added when integrating with agent metrics service
        return key

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics from Redis.

        Returns:
            Dictionary with cache statistics
        """
        try:
            info = await self.redis.redis.info()

            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)

            return {
                "used_memory": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate_percent": self._calculate_hit_rate(hits, misses),
                "evicted_keys": info.get("evicted_keys"),
                "expired_keys": info.get("expired_keys"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "uptime_in_days": info.get("uptime_in_days"),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """
        Calculate cache hit rate percentage.

        Args:
            hits: Number of cache hits
            misses: Number of cache misses

        Returns:
            Hit rate as percentage (0-100)
        """
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern using SCAN (production-safe).

        Args:
            pattern: Redis key pattern

        Returns:
            Number of keys deleted

        Note: This uses SCAN instead of KEYS for production safety.
        There is a potential race condition where keys created during
        SCAN iteration might be missed. This is acceptable for cache
        invalidation use cases.
        """
        try:
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )

                if keys:
                    await self.redis.redis.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} keys matching pattern: {pattern}")
                record_cache_invalidation(pattern)

            return deleted_count
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            record_cache_error("clear_pattern", type(e).__name__)
            return 0

    @staticmethod
    def _get_key_pattern(key: str) -> str:
        """Extract pattern from cache key for metrics.

        Args:
            key: Cache key (e.g., "metric:cpu:user:123")

        Returns:
            Key pattern (e.g., "metric:cpu")
        """
        parts = key.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}"
        return parts[0] if parts else "unknown"
