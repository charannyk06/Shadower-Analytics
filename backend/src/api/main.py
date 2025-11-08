"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from ..core.config import settings
from ..core.database import engine, Base
from .routes import (
    executive_router,
    agents_router,
    users_router,
    workspaces_router,
    metrics_router,
    exports_router,
    reports_router,
    health_router,
    websocket_router,
)
from .middleware.cors import setup_cors
from .middleware.logging import RequestLoggingMiddleware

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

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health_router)
app.include_router(executive_router)
app.include_router(agents_router)
app.include_router(users_router)
app.include_router(workspaces_router)
app.include_router(metrics_router)
app.include_router(exports_router)
app.include_router(reports_router)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Shadow Analytics API...")
    # Create database tables
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    logger.info("Shadow Analytics API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Shadow Analytics API...")
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
