# Specification: Search API Endpoints

## Overview
Define search API endpoints for finding and filtering analytics data, users, agents, and historical records.

## Technical Requirements

### Global Search Endpoints

#### GET `/api/v1/search/global`
```python
@router.get("/search/global")
async def global_search(
    q: str,
    types: Optional[List[str]] = None,
    workspace_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Global search across all analytics data
    
    Query parameters:
    - q: Search query
    - types: Filter by type (users, agents, reports, alerts)
    - limit: Maximum results per type
    """
    results = await perform_global_search(
        query=q,
        types=types or ["all"],
        workspace_id=workspace_id,
        limit=limit
    )
    
    return {
        "query": q,
        "total_results": results.total,
        "results": {
            "users": [
                {
                    "id": "user_123",
                    "email": "john@company.com",
                    "name": "John Doe",
                    "match_score": 0.95,
                    "highlight": "john@company.com"
                }
            ],
            "agents": [
                {
                    "id": "agent_456",
                    "name": "Customer Support Bot",
                    "type": "support",
                    "match_score": 0.87,
                    "highlight": "Customer <mark>Support</mark> Bot"
                }
            ],
            "reports": [
                {
                    "id": "report_789",
                    "name": "Q1 Analytics Report",
                    "created_at": "2024-01-15",
                    "match_score": 0.82
                }
            ]
        },
        "suggestions": ["support metrics", "support agent", "customer support"]
    }
```

#### POST `/api/v1/search/advanced`
```python
@router.post("/search/advanced")
async def advanced_search(
    search_config: AdvancedSearchConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Advanced search with complex filters
    
    Request body:
    {
        "query": "error rate",
        "filters": {
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-01-31"
            },
            "entities": {
                "agents": ["agent_123", "agent_456"],
                "users": null
            },
            "metrics": {
                "error_rate": {
                    "min": 0.01,
                    "max": 0.05
                }
            }
        },
        "aggregations": [
            {
                "field": "agent_id",
                "type": "terms",
                "size": 10
            }
        ],
        "sort": [
            {"field": "error_rate", "order": "desc"}
        ],
        "highlight": {
            "fields": ["description", "notes"],
            "pre_tag": "<mark>",
            "post_tag": "</mark>"
        }
    }
    """
    results = await execute_advanced_search(
        workspace_id=user.workspace_id,
        config=search_config
    )
    
    return {
        "results": results.hits,
        "total": results.total,
        "aggregations": results.aggregations,
        "execution_time_ms": results.execution_time
    }
```

### Entity Search Endpoints

#### GET `/api/v1/search/users`
```python
@router.get("/search/users")
async def search_users(
    q: str,
    workspace_id: str,
    filters: Optional[UserSearchFilters] = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user)
) -> PaginatedResponse:
    """
    Search users with filters
    
    Query parameters:
    - q: Search query (name, email, id)
    - active_only: Filter active users
    - min_activity: Minimum activity threshold
    """
    users = await search_workspace_users(
        query=q,
        workspace_id=workspace_id,
        filters=filters,
        pagination=pagination
    )
    
    return {
        "users": [
            {
                "id": "user_123",
                "email": "user@company.com",
                "name": "John Doe",
                "last_active": "2024-01-15T14:30:00Z",
                "total_executions": 5420,
                "match_fields": ["email", "name"]
            }
        ],
        **pagination.dict()
    }
```

#### GET `/api/v1/search/agents`
```python
@router.get("/search/agents")
async def search_agents(
    q: Optional[str] = None,
    workspace_id: str,
    filters: Optional[AgentSearchFilters] = None,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Search agents with performance filters
    
    Query parameters:
    - q: Search in name, description, tags
    - min_success_rate: Minimum success rate
    - agent_type: Filter by type
    """
    agents = await search_workspace_agents(
        query=q,
        workspace_id=workspace_id,
        filters=filters
    )
    
    return {
        "agents": [
            {
                "id": "agent_123",
                "name": "Support Bot",
                "type": "customer_service",
                "success_rate": 94.5,
                "total_executions": 10420,
                "tags": ["support", "automated"],
                "relevance_score": 0.92
            }
        ]
    }
```

