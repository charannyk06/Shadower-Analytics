# Specification: Dashboard API Endpoints

## Overview
Define all dashboard-specific API endpoints for executive, agent, user, and workspace analytics views.

## Technical Requirements

### Executive Dashboard Endpoints

#### GET `/api/v1/dashboard/executive/summary`
```python
@router.get("/executive/summary")
async def get_executive_summary(
    workspace_id: str,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns high-level KPIs for executive dashboard
    """
    return {
        "revenue_metrics": {
            "total_revenue": 125000,
            "mrr": 25000,
            "arr": 300000,
            "growth_rate": 15.5
        },
        "user_metrics": {
            "total_users": 5420,
            "active_users": 3211,
            "new_users": 342,
            "churn_rate": 2.1
        },
        "usage_metrics": {
            "total_credits": 1500000,
            "credits_consumed": 980000,
            "avg_credits_per_user": 305
        },
        "performance_metrics": {
            "uptime": 99.95,
            "avg_response_time": 145,
            "error_rate": 0.02
        }
    }
```

#### GET `/api/v1/dashboard/executive/trends`
```python
@router.get("/executive/trends")
async def get_executive_trends(
    workspace_id: str,
    metrics: List[str],
    granularity: str = "daily",
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns trend data for specified metrics
    Query params:
    - metrics: comma-separated list (revenue,users,usage)
    - granularity: hourly, daily, weekly, monthly
    """
    return {
        "trends": [
            {
                "metric": "revenue",
                "data": [
                    {"date": "2024-01-01", "value": 25000},
                    {"date": "2024-01-02", "value": 26500}
                ]
            }
        ]
    }
```

### Agent Analytics Endpoints

#### GET `/api/v1/dashboard/agents/performance`
```python
@router.get("/agents/performance")
async def get_agent_performance(
    workspace_id: str,
    agent_ids: Optional[List[str]] = None,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns performance metrics for agents
    """
    return {
        "agents": [
            {
                "agent_id": "agent_123",
                "agent_name": "Customer Support Bot",
                "total_executions": 5420,
                "success_rate": 94.5,
                "avg_execution_time": 2.3,
                "error_rate": 5.5,
                "credits_consumed": 12500,
                "user_satisfaction": 4.2
            }
        ],
        "aggregates": {
            "total_agents": 15,
            "avg_success_rate": 92.3,
            "total_executions": 45000
        }
    }
```

#### GET `/api/v1/dashboard/agents/usage`
```python
@router.get("/agents/usage")
async def get_agent_usage(
    workspace_id: str,
    agent_id: str,
    granularity: str = "hourly",
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns detailed usage patterns for specific agent
    """
    return {
        "usage_pattern": [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "executions": 45,
                "unique_users": 12,
                "credits": 234,
                "errors": 2
            }
        ],
        "peak_hours": [14, 15, 16],
        "busiest_days": ["Monday", "Tuesday"]
    }
```

### User Activity Endpoints

#### GET `/api/v1/dashboard/users/activity`
```python
@router.get("/users/activity")
async def get_user_activity(
    workspace_id: str,
    user_ids: Optional[List[str]] = None,
    activity_type: Optional[str] = None,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns user activity metrics
    Query params:
    - activity_type: login, execution, api_call
    """
    return {
        "users": [
            {
                "user_id": "user_456",
                "email": "user@example.com",
                "last_active": "2024-01-15T10:30:00Z",
                "total_sessions": 145,
                "total_executions": 892,
                "credits_consumed": 3420,
                "favorite_agents": ["agent_123", "agent_456"]
            }
        ],
        "activity_summary": {
            "dau": 3211,
            "wau": 4102,
            "mau": 5420,
            "avg_session_duration": 12.5
        }
    }
```

#### GET `/api/v1/dashboard/users/engagement`
```python
@router.get("/users/engagement")
async def get_user_engagement(
    workspace_id: str,
    cohort: Optional[str] = None,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns user engagement metrics and retention
    """
    return {
        "engagement_metrics": {
            "activation_rate": 68.5,
            "retention_day_1": 85.2,
            "retention_day_7": 72.1,
            "retention_day_30": 61.3
        },
        "cohort_analysis": {
            "cohorts": [
                {
                    "cohort_date": "2024-01-01",
                    "users": 342,
                    "retention": [100, 85, 72, 65, 61]
                }
            ]
        }
    }
```

### Workspace Analytics Endpoints

