# Agent Lifecycle Analytics Implementation Plan

## Overview

This document maps the existing Shadower-Analytics patterns and infrastructure to guide implementation of agent lifecycle analytics tracking agent creation → active → deprecated → archived states.

---

## 1. Existing Patterns to Reuse

### Pattern 1: Database Schema with Materialized Views

**Current Example**: `009_create_agent_analytics_tables.sql`

**For Lifecycle Analytics**:
```sql
-- Create lifecycle tracking tables
CREATE TABLE IF NOT EXISTS analytics.agent_lifecycle_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    
    -- State tracking
    from_state VARCHAR(50),  -- created, active, paused, deprecated, archived
    to_state VARCHAR(50),
    transition_reason VARCHAR(255),
    
    -- Timing
    transition_at TIMESTAMPTZ NOT NULL,
    duration_in_state INTERVAL,  -- How long in previous state
    
    -- Metadata
    triggered_by VARCHAR(50),  -- user, system, api, automation
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_state_transition CHECK (from_state IS NULL OR from_state != to_state)
);

-- Create materialized view for lifecycle summary
CREATE MATERIALIZED VIEW analytics.agent_lifecycle_summary AS
SELECT
    agent_id,
    workspace_id,
    
    -- Current state
    (array_agg(to_state ORDER BY transition_at DESC))[1] as current_state,
    MAX(transition_at) as last_state_change,
    
    -- State durations (in days)
    ROUND(EXTRACT(EPOCH FROM (MAX(transition_at) - MIN(transition_at))) / 86400, 2) as days_since_created,
    
    -- Transition counts
    COUNT(*) as total_transitions,
    COUNT(*) FILTER (WHERE from_state = 'created') as activated_count,
    COUNT(*) FILTER (WHERE to_state = 'deprecated') as deprecated_at,
    
    -- Timing metrics
    ROUND(AVG(EXTRACT(EPOCH FROM duration_in_state)) / 3600, 2) as avg_state_duration_hours,
    
    created_at
FROM analytics.agent_lifecycle_events
WHERE agent_id IS NOT NULL
GROUP BY agent_id, workspace_id, created_at;
```

### Pattern 2: Service Layer with Async Queries

**Current Example**: `AgentAnalyticsService.get_agent_analytics()`

**For Lifecycle Analytics**:
```python
# File: backend/src/services/analytics/agent_lifecycle_service.py

from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import asyncio
from datetime import datetime, timedelta

class AgentLifecycleService:
    """Service for agent lifecycle analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_lifecycle_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "all"
    ) -> Dict[str, Any]:
        """Get comprehensive lifecycle analytics for an agent."""
        
        # Fetch in parallel (like existing pattern)
        current_state, transitions, state_durations, timeline = await asyncio.gather(
            self._get_current_state(agent_id),
            self._get_state_transitions(agent_id, timeframe),
            self._calculate_state_durations(agent_id),
            self._get_state_timeline(agent_id, timeframe),
            return_exceptions=True
        )
        
        return {
            "agentId": agent_id,
            "currentState": current_state,
            "transitions": transitions,
            "stateDurations": state_durations,
            "timeline": timeline,
            "generatedAt": datetime.utcnow().isoformat()
        }
    
    async def _get_current_state(self, agent_id: str) -> Dict[str, Any]:
        """Get current lifecycle state."""
        query = text("""
            SELECT 
                to_state as state,
                transition_at,
                duration_in_state,
                triggered_by,
                metadata
            FROM analytics.agent_lifecycle_events
            WHERE agent_id = :agent_id
            ORDER BY transition_at DESC
            LIMIT 1
        """)
        result = await self.db.execute(query, {"agent_id": agent_id})
        row = result.first()
        return dict(row._mapping) if row else {}
    
    async def _get_state_transitions(
        self,
        agent_id: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get state transitions within timeframe."""
        start_date = self._calculate_start_date(timeframe)
        
        query = text("""
            SELECT 
                from_state,
                to_state,
                transition_at,
                duration_in_state,
                triggered_by,
                transition_reason,
                metadata
            FROM analytics.agent_lifecycle_events
            WHERE agent_id = :agent_id
              AND transition_at >= :start_date
            ORDER BY transition_at DESC
        """)
        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "start_date": start_date}
        )
        return [dict(row._mapping) for row in result.fetchall()]
    
    def _calculate_start_date(self, timeframe: str) -> datetime:
        """Convert timeframe to start date."""
        if timeframe == "24h":
            return datetime.utcnow() - timedelta(days=1)
        elif timeframe == "7d":
            return datetime.utcnow() - timedelta(days=7)
        elif timeframe == "30d":
            return datetime.utcnow() - timedelta(days=30)
        else:  # "all"
            return datetime(2000, 1, 1)
```

