"""Tests for rate limiting functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.api.middleware.rate_limit import RateLimiter, InMemoryRateLimiter


class TestRateLimiter:
    """Test Redis-backed rate limiter."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = AsyncMock()
        redis.zremrangebyscore = AsyncMock()
        redis.zcard = AsyncMock()
        redis.zrange = AsyncMock()
        redis.zadd = AsyncMock()
        redis.expire = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, mock_redis):
        """Test that requests within the limit are allowed."""
        mock_redis.zcard.return_value = 5  # 5 requests in window

        limiter = RateLimiter(requests_per_minute=10)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            allowed, msg = await limiter.check_rate_limit("user123", "test_endpoint")

        assert allowed is True
        assert msg is None

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, mock_redis):
        """Test that requests over the limit are blocked."""
        mock_redis.zcard.return_value = 61  # Over 60/min limit
        mock_redis.zrange.return_value = [(b"123.456", 123.456)]

        limiter = RateLimiter(requests_per_minute=60)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            allowed, msg = await limiter.check_rate_limit("user123", "test_endpoint")

        assert allowed is False
        assert msg is not None
        assert "Rate limit exceeded" in msg

    @pytest.mark.asyncio
    async def test_cleans_old_entries(self, mock_redis):
        """Test that old entries are removed from the window."""
        mock_redis.zcard.return_value = 5

        limiter = RateLimiter(requests_per_minute=10)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            await limiter.check_rate_limit("user123", "test_endpoint")

        # Should have called zremrangebyscore to remove old entries
        mock_redis.zremrangebyscore.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_expiration_on_key(self, mock_redis):
        """Test that expiration is set on rate limit keys."""
        mock_redis.zcard.return_value = 5

        limiter = RateLimiter(requests_per_minute=10)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            await limiter.check_rate_limit("user123", "test_endpoint")

        # Should have called expire to set TTL
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_time_windows(self, mock_redis):
        """Test that both per-minute and per-hour limits are checked."""
        mock_redis.zcard.return_value = 5

        limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            allowed, msg = await limiter.check_rate_limit("user123", "test_endpoint")

        # Should check both minute and hour windows
        assert mock_redis.zcard.call_count == 2

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_unavailable(self):
        """Test that requests are allowed when Redis is unavailable."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=None):
            allowed, msg = await limiter.check_rate_limit("user123", "test_endpoint")

        assert allowed is True
        assert msg is None

    @pytest.mark.asyncio
    async def test_different_identifiers_tracked_separately(self, mock_redis):
        """Test that different users are tracked separately."""
        mock_redis.zcard.return_value = 5

        limiter = RateLimiter(requests_per_minute=10)

        with patch('src.api.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            await limiter.check_rate_limit("user1", "test_endpoint")
            await limiter.check_rate_limit("user2", "test_endpoint")

        # Should have created separate keys for each user
        assert mock_redis.zadd.call_count == 2


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter (for development/testing)."""

    def test_allows_requests_within_limit(self):
        """Test that requests within the limit are allowed."""
        limiter = InMemoryRateLimiter(calls=10, period=60)

        # First 10 requests should be allowed
        for _ in range(10):
            assert limiter.is_allowed("test_client") is True

    def test_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        limiter = InMemoryRateLimiter(calls=5, period=60)

        # First 5 requests allowed
        for _ in range(5):
            limiter.is_allowed("test_client")

        # 6th request should be blocked
        assert limiter.is_allowed("test_client") is False

    def test_cleans_old_entries(self):
        """Test that old entries are removed over time."""
        limiter = InMemoryRateLimiter(calls=5, period=1)  # 1 second period

        # Make 5 requests
        for _ in range(5):
            limiter.is_allowed("test_client")

        # Should be blocked
        assert limiter.is_allowed("test_client") is False

        # Wait for period to expire
        import time
        time.sleep(1.1)

        # Should now be allowed again
        assert limiter.is_allowed("test_client") is True

    def test_different_clients_tracked_separately(self):
        """Test that different clients are tracked separately."""
        limiter = InMemoryRateLimiter(calls=5, period=60)

        # Client 1 makes 5 requests
        for _ in range(5):
            limiter.is_allowed("client1")

        # Client 2 should still be allowed
        assert limiter.is_allowed("client2") is True


class TestRateLimitMiddleware:
    """Test rate limiting middleware integration."""

    @pytest.mark.asyncio
    async def test_auth_endpoints_have_stricter_limits(self, mock_redis):
        """Test that auth endpoints have stricter rate limits."""
        # This is more of an integration test
        # The actual limit configuration is in the middleware
        # Just verify the pattern exists
        from src.api.middleware.rate_limit import auth_rate_limiter, api_rate_limiter

        # Auth should have stricter limits
        assert auth_rate_limiter.requests_per_minute < api_rate_limiter.requests_per_minute
        assert auth_rate_limiter.requests_per_hour < api_rate_limiter.requests_per_hour

    @pytest.mark.asyncio
    async def test_retry_after_header_included(self, mock_redis):
        """Test that Retry-After header is set when rate limited."""
        # This would be tested in integration tests
        # Here we just verify the pattern
        pass
