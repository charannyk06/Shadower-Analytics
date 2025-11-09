# Specification: Admin API Endpoints

## Overview
Define administrative API endpoints for system management, monitoring, configuration, and maintenance.

## Technical Requirements

### System Health Endpoints

#### GET `/api/v1/admin/health/system`
```python
@router.get("/health/system")
async def get_system_health(
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Comprehensive system health check
    """
    health = await check_system_health()
    
    return {
        "status": health.overall_status,  # healthy, degraded, critical
        "components": {
            "api": {
                "status": "healthy",
                "response_time_ms": 45,
                "uptime_seconds": 864000
            },
            "database": {
                "status": "healthy",
                "connections": {
                    "active": 45,
                    "idle": 155,
                    "max": 200
                },
                "replication_lag_ms": 12
            },
            "redis": {
                "status": "healthy",
                "memory_used_mb": 512,
                "memory_max_mb": 2048,
                "connected_clients": 23
            },
            "workers": {
                "status": "healthy",
                "active_jobs": 12,
                "queued_jobs": 34,
                "failed_jobs": 2
            }
        },
        "metrics": {
            "cpu_usage_percent": 34.5,
            "memory_usage_percent": 67.8,
            "disk_usage_percent": 45.2
        }
    }
```

#### GET `/api/v1/admin/health/dependencies`
```python
@router.get("/health/dependencies")
async def check_dependencies(
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Check external dependencies health
    """
    dependencies = await check_external_dependencies()
    
    return {
        "dependencies": [
            {
                "service": "Main App API",
                "url": "https://api.shadower.ai",
                "status": "healthy",
                "response_time_ms": 123
            },
            {
                "service": "Supabase",
                "url": "https://project.supabase.co",
                "status": "healthy",
                "response_time_ms": 45
            },
            {
                "service": "Email Service",
                "provider": "SendGrid",
                "status": "healthy",
                "quota_remaining": 98500
            }
        ]
    }
```

### Performance Monitoring Endpoints

#### GET `/api/v1/admin/performance/metrics`
```python
@router.get("/performance/metrics")
async def get_performance_metrics(
    timeframe: str = "1h",  # 1h, 24h, 7d, 30d
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    System performance metrics
    """
    metrics = await get_system_metrics(timeframe)
    
    return {
        "api_performance": {
            "requests_per_second": 145,
            "avg_response_time_ms": 87,
            "p50_response_time_ms": 65,
            "p95_response_time_ms": 234,
            "p99_response_time_ms": 512,
            "error_rate": 0.02,
            "endpoints": [
                {
                    "path": "/api/v1/dashboard/executive",
                    "calls": 5420,
                    "avg_time_ms": 123
                }
            ]
        },
        "database_performance": {
            "queries_per_second": 234,
            "avg_query_time_ms": 12,
            "slow_queries": 5,
            "deadlocks": 0,
            "cache_hit_ratio": 0.89
        },
        "cache_performance": {
            "hit_ratio": 0.76,
            "evictions_per_minute": 23,
            "avg_get_time_ms": 2,
            "avg_set_time_ms": 3
        }
    }
```

#### GET `/api/v1/admin/performance/slow-queries`
```python
@router.get("/performance/slow-queries")
async def get_slow_queries(
    threshold_ms: int = 1000,
    limit: int = 20,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    List slow database queries
    """
    queries = await get_slow_query_log(threshold_ms, limit)
    
    return {
        "slow_queries": [
            {
                "query": "SELECT * FROM analytics.user_activity WHERE...",
                "execution_time_ms": 2340,
                "rows_examined": 150000,
                "rows_returned": 100,
                "timestamp": "2024-01-15T14:30:00Z",
                "source": "dashboard_api.py:145"
            }
        ]
    }
```

### Cache Management Endpoints

#### POST `/api/v1/admin/cache/clear`
```python
@router.post("/cache/clear")
async def clear_cache(
    cache_config: CacheClearConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Clear cache by pattern or type
    
    Request body:
    {
        "pattern": "dashboard:*",  # Redis key pattern
        "cache_type": "api_responses",  # all, api_responses, queries, sessions
        "workspace_id": null  # Optional: clear for specific workspace
    }
    """
    cleared = await clear_cache_keys(cache_config)
    
    return {
        "keys_cleared": cleared.count,
        "memory_freed_mb": cleared.memory_freed
    }
```

#### GET `/api/v1/admin/cache/stats`
```python
@router.get("/cache/stats")
async def get_cache_statistics(
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Cache usage statistics
    """
    stats = await get_cache_stats()
    
    return {
        "cache_stats": {
            "total_keys": 45678,
            "memory_used_mb": 512,
            "hit_ratio": 0.76,
            "miss_ratio": 0.24,
            "evicted_keys": 234,
            "expired_keys": 567,
            "key_distribution": {
                "api_responses": 12345,
                "query_results": 8901,
                "sessions": 2345
            },
            "top_patterns": [
                {"pattern": "dashboard:*", "count": 5678, "size_mb": 123}
            ]
        }
    }
```

### User Management Endpoints

#### GET `/api/v1/admin/users`
```python
@router.get("/users")
async def get_system_users(
    filters: Optional[UserFilters] = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(require_admin)
) -> PaginatedResponse:
    """
    List all users with admin details
    """
    users = await get_users_admin(filters, pagination)
    
    return {
        "users": [
            {
                "user_id": "user_123",
                "email": "user@company.com",
                "workspaces": ["ws_123", "ws_456"],
                "role": "admin",
                "created_at": "2023-06-15T00:00:00Z",
                "last_login": "2024-01-15T10:30:00Z",
                "total_executions": 5420,
                "total_credits": 125000,
                "status": "active"
            }
        ],
        **pagination.dict()
    }
```

