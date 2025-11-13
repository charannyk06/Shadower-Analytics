"""Unit tests for API Gateway components."""

import pytest
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import time

from backend.src.api.gateway import (
    APIGateway,
    RateLimitMiddleware,
    AuthenticationMiddleware,
    CacheMiddleware,
    RATE_LIMITS
)
from backend.src.api.models import ErrorCode


class TestAPIGateway:
    """Test APIGateway class."""

    def test_gateway_initialization(self):
        """Test gateway initializes correctly."""
        gateway = APIGateway()

        assert gateway.app is not None
        assert isinstance(gateway.app, FastAPI)
        assert gateway.app.title == "Shadower Analytics API"
        assert gateway.app.version == "1.0.0"

    def test_gateway_middleware_setup(self):
        """Test middleware is configured correctly."""
        gateway = APIGateway()

        # Check middleware is added (by checking app.user_middleware)
        middleware_names = [m.cls.__name__ for m in gateway.app.user_middleware]

        # Should have CORS, Auth, RateLimit, Cache middleware
        assert "CORSMiddleware" in middleware_names
        assert "AuthenticationMiddleware" in middleware_names
        assert "RateLimitMiddleware" in middleware_names
        assert "CacheMiddleware" in middleware_names

    def test_include_router(self):
        """Test router inclusion."""
        from fastapi import APIRouter

        gateway = APIGateway()
        router = APIRouter()

        @router.get("/test")
        async def test_endpoint():
            return {"test": "endpoint"}

        gateway.include_router(router)

        # Router should be included
        client = TestClient(gateway.app)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"test": "endpoint"}


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.fixture
    def app_with_rate_limit(self):
        """Create test app with rate limiting."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"success": True}

        return app

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_allows_within_limit(self, app_with_rate_limit):
        """Test requests within rate limit are allowed."""
        client = TestClient(app_with_rate_limit)

        # Mock Redis to allow requests
        with patch('backend.src.api.gateway.get_redis_client') as mock_redis:
            mock_client = AsyncMock()
            mock_client.redis.zremrangebyscore = AsyncMock()
            mock_client.redis.zcard = AsyncMock(return_value=0)
            mock_client.redis.zadd = AsyncMock()
            mock_client.redis.expire = AsyncMock()
            mock_client.redis.zrange = AsyncMock(return_value=[])
            mock_redis.return_value = mock_client

            response = client.get("/test")

            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

    def test_rate_limit_type_detection(self):
        """Test correct rate limit type is detected from path."""
        middleware = RateLimitMiddleware(FastAPI())

        assert middleware._get_limit_type("/api/v1/analytics/metrics") == "analytics"
        assert middleware._get_limit_type("/api/v1/reports/generate") == "reports"
        assert middleware._get_limit_type("/api/v1/exports/csv") == "exports"
        assert middleware._get_limit_type("/api/v1/dashboard/executive") == "dashboard"
        assert middleware._get_limit_type("/api/v1/admin/users") == "admin"
        assert middleware._get_limit_type("/api/v1/other") == "default"

    def test_rate_limits_configuration(self):
        """Test rate limits are configured correctly."""
        assert "default" in RATE_LIMITS
        assert "analytics" in RATE_LIMITS
        assert "reports" in RATE_LIMITS
        assert "exports" in RATE_LIMITS

        # Check analytics has strict limit
        assert RATE_LIMITS["analytics"]["requests"] == 100
        assert RATE_LIMITS["analytics"]["window"] == 60

        # Check exports has very strict limit
        assert RATE_LIMITS["exports"]["requests"] == 5
        assert RATE_LIMITS["exports"]["window"] == 3600


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    @pytest.fixture
    def app_with_auth(self):
        """Create test app with authentication."""
        app = FastAPI()
        app.add_middleware(AuthenticationMiddleware)

        @app.get("/protected")
        async def protected_endpoint(request: Request):
            return {"user": request.state.user}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return app

    def test_auth_skips_public_endpoints(self, app_with_auth):
        """Test authentication is skipped for public endpoints."""
        client = TestClient(app_with_auth)

        # Health endpoint should work without auth
        response = client.get("/health")
        assert response.status_code == 200

    def test_auth_requires_header_for_protected_endpoints(self, app_with_auth):
        """Test protected endpoints require auth header."""
        client = TestClient(app_with_auth)

        # Should fail without auth header
        response = client.get("/protected")
        assert response.status_code == 401
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_auth_validates_token(self, app_with_auth):
        """Test token validation."""
        client = TestClient(app_with_auth)

        # Mock successful token verification
        with patch('backend.src.api.gateway.verify_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "user123",
                "email": "test@example.com",
                "workspaceId": "ws123",
                "workspaces": ["ws123"],
                "role": "user",
                "permissions": []
            }

            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer valid-token"}
            )

            assert response.status_code == 200
            assert "user" in response.json()
            mock_verify.assert_called_once()


class TestCacheMiddleware:
    """Test caching middleware."""

    @pytest.fixture
    def app_with_cache(self):
        """Create test app with caching."""
        app = FastAPI()
        app.add_middleware(CacheMiddleware, default_ttl=60)

        @app.get("/data")
        async def get_data():
            return {"data": "test", "timestamp": time.time()}

        @app.post("/data")
        async def post_data():
            return {"success": True}

        return app

    def test_cache_only_caches_get_requests(self, app_with_cache):
        """Test only GET requests are cached."""
        client = TestClient(app_with_cache)

        # POST should not be cached
        response = client.post("/data")
        assert response.status_code == 200
        # No cache header expected for POST
        assert "X-Cache" not in response.headers

    @pytest.mark.asyncio
    async def test_cache_generates_unique_keys(self):
        """Test cache key generation."""
        middleware = CacheMiddleware(FastAPI())

        # Mock request
        request1 = Mock(spec=Request)
        request1.url.path = "/api/v1/data"
        request1.query_params = {"param": "value1"}
        request1.state.user = {"user_id": "user1", "workspace_id": "ws1"}

        request2 = Mock(spec=Request)
        request2.url.path = "/api/v1/data"
        request2.query_params = {"param": "value2"}
        request2.state.user = {"user_id": "user1", "workspace_id": "ws1"}

        key1 = await middleware._generate_cache_key(request1)
        key2 = await middleware._generate_cache_key(request2)

        # Keys should be different for different params
        assert key1 != key2
        assert key1.startswith("cache:response:")
        assert key2.startswith("cache:response:")

    def test_cache_ttl_configuration(self):
        """Test cache TTL is configured correctly."""
        middleware = CacheMiddleware(FastAPI())

        # Check TTL for different paths
        assert middleware._get_ttl("/api/v1/dashboard/executive") == 60
        assert middleware._get_ttl("/api/v1/analytics/metrics") == 300
        assert middleware._get_ttl("/api/v1/reports/list") == 600
        assert middleware._get_ttl("/api/v1/other") == middleware.default_ttl


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    def test_rate_limit_values_are_reasonable(self):
        """Test rate limits are configured with reasonable values."""
        # Default should allow good throughput
        assert RATE_LIMITS["default"]["requests"] >= 100
        assert RATE_LIMITS["default"]["window"] >= 60

        # Analytics should be reasonable for dashboard usage
        assert RATE_LIMITS["analytics"]["requests"] >= 10
        assert RATE_LIMITS["analytics"]["window"] >= 60

        # Exports should be limited (expensive operations)
        assert RATE_LIMITS["exports"]["requests"] <= 10
        assert RATE_LIMITS["exports"]["window"] >= 300

    def test_all_rate_limits_have_required_fields(self):
        """Test all rate limits have requests and window fields."""
        for limit_type, config in RATE_LIMITS.items():
            assert "requests" in config, f"{limit_type} missing 'requests'"
            assert "window" in config, f"{limit_type} missing 'window'"
            assert config["requests"] > 0, f"{limit_type} has invalid requests"
            assert config["window"] > 0, f"{limit_type} has invalid window"


@pytest.mark.asyncio
async def test_gateway_exception_handlers():
    """Test gateway exception handlers."""
    gateway = APIGateway()

    # Add test endpoint that raises exception
    @gateway.app.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=400, detail="Test error")

    @gateway.app.get("/server_error")
    async def server_error_endpoint():
        raise Exception("Internal error")

    client = TestClient(gateway.app)

    # Test HTTP exception handler
    response = client.get("/error")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "code" in data
    assert "timestamp" in data

    # Test general exception handler
    response = client.get("/server_error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "Internal server error"
    assert data["code"] == "INTERNAL_ERROR"
