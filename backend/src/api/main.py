"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from ..core.config import settings
from ..core.database import engine, Base
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
)
from .middleware.cors import setup_cors
from .middleware.logging import RequestLoggingMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.security import SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Shadow Analytics API",
    description="Analytics service for Shadow agent platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup CORS
setup_cors(app)

# Add middleware (order matters - applied in reverse order)
app.add_middleware(SecurityHeadersMiddleware)  # Add security headers first
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth_router)  # Authentication endpoints first
app.include_router(health_router)
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


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Shadow Analytics API...")

    # Create database tables
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis pub/sub for WebSocket scaling
    if settings.ENABLE_REALTIME:
        try:
            from .websocket import init_redis_pubsub
            await init_redis_pubsub(settings.REDIS_URL)
            logger.info("Redis pub/sub initialized for WebSocket scaling")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis pub/sub: {e}")
            logger.warning("WebSocket will work but won't scale across instances")

    logger.info("Shadow Analytics API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Shadow Analytics API...")

    # Shutdown Redis pub/sub
    if settings.ENABLE_REALTIME:
        try:
            from .websocket import shutdown_redis_pubsub
            await shutdown_redis_pubsub()
            logger.info("Redis pub/sub shut down")
        except Exception as e:
            logger.error(f"Error shutting down Redis pub/sub: {e}")

    await engine.dispose()
    logger.info("Shadow Analytics API shut down successfully")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Shadow Analytics API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