#### PUT `/api/v1/admin/users/{user_id}/status`
```python
@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Update user status (suspend, activate, etc.)
    
    Request body:
    {
        "status": "suspended",  # active, suspended, deleted
        "reason": "Violation of terms",
        "suspension_until": "2024-02-01T00:00:00Z"
    }
    """
    await update_user_admin_status(user_id, status_update)
    
    return {
        "user_id": user_id,
        "new_status": status_update.status,
        "updated": True
    }
```

### Configuration Management Endpoints

#### GET `/api/v1/admin/config`
```python
@router.get("/config")
async def get_system_configuration(
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Get current system configuration
    """
    config = await get_system_config()
    
    return {
        "configuration": {
            "features": {
                "realtime_updates": True,
                "predictive_analytics": True,
                "export_enabled": True
            },
            "limits": {
                "max_api_requests_per_hour": 10000,
                "max_export_rows": 100000,
                "max_report_pages": 500
            },
            "maintenance": {
                "mode": False,
                "message": None,
                "scheduled_at": None
            },
            "integrations": {
                "slack": {"enabled": True, "webhook_configured": True},
                "teams": {"enabled": False, "webhook_configured": False}
            }
        }
    }
```

#### PUT `/api/v1/admin/config`
```python
@router.put("/config")
async def update_system_configuration(
    config_update: SystemConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Update system configuration
    
    Request body:
    {
        "features": {
            "predictive_analytics": false
        },
        "maintenance": {
            "mode": true,
            "message": "System maintenance in progress"
        }
    }
    """
    await update_system_config(config_update)
    
    return {
        "updated": True,
        "restart_required": config_update.requires_restart()
    }
```

### Job Management Endpoints

#### GET `/api/v1/admin/jobs`
```python
@router.get("/jobs")
async def get_background_jobs(
    status: Optional[str] = None,
    queue: Optional[str] = None,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    List background jobs
    """
    jobs = await get_job_queue_status(status, queue)
    
    return {
        "jobs": {
            "queued": 45,
            "running": 12,
            "completed": 5420,
            "failed": 23,
            "scheduled": 8
        },
        "queues": [
            {
                "name": "reports",
                "pending": 5,
                "processing": 2,
                "workers": 4
            },
            {
                "name": "analytics",
                "pending": 15,
                "processing": 5,
                "workers": 8
            }
        ],
        "recent_failures": [
            {
                "job_id": "job_789",
                "queue": "reports",
                "error": "Template not found",
                "failed_at": "2024-01-15T14:30:00Z",
                "retries": 3
            }
        ]
    }
```

#### POST `/api/v1/admin/jobs/{job_id}/retry`
```python
@router.post("/jobs/{job_id}/retry")
async def retry_failed_job(
    job_id: str,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Retry a failed job
    """
    new_job = await retry_job(job_id)
    
    return {
        "original_job_id": job_id,
        "new_job_id": new_job.id,
        "status": "queued"
    }
```

### Database Management Endpoints

#### POST `/api/v1/admin/database/vacuum`
```python
@router.post("/database/vacuum")
async def vacuum_database(
    vacuum_config: VacuumConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Run database vacuum operation
    
    Request body:
    {
        "tables": ["user_activity", "agent_performance"],
        "analyze": true,
        "full": false
    }
    """
    job_id = await queue_vacuum_job(vacuum_config)
    
    return {
        "job_id": job_id,
        "status": "started",
        "estimated_time": 300  # seconds
    }
```

#### GET `/api/v1/admin/database/stats`
```python
@router.get("/database/stats")
async def get_database_statistics(
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Database usage statistics
    """
    stats = await get_db_stats()
    
    return {
        "database_stats": {
            "total_size_mb": 2456,
            "tables": [
                {
                    "name": "user_activity",
                    "rows": 5420000,
                    "size_mb": 890,
                    "index_size_mb": 234
                }
            ],
            "indexes": {
                "total": 45,
                "unused": 3,
                "bloat_percent": 12.3
            },
            "connections": {
                "current": 45,
                "max": 200,
                "idle": 155
            }
        }
    }
```

### Audit Log Endpoints

#### GET `/api/v1/admin/audit-log`
```python
@router.get("/audit-log")
async def get_audit_log(
    filters: Optional[AuditFilters] = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(require_admin)
) -> PaginatedResponse:
    """
    System audit log
    """
    logs = await get_audit_logs(filters, pagination)
    
    return {
        "audit_logs": [
            {
                "id": "audit_123",
                "timestamp": "2024-01-15T14:30:00Z",
                "user_id": "user_456",
                "action": "config_update",
                "resource": "system_configuration",
                "details": {
                    "field": "maintenance.mode",
                    "old_value": False,
                    "new_value": True
                },
                "ip_address": "192.168.1.1"
            }
        ],
        **pagination.dict()
    }
```

## Implementation Priority
1. System health endpoints
2. Performance monitoring
3. Cache management
4. User management
5. Configuration and audit logs

## Success Metrics
- Admin API uptime > 99.99%
- Health check latency < 100ms
- Configuration changes audit rate 100%
- Cache management effectiveness > 90%