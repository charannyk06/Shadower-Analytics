# Agent Resource Utilization Analytics - Quick Start Guide

## Implementation Checklist

### Phase 1: Database Layer
- [ ] Create migration file: `database/migrations/028_create_agent_resource_tables.sql`
- [ ] Define tables:
  - `analytics.agent_resources` (resource metrics)
  - `analytics.resource_allocations` (allocated vs actual)
  - `analytics.resource_trends` (time-series)
- [ ] Create indexes (BRIN on timestamps, composite on agent_id + time)
- [ ] Create materialized view: `analytics.agent_resource_summary`
- [ ] Write migration test queries

### Phase 2: Backend Service Layer
- [ ] Create: `backend/src/services/metrics/resource_metrics.py`
- [ ] Implement `ResourceMetricsService` class with:
  - `get_agent_resources(agent_id, workspace_id, timeframe)`
  - `_get_resource_allocation()`
  - `_get_resource_trends()`
  - `_get_efficiency_metrics()`
  - `_get_comparative_analysis()`
  - `predict_resource_needs()`

### Phase 3: Backend API Layer
- [ ] Create: `backend/src/api/routes/resources.py`
- [ ] Implement endpoints:
  - `GET /api/v1/resources/agents/{agent_id}` - Agent resources
  - `GET /api/v1/resources/agents/{agent_id}/allocation` - Allocation efficiency
  - `GET /api/v1/resources/agents/{agent_id}/trends` - Historical trends
  - `GET /api/v1/resources/workspace/{workspace_id}` - Workspace-wide
  - `POST /api/v1/resources/forecast` - Prediction endpoint
- [ ] Add request validation schemas
- [ ] Add response schemas to: `backend/src/models/schemas/resources.py`

### Phase 4: Background Jobs
- [ ] Add aggregation job: `jobs/aggregation/resource_aggregation.py`
- [ ] Register in: `jobs/celeryconfig.py`
- [ ] Implement:
  - Hourly resource aggregation
  - Materialized view refresh
  - Resource alert checks

### Phase 5: Frontend Types & Hooks
- [ ] Create: `frontend/src/types/resources.ts`
- [ ] Define TypeScript interfaces:
  - `ResourceMetrics`
  - `AllocationData`
  - `ResourceTrend`
  - `ResourceForecast`
  - `ResourceComparison`
- [ ] Create: `frontend/src/hooks/api/useResourceMetrics.ts`
- [ ] Implement React Query hooks:
  - `useAgentResources()`
  - `useResourceAllocation()`
  - `useResourceTrends()`
  - `useResourceForecast()`

### Phase 6: Frontend Components
- [ ] Create directory: `frontend/src/components/resources/`
- [ ] Implement components:
  - `ResourceOverview.tsx` - Key metrics cards
  - `ResourceAllocation.tsx` - Allocated vs actual visualization
  - `ResourceTimeline.tsx` - Historical trend chart
  - `ResourceForecast.tsx` - Prediction chart
  - `ResourceComparison.tsx` - Agent comparison table
  - `ResourceAlerts.tsx` - Alert status

### Phase 7: Integration
- [ ] Add resource endpoint to: `backend/src/api/main.py`
- [ ] Register router in main.py: `from .routes.resources import router as resources_router`
- [ ] Add to OpenAPI schema tags
- [ ] Add resource section to agent detail page
- [ ] Add resource widget to dashboard

### Phase 8: Documentation & Testing
- [ ] Write docstrings in service methods
- [ ] Create unit tests for calculation functions
- [ ] Write integration tests for API endpoints
- [ ] Update project documentation
- [ ] Create API documentation

---

## Key Files to Create/Modify

### Database Migration Template
```sql
-- File: database/migrations/028_create_agent_resource_tables.sql

SET search_path TO analytics, public;

CREATE TABLE analytics.agent_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    
    -- Resource metrics
    cpu_usage_percent NUMERIC(5,2),
    memory_usage_percent NUMERIC(5,2),
    tokens_used INTEGER,
    requests_processed INTEGER,
    
    -- Allocation info
    allocated_cpu_cores NUMERIC(5,2),
    allocated_memory_mb INTEGER,
    
    -- Timestamps
    measured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_resources_agent_time 
    ON analytics.agent_resources(agent_id, measured_at DESC);
CREATE INDEX idx_agent_resources_workspace_time 
    ON analytics.agent_resources(workspace_id, measured_at DESC);
```

### Service Template
```python
# File: backend/src/services/metrics/resource_metrics.py

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.schemas.resources import ResourceMetricsResponse

class ResourceMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_agent_resources(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = '7d'
    ) -> ResourceMetricsResponse:
        """Get comprehensive agent resource metrics."""
        # Implementation using asyncio.gather() for parallel queries
        pass
    
    async def _get_resource_allocation(self, agent_id: str) -> Dict:
        """Get allocated vs actual resources."""
        pass
    
    async def _get_resource_trends(self, agent_id: str, days: int) -> List:
        """Get historical resource trends."""
        pass
```

