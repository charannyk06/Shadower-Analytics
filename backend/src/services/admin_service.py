"""Admin service layer for system management operations."""

import psutil
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..core.redis import get_redis_client
from ..models.schemas.admin import (
    SystemHealthResponse,
    ComponentStatus,
    SystemHealthComponents,
    APIHealthStatus,
    DatabaseHealthStatus,
    RedisHealthStatus,
    WorkersHealthStatus,
    SystemMetrics,
    DependenciesHealthResponse,
    DependencyStatus,
    PerformanceMetricsResponse,
    APIPerformanceMetrics,
    DatabasePerformanceMetrics,
    CachePerformanceMetrics,
    EndpointPerformance,
    SlowQueriesResponse,
    SlowQuery,
    CacheClearConfig,
    CacheClearResponse,
    CacheStatsResponse,
    CacheStats,
    KeyDistribution,
    TopPattern,
    UserFilters,
    UsersListResponse,
    AdminUserDetails,
    UserStatusUpdate,
    UserStatusUpdateResponse,
    UserStatus,
    SystemConfigResponse,
    SystemConfiguration,
    FeatureFlags,
    SystemLimits,
    MaintenanceConfig,
    IntegrationsConfig,
    IntegrationStatus,
    SystemConfigUpdate,
    SystemConfigUpdateResponse,
    JobsResponse,
    JobCounts,
    JobQueue,
    JobFailure,
    JobRetryResponse,
    VacuumConfig,
    VacuumResponse,
    DatabaseStatsResponse,
    DatabaseStats,
    TableStats,
    IndexStats,
    ConnectionStats,
    AuditFilters,
    AuditLogResponse,
    AuditLogEntry,
)

logger = logging.getLogger(__name__)

# Track API start time for uptime calculation
API_START_TIME = time.time()


