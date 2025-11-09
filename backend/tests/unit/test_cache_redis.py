"""Unit tests for Redis caching layer."""

import pytest
import json
from unittest.mock import AsyncMock, patch

from src.core.redis import RedisClient
from src.services.cache.keys import CacheKeys
from src.services.cache.redis_cache import CacheService
from src.services.cache.decorator import cached, invalidate_pattern


class TestRedisClient:
    """Tests for RedisClient class."""

    @pytest.fixture
    async def redis_client(self):
        """Create a mock Redis client."""
        with patch("src.core.redis.redis") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.from_url.return_value = mock_redis_instance
            client = RedisClient("redis://localhost:6379/0")
            yield client

    @pytest.mark.asyncio
    async def test_get_returns_none_when_key_not_exists(self, redis_client):
        """Test get returns None when key doesn't exist."""
        redis_client.redis.get = AsyncMock(return_value=None)

        result = await redis_client.get("nonexistent_key")

        assert result is None
        redis_client.redis.get.assert_called_once_with("nonexistent_key")

    @pytest.mark.asyncio
    async def test_get_deserializes_json(self, redis_client):
        """Test get deserializes JSON data correctly."""
        test_data = {"foo": "bar", "count": 123}
        redis_client.redis.get = AsyncMock(return_value=json.dumps(test_data).encode())

        result = await redis_client.get("test_key")

        assert result == test_data

    @pytest.mark.asyncio
    async def test_set_serializes_json(self, redis_client):
        """Test set serializes data as JSON."""
        test_data = {"foo": "bar"}
        redis_client.redis.setex = AsyncMock(return_value=True)

        result = await redis_client.set("test_key", test_data, expire=300)

        assert result is True
        redis_client.redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, redis_client):
        """Test delete removes key from cache."""
        redis_client.redis.delete = AsyncMock(return_value=1)

        result = await redis_client.delete("test_key")

        assert result is True
        redis_client.redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_checks_key_existence(self, redis_client):
        """Test exists checks if key exists."""
        redis_client.redis.exists = AsyncMock(return_value=1)

        result = await redis_client.exists("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_flush_pattern_uses_scan(self, redis_client):
        """Test flush_pattern uses SCAN instead of KEYS."""
        # Mock SCAN to return keys in batches
        redis_client.redis.scan = AsyncMock(
            side_effect=[
                (100, [b"key1", b"key2"]),
                (0, [b"key3"]),  # cursor 0 means end
            ]
        )
        redis_client.redis.delete = AsyncMock(return_value=3)

        deleted = await redis_client.flush_pattern("test:*")

        assert deleted == 6  # 2 + 1 keys deleted (mock returns 3 each time)
        assert redis_client.redis.scan.call_count == 2


class TestCacheKeys:
    """Tests for CacheKeys naming conventions."""

    def test_executive_dashboard_key(self):
        """Test executive dashboard key generation."""
        key = CacheKeys.executive_dashboard("ws123", "7d")
        assert key == "exec:dashboard:ws123:7d"

    def test_agent_analytics_key(self):
        """Test agent analytics key generation."""
        key = CacheKeys.agent_analytics("agent456", "30d")
        assert key == "agent:analytics:agent456:30d"

    def test_workspace_pattern(self):
        """Test workspace pattern generation."""
        patterns = CacheKeys.get_workspace_pattern("ws123")

        assert "exec:*:ws123:*" in patterns
        assert "ws:*:ws123:*" in patterns
        assert "metrics:*:ws123:*" in patterns

    def test_query_hash_generation(self):
        """Test query hash is consistent."""
        query = "SELECT * FROM users WHERE id = :id"
        params = {"id": 123}

        hash1 = CacheKeys.generate_query_hash(query, params)
        hash2 = CacheKeys.generate_query_hash(query, params)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_ttl_for_timeframe(self):
        """Test TTL mapping for different timeframes."""
        assert CacheKeys.get_ttl_for_timeframe("24h") == CacheKeys.TTL_MEDIUM
        assert CacheKeys.get_ttl_for_timeframe("7d") == CacheKeys.TTL_LONG
        assert CacheKeys.get_ttl_for_timeframe("30d") == CacheKeys.TTL_HOUR


class TestCacheService:
    """Tests for CacheService."""

    @pytest.fixture
    async def cache_service(self):
        """Create a cache service with mocked Redis client."""
        mock_redis = AsyncMock()
        service = CacheService(mock_redis)
        yield service

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, cache_service):
        """Test get_or_compute returns cached value on cache hit."""
        cache_service.redis.get = AsyncMock(return_value={"cached": "data"})
        compute_func = AsyncMock()

        result = await cache_service.get_or_compute("test_key", compute_func)

        assert result == {"cached": "data"}
        compute_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, cache_service):
        """Test get_or_compute computes and caches on cache miss."""
        cache_service.redis.get = AsyncMock(return_value=None)
        cache_service.redis.set = AsyncMock()
        compute_func = AsyncMock(return_value={"computed": "data"})

        result = await cache_service.get_or_compute("test_key", compute_func, ttl=300)

        assert result == {"computed": "data"}
        compute_func.assert_called_once()
        cache_service.redis.set.assert_called_once_with(
            "test_key", {"computed": "data"}, expire=300
        )

    @pytest.mark.asyncio
    async def test_invalidate_workspace(self, cache_service):
        """Test workspace cache invalidation."""
        cache_service.redis.flush_pattern = AsyncMock(return_value=5)

        deleted = await cache_service.invalidate_workspace("ws123")

        # Should call flush_pattern for multiple patterns
        assert cache_service.redis.flush_pattern.call_count >= 3
        assert deleted > 0

    @pytest.mark.asyncio
    async def test_invalidate_agent(self, cache_service):
        """Test agent cache invalidation."""
        cache_service.redis.flush_pattern = AsyncMock(return_value=3)

        deleted = await cache_service.invalidate_agent("agent456")

        assert deleted == 3
        cache_service.redis.flush_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_service):
        """Test cache statistics retrieval."""
        cache_service.redis.redis.info = AsyncMock(
            return_value={
                "used_memory_human": "10M",
                "keyspace_hits": 800,
                "keyspace_misses": 200,
                "evicted_keys": 5,
            }
        )

        stats = await cache_service.get_cache_stats()

        assert stats["used_memory"] == "10M"
        assert stats["hit_rate_percent"] == 80.0
        assert stats["evicted_keys"] == 5


class TestCacheDecorator:
    """Tests for cache decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_hit(self):
        """Test cached decorator returns cached value on hit."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value={"cached": "result"})

        with patch(
            "src.services.cache.decorator.get_redis_client", return_value=mock_redis
        ):

            @cached(
                key_func=lambda workspace_id, **_: f"test:{workspace_id}",
                ttl=CacheKeys.TTL_MEDIUM,
            )
            async def test_function(workspace_id: str):
                return {"computed": "result"}

            result = await test_function("ws123")

            assert result == {"cached": "result"}

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_miss(self):
        """Test cached decorator computes and caches on miss."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        with patch(
            "src.services.cache.decorator.get_redis_client", return_value=mock_redis
        ):

            @cached(
                key_func=lambda workspace_id, **_: f"test:{workspace_id}",
                ttl=CacheKeys.TTL_MEDIUM,
            )
            async def test_function(workspace_id: str):
                return {"computed": "result"}

            result = await test_function("ws123")

            assert result == {"computed": "result"}
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_skip_cache(self):
        """Test cached decorator bypasses cache when skip_cache=True."""
        mock_redis = AsyncMock()

        with patch(
            "src.services.cache.decorator.get_redis_client", return_value=mock_redis
        ):

            @cached(
                key_func=lambda workspace_id, **_: f"test:{workspace_id}",
                ttl=CacheKeys.TTL_MEDIUM,
            )
            async def test_function(workspace_id: str, skip_cache: bool = False):
                return {"computed": "result"}

            result = await test_function("ws123", skip_cache=True)

            assert result == {"computed": "result"}
            mock_redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_pattern_helper():
    """Test invalidate_pattern helper function."""
    mock_redis = AsyncMock()
    mock_redis.flush_pattern = AsyncMock(return_value=10)

    with patch(
        "src.services.cache.decorator.get_redis_client", return_value=mock_redis
    ):
        deleted = await invalidate_pattern("test:*")

        assert deleted == 10
        mock_redis.flush_pattern.assert_called_once_with("test:*")
