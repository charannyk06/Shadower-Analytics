"""Health check and monitoring routes."""

from fastapi import APIRouter, Depends
from ...core.database import get_db
from ...core.redis import get_redis

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
    """Prometheus metrics endpoint."""
    # Implementation will expose Prometheus metrics
    return {
        "http_requests_total": 0,
        "http_request_duration_seconds": 0,
    }


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
