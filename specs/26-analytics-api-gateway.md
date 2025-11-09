# Specification: Analytics API Gateway

## Overview
Implement API gateway for analytics service with rate limiting, authentication, request routing, and response caching.

## Technical Requirements

### Backend Implementation

#### Service: `api/gateway.py`
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Rate limiting per workspace/user
        Uses Redis for distributed counting
        """
        # Check rate limits
        # Increment counter
        # Return 429 if exceeded
        
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        JWT validation and workspace verification
        Injects user context into request
        """
        # Validate JWT token
        # Check workspace access
        # Inject user context
        
class CacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Response caching for GET requests
        Cache key based on URL + query params + user context
        """
        # Check cache for GET requests
        # Return cached if fresh
        # Store response in cache

class APIGateway:
    def __init__(self):
        self.app = FastAPI(title="Shadower Analytics API")
        self.setup_middleware()
        self.setup_routes()
    
    def setup_middleware(self):
        # CORS configuration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://app.shadower.ai"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Custom middleware
        self.app.add_middleware(RateLimitMiddleware)
        self.app.add_middleware(AuthenticationMiddleware)
        self.app.add_middleware(CacheMiddleware)
    
    def setup_routes(self):
        # Mount route groups
        self.app.include_router(dashboard_router, prefix="/api/v1/dashboard")
        self.app.include_router(analytics_router, prefix="/api/v1/analytics")
        self.app.include_router(reports_router, prefix="/api/v1/reports")
        self.app.include_router(admin_router, prefix="/api/v1/admin")
```

#### Rate Limiting Configuration
```python
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
    }
}

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def check_rate_limit(
        self,
        key: str,
        limit_type: str = "default"
    ):
        """Check if rate limit exceeded"""
        limit = RATE_LIMITS[limit_type]
        current = await self.redis.incr(key)
        
        if current == 1:
            await self.redis.expire(key, limit["window"])
        
        if current > limit["requests"]:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(limit["window"])}
            )
        
        return {
            "remaining": limit["requests"] - current,
            "reset": await self.redis.ttl(key)
        }
```

### API Versioning

```python
from fastapi import APIRouter
from typing import Optional

class VersionedAPI:
    def __init__(self):
        self.versions = {}
    
    def register_version(self, version: str, router: APIRouter):
        """Register API version"""
        self.versions[version] = router
    
    def get_router(self, version: str) -> APIRouter:
        """Get router for specific version"""
        if version not in self.versions:
            # Fallback to latest stable
            return self.versions["v1"]
        return self.versions[version]

# Version-specific routers
v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")
```

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(APIResponse):
    """Paginated response wrapper"""
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

class ErrorResponse(BaseModel):
    """Error response format"""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
    timestamp: datetime
```

### API Documentation

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Shadower Analytics API",
        version="1.0.0",
        description="""
        ## Overview
        Analytics API for Shadower platform providing:
        - Real-time metrics
        - Historical analytics
        - Predictive insights
        - Custom reports
        
        ## Authentication
        All endpoints require JWT authentication.
        Include token in Authorization header:
        `Authorization: Bearer <token>`
        
        ## Rate Limiting
        API calls are rate-limited per workspace.
        Check response headers for limit status.
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Health Checks and Monitoring

```python
from fastapi import status
from typing import Dict

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health() -> Dict[str, Any]:
    """Detailed health with dependency checks"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "websocket": await check_websocket()
    }
    
    overall_status = "healthy" if all(
        c["status"] == "healthy" for c in checks.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    return Response(
        generate_latest(),
        media_type="text/plain"
    )
```

### Request Validation

```python
from fastapi import Request, HTTPException
from pydantic import ValidationError

class RequestValidator:
    @staticmethod
    async def validate_workspace_access(
        request: Request,
        workspace_id: str
    ):
        """Validate user has access to workspace"""
        user = request.state.user
        if workspace_id not in user.workspace_ids:
            raise HTTPException(
                status_code=403,
                detail="Access denied to workspace"
            )
    
    @staticmethod
    def validate_date_range(
        start_date: datetime,
        end_date: datetime,
        max_days: int = 365
    ):
        """Validate date range constraints"""
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=400,
                detail=f"Date range exceeds maximum of {max_days} days"
            )
```

### API Endpoints Structure

```python
# Dashboard endpoints
@v1_router.get("/dashboard/executive")
@v1_router.get("/dashboard/agents")
@v1_router.get("/dashboard/users")
@v1_router.get("/dashboard/workspace")

# Analytics endpoints
@v1_router.get("/analytics/metrics")
@v1_router.get("/analytics/trends")
@v1_router.get("/analytics/comparisons")
@v1_router.get("/analytics/cohorts")
@v1_router.get("/analytics/funnels")

# Reports endpoints
@v1_router.post("/reports/generate")
@v1_router.get("/reports/{report_id}")
@v1_router.get("/reports/scheduled")
@v1_router.post("/reports/export")

# Real-time endpoints
@v1_router.websocket("/ws")
@v1_router.get("/stream/metrics")
@v1_router.get("/stream/events")

# Admin endpoints
@v1_router.get("/admin/usage")
@v1_router.post("/admin/cache/clear")
@v1_router.get("/admin/performance")
```

## Implementation Priority
1. Basic gateway with authentication
2. Rate limiting implementation
3. Response caching
4. API versioning
5. Advanced monitoring

## Success Metrics
- API response time < 200ms (p95)
- Gateway uptime > 99.9%
- Rate limit accuracy 100%
- Cache hit rate > 60%