"""Admin API schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# ===== System Health Schemas =====

class ComponentStatus(str, Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class DatabaseHealthStatus(BaseModel):
    """Database health status."""
    status: str
    connections: Dict[str, int]
    replication_lag_ms: Optional[int] = None


class RedisHealthStatus(BaseModel):
    """Redis health status."""
    status: str
    memory_used_mb: int
    memory_max_mb: int
    connected_clients: int


class WorkersHealthStatus(BaseModel):
    """Workers health status."""
    status: str
    active_jobs: int
    queued_jobs: int
    failed_jobs: int


class APIHealthStatus(BaseModel):
    """API health status."""
    status: str
    response_time_ms: float
    uptime_seconds: int


class SystemHealthComponents(BaseModel):
    """System health components."""
    api: APIHealthStatus
    database: DatabaseHealthStatus
    redis: RedisHealthStatus
    workers: WorkersHealthStatus


class SystemMetrics(BaseModel):
    """System resource metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float


class SystemHealthResponse(BaseModel):
    """System health response."""
    status: ComponentStatus
    components: SystemHealthComponents
    metrics: SystemMetrics


class DependencyStatus(BaseModel):
    """External dependency status."""
    service: str
    url: Optional[str] = None
    provider: Optional[str] = None
    status: str
    response_time_ms: Optional[int] = None
    quota_remaining: Optional[int] = None


class DependenciesHealthResponse(BaseModel):
    """Dependencies health response."""
    dependencies: List[DependencyStatus]


# ===== Performance Monitoring Schemas =====

class EndpointPerformance(BaseModel):
    """Endpoint performance metrics."""
    path: str
    calls: int
    avg_time_ms: float


class APIPerformanceMetrics(BaseModel):
    """API performance metrics."""
    requests_per_second: float
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate: float
    endpoints: List[EndpointPerformance]


class DatabasePerformanceMetrics(BaseModel):
    """Database performance metrics."""
    queries_per_second: float
    avg_query_time_ms: float
    slow_queries: int
    deadlocks: int
    cache_hit_ratio: float


class CachePerformanceMetrics(BaseModel):
    """Cache performance metrics."""
    hit_ratio: float
    evictions_per_minute: int
    avg_get_time_ms: float
    avg_set_time_ms: float


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""
    api_performance: APIPerformanceMetrics
    database_performance: DatabasePerformanceMetrics
    cache_performance: CachePerformanceMetrics


class SlowQuery(BaseModel):
    """Slow database query."""
    query: str
    execution_time_ms: float
    rows_examined: int
    rows_returned: int
    timestamp: datetime
    source: str


class SlowQueriesResponse(BaseModel):
    """Slow queries response."""
    slow_queries: List[SlowQuery]


# ===== Cache Management Schemas =====

class CacheType(str, Enum):
    """Cache type enumeration."""
    ALL = "all"
    API_RESPONSES = "api_responses"
    QUERIES = "queries"
    SESSIONS = "sessions"


class CacheClearConfig(BaseModel):
    """Cache clear configuration."""
    pattern: Optional[str] = Field(None, description="Redis key pattern to match")
    cache_type: CacheType = Field(CacheType.ALL, description="Type of cache to clear")
    workspace_id: Optional[str] = Field(None, description="Clear cache for specific workspace")


class CacheClearResponse(BaseModel):
    """Cache clear response."""
    keys_cleared: int
    memory_freed_mb: float


class KeyDistribution(BaseModel):
    """Cache key distribution."""
    api_responses: int
    query_results: int
    sessions: int


class TopPattern(BaseModel):
    """Top cache pattern."""
    pattern: str
    count: int
    size_mb: float


class CacheStats(BaseModel):
    """Cache statistics."""
    total_keys: int
    memory_used_mb: float
    hit_ratio: float
    miss_ratio: float
    evicted_keys: int
    expired_keys: int
    key_distribution: KeyDistribution
    top_patterns: List[TopPattern]


class CacheStatsResponse(BaseModel):
    """Cache stats response."""
    cache_stats: CacheStats


# ===== User Management Schemas =====

class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class AdminUserDetails(BaseModel):
    """Admin view of user details."""
    user_id: str
    email: str
    workspaces: List[str]
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    total_executions: int
    total_credits: int
    status: UserStatus


class UserFilters(BaseModel):
    """User list filters."""
    status: Optional[UserStatus] = None
    role: Optional[str] = None
    search: Optional[str] = None