### API Route Template
```python
# File: backend/src/api/routes/resources.py

from fastapi import APIRouter, Depends, Path, Query
from ...core.database import get_db
from ..dependencies.auth import get_current_user
from ...services.metrics.resource_metrics import ResourceMetricsService
from ...models.schemas.resources import ResourceMetricsResponse

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])

@router.get("/agents/{agent_id}")
async def get_agent_resources(
    agent_id: str = Path(...),
    workspace_id: str = Query(...),
    timeframe: str = Query("7d"),
    db = Depends(get_db),
    current_user = Depends(get_current_user),
) -> ResourceMetricsResponse:
    """Get comprehensive agent resource utilization metrics."""
    service = ResourceMetricsService(db)
    return await service.get_agent_resources(agent_id, workspace_id, timeframe)
```

### React Hook Template
```typescript
// File: frontend/src/hooks/api/useResourceMetrics.ts

import { useQuery } from '@tanstack/react-query';
import { ResourceMetrics } from '@/types/resources';

export function useAgentResources(
  agentId: string,
  workspaceId: string,
  timeframe: string = '7d'
) {
  return useQuery({
    queryKey: ['agent-resources', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await fetch(
        `/api/v1/resources/agents/${agentId}?workspace_id=${workspaceId}&timeframe=${timeframe}`,
        {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        }
      );
      return response.json() as Promise<ResourceMetrics>;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### React Component Template
```typescript
// File: frontend/src/components/resources/ResourceOverview.tsx

'use client';

import { useAgentResources } from '@/hooks/api/useResourceMetrics';

export function ResourceOverview({ agentId, workspaceId }) {
  const { data, isLoading, error } = useAgentResources(agentId, workspaceId);
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Metric cards */}
    </div>
  );
}
```

---

## Architecture Diagram

```
API Request
    |
    v
routes/resources.py (FastAPI Router)
    |
    +---> Dependency Injection
    |     ├─ get_db
    |     ├─ get_current_user
    |     └─ validate_workspace_access
    |
    v
ResourceMetricsService (Business Logic)
    |
    +---> asyncio.gather() [Parallel Queries]
    |     ├─ _get_resource_allocation()
    |     ├─ _get_resource_trends()
    |     ├─ _get_efficiency_metrics()
    |     └─ _get_comparative_analysis()
    |
    v
Database (PostgreSQL)
    |
    +---> analytics.agent_resources (base table)
    +---> analytics.resource_allocations
    +---> analytics.agent_resource_summary (materialized view)
    |
    v
Response (Pydantic Schema)
    |
    v
Frontend (React Component)
```

---

## Testing Checklist

### Unit Tests
- [ ] Test resource calculation functions
- [ ] Test timeframe conversion (7d, 30d, 90d, etc.)
- [ ] Test comparison calculations
- [ ] Test edge cases (no data, missing fields)

### Integration Tests
- [ ] Test API endpoint with mock data
- [ ] Test database queries with sample data
- [ ] Test authentication/authorization
- [ ] Test error handling and validation

### Frontend Tests
- [ ] Test component rendering
- [ ] Test React Query integration
- [ ] Test loading/error states
- [ ] Test chart rendering

---

## Deployment Checklist

- [ ] Run database migration in staging
- [ ] Verify materialized view creation
- [ ] Test API endpoints in staging
- [ ] Build and test frontend
- [ ] Configure Celery job scheduling
- [ ] Test background job execution
- [ ] Monitor database performance
- [ ] Deploy to production
- [ ] Monitor metrics and logs
- [ ] Gather user feedback

---

## Performance Optimization Tips

1. **Use BRIN indexes** for time-series queries (orders of magnitude faster)
2. **Materialize views** for frequently accessed aggregates
3. **Cache results** with Redis (@cache decorator)
4. **Use asyncio.gather()** for parallel database queries
5. **Batch database inserts** in aggregation jobs
6. **Set appropriate stale times** in React Query (5-10 minutes)
7. **Implement pagination** for large result sets
8. **Use indexes** on filter columns (agent_id, workspace_id, etc.)

---

## Common Commands

### Run Database Migration
```bash
psql -U postgres -d shadower_analytics -f database/migrations/028_create_agent_resource_tables.sql
```

### Generate Sample Data
```sql
-- Insert sample resource data for testing
INSERT INTO analytics.agent_resources (agent_id, workspace_id, cpu_usage_percent, memory_usage_percent, measured_at)
VALUES (
  '550e8400-e29b-41d4-a716-446655440000'::uuid,
  '660e8400-e29b-41d4-a716-446655440000'::uuid,
  45.5,
  62.3,
  NOW()
);
```

### Run Tests
```bash
# Backend tests
pytest backend/tests/ -v

# Frontend tests
npm test --prefix frontend
```

### Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migration in container
docker-compose exec postgres psql -U postgres -d shadower_analytics -f /migrations/028_create_agent_resource_tables.sql
```

### Check API Documentation
```
http://localhost:8000/docs
```

---

## Common Issues & Solutions

### Issue: Materialized view refresh takes too long
**Solution**: Use `REFRESH MATERIALIZED VIEW CONCURRENTLY` with `ORDER BY` clause

### Issue: Slow query on agent_id + timestamp
**Solution**: Add BRIN index: `CREATE INDEX idx_brin ON analytics.agent_resources USING BRIN(measured_at)`

### Issue: React Query not updating cache
**Solution**: Invalidate cache after mutations: `queryClient.invalidateQueries({ queryKey: ['agent-resources'] })`

### Issue: API returns 401 Unauthorized
**Solution**: Check JWT token is valid and included in Authorization header

### Issue: Celery job not running
**Solution**: Check Celery Beat is running and job is registered in `celeryconfig.py`

