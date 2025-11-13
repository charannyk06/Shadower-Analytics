"""Comprehensive health check service."""

import time
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ..api.models import HealthStatus, ServiceHealth, HealthCheckResponse

logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health checker for all system dependencies."""

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        redis_client: Optional[Redis] = None,
        main_app_url: Optional[str] = None
    ):
        """Initialize health checker.

        Args:
            db_session: Database session for health checks
            redis_client: Redis client for health checks
            main_app_url: URL of main application for connectivity checks
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.main_app_url = main_app_url

    async def check_database(self) -> ServiceHealth:
        """Check database connectivity and performance.

        Returns:
            ServiceHealth with database status
        """
        if not self.db_session:
            return ServiceHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Database session not available"
            )

        start = time.time()
        try:
            # Test basic connectivity
            await self.db_session.execute(text("SELECT 1"))

            # Test a more complex query
            await self.db_session.execute(text("SELECT version()"))

            latency = (time.time() - start) * 1000

            # Check if latency is acceptable
            if latency > 1000:  # > 1 second
                status = HealthStatus.DEGRADED
                message = f"High database latency: {latency:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "PostgreSQL connection successful"

            return ServiceHealth(
                name="database",
                status=status,
                latency_ms=round(latency, 2),
                message=message,
                metadata={
                    "type": "postgresql",
                    "pool_size": self._get_pool_size()
                }
            )

        except Exception as e:
            logger.error(f"Database health check failed: {e}", exc_info=True)
            return ServiceHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}"
            )

    async def check_redis(self) -> ServiceHealth:
        """Check Redis connectivity and performance.

        Returns:
            ServiceHealth with Redis status
        """
        if not self.redis_client:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="Redis client not configured (optional service)"
            )

        start = time.time()
        try:
            # Test connection with ping
            await self.redis_client.ping()

            # Test read/write
            test_key = "_health_check_test"
            await self.redis_client.set(test_key, "ok", ex=10)
            value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)

            if value != b"ok":
                raise Exception("Redis read/write test failed")

            latency = (time.time() - start) * 1000

            # Check if latency is acceptable
            if latency > 100:  # > 100ms
                status = HealthStatus.DEGRADED
                message = f"High Redis latency: {latency:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis connection successful"

            # Get Redis info
            info = await self.redis_client.info()

            return ServiceHealth(
                name="redis",
                status=status,
                latency_ms=round(latency, 2),
                message=message,
                metadata={
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown")
                }
            )

        except Exception as e:
            logger.error(f"Redis health check failed: {e}", exc_info=True)
            return ServiceHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}"
            )

    async def check_websocket(self) -> ServiceHealth:
        """Check WebSocket service health.

        Returns:
            ServiceHealth with WebSocket status
        """
        try:
            from ...core.config import settings

            if not settings.ENABLE_REALTIME:
                return ServiceHealth(
                    name="websocket",
                    status=HealthStatus.HEALTHY,
                    message="WebSocket disabled (not required)"
                )

            # Check if Redis (required for WebSocket) is available
            if not self.redis_client:
                return ServiceHealth(
                    name="websocket",
                    status=HealthStatus.DEGRADED,
                    message="WebSocket available but Redis unavailable (won't scale)"
                )

            # Try to ping Redis
            await self.redis_client.ping()

            return ServiceHealth(
                name="websocket",
                status=HealthStatus.HEALTHY,
                message="WebSocket service operational",
                metadata={
                    "enabled": True,
                    "redis_backend": True
                }
            )

        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}", exc_info=True)
            return ServiceHealth(
                name="websocket",
                status=HealthStatus.DEGRADED,
                message=f"WebSocket error: {str(e)}"
            )

    async def check_celery(self) -> ServiceHealth:
        """Check Celery worker health.

        Returns:
            ServiceHealth with Celery status
        """
        try:
            # Try to check if Celery workers are available
            # This requires celery app to be available
            from ...celery_app import celery_app

            # Inspect active workers
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()

            if not active_workers:
                return ServiceHealth(
                    name="celery",
                    status=HealthStatus.DEGRADED,
                    message="No active Celery workers found"
                )

            worker_count = len(active_workers)

            return ServiceHealth(
                name="celery",
                status=HealthStatus.HEALTHY,
                message=f"{worker_count} active worker(s)",
                metadata={
                    "workers": worker_count,
                    "worker_names": list(active_workers.keys())
                }
            )

        except ImportError:
            return ServiceHealth(
                name="celery",
                status=HealthStatus.DEGRADED,
                message="Celery not configured (optional service)"
            )
        except Exception as e:
            logger.error(f"Celery health check failed: {e}", exc_info=True)
            return ServiceHealth(
                name="celery",
                status=HealthStatus.DEGRADED,
                message=f"Celery error: {str(e)}"
            )

    async def check_external_services(self) -> Dict[str, ServiceHealth]:
        """Check external service connectivity.

        Returns:
            Dictionary of ServiceHealth for each external service
        """
        checks = {}

        # Check main app API
        if self.main_app_url:
            checks['main_app'] = await self._check_http_endpoint(
                name="main_app",
                url=f"{self.main_app_url}/health",
                timeout=5
            )

        return checks

    async def _check_http_endpoint(
        self,
        name: str,
        url: str,
        timeout: int = 5
    ) -> ServiceHealth:
        """Check an HTTP endpoint.

        Args:
            name: Service name
            url: Endpoint URL
            timeout: Request timeout in seconds

        Returns:
            ServiceHealth for the endpoint
        """
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout)

            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                message = "Service responding normally"
            elif 500 <= response.status_code < 600:
                status = HealthStatus.UNHEALTHY
                message = f"Service error (status {response.status_code})"
            else:
                status = HealthStatus.DEGRADED
                message = f"Unexpected status code: {response.status_code}"

            return ServiceHealth(
                name=name,
                status=status,
                latency_ms=round(latency, 2),
                message=message,
                metadata={
                    "url": url,
                    "status_code": response.status_code
                }
            )

        except httpx.TimeoutException:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Request timeout after {timeout}s",
                metadata={"url": url}
            )
        except Exception as e:
            logger.error(f"HTTP endpoint check failed for {name}: {e}")
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Connection error: {str(e)}",
                metadata={"url": url}
            )

    async def comprehensive_health_check(self) -> HealthCheckResponse:
        """Run all health checks in parallel.

        Returns:
            HealthCheckResponse with overall status and all service statuses
        """
        # Run all checks in parallel
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_websocket(),
            self.check_celery(),
            return_exceptions=True
        )

        # Handle any exceptions from health checks
        service_checks = []
        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check exception: {check}")
                service_checks.append(ServiceHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(check)
                ))
            else:
                service_checks.append(check)

        # Check external services
        try:
            external_checks = await self.check_external_services()
            service_checks.extend(external_checks.values())
        except Exception as e:
            logger.error(f"External services check failed: {e}")

        # Determine overall status
        overall_status = self._determine_overall_status(service_checks)

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            services=service_checks,
            metadata={
                "checks_performed": len(service_checks),
                "critical_services": ["database"],
                "optional_services": ["redis", "websocket", "celery", "main_app"],
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _determine_overall_status(self, services: list[ServiceHealth]) -> HealthStatus:
        """Determine overall health status from service statuses.

        Args:
            services: List of service health checks

        Returns:
            Overall HealthStatus
        """
        statuses = [s.status for s in services]

        # Check if critical services are down
        critical_services = ["database"]
        critical_down = any(
            s.name in critical_services and s.status == HealthStatus.UNHEALTHY
            for s in services
        )

        if critical_down:
            return HealthStatus.UNHEALTHY

        # Check if any service is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.DEGRADED

        # Check if any service is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # All services healthy
        return HealthStatus.HEALTHY

    def _get_pool_size(self) -> Optional[int]:
        """Get database connection pool size.

        Returns:
            Pool size or None if unavailable
        """
        try:
            if self.db_session:
                engine = self.db_session.get_bind()
                return engine.pool.size()
        except Exception:
            pass
        return None
