"""Admin API routes for system management."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...api.dependencies.auth import require_admin
from ...services.admin_service import AdminService
from ...models.schemas.admin import (
    SystemHealthResponse,
    DependenciesHealthResponse,
    PerformanceMetricsResponse,
    SlowQueriesResponse,
    CacheClearConfig,
    CacheClearResponse,
    CacheStatsResponse,
    UserFilters,
    UsersListResponse,
    UserStatusUpdate,
    UserStatusUpdateResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemConfigUpdateResponse,
    JobsResponse,
    JobRetryResponse,
    VacuumConfig,
    VacuumResponse,
    DatabaseStatsResponse,
    AuditFilters,
    AuditLogResponse,
)
from ...models.schemas.common import PaginationParams

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ===== System Health Endpoints =====


@router.get("/health/system", response_model=SystemHealthResponse)
async def get_system_health(
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive system health check.

    Returns health status of all system components:
    - API service
    - Database connections
    - Redis cache
    - Background workers

    Also includes system resource metrics (CPU, memory, disk).

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_system_health()


@router.get("/health/dependencies", response_model=DependenciesHealthResponse)
async def check_dependencies(
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Check external dependencies health.

    Tests connectivity and response times for:
    - PostgreSQL database
    - Redis cache
    - External APIs (if configured)

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.check_dependencies()


# ===== Performance Monitoring Endpoints =====


@router.get("/performance/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    timeframe: str = Query(
        "1h",
        description="Timeframe for metrics",
        regex="^(1h|24h|7d|30d)$",
    ),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get system performance metrics.

    Returns performance data for:
    - API endpoints (requests/sec, response times, error rates)
    - Database (queries/sec, slow queries, cache hit ratio)
    - Cache (hit ratio, eviction rate, latency)

    Timeframe options: 1h, 24h, 7d, 30d

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_performance_metrics(timeframe)


@router.get("/performance/slow-queries", response_model=SlowQueriesResponse)
async def get_slow_queries(
    threshold_ms: int = Query(
        1000,
        ge=100,
        le=60000,
        description="Query execution time threshold in milliseconds",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of queries to return"),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List slow database queries.

    Returns queries that exceed the specified execution time threshold.
    Useful for identifying performance bottlenecks.

    Requires pg_stat_statements extension to be enabled.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_slow_queries(threshold_ms, limit)


# ===== Cache Management Endpoints =====


@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    cache_config: CacheClearConfig,
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Clear cache by pattern or type.

    Allows selective cache clearing:
    - By Redis key pattern (e.g., "dashboard:*")
    - By cache type (api_responses, queries, sessions, all)
    - By workspace_id (clear all cache for a specific workspace)

    Returns number of keys cleared and memory freed.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.clear_cache(cache_config)


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cache usage statistics.

    Returns detailed cache metrics:
    - Total keys and memory usage
    - Hit/miss ratios
    - Eviction and expiration rates
    - Key distribution by type
    - Top cache patterns by size

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_cache_stats()


# ===== User Management Endpoints =====


@router.get("/users", response_model=UsersListResponse)
async def get_system_users(
    status: Optional[str] = Query(None, description="Filter by user status"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with admin details.

    Returns comprehensive user information including:
    - User details (email, role, status)
    - Workspace associations
    - Activity metrics (executions, credits)
    - Account dates (created, last login)

    Supports filtering by status, role, and search.

    Requires admin authentication.
    """
    filters = UserFilters(status=status, role=role, search=search)
    service = AdminService(db)
    return await service.get_users(filters, skip, limit)


@router.put("/users/{user_id}/status", response_model=UserStatusUpdateResponse)
async def update_user_status(
    user_id: str = Path(..., description="User ID to update"),
    status_update: UserStatusUpdate = ...,
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user status (suspend, activate, etc.).

    Allows admins to:
    - Activate or suspend user accounts
    - Set suspension duration
    - Record reason for status change

    All status changes are logged in the audit log.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.update_user_status(user_id, status_update)


# ===== Configuration Management Endpoints =====


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_configuration(
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current system configuration.

    Returns all system settings:
    - Feature flags (realtime updates, analytics, exports)
    - System limits (rate limits, export sizes)
    - Maintenance mode settings
    - Integration configurations (Slack, Teams, etc.)

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_system_config()


@router.put("/config", response_model=SystemConfigUpdateResponse)
async def update_system_configuration(
    config_update: SystemConfigUpdate,
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update system configuration.

    Allows updating:
    - Feature flags (enable/disable features)
    - System limits (adjust rate limits, quotas)
    - Maintenance mode (activate/schedule maintenance)
    - Integration settings

    Some changes may require system restart.

    All configuration changes are logged in the audit log.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.update_system_config(config_update)


# ===== Job Management Endpoints =====


@router.get("/jobs", response_model=JobsResponse)
async def get_background_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List background jobs.

    Returns information about:
    - Job counts by status (queued, running, completed, failed)
    - Queue statistics (pending jobs, active workers)
    - Recent job failures with error details

    Supports filtering by status and queue name.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_jobs(status, queue)


@router.post("/jobs/{job_id}/retry", response_model=JobRetryResponse)
async def retry_failed_job(
    job_id: str = Path(..., description="Job ID to retry"),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry a failed job.

    Re-queues a failed background job for execution.
    Creates a new job with the same parameters as the original.

    Returns the new job ID and status.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.retry_job(job_id)


# ===== Database Management Endpoints =====


@router.post("/database/vacuum", response_model=VacuumResponse)
async def vacuum_database(
    vacuum_config: VacuumConfig,
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Run database vacuum operation.

    Performs PostgreSQL VACUUM to:
    - Reclaim storage space
    - Update table statistics (if analyze=true)
    - Prevent transaction ID wraparound

    Can be run on specific tables or entire database.
    Operation is queued as a background job.

    Warning: VACUUM FULL (full=true) requires exclusive table locks.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.queue_vacuum_job(vacuum_config)


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_statistics(
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get database usage statistics.

    Returns comprehensive database metrics:
    - Total database size
    - Table sizes and row counts
    - Index statistics and bloat
    - Connection pool usage

    Useful for capacity planning and optimization.

    Requires admin authentication.
    """
    service = AdminService(db)
    return await service.get_database_stats()


# ===== Audit Log Endpoints =====


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get system audit log.

    Returns audit trail of admin actions:
    - Configuration changes
    - User status modifications
    - Cache operations
    - Database maintenance
    - Job management actions

    Each entry includes:
    - Timestamp and user who performed the action
    - Action type and affected resource
    - Detailed change information
    - IP address of the request

    Supports filtering by user, action type, and date range.

    Requires admin authentication.
    """
    from datetime import datetime

    filters = AuditFilters(
        user_id=user_id,
        action=action,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )
    service = AdminService(db)
    return await service.get_audit_logs(filters, skip, limit)