### Pattern 3: Pydantic Response Schemas

**Current Example**: `models/schemas/agent_analytics.py`

**For Lifecycle Analytics**:
```python
# File: backend/src/models/schemas/agent_lifecycle.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class StateTransition(BaseModel):
    """Individual state transition."""
    from_state: Optional[str] = Field(None, description="Previous state")
    to_state: str = Field(..., description="New state")
    transition_at: str = Field(..., description="Transition timestamp")
    duration_in_state: Optional[float] = Field(None, description="Duration in previous state (seconds)")
    triggered_by: str = Field(..., description="user, system, api, automation")
    transition_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class StateDuration(BaseModel):
    """Duration spent in each state."""
    state: str
    total_duration_seconds: float
    average_duration_seconds: float
    total_occurrences: int
    percentage_of_lifetime: float

class LifecycleTimeline(BaseModel):
    """Timeline visualization data."""
    timestamp: str
    state: str
    event: str

class LifecycleMetrics(BaseModel):
    """Lifecycle metrics."""
    current_state: str
    days_in_current_state: float
    total_days_since_creation: float
    total_transitions: int
    activation_lag: Optional[float]  # Days from created to active
    deprecation_lag: Optional[float]  # Days from active to deprecated

class AgentLifecycleResponse(BaseModel):
    """Complete agent lifecycle response."""
    agent_id: str = Field(..., alias="agentId")
    workspace_id: str = Field(..., alias="workspaceId")
    generated_at: str = Field(..., alias="generatedAt")
    
    # Current state info
    current_state: str = Field(..., alias="currentState")
    current_state_since: str = Field(..., alias="currentStateSince")
    
    # Metrics
    lifecycle_metrics: LifecycleMetrics = Field(..., alias="lifecycleMetrics")
    state_durations: List[StateDuration] = Field(default_factory=list, alias="stateDurations")
    
    # Transitions
    transitions: List[StateTransition] = Field(default_factory=list)
    total_transitions: int = Field(..., alias="totalTransitions")
    
    # Timeline for visualization
    timeline: List[LifecycleTimeline] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
```

### Pattern 4: API Routes with Authentication

**Current Example**: `api/routes/agents.py`

**For Lifecycle Analytics**:
```python
# File: backend/src/api/routes/agents.py (add these endpoints)

from fastapi import APIRouter, Depends, Query, Path
from ...services.analytics.agent_lifecycle_service import AgentLifecycleService
from ...models.schemas.agent_lifecycle import AgentLifecycleResponse
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access

router = APIRouter()

@router.get("/{agent_id}/lifecycle", response_model=AgentLifecycleResponse)
async def get_agent_lifecycle(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "all",
        description="Time range: 24h, 7d, 30d, all",
        pattern="^(24h|7d|30d|all)$"
    ),
    db=Depends(get_db),
    current_user = Depends(get_current_user),
    workspace_access = Depends(validate_workspace_access)
):
    """
    Get agent lifecycle analytics.
    
    Tracks agent state transitions and provides metrics on:
    - Current state and time in state
    - State durations and patterns
    - Activation lag (created to active)
    - Deprecation lag (active to deprecated)
    """
    service = AgentLifecycleService(db)
    return await service.get_lifecycle_analytics(
        agent_id=agent_id,
        workspace_id=workspace_id,
        timeframe=timeframe
    )

@router.get("/{agent_id}/lifecycle/transitions")
async def get_lifecycle_transitions(
    agent_id: str = Path(...),
    workspace_id: str = Query(...),
    db=Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detailed state transition history."""
    service = AgentLifecycleService(db)
    return await service.get_state_transitions(agent_id, "all")

@router.get("/{agent_id}/lifecycle/status")
async def get_lifecycle_status(
    agent_id: str = Path(...),
    workspace_id: str = Query(...),
    db=Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current lifecycle status (lightweight endpoint)."""
    service = AgentLifecycleService(db)
    return await service.get_current_state(agent_id)
```

