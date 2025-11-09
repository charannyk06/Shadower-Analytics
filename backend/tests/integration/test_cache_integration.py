"""Integration tests for caching layer with real Redis."""

import pytest
import asyncio
from datetime import datetime

from src.core.redis import get_redis_client, close_redis
from src.services.cache.redis_cache import CacheService
from src.services.cache.keys import CacheKeys
from src.services.cache.decorator import cached, invalidate_pattern


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests with real Redis instance."""

    @pytest.fixture(autouse=True)
    async def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: ensure Redis is connected
        redis_client = await get_redis_client()

        yield

        # Teardown: clean up test keys
        await redis_client.flush_pattern("test:*")
        await redis_client.flush_pattern("integration:*")

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test Redis connection is established."""
        redis_client = await get_redis_client()
        ping = await redis_client.ping()

        assert ping is True

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting values from Redis."""
        redis_client = await get_redis_client()

        test_data = {"user": "test", "count": 42, "active": True}

        # Set value
        success = await redis_client.set("test:user:123", test_data, expire=60)
        assert success is True

        # Get value
        result = await redis_client.get("test:user:123")
        assert result == test_data

    @pytest.mark.asyncio
    async def test_expiration(self):
        """Test key expiration."""
        redis_client = await get_redis_client()

        # Set with 1 second TTL
        await redis_client.set("test:expire", "data", expire=1)

        # Should exist immediately
        exists = await redis_client.exists("test:expire")
        assert exists is True

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should not exist after expiration
        exists = await redis_client.exists("test:expire")
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting keys."""
        redis_client = await get_redis_client()

        await redis_client.set("test:delete", "data")
        assert await redis_client.exists("test:delete") is True

        deleted = await redis_client.delete("test:delete")
        assert deleted is True
        assert await redis_client.exists("test:delete") is False

    @pytest.mark.asyncio
    async def test_flush_pattern(self):
        """Test flushing keys by pattern."""
        redis_client = await get_redis_client()

        # Create multiple keys
        await redis_client.set("test:pattern:1", "data1")
        await redis_client.set("test:pattern:2", "data2")
        await redis_client.set("test:pattern:3", "data3")
        await redis_client.set("test:other", "other")

        # Flush pattern
        deleted = await redis_client.flush_pattern("test:pattern:*")

        assert deleted == 3
        assert await redis_client.exists("test:pattern:1") is False
        assert await redis_client.exists("test:pattern:2") is False
        assert await redis_client.exists("test:pattern:3") is False
        assert await redis_client.exists("test:other") is True


@pytest.mark.integration
class TestCacheServiceIntegration:
    """Integration tests for CacheService."""

    @pytest.fixture
    async def cache_service(self):
        """Create cache service with real Redis."""
        redis_client = await get_redis_client()
        service = CacheService(redis_client)
        yield service

        # Cleanup
        await redis_client.flush_pattern("integration:*")

    @pytest.mark.asyncio
    async def test_get_or_compute_integration(self, cache_service):
        """Test get_or_compute with real Redis."""
        call_count = 0

        async def compute_func():
            nonlocal call_count
            call_count += 1
            return {"result": "computed", "timestamp": datetime.utcnow().isoformat()}

        # First call should compute
        result1 = await cache_service.get_or_compute(
            "integration:compute:test", compute_func, ttl=60
        )
        assert call_count == 1
        assert result1["result"] == "computed"

        # Second call should use cache
        result2 = await cache_service.get_or_compute(
            "integration:compute:test", compute_func, ttl=60
        )
        assert call_count == 1  # Should not increment
        assert result2 == result1  # Should be same cached result

    @pytest.mark.asyncio
    async def test_invalidate_workspace_integration(self, cache_service):
        """Test workspace invalidation with real Redis."""
        redis_client = await get_redis_client()

        # Create workspace-related cache entries
        await redis_client.set(
            CacheKeys.executive_dashboard("ws123", "7d"), {"data": "dashboard"}
        )
        await redis_client.set(CacheKeys.workspace_metrics("ws123", "runs", "2024-01-01"), {"count": 100})
        await redis_client.set(CacheKeys.agent_top("ws123", "7d"), {"agents": []})

        # Invalidate workspace
        deleted = await cache_service.invalidate_workspace("ws123")

        assert deleted >= 3

        # Verify keys are deleted
        assert await redis_client.exists(CacheKeys.executive_dashboard("ws123", "7d")) is False
        assert (
            await redis_client.exists(CacheKeys.workspace_metrics("ws123", "runs", "2024-01-01"))
            is False
        )