class UsersListResponse(BaseModel):
    """Users list response."""
    users: List[AdminUserDetails]
    total: int
    skip: int
    limit: int


class UserStatusUpdate(BaseModel):
    """User status update."""
    status: UserStatus
    reason: Optional[str] = None
    suspension_until: Optional[datetime] = None


class UserStatusUpdateResponse(BaseModel):
    """User status update response."""
    user_id: str
    new_status: UserStatus
    updated: bool


# ===== Configuration Management Schemas =====

class FeatureFlags(BaseModel):
    """Feature flags configuration."""
    realtime_updates: Optional[bool] = None
    predictive_analytics: Optional[bool] = None
    export_enabled: Optional[bool] = None


class SystemLimits(BaseModel):
    """System limits configuration."""
    max_api_requests_per_hour: Optional[int] = None
    max_export_rows: Optional[int] = None
    max_report_pages: Optional[int] = None


class MaintenanceConfig(BaseModel):
    """Maintenance configuration."""
    mode: Optional[bool] = None
    message: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class IntegrationStatus(BaseModel):
    """Integration status."""
    enabled: bool
    webhook_configured: bool


class IntegrationsConfig(BaseModel):
    """Integrations configuration."""
    slack: Optional[IntegrationStatus] = None
    teams: Optional[IntegrationStatus] = None


class SystemConfiguration(BaseModel):
    """System configuration."""
    features: FeatureFlags
    limits: SystemLimits
    maintenance: MaintenanceConfig
    integrations: IntegrationsConfig


class SystemConfigResponse(BaseModel):
    """System configuration response."""
    configuration: SystemConfiguration


class SystemConfigUpdate(BaseModel):
    """System configuration update."""
    features: Optional[FeatureFlags] = None
    limits: Optional[SystemLimits] = None
    maintenance: Optional[MaintenanceConfig] = None
    integrations: Optional[IntegrationsConfig] = None


class SystemConfigUpdateResponse(BaseModel):
    """System configuration update response."""
    updated: bool
    restart_required: bool


# ===== Job Management Schemas =====

class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class JobQueue(BaseModel):
    """Job queue information."""
    name: str
    pending: int
    processing: int
    workers: int


class JobFailure(BaseModel):
    """Failed job information."""
    job_id: str
    queue: str
    error: str
    failed_at: datetime
    retries: int


class JobCounts(BaseModel):
    """Job counts."""
    queued: int
    running: int
    completed: int
    failed: int
    scheduled: int


class JobsResponse(BaseModel):
    """Jobs response."""
    jobs: JobCounts
    queues: List[JobQueue]
    recent_failures: List[JobFailure]


class JobRetryResponse(BaseModel):
    """Job retry response."""
    original_job_id: str
    new_job_id: str
    status: str


# ===== Database Management Schemas =====

class VacuumConfig(BaseModel):
    """Database vacuum configuration."""
    tables: Optional[List[str]] = None
    analyze: bool = True
    full: bool = False


class VacuumResponse(BaseModel):
    """Vacuum response."""
    job_id: str
    status: str
    estimated_time: int


class TableStats(BaseModel):
    """Table statistics."""
    name: str
    rows: int
    size_mb: float
    index_size_mb: float


class IndexStats(BaseModel):
    """Index statistics."""
    total: int
    unused: int
    bloat_percent: float


class ConnectionStats(BaseModel):
    """Connection statistics."""
    current: int
    max: int
    idle: int


class DatabaseStats(BaseModel):
    """Database statistics."""
    total_size_mb: float
    tables: List[TableStats]
    indexes: IndexStats
    connections: ConnectionStats


class DatabaseStatsResponse(BaseModel):
    """Database stats response."""
    database_stats: DatabaseStats


# ===== Audit Log Schemas =====

class AuditAction(str, Enum):
    """Audit action types."""
    CONFIG_UPDATE = "config_update"
    USER_STATUS_CHANGE = "user_status_change"
    CACHE_CLEAR = "cache_clear"
    DATABASE_VACUUM = "database_vacuum"
    JOB_RETRY = "job_retry"


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: str
    timestamp: datetime
    user_id: str
    action: AuditAction
    resource: str
    details: Dict[str, Any]
    ip_address: Optional[str]


class AuditFilters(BaseModel):
    """Audit log filters."""
    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AuditLogResponse(BaseModel):
    """Audit log response."""
    audit_logs: List[AuditLogEntry]
    total: int
    skip: int
    limit: int
