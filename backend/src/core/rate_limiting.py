"""Rate limiting utilities using Redis for API protection."""

import time
import logging
from typing import Dict, Tuple, Any, Optional
from fastapi import HTTPException, Request
from .redis import get_redis_client

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration for different endpoints."""

    # Format: (requests, window_seconds)
    DEFAULT = (1000, 3600)  # 1000 requests per hour
    API_KEY = (5000, 3600)  # 5000 requests per hour for API keys
    EXPORT = (10, 3600)  # 10 exports per hour
    REPORT = (50, 3600)  # 50 reports per hour
    AUTH = (5, 300)  # 5 auth attempts per 5 minutes
    ANALYTICS = (100, 60)  # 100 analytics requests per minute


class RateLimiter:
    """
    Rate limiter using Redis and sliding window algorithm.

    Provides flexible rate limiting for different API endpoints.
    """

    def __init__(self):
        """Initialize rate limiter."""
        self.limits = {
            "default": RateLimitConfig.DEFAULT,
            "api_key": RateLimitConfig.API_KEY,
            "export": RateLimitConfig.EXPORT,
            "report": RateLimitConfig.REPORT,
            "auth": RateLimitConfig.AUTH,
            "analytics": RateLimitConfig.ANALYTICS,
        }

    async def check_rate_limit(
        self,
        key: str,
        limit_type: str = "default",
        custom_limit: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Check and update rate limit using sliding window algorithm.

        Args:
            key: Unique identifier (e.g., user_id, ip_address, api_key)
            limit_type: Type of rate limit to apply
            custom_limit: Optional custom limit (requests, window_seconds)

        Returns:
            Dictionary with rate limit information

        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get limit configuration
        limit, window = custom_limit or self.limits.get(limit_type, self.limits["default"])

        redis = await get_redis_client()
        if not redis:
            logger.warning("Redis not available, skipping rate limit check")
            return {
                "limit": limit,
                "remaining": limit,
                "reset_in": window,
            }

        # Create Redis key for this rate limit
        redis_key = f"rate_limit:{limit_type}:{key}"

        try:
            # Current timestamp
            now = time.time()
            window_start = now - window

            # Remove old entries outside the sliding window
            await redis.zremrangebyscore(redis_key, 0, window_start)

            # Count requests in current window
            request_count = await redis.zcard(redis_key)

            if request_count >= limit:
                # Rate limit exceeded
                # Get the oldest request to calculate reset time
                oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    reset_in = int(oldest[0][1] + window - now)
                else:
                    reset_in = window

                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window": window,
                        "reset_in": reset_in,
                    },
                    headers={"Retry-After": str(reset_in)},
                )

            # Add current request to the sliding window
            await redis.zadd(redis_key, {str(now): now})

            # Set expiration on the key (cleanup)
            await redis.expire(redis_key, window)

            # Calculate remaining requests
            remaining = limit - request_count - 1

            return {
                "limit": limit,
                "remaining": remaining,
                "reset_in": window,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return {
                "limit": limit,
                "remaining": limit,
                "reset_in": window,
            }

    async def reset_rate_limit(self, key: str, limit_type: str = "default") -> bool:
        """
        Reset rate limit for a specific key.

        Args:
            key: Unique identifier
            limit_type: Type of rate limit

        Returns:
            True if reset successful, False otherwise
        """
        try:
            redis = await get_redis_client()
            if not redis:
                return False

            redis_key = f"rate_limit:{limit_type}:{key}"
            await redis.delete(redis_key)
            return True

        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False

    async def get_rate_limit_status(
        self, key: str, limit_type: str = "default"
    ) -> Dict[str, Any]:
        """
        Get current rate limit status without incrementing.

        Args:
            key: Unique identifier
            limit_type: Type of rate limit

        Returns:
            Dictionary with current rate limit status
        """
        limit, window = self.limits.get(limit_type, self.limits["default"])

        redis = await get_redis_client()
        if not redis:
            return {
                "limit": limit,
                "remaining": limit,
                "reset_in": window,
                "current_count": 0,
            }

        redis_key = f"rate_limit:{limit_type}:{key}"

        try:
            now = time.time()
            window_start = now - window

            # Remove old entries
            await redis.zremrangebyscore(redis_key, 0, window_start)

            # Count current requests
            request_count = await redis.zcard(redis_key)

            # Get reset time
            oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                reset_in = int(oldest[0][1] + window - now)
            else:
                reset_in = window

            return {
                "limit": limit,
                "remaining": max(0, limit - request_count),
                "reset_in": reset_in,
                "current_count": request_count,
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "reset_in": window,
                "current_count": 0,
            }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_rate_limit(
    request: Request,
    limit_type: str = "default",
    custom_limit: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    """
    Check rate limit for a request.

    Uses IP address or user_id as the key.

    Args:
        request: FastAPI request object
        limit_type: Type of rate limit to apply
        custom_limit: Optional custom limit

    Returns:
        Rate limit information
    """
    # Determine rate limit key
    # Priority: user_id > api_key > ip_address
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        key = f"user:{user.id}"
    elif hasattr(request.state, "api_key"):
        key = f"api_key:{request.state.api_key}"
    else:
        # Use client IP address
        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}"

    limiter = get_rate_limiter()
    return await limiter.check_rate_limit(key, limit_type, custom_limit)


def rate_limit(
    limit_type: str = "default",
    requests: Optional[int] = None,
    window: Optional[int] = None,
):
    """
    Decorator for rate limiting endpoints.

    Usage:
        @router.get("/analytics")
        @rate_limit("analytics")
        async def get_analytics():
            ...

        @router.post("/export")
        @rate_limit(requests=10, window=3600)
        async def export_data():
            ...

    Args:
        limit_type: Predefined limit type
        requests: Optional custom request limit
        window: Optional custom window in seconds
    """

    def decorator(func):
        async def wrapper(*args, request: Request, **kwargs):
            # Custom limit if provided
            custom = (requests, window) if requests and window else None

            # Check rate limit
            await check_rate_limit(request, limit_type, custom)

            # Call original function
            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator
