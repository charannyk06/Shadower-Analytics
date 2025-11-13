"""Health check and monitoring routes."""

from fastapi import APIRouter, Depends, Response, status
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime
from typing import Dict, Any
import time
import logging
import asyncio

from ...core.database import get_db
from ...core.redis import get_redis_client
from ..models import HealthStatus, ServiceHealth, HealthCheckResponse

router = APIRouter(prefix="/api/v1", tags=["health"])
logger = logging.getLogger(__name__)


async def check_database() -> ServiceHealth:
    """Check database connection health."""
    start = time.time()
    try:
        db = await anext(get_db())
        # Simple query to test connection
        await db.execute("SELECT 1")
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="PostgreSQL connection successful"
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ServiceHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {str(e)}"
        )


async def check_redis() -> ServiceHealth:
    """Check Redis connection health."""
    start = time.time()
    try:
        redis = await get_redis_client()
        if not redis:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message="Redis client not available"
            )

        # Test connection with ping
        await redis.ping()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Redis connection successful"
        )
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis error: {str(e)}"
        )


async def check_websocket() -> ServiceHealth:
    """Check WebSocket service health."""
    try:
        # Basic check - could be enhanced to test pub/sub
        from ...core.config import settings

        if not settings.ENABLE_REALTIME:
            return ServiceHealth(
                name="websocket",
                status=HealthStatus.HEALTHY,
                message="WebSocket disabled (not required)"
            )

        # Check if Redis (required for WebSocket) is available
        redis = await get_redis_client()
        if not redis:
            return ServiceHealth(
                name="websocket",
                status=HealthStatus.DEGRADED,
                message="WebSocket available but Redis unavailable (won't scale)"
            )

        return ServiceHealth(
            name="websocket",
            status=HealthStatus.HEALTHY,
            message="WebSocket service operational"
        )
    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        return ServiceHealth(
            name="websocket",
            status=HealthStatus.DEGRADED,
            message=f"WebSocket error: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Basic health check endpoint.

    Fast health check that doesn't test dependencies.
    Used for basic monitoring and load balancer health checks.
    """
    return {
        "status": "healthy",
        "service": "shadower-analytics",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/detailed", response_model=HealthCheckResponse)
async def detailed_health_check():
    """Detailed health check including all dependencies.

    Checks:
    - Database connectivity
    - Redis connectivity
    - WebSocket service status

    Returns overall status as:
    - healthy: All services operational
    - degraded: Some non-critical services down
    - unhealthy: Critical services down
    """
    # Run all health checks in parallel
    services = await asyncio.gather(
        check_database(),
        check_redis(),
        check_websocket(),
        return_exceptions=True
    )

    # Handle any exceptions from health checks
    service_checks = []
    for service in services:
        if isinstance(service, Exception):
            logger.error(f"Health check exception: {service}")
            service_checks.append(ServiceHealth(
                name="unknown",
                status=HealthStatus.UNHEALTHY,
                message=str(service)
            ))
        else:
            service_checks.append(service)

    # Determine overall status
    statuses = [s.status for s in service_checks]

    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall_status = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        # Check if critical services are down
        critical_services = ["database"]
        critical_down = any(
            s.name in critical_services and s.status == HealthStatus.UNHEALTHY
            for s in service_checks
        )
        overall_status = HealthStatus.UNHEALTHY if critical_down else HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.DEGRADED

    return HealthCheckResponse(
        status=overall_status,
        version="1.0.0",
        services=service_checks,
        metadata={
            "checks_performed": len(service_checks),
            "critical_services": ["database"],
            "optional_services": ["redis", "websocket"]
        }
    )


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint.

    Exposes metrics in Prometheus format for scraping.
    Includes:
    - Request counts and latencies
    - Cache hits/misses
    - Database connection pool stats
    - Custom business metrics
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe.

    Indicates if service is ready to accept traffic.
    Checks critical dependencies (database).
    """
    try:
        db_health = await check_database()

        if db_health.status == HealthStatus.HEALTHY:
            return {
                "ready": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return Response(
                content={"ready": False, "reason": db_health.message},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return Response(
            content={"ready": False, "reason": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe.

    Indicates if service is alive and should not be restarted.
    Simple check that doesn't test external dependencies.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
