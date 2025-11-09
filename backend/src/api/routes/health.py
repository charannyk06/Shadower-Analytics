"""Health check and monitoring routes."""

from fastapi import APIRouter, Depends, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from ...core.database import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "shadow-analytics",
        "version": "0.1.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db=Depends(get_db),
):
    """Detailed health check including dependencies."""
    # Implementation will check DB, Redis, etc.
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "celery": "running",
    }


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint.

    Exposes metrics in Prometheus format for scraping.
    Includes cache operations, hits/misses, errors, and latencies.
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


@router.get("/ready")
async def readiness_check(
    db=Depends(get_db),
):
    """Kubernetes readiness probe."""
    # Check if service is ready to accept traffic
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    # Check if service is alive
    return {"alive": True}
