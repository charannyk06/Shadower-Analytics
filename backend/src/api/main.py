"""Main FastAPI application with API Gateway."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging

from ..core.config import settings
from ..core.database import engine, Base
from ..core.redis import get_redis_client, close_redis
from .gateway import APIGateway
from .routes import (
    auth_router,
    executive_router,
    agents_router,
    users_router,
    workspaces_router,
    metrics_router,
    exports_router,
    reports_router,
    health_router,
    websocket_router,
    user_activity_router,
    credits_router,
    errors_router,
    trends_router,
    leaderboards_router,
    funnels_router,
    materialized_views_router,
    moving_averages_router,
    anomalies_router,
    analytics_router,
    dashboard_router,
    alerts_router,
    predictions_router,
    notifications_router,
    admin_router,
)
from .middleware.logging import RequestLoggingMiddleware
from .middleware.security import SecurityHeadersMiddleware
from .versioning import versioned_api, get_api_version_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper startup and shutdown."""
    # Startup
    logger.info("Starting Shadower Analytics API...")

    try:
        # Initialize Redis connection
        redis_client = await get_redis_client()
        if redis_client:
            logger.info("Redis connection initialized successfully")
        else:
            logger.warning("Redis connection failed - caching will be disabled")

        # Initialize Redis pub/sub for WebSocket scaling
        if settings.ENABLE_REALTIME:
            try:
                from .websocket import init_redis_pubsub
                await init_redis_pubsub(settings.REDIS_URL)
                logger.info("Redis pub/sub initialized for WebSocket scaling")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis pub/sub: {e}")
                logger.warning("WebSocket will work but won't scale across instances")

        logger.info("Shadower Analytics API started successfully")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Shadower Analytics API...")

    try:
        # Shutdown Redis pub/sub
        if settings.ENABLE_REALTIME:
            try:
                from .websocket import shutdown_redis_pubsub
                await shutdown_redis_pubsub()
                logger.info("Redis pub/sub shut down")
            except Exception as e:
                logger.error(f"Error shutting down Redis pub/sub: {e}")

        # Close Redis connection
        await close_redis()
        logger.info("Redis connection closed")

        # Close database connections
        await engine.dispose()
        logger.info("Database connections closed")

        logger.info("Shadower Analytics API shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create API Gateway with lifespan
gateway = APIGateway(lifespan=lifespan)
app = gateway.app

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware (order matters - applied in reverse order)
# Gateway already includes CORS and RateLimitMiddleware
app.add_middleware(SecurityHeadersMiddleware)  # Add security headers
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth_router)  # Authentication endpoints first
app.include_router(health_router)
app.include_router(dashboard_router)  # Unified dashboard API
app.include_router(executive_router)
app.include_router(agents_router)
app.include_router(users_router)
app.include_router(workspaces_router)
app.include_router(metrics_router)
app.include_router(exports_router)
app.include_router(reports_router)
app.include_router(websocket_router)
app.include_router(user_activity_router)
app.include_router(credits_router)
app.include_router(errors_router)
app.include_router(trends_router)
app.include_router(leaderboards_router)
app.include_router(funnels_router)
app.include_router(materialized_views_router)
app.include_router(moving_averages_router)
app.include_router(anomalies_router)
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(predictions_router)
app.include_router(notifications_router)
app.include_router(admin_router)


def custom_openapi():
    """Custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Shadower Analytics API",
        version="1.0.0",
        description="""
## Overview
Analytics API for Shadower platform providing:
- **Real-time metrics**: Live dashboards and monitoring
- **Historical analytics**: Trends and comparisons over time
- **Predictive insights**: Anomaly detection and forecasting
- **Custom reports**: Scheduled and on-demand reporting
- **Data exports**: Multiple format support (CSV, JSON, PDF, Excel)

## Authentication
All endpoints require JWT authentication.
Include your token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting
API calls are rate-limited per workspace to ensure fair usage:

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Default | 1000 requests | 1 hour |
| Dashboard | 200 requests | 1 minute |
| Analytics | 100 requests | 1 minute |
| Reports | 10 requests | 1 minute |
| Exports | 5 requests | 1 hour |
| Admin | 50 requests | 1 minute |

**Response Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Response Caching
GET requests are cached to improve performance:
- Dashboard endpoints: 1 minute TTL
- Analytics endpoints: 5 minutes TTL
- Reports endpoints: 10 minutes TTL
- Metrics endpoints: 2 minutes TTL

**Cache Headers:**
- `X-Cache`: `HIT` (served from cache) or `MISS` (fresh data)

## Error Handling
All errors follow a consistent format:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z",
  "path": "/api/v1/endpoint"
}
```

**Common Error Codes:**
- `UNAUTHORIZED`: Missing or invalid authentication
- `FORBIDDEN`: Insufficient permissions
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `VALIDATION_ERROR`: Invalid request parameters
- `NOT_FOUND`: Resource not found
- `INTERNAL_ERROR`: Server error

## Versioning
API is versioned with prefix `/api/v1/`
Breaking changes will increment the version number.
Current version: **v1** (stable)

## Support
For issues or questions, contact: support@shadower.ai
        """,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token"
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"Bearer": []}]

    # Add custom tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "dashboard",
            "description": "Dashboard metrics and visualizations"
        },
        {
            "name": "analytics",
            "description": "Advanced analytics and trends"
        },
        {
            "name": "reports",
            "description": "Report generation and management"
        },
        {
            "name": "exports",
            "description": "Data export functionality"
        },
        {
            "name": "admin",
            "description": "Administrative endpoints (requires admin role)"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Set custom OpenAPI schema
app.openapi = custom_openapi


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Shadower Analytics API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "api_versions": get_api_version_info()
    }


# Note: Startup and shutdown events are now handled by the lifespan context manager above
# This is the recommended approach in FastAPI 0.104+ and provides better resource management