### Pattern 5: Frontend Hooks with React Query

**Current Example**: `hooks/api/useAgentAnalytics.ts`

**For Lifecycle Analytics**:
```typescript
// File: frontend/src/hooks/api/useAgentLifecycle.ts

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AgentLifecycle } from '@/types/agent-lifecycle';

interface UseAgentLifecycleParams {
  agentId: string;
  workspaceId: string;
  timeframe?: '24h' | '7d' | '30d' | 'all';
  skipCache?: boolean;
}

export function useAgentLifecycle({
  agentId,
  workspaceId,
  timeframe = 'all',
  skipCache = false
}: UseAgentLifecycleParams) {
  return useQuery<AgentLifecycle>({
    queryKey: ['agentLifecycle', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await api.get(
        `/agents/${agentId}/lifecycle`,
        {
          params: { workspace_id: workspaceId, timeframe }
        }
      );
      return response.data;
    },
    staleTime: 1000 * 60, // 1 minute
    gcTime: 1000 * 60 * 5, // 5 minutes (was cacheTime)
    refetchOnWindowFocus: true,
    retry: 2,
    enabled: Boolean(agentId && workspaceId) && !skipCache
  });
}

// Lightweight status-only hook for frequent polling
export function useAgentLifecycleStatus({
  agentId,
  workspaceId
}: Omit<UseAgentLifecycleParams, 'timeframe' | 'skipCache'>) {
  return useQuery<AgentLifecycleStatus>({
    queryKey: ['agentLifecycleStatus', agentId, workspaceId],
    queryFn: async () => {
      const response = await api.get(
        `/agents/${agentId}/lifecycle/status`,
        { params: { workspace_id: workspaceId } }
      );
      return response.data;
    },
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60, // 1 minute
    refetchInterval: 1000 * 60 // Poll every minute
  });
}
```

### Pattern 6: Frontend Components

**Current Example**: `components/agents/PerformanceMetrics.tsx`