### Activity Search

#### GET `/api/v1/search/activities`
```python
@router.get("/search/activities")
async def search_activities(
    workspace_id: str,
    filters: ActivitySearchFilters,
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user)
) -> PaginatedResponse:
    """
    Search user activities and events
    
    Query parameters:
    - user_ids: Filter by users
    - event_types: Filter by event type
    - date_range: Time period
    """
    activities = await search_user_activities(
        workspace_id=workspace_id,
        filters=filters,
        pagination=pagination
    )
    
    return {
        "activities": [
            {
                "id": "activity_123",
                "user_id": "user_456",
                "event_type": "execution_completed",
                "agent_id": "agent_789",
                "timestamp": "2024-01-15T14:30:00Z",
                "details": {
                    "credits_consumed": 45,
                    "execution_time_ms": 234
                }
            }
        ],
        **pagination.dict()
    }
```

### Metric Search

#### GET `/api/v1/search/metrics`
```python
@router.get("/search/metrics")
async def search_metrics(
    metric_name: Optional[str] = None,
    workspace_id: str,
    value_range: Optional[ValueRange] = None,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Search for specific metric values
    
    Query parameters:
    - metric_name: Name pattern to search
    - value_min: Minimum value
    - value_max: Maximum value
    """
    metrics = await search_metric_values(
        metric_name=metric_name,
        workspace_id=workspace_id,
        value_range=value_range,
        date_range=date_range
    )
    
    return {
        "metrics": [
            {
                "name": "error_rate",
                "timestamp": "2024-01-15T14:00:00Z",
                "value": 0.045,
                "tags": {"agent_id": "agent_123"},
                "anomaly": True
            }
        ]
    }
```

### Alert Search

#### GET `/api/v1/search/alerts`
```python
@router.get("/search/alerts")
async def search_alerts(
    q: Optional[str] = None,
    workspace_id: str,
    filters: AlertSearchFilters,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Search alerts and notifications
    
    Query parameters:
    - q: Search in title, message
    - severity: Filter by severity
    - status: active, acknowledged, resolved
    """
    alerts = await search_workspace_alerts(
        query=q,
        workspace_id=workspace_id,
        filters=filters
    )
    
    return {
        "alerts": [
            {
                "id": "alert_123",
                "title": "High Error Rate",
                "severity": "critical",
                "status": "active",
                "triggered_at": "2024-01-15T14:30:00Z",
                "metric": "error_rate",
                "value": 0.08,
                "threshold": 0.05
            }
        ]
    }
```

### Report Search

#### GET `/api/v1/search/reports`
```python
@router.get("/search/reports")
async def search_reports(
    q: Optional[str] = None,
    workspace_id: str,
    filters: ReportSearchFilters,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Search generated reports
    
    Query parameters:
    - q: Search in name, description
    - report_type: Filter by type
    - created_by: Filter by creator
    """
    reports = await search_workspace_reports(
        query=q,
        workspace_id=workspace_id,
        filters=filters
    )
    
    return {
        "reports": [
            {
                "id": "report_123",
                "name": "Monthly Analytics",
                "type": "scheduled",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": "admin@company.com",
                "size_mb": 4.5,
                "download_url": "/api/v1/reports/download/report_123"
            }
        ]
    }
```

### Search Suggestions

#### GET `/api/v1/search/suggestions`
```python
@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str,
    workspace_id: str,
    limit: int = 10,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get search suggestions based on partial query
    """
    suggestions = await generate_search_suggestions(
        query=q,
        workspace_id=workspace_id,
        user_context=user.id,
        limit=limit
    )
    
    return {
        "query": q,
        "suggestions": [
            {
                "text": "error rate by agent",
                "type": "query",
                "score": 0.95
            },
            {
                "text": "agent_123",
                "type": "entity",
                "entity_type": "agent",
                "score": 0.89
            }
        ]
    }
```

