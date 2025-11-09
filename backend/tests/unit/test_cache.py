"""Unit tests for cache service."""

import pytest
from src.services.cache.redis_cache import CacheService, CacheKeyValidationError
from unittest.mock import AsyncMock, MagicMock, patch


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


@pytest.mark.asyncio
async def test_cache_key_validation_valid_keys():
    """Test cache key validation with valid keys."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    valid_keys = [
        "simple_key",
        "user:123:profile",
        "metric:cpu:user:123:30d",
        "test-key",
        "test.key",
        "TEST_KEY_123",
    ]

    for key in valid_keys:
        # Should not raise exception
        cache._validate_cache_key(key)


def test_cache_key_validation_invalid_keys():
    """Test cache key validation with invalid keys."""
    mock_redis = MagicMock()
    cache = CacheService(mock_redis)

    # Empty key
    with pytest.raises(CacheKeyValidationError, match="cannot be empty"):
        cache._validate_cache_key("")

    # Too long key
    long_key = "x" * 257
    with pytest.raises(CacheKeyValidationError, match="exceeds maximum length"):
        cache._validate_cache_key(long_key)

    # Invalid characters
    invalid_keys = [
        "key with spaces",
        "key@invalid",
        "key#invalid",
        "key$invalid",
        "key%invalid",
        "key/invalid",
    ]

    for key in invalid_keys:
        with pytest.raises(CacheKeyValidationError, match="invalid characters"):
            cache._validate_cache_key(key)


@pytest.mark.asyncio
async def test_cache_get_with_invalid_key():
    """Test cache get with invalid key returns None and logs warning."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    # Invalid key should return None without calling Redis
    result = await cache.get("invalid key with spaces")
    assert result is None
    mock_redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_cache_set_with_invalid_key():
    """Test cache set with invalid key doesn't call Redis."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    # Invalid key should not call Redis
    await cache.set("invalid@key", {"value": 123})
    mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_cache_clear_pattern_uses_scan():
    """Test cache clear pattern uses SCAN instead of KEYS."""
    mock_redis = AsyncMock()
    cache = CacheService(mock_redis)

    # Mock SCAN to return keys in batches
    mock_redis.scan.side_effect = [
        (10, ["key1", "key2"]),  # First batch
        (20, ["key3", "key4"]),  # Second batch
        (0, ["key5"]),  # Last batch (cursor = 0)
    ]

    await cache.clear_pattern("test:*")

    # Verify SCAN was called, not KEYS
    assert mock_redis.scan.call_count == 3
    assert mock_redis.keys.call_count == 0

    # Verify delete was called for all keys
    assert mock_redis.delete.call_count == 3


@pytest.mark.asyncio
async def test_cache_get_hit_records_metric():
    """Test cache hit records metric."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = '{"value": 123}'
    cache = CacheService(mock_redis)

    with patch("src.services.cache.redis_cache.record_cache_hit") as mock_hit:
        result = await cache.get("test:key")
        assert result == {"value": 123}
        mock_hit.assert_called_once_with("get", "test:key")


@pytest.mark.asyncio
async def test_cache_get_miss_records_metric():
    """Test cache miss records metric."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    cache = CacheService(mock_redis)

    with patch("src.services.cache.redis_cache.record_cache_miss") as mock_miss:
        result = await cache.get("test:key")
        assert result is None
        mock_miss.assert_called_once_with("get", "test:key")


@pytest.mark.asyncio
async def test_cache_error_records_metric():
    """Test cache errors record metrics."""
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection error")
    cache = CacheService(mock_redis)

    with patch("src.services.cache.redis_cache.record_cache_error") as mock_error:
        result = await cache.get("test:key")
        assert result is None
        mock_error.assert_called_once_with("get", "Exception")


def test_get_key_pattern():
    """Test key pattern extraction for metrics."""
    mock_redis = MagicMock()
    cache = CacheService(mock_redis)

    assert cache._get_key_pattern("metric:cpu:user:123") == "metric:cpu"
    assert cache._get_key_pattern("user:123") == "user:123"
    assert cache._get_key_pattern("simple") == "simple"
    assert cache._get_key_pattern("") == "unknown"


@pytest.mark.asyncio
async def test_cache_invalidation_pattern():
    """Test cache invalidation records metric."""
    mock_redis = AsyncMock()
    mock_redis.scan.return_value = (0, ["key1", "key2"])
    cache = CacheService(mock_redis)

    with patch(
        "src.services.cache.redis_cache.record_cache_invalidation"
    ) as mock_invalidation:
        await cache.clear_pattern("test:*")
        mock_invalidation.assert_called_once_with("test:*")