#### GET `/api/v1/dashboard/workspace/overview`
```python
@router.get("/workspace/overview")
async def get_workspace_overview(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns workspace-level analytics overview
    """
    return {
        "workspace": {
            "id": workspace_id,
            "name": "Acme Corp",
            "created_at": "2023-06-15T00:00:00Z",
            "plan": "enterprise",
            "seats": 50,
            "seats_used": 42
        },
        "usage": {
            "total_credits": 500000,
            "credits_consumed": 342000,
            "credits_remaining": 158000,
            "reset_date": "2024-02-01"
        },
        "activity": {
            "active_users_today": 38,
            "total_executions_today": 1234,
            "top_agents": ["agent_123", "agent_456"]
        }
    }
```

#### GET `/api/v1/dashboard/workspace/comparison`
```python
@router.get("/workspace/comparison")
async def get_workspace_comparison(
    workspace_ids: List[str],
    metrics: List[str],
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Compare metrics across multiple workspaces
    """
    return {
        "comparisons": [
            {
                "workspace_id": "ws_123",
                "workspace_name": "Team A",
                "metrics": {
                    "total_users": 142,
                    "credits_consumed": 45000,
                    "avg_success_rate": 92.3
                }
            }
        ],
        "rankings": {
            "by_users": ["ws_456", "ws_123", "ws_789"],
            "by_usage": ["ws_123", "ws_789", "ws_456"]
        }
    }
```

### Real-time Metrics Endpoints

#### GET `/api/v1/dashboard/realtime/metrics`
```python
@router.websocket("/realtime/metrics")
async def realtime_metrics(
    websocket: WebSocket,
    workspace_id: str,
    metrics: List[str]
):
    """
    WebSocket endpoint for real-time metrics
    Streams updates every second
    """
    await websocket.accept()
    try:
        while True:
            data = await get_realtime_data(workspace_id, metrics)
            await websocket.send_json({
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": data
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

#### GET `/api/v1/dashboard/realtime/events`
```python
@router.get("/realtime/events", response_class=EventSourceResponse)
async def realtime_events_stream(
    workspace_id: str,
    event_types: Optional[List[str]] = None,
    user: User = Depends(get_current_user)
):
    """
    Server-sent events for real-time updates
    """
    async def event_generator():
        while True:
            event = await get_next_event(workspace_id, event_types)
            if event:
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"])
                }
            await asyncio.sleep(0.1)
    
    return EventSourceResponse(event_generator())
```

### Leaderboard Endpoints

#### GET `/api/v1/dashboard/leaderboards`
```python
@router.get("/leaderboards")
async def get_leaderboards(
    workspace_id: str,
    leaderboard_type: str,
    limit: int = 10,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns various leaderboards
    Types: users, agents, workspaces, features
    """
    return {
        "leaderboard": [
            {
                "rank": 1,
                "entity_id": "user_123",
                "entity_name": "John Doe",
                "score": 9842,
                "change": 2,
                "details": {
                    "executions": 452,
                    "success_rate": 96.2
                }
            }
        ],
        "user_rank": {
            "rank": 15,
            "score": 5421,
            "percentile": 85.2
        }
    }
```

### Export Endpoints

#### POST `/api/v1/dashboard/export`
```python
@router.post("/export")
async def export_dashboard_data(
    workspace_id: str,
    export_config: ExportConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Export dashboard data in various formats
    """
    job_id = await queue_export_job(
        workspace_id=workspace_id,
        format=export_config.format,
        data_types=export_config.data_types,
        date_range=export_config.date_range
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_time": 30
    }
```

#### GET `/api/v1/dashboard/export/{job_id}`
```python
@router.get("/export/{job_id}")
async def get_export_status(
    job_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Check export job status and download link
    """
    job = await get_export_job(job_id)
    
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "download_url": job.download_url if job.status == "completed" else None,
        "error": job.error if job.status == "failed" else None
    }
```

## Response Pagination

```python
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    order: Optional[str] = Field("desc", regex="^(asc|desc)$")

def paginate(query, params: PaginationParams):
    """Apply pagination to query"""
    total = query.count()
    items = query.offset(
        (params.page - 1) * params.per_page
    ).limit(params.per_page).all()
    
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "per_page": params.per_page,
        "pages": (total + params.per_page - 1) // params.per_page
    }
```

## Error Responses

```python
ERROR_RESPONSES = {
    400: {"description": "Bad Request", "model": ErrorResponse},
    401: {"description": "Unauthorized", "model": ErrorResponse},
    403: {"description": "Forbidden", "model": ErrorResponse},
    404: {"description": "Not Found", "model": ErrorResponse},
    429: {"description": "Rate Limited", "model": ErrorResponse},
    500: {"description": "Internal Server Error", "model": ErrorResponse}
}
```

## Implementation Priority
1. Executive summary endpoint
2. Agent performance endpoints
3. User activity endpoints
4. Real-time metrics WebSocket
5. Export functionality

## Success Metrics
- Average response time < 200ms
- Endpoint availability > 99.9%
- Successful request rate > 98%
- Data freshness < 1 minute