class AdminService:
    """Service for admin operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===== System Health Methods =====

    async def get_system_health(self) -> SystemHealthResponse:
        """Get comprehensive system health status."""
        try:
            # Check API health
            uptime = int(time.time() - API_START_TIME)
            api_status = APIHealthStatus(
                status="healthy",
                response_time_ms=45.0,
                uptime_seconds=uptime,
            )

            # Check database health
            db_status = await self._check_database_health()

            # Check Redis health
            redis_status = await self._check_redis_health()

            # Check workers health (placeholder)
            workers_status = WorkersHealthStatus(
                status="healthy",
                active_jobs=0,
                queued_jobs=0,
                failed_jobs=0,
            )

            # Get system metrics
            metrics = self._get_system_metrics()

            # Determine overall status
            overall_status = self._determine_overall_status(
                api_status, db_status, redis_status, workers_status
            )

            return SystemHealthResponse(
                status=overall_status,
                components=SystemHealthComponents(
                    api=api_status,
                    database=db_status,
                    redis=redis_status,
                    workers=workers_status,
                ),
                metrics=metrics,
            )
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            raise

    async def _check_database_health(self) -> DatabaseHealthStatus:
        """Check database health."""
        try:
            # Get connection pool stats
            result = await self.db.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE state = 'active') as active,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle,
                        200 as max_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
            )
            row = result.fetchone()

            return DatabaseHealthStatus(
                status="healthy",
                connections={
                    "active": row.active if row else 0,
                    "idle": row.idle if row else 0,
                    "max": 200,
                },
                replication_lag_ms=0,
            )
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            return DatabaseHealthStatus(
                status="critical",
                connections={"active": 0, "idle": 0, "max": 200},
                replication_lag_ms=None,
            )

    async def _check_redis_health(self) -> RedisHealthStatus:
        """Check Redis health."""
        try:
            redis_client = await get_redis_client()
            if redis_client and await redis_client.ping():
                # Get Redis info
                info = await redis_client.redis.info("memory")
                info_clients = await redis_client.redis.info("clients")

                memory_used = info.get("used_memory", 0) / (1024 * 1024)  # Convert to MB
                memory_max = info.get("maxmemory", 2048 * 1024 * 1024) / (
                    1024 * 1024
                )  # Convert to MB
                connected_clients = info_clients.get("connected_clients", 0)

                return RedisHealthStatus(
                    status="healthy",
                    memory_used_mb=int(memory_used),
                    memory_max_mb=int(memory_max) if memory_max > 0 else 2048,
                    connected_clients=connected_clients,
                )
            else:
                return RedisHealthStatus(
                    status="critical",
                    memory_used_mb=0,
                    memory_max_mb=0,
                    connected_clients=0,
                )
        except Exception as e:
            logger.error(f"Error checking Redis health: {e}")
            return RedisHealthStatus(
                status="critical",
                memory_used_mb=0,
                memory_max_mb=0,
                connected_clients=0,
            )

    def _get_system_metrics(self) -> SystemMetrics:
        """Get system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
            )
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return SystemMetrics(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
            )

    def _determine_overall_status(
        self,
        api_status: APIHealthStatus,
        db_status: DatabaseHealthStatus,
        redis_status: RedisHealthStatus,
        workers_status: WorkersHealthStatus,
    ) -> ComponentStatus:
        """Determine overall system health status."""
        statuses = [
            api_status.status,
            db_status.status,
            redis_status.status,
            workers_status.status,
        ]

        if any(s == "critical" for s in statuses):
            return ComponentStatus.CRITICAL
        elif any(s == "degraded" for s in statuses):
            return ComponentStatus.DEGRADED
        else:
            return ComponentStatus.HEALTHY

    async def check_dependencies(self) -> DependenciesHealthResponse:
        """Check external dependencies health."""
        dependencies = []

        # Check database
        try:
            start = time.time()
            await self.db.execute(text("SELECT 1"))
            response_time = int((time.time() - start) * 1000)
            dependencies.append(
                DependencyStatus(
                    service="PostgreSQL Database",
                    status="healthy",
                    response_time_ms=response_time,
                )
            )
        except Exception as e:
            logger.error(f"Database dependency check failed: {e}")
            dependencies.append(
                DependencyStatus(
                    service="PostgreSQL Database",
                    status="unhealthy",
                )
            )

        # Check Redis
        try:
            redis_client = await get_redis_client()
            start = time.time()
            if redis_client:
                await redis_client.ping()
                response_time = int((time.time() - start) * 1000)
                dependencies.append(
                    DependencyStatus(
                        service="Redis Cache",
                        status="healthy",
                        response_time_ms=response_time,
                    )
                )
            else:
                dependencies.append(
                    DependencyStatus(
                        service="Redis Cache",
                        status="unhealthy",
                    )
                )
        except Exception as e:
            logger.error(f"Redis dependency check failed: {e}")
            dependencies.append(
                DependencyStatus(
                    service="Redis Cache",
                    status="unhealthy",
                )
            )

        return DependenciesHealthResponse(dependencies=dependencies)

    # ===== Performance Monitoring Methods =====

    async def get_performance_metrics(self, timeframe: str = "1h") -> PerformanceMetricsResponse:
        """Get system performance metrics."""
        # This is a placeholder implementation
        # In production, you'd query from a metrics database or Prometheus

        api_performance = APIPerformanceMetrics(
            requests_per_second=145.0,
            avg_response_time_ms=87.0,
            p50_response_time_ms=65.0,
            p95_response_time_ms=234.0,
            p99_response_time_ms=512.0,
            error_rate=0.02,
            endpoints=[
                EndpointPerformance(
                    path="/api/v1/dashboard/executive",
                    calls=5420,
                    avg_time_ms=123.0,
                )
            ],
        )

        db_performance = DatabasePerformanceMetrics(
            queries_per_second=234.0,
            avg_query_time_ms=12.0,
            slow_queries=5,
            deadlocks=0,
            cache_hit_ratio=0.89,
        )

        cache_performance = CachePerformanceMetrics(
            hit_ratio=0.76,
            evictions_per_minute=23,
            avg_get_time_ms=2.0,
            avg_set_time_ms=3.0,
        )

        return PerformanceMetricsResponse(
            api_performance=api_performance,
            database_performance=db_performance,
            cache_performance=cache_performance,
        )

    async def get_slow_queries(
        self, threshold_ms: int = 1000, limit: int = 20
    ) -> SlowQueriesResponse:
        """Get slow database queries."""
        try:
            # Query pg_stat_statements if available
            result = await self.db.execute(
                text("""
                    SELECT
                        query,
                        mean_exec_time as execution_time_ms,
                        rows as rows_examined,
                        calls
                    FROM pg_stat_statements
                    WHERE mean_exec_time > :threshold
                    ORDER BY mean_exec_time DESC
                    LIMIT :limit
                """),
                {"threshold": threshold_ms, "limit": limit},
            )

            slow_queries = []
            for row in result:
                slow_queries.append(
                    SlowQuery(
                        query=row.query[:200] + "..." if len(row.query) > 200 else row.query,
                        execution_time_ms=float(row.execution_time_ms),
                        rows_examined=row.rows_examined,
                        rows_returned=row.rows_examined,  # Approximation
                        timestamp=datetime.now(),
                        source="pg_stat_statements",
                    )
                )

            return SlowQueriesResponse(slow_queries=slow_queries)
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return SlowQueriesResponse(slow_queries=[])

    # ===== Cache Management Methods =====

    async def clear_cache(self, config: CacheClearConfig) -> CacheClearResponse:
        """Clear cache based on pattern or type."""
        try:
            redis_client = await get_redis_client()
            if not redis_client:
                raise Exception("Redis client not available")

            # Determine pattern to use
            pattern = config.pattern
            if not pattern:
                if config.cache_type.value == "api_responses":
                    pattern = "api:*"
                elif config.cache_type.value == "queries":
                    pattern = "query:*"
                elif config.cache_type.value == "sessions":
                    pattern = "session:*"
                else:
                    pattern = "*"

            # Add workspace filter if specified
            if config.workspace_id:
                pattern = f"workspace:{config.workspace_id}:*"

            # Get memory before clearing
            info_before = await redis_client.redis.info("memory")
            memory_before = info_before.get("used_memory", 0) / (1024 * 1024)

            # Clear keys
            keys_cleared = await redis_client.flush_pattern(pattern)

            # Get memory after clearing
            info_after = await redis_client.redis.info("memory")
            memory_after = info_after.get("used_memory", 0) / (1024 * 1024)

            memory_freed = max(0, memory_before - memory_after)

            return CacheClearResponse(
                keys_cleared=keys_cleared,
                memory_freed_mb=round(memory_freed, 2),
            )
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise

    async def get_cache_stats(self) -> CacheStatsResponse:
        """Get cache statistics."""
        try:
            redis_client = await get_redis_client()
            if not redis_client:
                raise Exception("Redis client not available")

            # Get Redis info
            info = await redis_client.redis.info("stats")
            info_memory = await redis_client.redis.info("memory")

            # Get keyspace info
            keyspace_info = await redis_client.redis.info("keyspace")
            db_info = keyspace_info.get("db0", {})
            total_keys = db_info.get("keys", 0) if isinstance(db_info, dict) else 0

            # Calculate hit/miss ratios
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total_ops = hits + misses
            hit_ratio = hits / total_ops if total_ops > 0 else 0
            miss_ratio = misses / total_ops if total_ops > 0 else 0

            memory_used = info_memory.get("used_memory", 0) / (1024 * 1024)
            evicted_keys = info.get("evicted_keys", 0)
            expired_keys = info.get("expired_keys", 0)

            # Get key distribution (simplified)
            key_distribution = KeyDistribution(
                api_responses=0,
                query_results=0,
                sessions=0,
            )

            # Count keys by pattern
            cursor = 0
            patterns_count: Dict[str, int] = {}

            # Sample keys to get distribution
            while True:
                cursor, keys = await redis_client.redis.scan(cursor=cursor, count=1000)
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode("utf-8")

                    if key.startswith("api:"):
                        key_distribution.api_responses += 1
                    elif key.startswith("query:"):
                        key_distribution.query_results += 1
                    elif key.startswith("session:"):
                        key_distribution.sessions += 1

                    # Track pattern prefix
                    prefix = key.split(":")[0] if ":" in key else "other"
                    patterns_count[prefix] = patterns_count.get(prefix, 0) + 1

                if cursor == 0:
                    break

            # Get top patterns
            top_patterns = [
                TopPattern(pattern=f"{pattern}:*", count=count, size_mb=0.0)
                for pattern, count in sorted(
                    patterns_count.items(), key=lambda x: x[1], reverse=True
                )[:5]
            ]

            stats = CacheStats(
                total_keys=total_keys,
                memory_used_mb=round(memory_used, 2),
                hit_ratio=round(hit_ratio, 3),
                miss_ratio=round(miss_ratio, 3),
                evicted_keys=evicted_keys,
                expired_keys=expired_keys,
                key_distribution=key_distribution,
                top_patterns=top_patterns,
            )

            return CacheStatsResponse(cache_stats=stats)
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            raise

    # ===== User Management Methods =====

    async def get_users(
        self, filters: Optional[UserFilters], skip: int = 0, limit: int = 100
    ) -> UsersListResponse:
        """Get list of users with admin details."""
        # This is a placeholder implementation
        # In production, you'd query from your users table
        return UsersListResponse(
            users=[],
            total=0,
            skip=skip,
            limit=limit,
        )

    async def update_user_status(
        self, user_id: str, status_update: UserStatusUpdate
    ) -> UserStatusUpdateResponse:
        """Update user status."""
        # This is a placeholder implementation
        # In production, you'd update the user's status in the database
        return UserStatusUpdateResponse(
            user_id=user_id,
            new_status=status_update.status,
            updated=True,
        )

    # ===== Configuration Management Methods =====

    async def get_system_config(self) -> SystemConfigResponse:
        """Get current system configuration."""
        # This is a placeholder implementation
        # In production, you'd load from a config table or file
        config = SystemConfiguration(
            features=FeatureFlags(
                realtime_updates=True,
                predictive_analytics=True,
                export_enabled=True,
            ),
            limits=SystemLimits(
                max_api_requests_per_hour=10000,
                max_export_rows=100000,
                max_report_pages=500,
            ),
            maintenance=MaintenanceConfig(
                mode=False,
                message=None,
                scheduled_at=None,
            ),
            integrations=IntegrationsConfig(
                slack=IntegrationStatus(enabled=True, webhook_configured=True),
                teams=IntegrationStatus(enabled=False, webhook_configured=False),
            ),
        )

        return SystemConfigResponse(configuration=config)

    async def update_system_config(
        self, config_update: SystemConfigUpdate
    ) -> SystemConfigUpdateResponse:
        """Update system configuration."""
        # This is a placeholder implementation
        # In production, you'd save to a config table or file
        restart_required = False

        # Check if certain changes require restart
        if config_update.features and config_update.features.realtime_updates is not None:
            restart_required = True

        return SystemConfigUpdateResponse(
            updated=True,
            restart_required=restart_required,
        )

    # ===== Job Management Methods =====

    async def get_jobs(
        self, status: Optional[str] = None, queue: Optional[str] = None
    ) -> JobsResponse:
        """Get background jobs status."""
        # This is a placeholder implementation
        # In production, you'd query from Celery or your job queue
        return JobsResponse(
            jobs=JobCounts(
                queued=0,
                running=0,
                completed=0,
                failed=0,
                scheduled=0,
            ),
            queues=[],
            recent_failures=[],
        )

    async def retry_job(self, job_id: str) -> JobRetryResponse:
        """Retry a failed job."""
        # This is a placeholder implementation
        # In production, you'd interact with Celery or your job queue
        return JobRetryResponse(
            original_job_id=job_id,
            new_job_id=f"retry_{job_id}",
            status="queued",
        )

    # ===== Database Management Methods =====

    async def queue_vacuum_job(self, config: VacuumConfig) -> VacuumResponse:
        """Queue a database vacuum operation."""
        # This is a placeholder implementation
        # In production, you'd queue a background job to run VACUUM
        return VacuumResponse(
            job_id="vacuum_job_123",
            status="started",
            estimated_time=300,
        )

    async def get_database_stats(self) -> DatabaseStatsResponse:
        """Get database statistics."""
        try:
            # Get total database size
            result = await self.db.execute(
                text("""
                    SELECT pg_database_size(current_database()) / (1024 * 1024) as size_mb
                """)
            )
            row = result.fetchone()
            total_size_mb = float(row.size_mb) if row else 0

            # Get table stats
            result = await self.db.execute(
                text("""
                    SELECT
                        schemaname || '.' || tablename as table_name,
                        n_live_tup as rows,
                        pg_total_relation_size(schemaname||'.'||tablename) / (1024 * 1024) as size_mb,
                        pg_indexes_size(schemaname||'.'||tablename) / (1024 * 1024) as index_size_mb
                    FROM pg_stat_user_tables
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 20
                """)
            )

            tables = []
            for row in result:
                tables.append(
                    TableStats(
                        name=row.table_name,
                        rows=row.rows,
                        size_mb=round(float(row.size_mb), 2),
                        index_size_mb=round(float(row.index_size_mb), 2),
                    )
                )

            # Get connection stats
            result = await self.db.execute(
                text("""
                    SELECT
                        COUNT(*) as current,
                        200 as max,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
            )
            row = result.fetchone()

            connections = ConnectionStats(
                current=row.current if row else 0,
                max=200,
                idle=row.idle if row else 0,
            )

            # Index stats
            indexes = IndexStats(
                total=0,
                unused=0,
                bloat_percent=0.0,
            )

            stats = DatabaseStats(
                total_size_mb=round(total_size_mb, 2),
                tables=tables,
                indexes=indexes,
                connections=connections,
            )

            return DatabaseStatsResponse(database_stats=stats)
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            raise

    # ===== Audit Log Methods =====

    async def get_audit_logs(
        self, filters: Optional[AuditFilters], skip: int = 0, limit: int = 100
    ) -> AuditLogResponse:
        """Get audit logs."""
        # This is a placeholder implementation
        # In production, you'd query from an audit_log table
        return AuditLogResponse(
            audit_logs=[],
            total=0,
            skip=skip,
            limit=limit,
        )
