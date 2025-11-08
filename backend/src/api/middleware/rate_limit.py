"""Rate limiting middleware."""

from fastapi import Request, HTTPException, status
from typing import Callable
import time
from collections import defaultdict

from ...core.redis import get_redis_client


class RateLimitMiddleware:
    """Rate limiting middleware using Redis."""

    def __init__(
        self,
        app,
        calls: int = 60,
        period: int = 60,
    ):
        self.app = app
        self.calls = calls
        self.period = period

    async def __call__(self, request: Request, call_next: Callable):
        # Get client identifier (IP or user ID)
        client_id = request.client.host

        # Check rate limit
        redis_client = await get_redis_client()
        if redis_client:
            key = f"rate_limit:{client_id}"
            current = await redis_client.get(key)

            if current is None:
                await redis_client.setex(key, self.period, 1)
            elif int(current) >= self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            else:
                await redis_client.incr(key)

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
