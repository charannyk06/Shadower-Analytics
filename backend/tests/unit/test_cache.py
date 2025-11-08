"""Unit tests for cache service."""

import pytest
from src.services.cache.redis_cache import CacheService
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_cache_get_set():
    """Test cache get and set operations."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    # Test set
    await cache.set("test_key", {"value": 123})
    mock_redis.setex.assert_called_once()

    # Test get
    mock_redis.get.return_value = '{"value": 123}'
    result = await cache.get("test_key")
    assert result == {"value": 123}


@pytest.mark.asyncio
async def test_cache_delete():
    """Test cache delete operation."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    await cache.delete("test_key")
    mock_redis.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_exists():
    """Test cache exists check."""
    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 1
    cache = CacheService(mock_redis)

    result = await cache.exists("test_key")
    assert result is True
