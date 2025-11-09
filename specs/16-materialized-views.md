# Specification: Materialized Views

## Feature Overview
Pre-computed database views for complex aggregations to improve query performance and reduce load.

## Technical Requirements
- Automatic refresh scheduling
- Incremental updates
- Dependency management
- Refresh monitoring
- Query optimization

## Implementation Details

### Materialized View Definitions
```sql
-- Active Users Summary
CREATE MATERIALIZED VIEW analytics.mv_active_users AS
SELECT 
    workspace_id,
    DATE(created_at) as activity_date,
    COUNT(DISTINCT user_id) as daily_active_users,
    COUNT(DISTINCT CASE 
        WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' 
        THEN user_id 
    END) as weekly_active_users,
    COUNT(DISTINCT CASE 
        WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' 
        THEN user_id 
    END) as monthly_active_users
FROM analytics.user_activity
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY workspace_id, DATE(created_at);

CREATE UNIQUE INDEX idx_mv_active_users 
    ON analytics.mv_active_users(workspace_id, activity_date);

-- Agent Performance Summary
CREATE MATERIALIZED VIEW analytics.mv_agent_performance AS
SELECT 
    agent_id,
    workspace_id,
    DATE(started_at) as run_date,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    AVG(runtime_seconds) as avg_runtime,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as median_runtime,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95_runtime,
    SUM(credits_consumed) as total_credits
FROM public.agent_runs
WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY agent_id, workspace_id, DATE(started_at);

CREATE UNIQUE INDEX idx_mv_agent_performance 
    ON analytics.mv_agent_performance(agent_id, run_date);

-- Workspace Metrics Summary
CREATE MATERIALIZED VIEW analytics.mv_workspace_metrics AS
SELECT 
    workspace_id,
    COUNT(DISTINCT user_id) as total_users,
    COUNT(DISTINCT agent_id) as total_agents,
    SUM(total_runs) as total_executions,
    AVG(success_rate) as avg_success_rate,
    SUM(credits_consumed) as total_credits_consumed,
    MAX(last_activity) as last_activity_at
FROM (
    SELECT 
        workspace_id,
        user_id,
        agent_id,
        COUNT(*) as total_runs,
        AVG(CASE WHEN status = 'completed' THEN 100.0 ELSE 0 END) as success_rate,
        SUM(credits_consumed) as credits_consumed,
        MAX(started_at) as last_activity
    FROM public.agent_runs
    WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workspace_id, user_id, agent_id
) subquery
GROUP BY workspace_id;

CREATE UNIQUE INDEX idx_mv_workspace_metrics 
    ON analytics.mv_workspace_metrics(workspace_id);
```

### Refresh Management
```python
# backend/src/services/materialized_views/refresh_service.py
class MaterializedViewRefreshService:
    def __init__(self, db):
        self.db = db
        self.views = [
            'mv_active_users',
            'mv_agent_performance',
            'mv_workspace_metrics',
            'mv_top_agents',
            'mv_error_summary'
        ]
    
    async def refresh_all(self):
        """Refresh all materialized views"""
        for view in self.views:
            await self.refresh_view(view)
    
    async def refresh_view(self, view_name: str):
        """Refresh a single materialized view"""
        query = f"REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view_name}"
        await self.db.execute(query)
    
    async def get_refresh_status(self):
        """Get refresh status for all views"""
        query = """
            SELECT 
                schemaname,
                matviewname,
                last_refresh_time,
                refresh_duration_ms
            FROM pg_stat_user_tables
            WHERE schemaname = 'analytics'
                AND tablename LIKE 'mv_%'
        """
        return await self.db.fetch_all(query)
```

## Testing Requirements
- Refresh accuracy tests
- Performance improvement validation
- Concurrent refresh handling

## Performance Targets
- View refresh: <30 seconds
- Query improvement: >10x faster
- Concurrent refresh support

## Security Considerations
- View access permissions
- Data freshness validation