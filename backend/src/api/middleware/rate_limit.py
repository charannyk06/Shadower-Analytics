"""Rate limiting middleware for authentication endpoints."""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from datetime import datetime
import logging
import time
from functools import wraps
from collections import defaultdict

from ...core.redis import get_redis_client
from ...core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis for distributed rate limiting.

    Uses a sliding window algorithm for accurate rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            requests_per_hour: Maximum requests allowed per hour
        """
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.requests_per_hour = requests_per_hour or settings.RATE_LIMIT_PER_HOUR

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "default",
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier for the client (e.g., IP, user ID)
            endpoint: The endpoint being accessed

        Returns:
            Tuple of (is_allowed, error_message)
        """
        redis = await get_redis_client()
        if not redis:
            # If Redis is unavailable, allow the request
            logger.warning("Redis unavailable, rate limiting disabled")
            return True, None

        try:
            # Check per-minute limit
            if self.requests_per_minute:
                allowed, msg = await self._check_window(
                    redis,
                    identifier,
                    endpoint,
                    window_seconds=60,
                    max_requests=self.requests_per_minute,
                    window_name="minute",
                )
                if not allowed:
                    return False, msg

            # Check per-hour limit
            if self.requests_per_hour:
                allowed, msg = await self._check_window(
                    redis,
                    identifier,
                    endpoint,
                    window_seconds=3600,
                    max_requests=self.requests_per_hour,
                    window_name="hour",
                )
                if not allowed:
                    return False, msg

            return True, None

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return True, None

    async def _check_window(
        self,
        redis,
        identifier: str,
        endpoint: str,
        window_seconds: int,
        max_requests: int,
        window_name: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check rate limit for a specific time window.

        Uses Redis sorted sets with timestamps for sliding window.
        """
        key = f"ratelimit:{endpoint}:{identifier}:{window_name}"
        now = datetime.now().timestamp()
        window_start = now - window_seconds

        # Remove old entries outside the window
        await redis.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        request_count = await redis.zcard(key)

        if request_count >= max_requests:
            # Get oldest request time to calculate retry-after
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(window_seconds - (now - oldest[0][1]))
                msg = (
                    f"Rate limit exceeded. Maximum {max_requests} requests per {window_name}. "
                    f"Retry after {retry_after} seconds."
                )
                return False, msg

        # Add current request
        await redis.zadd(key, {str(now): now})

        # Set expiration on the key
        await redis.expire(key, window_seconds)

        return True, None


# Pre-configured rate limiters for different endpoint types
auth_rate_limiter = RateLimiter(
    requests_per_minute=5,  # Stricter limit for auth endpoints
    requests_per_hour=50,
)

api_rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
)


async def rate_limit_dependency(
    request: Request,
    limiter: RateLimiter = auth_rate_limiter,
):
    """
    FastAPI dependency for rate limiting.

    Usage:
        @app.post("/auth/login", dependencies=[Depends(rate_limit_dependency)])
        async def login(...):
            ...
    """
    # Get client identifier (IP address or user ID if authenticated)
    client_ip = request.client.host if request.client else "unknown"

    # If user is authenticated, use user ID for more accurate limiting
    user_id = getattr(request.state, "user", {}).get("sub")
    identifier = user_id or client_ip

    # Get endpoint path
    endpoint = request.url.path

    # Check rate limit
    allowed, error_msg = await limiter.check_rate_limit(identifier, endpoint)

    if not allowed:
        logger.warning(
            f"Rate limit exceeded for {identifier} on {endpoint}: {error_msg}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg,
            headers={"Retry-After": "60"},
        )


def rate_limit(
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None,
):
    """
    Decorator for rate limiting specific endpoints.

    Usage:
        @app.post("/auth/login")
        @rate_limit(requests_per_minute=5, requests_per_hour=50)
        async def login(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                limiter = RateLimiter(requests_per_minute, requests_per_hour)

                client_ip = request.client.host if request.client else "unknown"
                user_id = getattr(request.state, "user", {}).get("sub")
                identifier = user_id or client_ip
                endpoint = request.url.path

                allowed, error_msg = await limiter.check_rate_limit(
                    identifier, endpoint
                )

                if not allowed:
                    logger.warning(
                        f"Rate limit exceeded for {identifier} on {endpoint}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error_msg,
                        headers={"Retry-After": "60"},
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimitMiddleware:
    """
    Middleware for global rate limiting.

    Add to your FastAPI app:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            limiter: Custom rate limiter (optional)
        """
        self.app = app
        self.limiter = limiter or api_rate_limiter

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user", {}).get("sub")
        identifier = user_id or client_ip

        # Apply stricter limits to auth endpoints
        limiter = self.limiter
        if request.url.path.startswith("/api/v1/auth/"):
            limiter = auth_rate_limiter

        # Check rate limit
        allowed, error_msg = await limiter.check_rate_limit(
            identifier, request.url.path
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        return response


class InMemoryRateLimiter:
    """Simple in-memory rate limiter (for development)."""

    def __init__(self, calls: int = 60, period: int = 60):
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request."""
        now = time.time()
        # Remove old entries
        self.clients[client_id] = [
            timestamp
            for timestamp in self.clients[client_id]
            if now - timestamp < self.period
        ]

        # Check limit
        if len(self.clients[client_id]) >= self.calls:
            return False

        # Add new timestamp
        self.clients[client_id].append(now)
        return True