@pytest.mark.integration
class TestCacheDecoratorIntegration:
    """Integration tests for cache decorator."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Cleanup test keys."""
        yield
        redis_client = await get_redis_client()
        await redis_client.flush_pattern("integration:decorator:*")

    @pytest.mark.asyncio
    async def test_cached_decorator_integration(self):
        """Test cached decorator with real Redis."""
        call_count = 0

        @cached(
            key_func=lambda workspace_id, **_: f"integration:decorator:{workspace_id}",
            ttl=CacheKeys.TTL_MEDIUM,
        )
        async def get_metrics(workspace_id: str):
            nonlocal call_count
            call_count += 1
            return {"workspace_id": workspace_id, "metrics": [1, 2, 3]}

        # First call should execute function
        result1 = await get_metrics("ws123")
        assert call_count == 1
        assert result1["workspace_id"] == "ws123"

        # Second call should use cache
        result2 = await get_metrics("ws123")
        assert call_count == 1  # Should not increment
        assert result2 == result1

        # Different workspace should execute function
        result3 = await get_metrics("ws456")
        assert call_count == 2
        assert result3["workspace_id"] == "ws456"

    @pytest.mark.asyncio
    async def test_cached_decorator_invalidation(self):
        """Test invalidating cached function results."""

        @cached(
            key_func=lambda user_id, **_: f"integration:decorator:user:{user_id}",
            ttl=CacheKeys.TTL_MEDIUM,
        )
        async def get_user_data(user_id: str):
            return {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}

        # Cache initial result
        result1 = await get_user_data("user123")

        # Invalidate using decorator's invalidate method
        await get_user_data.invalidate("user123")

        # Next call should compute fresh data
        result2 = await get_user_data("user123")

        assert result1["user_id"] == result2["user_id"]
        assert result1["timestamp"] != result2["timestamp"]  # Different timestamp


@pytest.mark.integration
class TestCachePerformance:
    """Performance tests for caching layer."""

    @pytest.fixture
    async def cache_service(self):
        """Create cache service."""
        redis_client = await get_redis_client()
        service = CacheService(redis_client)
        yield service
        await redis_client.flush_pattern("perf:*")

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, cache_service):
        """Test cache hit is significantly faster than computation."""
        import time

        async def slow_computation():
            await asyncio.sleep(0.1)  # Simulate slow query
            return {"result": "data"}

        # First call (cache miss)
        start = time.time()
        await cache_service.get_or_compute("perf:slow", slow_computation, ttl=60)
        miss_time = time.time() - start

        # Second call (cache hit)
        start = time.time()
        await cache_service.get_or_compute("perf:slow", slow_computation, ttl=60)
        hit_time = time.time() - start

        # Cache hit should be at least 10x faster
        assert hit_time < miss_time / 10

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache_service):
        """Test concurrent cache access."""
        call_count = 0

        async def compute_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return {"result": "data"}

        # Multiple concurrent requests
        tasks = [
            cache_service.get_or_compute("perf:concurrent", compute_func, ttl=60)
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All results should be the same
        assert all(r == results[0] for r in results)

        # Due to race conditions, call_count may be > 1 but should be much less than 10
        assert call_count < 5
