"""API Gateway for Shadower Analytics.

Provides centralized request routing, rate limiting, authentication,
and response caching for the analytics service.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional, Callable
import logging
import time
import hashlib
import json
from datetime import datetime

from ..core.config import settings
from ..core.redis import get_redis_client
from ..core.security import verify_token

logger = logging.getLogger(__name__)


# Rate limiting configuration
RATE_LIMITS = {
    "default": {
        "requests": 1000,
        "window": 3600  # 1 hour
    },
    "analytics": {
        "requests": 100,
        "window": 60  # 1 minute
    },
    "reports": {
        "requests": 10,
        "window": 60  # 1 minute
    },
    "exports": {
        "requests": 5,
        "window": 3600  # 1 hour
    },
    "dashboard": {
        "requests": 200,
        "window": 60  # 1 minute
    },
    "admin": {
        "requests": 50,
        "window": 60  # 1 minute
    }
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware per workspace/user.

    Uses Redis for distributed counting across multiple instances.
    Implements sliding window algorithm for accurate rate limiting.
    """

    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = RATE_LIMITS

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        # Skip rate limiting for health and docs endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Get client identifier (user ID or IP)
        user_id = getattr(request.state, "user", {}).get("sub")
        client_ip = request.client.host if request.client else "unknown"
        identifier = user_id or client_ip

        # Determine rate limit type based on endpoint
        limit_type = self._get_limit_type(request.url.path)

        # Check rate limit
        try:
            rate_info = await self._check_rate_limit(identifier, request.url.path, limit_type)

            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

            return response

        except HTTPException as e:
            # Rate limit exceeded
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "code": "RATE_LIMIT_EXCEEDED"},
                headers=e.headers
            )
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return await call_next(request)

    def _get_limit_type(self, path: str) -> str:
        """Determine rate limit type based on endpoint path."""
        if "/analytics/" in path:
            return "analytics"
        elif "/reports/" in path:
            return "reports"
        elif "/exports/" in path:
            return "exports"
        elif "/dashboard/" in path:
            return "dashboard"
        elif "/admin/" in path:
            return "admin"
        else:
            return "default"

    async def _check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit_type: str = "default"
    ) -> Dict[str, Any]:
        """Check if rate limit is exceeded."""
        limit = self.rate_limits[limit_type]
        redis = await get_redis_client()

        if not redis:
            logger.warning("Redis unavailable, rate limiting disabled")
            return {
                "limit": limit["requests"],
                "remaining": limit["requests"],
                "reset": int(time.time() + limit["window"])
            }

        key = f"ratelimit:{limit_type}:{identifier}"
        now = int(time.time())
        window_start = now - limit["window"]

        try:
            # Use Redis sorted set for sliding window
            # Remove old entries
            await redis.redis.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            current_count = await redis.redis.zcard(key)

            if current_count >= limit["requests"]:
                # Get oldest request to calculate reset time
                oldest = await redis.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1] + limit["window"])
                else:
                    reset_time = now + limit["window"]

                retry_after = reset_time - now

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {limit['requests']} requests per {limit['window']} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

            # Add current request
            await redis.redis.zadd(key, {str(now): now})
            await redis.redis.expire(key, limit["window"])

            # Calculate reset time
            oldest = await redis.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = int(oldest[0][1] + limit["window"])
            else:
                reset_time = now + limit["window"]

            return {
                "limit": limit["requests"],
                "remaining": limit["requests"] - current_count - 1,
                "reset": reset_time
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open
            return {
                "limit": limit["requests"],
                "remaining": limit["requests"],
                "reset": now + limit["window"]
            }


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT validation and workspace verification middleware.

    Validates JWT tokens and injects user context into request state.
    """

    async def dispatch(self, request: Request, call_next):
        """Validate JWT and inject user context."""
        # Skip auth for public endpoints
        public_paths = [
            "/",
            "/health",
            "/health/detailed",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics"
        ]

        if request.url.path in public_paths:
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Missing or invalid authorization header",
                    "code": "UNAUTHORIZED"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = auth_header.split(" ")[1]

        try:
            # Verify token
            payload = await verify_token(token)

            # Inject user context into request state
            request.state.user = {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "workspace_id": payload.get("workspaceId"),
                "workspace_ids": payload.get("workspaces", []),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", [])
            }

            # Add user info to logger context
            logger.info(
                f"Authenticated request: user={payload.get('sub')}, "
                f"workspace={payload.get('workspaceId')}, "
                f"path={request.url.path}"
            )

        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": str(e) if str(e) else "Invalid authentication credentials",
                    "code": "INVALID_TOKEN"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        response = await call_next(request)
        return response


class CacheMiddleware(BaseHTTPMiddleware):
    """Response caching middleware for GET requests.

    Cache key is based on URL + query params + user context.
    Only caches successful GET requests (status 200).
    """

    def __init__(
        self,
        app,
        default_ttl: int = 300,  # 5 minutes default
        cache_patterns: Optional[Dict[str, int]] = None
    ):
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_patterns = cache_patterns or {
            "/api/v1/dashboard/": 60,      # 1 minute
            "/api/v1/analytics/": 300,     # 5 minutes
            "/api/v1/reports/": 600,       # 10 minutes
            "/api/v1/metrics/": 120,       # 2 minutes
        }

    async def dispatch(self, request: Request, call_next):
        """Cache GET request responses."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Skip caching for certain endpoints
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Generate cache key
        cache_key = await self._generate_cache_key(request)

        # Try to get from cache
        redis = await get_redis_client()
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit: {cache_key}")
                    # Return cached response
                    return JSONResponse(
                        content=cached["content"],
                        status_code=cached["status_code"],
                        headers={"X-Cache": "HIT"}
                    )
            except Exception as e:
                logger.error(f"Cache retrieval error: {e}")

        # Cache miss - proceed with request
        response = await call_next(request)

        # Cache successful responses
        if redis and response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # Parse response content
                content = json.loads(body.decode())

                # Determine TTL based on endpoint
                ttl = self._get_ttl(request.url.path)

                # Store in cache
                cache_data = {
                    "content": content,
                    "status_code": response.status_code
                }
                await redis.set(cache_key, cache_data, expire=ttl)

                logger.debug(f"Cache miss - stored: {cache_key} (TTL: {ttl}s)")

                # Return response with cache header
                return JSONResponse(
                    content=content,
                    status_code=response.status_code,
                    headers={"X-Cache": "MISS"}
                )

            except Exception as e:
                logger.error(f"Cache storage error: {e}")

        return response

    async def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Get user context
        user_id = getattr(request.state, "user", {}).get("user_id", "anonymous")
        workspace_id = getattr(request.state, "user", {}).get("workspace_id", "none")

        # Build cache key components
        path = request.url.path
        query = str(request.query_params)

        # Create hash of components
        key_data = f"{path}:{query}:{user_id}:{workspace_id}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()

        return f"cache:response:{key_hash}"

    def _get_ttl(self, path: str) -> int:
        """Get TTL for cache based on path."""
        for pattern, ttl in self.cache_patterns.items():
            if path.startswith(pattern):
                return ttl
        return self.default_ttl


class APIGateway:
    """API Gateway for Shadower Analytics.

    Centralizes middleware configuration, route management,
    and API versioning.
    """

    def __init__(self):
        """Initialize API Gateway."""
        self.app = FastAPI(
            title="Shadower Analytics API",
            description=self._get_description(),
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        self.setup_middleware()
        self.setup_exception_handlers()

    def setup_middleware(self):
        """Configure all middleware layers."""
        # CORS configuration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS + ["https://app.shadower.ai"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Custom middleware (order matters!)
        # 1. Authentication (verify user)
        self.app.add_middleware(AuthenticationMiddleware)

        # 2. Rate limiting (after auth to use user ID)
        self.app.add_middleware(RateLimitMiddleware)

        # 3. Caching (last, after auth and rate limit)
        self.app.add_middleware(CacheMiddleware)

    def setup_exception_handlers(self):
        """Configure custom exception handlers."""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle HTTP exceptions with standardized format."""
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "code": "HTTP_ERROR",
                    "path": request.url.path,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle unexpected exceptions."""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "path": request.url.path,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    def include_router(self, router, **kwargs):
        """Include a router in the application."""
        self.app.include_router(router, **kwargs)

    def add_middleware(self, middleware_class, **kwargs):
        """Add middleware to the application."""
        self.app.add_middleware(middleware_class, **kwargs)

    def on_event(self, event_type: str) -> Callable:
        """Register event handlers."""
        return self.app.on_event(event_type)

    @staticmethod
    def _get_description() -> str:
        """Get API description for OpenAPI docs."""
        return """
## Overview
Analytics API for Shadower platform providing:
- Real-time metrics and dashboards
- Historical analytics and trends
- Predictive insights and anomaly detection
- Custom reports and exports

## Authentication
All endpoints require JWT authentication.
Include token in Authorization header:
```
Authorization: Bearer <token>
```

## Rate Limiting
API calls are rate-limited per workspace:
- **Default**: 1000 requests/hour
- **Analytics**: 100 requests/minute
- **Reports**: 10 requests/minute
- **Exports**: 5 requests/hour
- **Dashboard**: 200 requests/minute
- **Admin**: 50 requests/minute

Check response headers for limit status:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Response Caching
GET requests are cached to improve performance:
- Dashboard endpoints: 1 minute
- Analytics endpoints: 5 minutes
- Reports endpoints: 10 minutes
- Metrics endpoints: 2 minutes

Check `X-Cache` header: `HIT` (from cache) or `MISS` (fresh data)

## Versioning
API is versioned with prefix `/api/v1/`
Breaking changes will increment version number.
        """