**For Lifecycle Analytics**:
```typescript
// File: frontend/src/components/agents/AgentLifecycleStatus.tsx

'use client';

import React from 'react';
import { useAgentLifecycle } from '@/hooks/api/useAgentLifecycle';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ErrorAlert } from '@/components/common/ErrorAlert';

interface AgentLifecycleStatusProps {
  agentId: string;
  workspaceId: string;
}

const stateColors = {
  created: 'bg-gray-100 text-gray-800',
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  deprecated: 'bg-orange-100 text-orange-800',
  archived: 'bg-red-100 text-red-800'
};

export function AgentLifecycleStatus({
  agentId,
  workspaceId
}: AgentLifecycleStatusProps) {
  const { data, isLoading, error } = useAgentLifecycle({
    agentId,
    workspaceId,
    timeframe: 'all'
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!data) return null;

  const { lifecycleMetrics, currentState, timeline } = data;

  return (
    <div className="space-y-4">
      {/* Current State */}
      <Card>
        <CardHeader>
          <CardTitle>Lifecycle Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-gray-500">Current State</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${stateColors[currentState]}`}>
                {currentState.toUpperCase()}
              </span>
              <span className="text-sm text-gray-600">
                for {lifecycleMetrics.days_in_current_state.toFixed(1)} days
              </span>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Days Since Creation</p>
              <p className="text-2xl font-semibold">
                {lifecycleMetrics.total_days_since_creation.toFixed(1)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Transitions</p>
              <p className="text-2xl font-semibold">
                {lifecycleMetrics.total_transitions}
              </p>
            </div>
          </div>

          {/* Activation Lag (if relevant) */}
          {lifecycleMetrics.activation_lag !== null && (
            <div>
              <p className="text-sm text-gray-500">Activation Lag</p>
              <p className="text-lg font-medium">
                {lifecycleMetrics.activation_lag.toFixed(1)} days
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>State Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {timeline.map((event, idx) => (
              <div key={idx} className="flex gap-4 text-sm">
                <span className="text-gray-500 whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleDateString()}
                </span>
                <span className={`px-2 py-1 rounded ${stateColors[event.state]}`}>
                  {event.state.toUpperCase()}
                </span>
                <span className="text-gray-600">{event.event}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Pattern 7: TypeScript Types

**Current Example**: `types/agent-analytics.ts`

**For Lifecycle Analytics**:
```typescript
// File: frontend/src/types/agent-lifecycle.ts

export interface StateTransition {
  fromState: string | null;
  toState: string;
  transitionAt: string;
  durationInState: number | null;
  triggeredBy: string;
  transitionReason?: string;
  metadata: Record<string, any>;
}

export interface StateDuration {
  state: string;
  totalDurationSeconds: number;
  averageDurationSeconds: number;
  totalOccurrences: number;
  percentageOfLifetime: number;
}

export interface LifecycleTimeline {
  timestamp: string;
  state: string;
  event: string;
}

export interface LifecycleMetrics {
  currentState: string;
  daysInCurrentState: number;
  totalDaysSinceCreation: number;
  totalTransitions: number;
  activationLag?: number;
  deprecationLag?: number;
}

export interface AgentLifecycle {
  agentId: string;
  workspaceId: string;
  generatedAt: string;
  currentState: string;
  currentStateSince: string;
  lifecycleMetrics: LifecycleMetrics;
  stateDurations: StateDuration[];
  transitions: StateTransition[];
  totalTransitions: number;
  timeline: LifecycleTimeline[];
}

export interface AgentLifecycleStatus {
  state: string;
  sinceTimestamp: string;
  daysInState: number;
}
```

---

## 2. Database Migration Template

Location: `/database/migrations/028_create_agent_lifecycle_tables.sql`

Key features:
- UUID primary keys
- Foreign key to agent_runs for context
- JSONB metadata for extensibility
- Proper indexes for query performance
- Constraints for valid state transitions
- Materialized view for summary data

---

## 3. Implementation Checklist

- [ ] Create database migration (SQL)
- [ ] Add Pydantic schemas for request/response
- [ ] Create lifecycle service class
- [ ] Add API route endpoints
- [ ] Create frontend types
- [ ] Create frontend hook
- [ ] Create frontend components
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add documentation
- [ ] Update main agent page to include lifecycle

---

## 4. State Machine Definition

```
created
  ↓
active (main operating state)
  ├→ paused (temporary pause)
  │   └→ active (resume)
  └→ deprecated (marked for sunset)
      └→ archived (permanently stored)

Transitions:
- created → active (required for use)
- active ↔ paused (temporary pause)
- active → deprecated (planned sunset)
- deprecated → archived (permanent removal)
- Any state → archived (force archival)
```

---

## 5. Key Metrics to Track

1. **Activation Lag**: Days from created to active
2. **Deprecation Lag**: Days from active to deprecated
3. **Mean Time in State**: Average duration in each state
4. **Transition Frequency**: How often agents change states
5. **State Distribution**: % of agents in each state
6. **State Churn**: Agents transitioning frequently

---

## 6. Integration Points

Existing systems that should be aware of lifecycle:
- Agent leaderboards (filter active agents only?)
- Agent analytics (lifecycle context)
- Executive dashboard (KPIs on agent health)
- Alerts (notify on state changes)
- Export services (include lifecycle in exports)

---

## 7. Performance Considerations

Using existing patterns:
- Materialized view for summary queries (refresh hourly or on-demand)
- BRIN indexes for time-series columns
- Query timeout: 30 seconds (like agent analytics)
- Result limits: 100 transitions max per query
- Async operations with `asyncio.gather()` for parallel queries

---

## References

- **Database Pattern**: `/database/migrations/009_create_agent_analytics_tables.sql`
- **Service Pattern**: `/backend/src/services/analytics/agent_analytics_service.py`
- **Route Pattern**: `/backend/src/api/routes/agents.py`
- **Schema Pattern**: `/backend/src/models/schemas/agent_analytics.py`
- **Hook Pattern**: `/frontend/src/hooks/api/useAgentAnalytics.ts`
- **Component Pattern**: `/frontend/src/components/agents/PerformanceMetrics.tsx`
- **Type Pattern**: `/frontend/src/types/agent-analytics.ts`