### Search History

#### GET `/api/v1/search/history`
```python
@router.get("/search/history")
async def get_search_history(
    workspace_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get user's search history
    """
    history = await get_user_search_history(
        user_id=user.id,
        workspace_id=workspace_id,
        limit=limit
    )
    
    return {
        "searches": [
            {
                "query": "high error rate",
                "timestamp": "2024-01-15T14:00:00Z",
                "result_count": 15,
                "filters_used": ["date_range", "agents"]
            }
        ]
    }
```

#### DELETE `/api/v1/search/history`
```python
@router.delete("/search/history")
async def clear_search_history(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Clear user's search history
    """
    await delete_user_search_history(
        user_id=user.id,
        workspace_id=workspace_id
    )
    
    return {
        "cleared": True
    }
```

### Saved Searches

#### POST `/api/v1/search/saved`
```python
@router.post("/search/saved")
async def save_search(
    search_config: SavedSearchConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Save search configuration
    
    Request body:
    {
        "name": "High Error Agents",
        "query": "error rate > 5%",
        "filters": {
            "metric": "error_rate",
            "threshold": 0.05
        },
        "alert_on_match": true,
        "share_with_team": true
    }
    """
    saved_search = await create_saved_search(
        user_id=user.id,
        workspace_id=user.workspace_id,
        config=search_config
    )
    
    return {
        "id": saved_search.id,
        "name": saved_search.name,
        "created": True
    }
```

#### GET `/api/v1/search/saved`
```python
@router.get("/search/saved")
async def get_saved_searches(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get user's saved searches
    """
    searches = await get_user_saved_searches(
        user_id=user.id,
        workspace_id=workspace_id
    )
    
    return {
        "saved_searches": [
            {
                "id": "search_123",
                "name": "Daily Check",
                "query": "status:active",
                "filters": {},
                "last_run": "2024-01-15T08:00:00Z",
                "run_count": 45
            }
        ]
    }
```

### Search Analytics

#### GET `/api/v1/search/analytics`
```python
@router.get("/search/analytics")
async def get_search_analytics(
    workspace_id: str,
    date_range: DateRange,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Analytics about search usage
    """
    analytics = await analyze_search_patterns(
        workspace_id=workspace_id,
        date_range=date_range
    )
    
    return {
        "search_analytics": {
            "total_searches": 5420,
            "unique_users": 142,
            "avg_searches_per_user": 38.2,
            "top_queries": [
                {"query": "error rate", "count": 234},
                {"query": "active users", "count": 189}
            ],
            "no_results_queries": [
                {"query": "missing data", "count": 12}
            ],
            "avg_results_per_search": 24.5,
            "search_performance": {
                "avg_response_time_ms": 145,
                "p95_response_time_ms": 342
            }
        }
    }
```

## Search Implementation

```python
class SearchEngine:
    def __init__(self, elasticsearch_client):
        self.es = elasticsearch_client
    
    async def search(self, index: str, query: dict):
        """Execute Elasticsearch query"""
        response = await self.es.search(
            index=index,
            body=query
        )
        return self.parse_response(response)
    
    def build_query(self, text: str, filters: dict):
        """Build Elasticsearch query"""
        return {
            "query": {
                "bool": {
                    "must": [
                        {"multi_match": {
                            "query": text,
                            "fields": ["name^2", "description", "tags"]
                        }}
                    ],
                    "filter": self.build_filters(filters)
                }
            },
            "highlight": {
                "fields": {"*": {}}
            }
        }
```

## Implementation Priority
1. Global search functionality
2. Entity-specific searches
3. Search suggestions
4. Saved searches
5. Search analytics

## Success Metrics
- Search response time < 200ms (p95)
- Search relevance score > 0.8
- Zero-result rate < 5%
- Search usage growth > 20% monthly