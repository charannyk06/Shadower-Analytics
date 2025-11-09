# Specification: Workspace Analytics

## Feature Overview
Multi-tenant workspace analytics providing insights into workspace performance, member activity, resource utilization, and cross-workspace comparisons for administrators.

## Technical Requirements
- Workspace-level data isolation
- Member activity tracking
- Resource usage monitoring
- Billing and subscription analytics
- Cross-workspace comparisons (admin only)
- Workspace health scoring

## Implementation Details

### Data Structure
```typescript
interface WorkspaceAnalytics {
  workspaceId: string;
  workspaceName: string;
  plan: 'free' | 'starter' | 'pro' | 'enterprise';
  timeframe: TimeFrame;
  
  // Overview Metrics
  overview: {
    // Members
    totalMembers: number;
    activeMembers: number;
    pendingInvites: number;
    memberGrowth: number; // percentage
    
    // Activity
    totalActivity: number;
    avgActivityPerMember: number;
    lastActivityAt: string;
    activityTrend: 'increasing' | 'stable' | 'decreasing';
    
    // Health Score
    healthScore: number; // 0-100
    healthFactors: {
      activity: number;
      engagement: number;
      efficiency: number;
      reliability: number;
    };
    
    // Status
    status: 'active' | 'idle' | 'at_risk' | 'churned';
    daysActive: number;
    createdAt: string;
  };
  
  // Member Analytics
  memberAnalytics: {
    // Member Breakdown
    membersByRole: {
      owner: number;
      admin: number;
      member: number;
      viewer: number;
    };
    
    // Activity Distribution
    activityDistribution: Array<{
      userId: string;
      userName: string;
      role: string;
      activityCount: number;
      lastActiveAt: string;
      engagementLevel: 'high' | 'medium' | 'low' | 'inactive';
    }>;
    
    // Top Contributors
    topContributors: Array<{
      userId: string;
      userName: string;
      contribution: {
        agentRuns: number;
        successRate: number;
        creditsUsed: number;
      };
    }>;
    
    // Inactive Members
    inactiveMembers: Array<{
      userId: string;
      userName: string;
      lastActiveAt: string;
      daysSinceActive: number;
    }>;
  };
  
  // Agent Usage
  agentUsage: {
    totalAgents: number;
    activeAgents: number;
    
    // Agent Performance
    agents: Array<{
      agentId: string;
      agentName: string;
      runs: number;
      successRate: number;
      avgRuntime: number;
      creditsConsumed: number;
      lastRunAt: string;
    }>;
    
    // Usage Patterns
    usageByAgent: {
      [agentId: string]: {
        daily: number[];
        weekly: number[];
        monthly: number[];
      };
    };
    
    // Agent Efficiency
    agentEfficiency: {
      mostEfficient: string;
      leastEfficient: string;
      avgSuccessRate: number;
      avgRuntime: number;
    };
  };
  
  // Resource Utilization
  resourceUtilization: {
    // Credits
    credits: {
      allocated: number;
      consumed: number;
      remaining: number;
      utilizationRate: number;
      projectedExhaustion: string | null;
      
      // Consumption Breakdown
      consumptionByModel: {
        [model: string]: {
          credits: number;
          percentage: number;
        };
      };
      
      // Daily Consumption
      dailyConsumption: Array<{
        date: string;
        credits: number;
      }>;
    };
    
    // Storage
    storage: {
      used: number; // bytes
      limit: number;
      utilizationRate: number;
      
      // Storage Breakdown
      breakdown: {
        documents: number;
        logs: number;
        cache: number;
        other: number;
      };
    };
    
    // API Usage
    apiUsage: {
      totalCalls: number;
      rateLimit: number;
      utilizationRate: number;
      
      // By Endpoint
      byEndpoint: {
        [endpoint: string]: {
          calls: number;
          avgLatency: number;
        };
      };
    };
  };
  
  // Billing & Subscription
  billing: {
    plan: string;
    status: 'active' | 'trial' | 'past_due' | 'cancelled';
    
    // Costs
    currentMonthCost: number;
    projectedMonthCost: number;
    lastMonthCost: number;
    
    // Usage vs Limits
    limits: {
      members: { used: number; limit: number };
      agents: { used: number; limit: number };
      credits: { used: number; limit: number };
      storage: { used: number; limit: number };
    };
    
    // Billing History
    history: Array<{
      date: string;
      amount: number;
      status: 'paid' | 'pending' | 'failed';
    }>;
    
    // Recommendations
    recommendations: Array<{
      type: 'upgrade' | 'downgrade' | 'add_on';
      reason: string;
      estimatedSavings: number;
    }>;
  };
  
  // Comparison (Admin Only)
  comparison?: {
    // Workspace Ranking
    ranking: {
      overall: number;
      totalWorkspaces: number;
      percentile: number;
    };
    
    // Benchmarks
    benchmarks: {
      activityVsAvg: number; // percentage
      efficiencyVsAvg: number;
      costVsAvg: number;
    };
    
    // Similar Workspaces
    similarWorkspaces: Array<{
      workspaceId: string;
      similarity: number; // 0-100
      metrics: {
        members: number;
        activity: number;
        credits: number;
      };
    }>;
  };
}
```

### Frontend Components

#### Workspace Analytics Dashboard
```typescript
// frontend/src/app/workspaces/[id]/page.tsx
'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useWorkspaceAnalytics } from '@/hooks/api/useWorkspaceAnalytics';
import { WorkspaceHeader } from '@/components/workspaces/WorkspaceHeader';
import { WorkspaceHealthScore } from '@/components/workspaces/WorkspaceHealthScore';
import { MemberActivity } from '@/components/workspaces/MemberActivity';
import { AgentUsageGrid } from '@/components/workspaces/AgentUsageGrid';
import { ResourceUtilization } from '@/components/workspaces/ResourceUtilization';
import { BillingOverview } from '@/components/workspaces/BillingOverview';
import { WorkspaceComparison } from '@/components/workspaces/WorkspaceComparison';

export default function WorkspaceAnalyticsPage() {
  const { id } = useParams();
  const [timeframe, setTimeframe] = useState<TimeFrame>('30d');
  const [activeTab, setActiveTab] = useState<'overview' | 'members' | 'agents' | 'resources' | 'billing'>('overview');
  
  const { data, isLoading, error } = useWorkspaceAnalytics(id as string, timeframe);
  const { user } = useAuth();
  
  if (isLoading) return <WorkspaceAnalyticsSkeleton />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-50">
      <WorkspaceHeader 
        workspace={data}
        timeframe={timeframe}
        onTimeframeChange={setTimeframe}
      />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Health Score Card */}
        <WorkspaceHealthScore 
          score={data.overview.healthScore}
          factors={data.overview.healthFactors}
          status={data.overview.status}
        />
        
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['overview', 'members', 'agents', 'resources', 'billing'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm capitalize
                  ${activeTab === tab 
                    ? 'border-blue-500 text-blue-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                `}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'overview' && (
            <>
              <OverviewMetrics data={data.overview} />
              {user.role === 'admin' && data.comparison && (
                <WorkspaceComparison comparison={data.comparison} />
              )}
            </>
          )}
          
          {activeTab === 'members' && (
            <MemberActivity data={data.memberAnalytics} />
          )}
          
          {activeTab === 'agents' && (
            <AgentUsageGrid data={data.agentUsage} />
          )}
          
          {activeTab === 'resources' && (
            <ResourceUtilization data={data.resourceUtilization} />
          )}
          
          {activeTab === 'billing' && (
            <BillingOverview data={data.billing} />
          )}
        </div>
      </div>
    </div>
  );
}
```

#### Workspace Health Score Component
```typescript
// frontend/src/components/workspaces/WorkspaceHealthScore.tsx
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';

interface WorkspaceHealthScoreProps {
  score: number;
  factors: {
    activity: number;
    engagement: number;
    efficiency: number;
    reliability: number;
  };
  status: string;
}

export function WorkspaceHealthScore({ score, factors, status }: WorkspaceHealthScoreProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#3b82f6';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  };
  
  const getStatusBadge = (status: string) => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      idle: 'bg-yellow-100 text-yellow-800',
      at_risk: 'bg-red-100 text-red-800',
      churned: 'bg-gray-100 text-gray-800'
    };
    
    return colors[status] || colors.idle;
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Workspace Health</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(status)}`}>
          {status.replace('_', ' ').toUpperCase()}
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        {/* Overall Score */}
        <div className="flex flex-col items-center">
          <div className="w-32 h-32">
            <CircularProgressbar
              value={score}
              text={`${score}`}
              styles={buildStyles({
                textSize: '24px',
                pathColor: getScoreColor(score),
                textColor: '#1f2937',
                trailColor: '#f3f4f6'
              })}
            />
          </div>
          <p className="mt-2 text-sm font-medium text-gray-600">Overall Health</p>
        </div>
        
        {/* Factor Scores */}
        {Object.entries(factors).map(([factor, value]) => (
          <div key={factor} className="flex flex-col items-center">
            <div className="w-24 h-24">
              <CircularProgressbar
                value={value}
                text={`${value}`}
                styles={buildStyles({
                  textSize: '28px',
                  pathColor: getScoreColor(value),
                  textColor: '#6b7280',
                  trailColor: '#f3f4f6'
                })}
              />
            </div>
            <p className="mt-2 text-sm text-gray-600 capitalize">{factor}</p>
          </div>
        ))}
      </div>
      
      {/* Health Insights */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Health Insights</h3>
        <ul className="space-y-1 text-sm text-blue-700">
          {score < 60 && <li>• Consider increasing member engagement</li>}
          {factors.efficiency < 60 && <li>• Agent success rates could be improved</li>}
          {factors.activity < 60 && <li>• Workspace activity is below average</li>}
          {factors.reliability < 60 && <li>• High error rates detected</li>}
        </ul>
      </div>
    </div>
  );
}
```

### Backend Implementation

#### Workspace Analytics Service
```python
# backend/src/services/analytics/workspace_analytics.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class WorkspaceAnalyticsService:
    def __init__(self, db, cache_service):
        self.db = db
        self.cache = cache_service
    
    async def get_workspace_analytics(
        self,
        workspace_id: str,
        timeframe: str,
        include_comparison: bool = False
    ) -> Dict[str, Any]:
        """Get comprehensive workspace analytics"""
        
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(timeframe)
        
        # Parallel fetch all metrics
        tasks = [
            self._get_overview_metrics(workspace_id, start_date, end_date),
            self._get_member_analytics(workspace_id, start_date, end_date),
            self._get_agent_usage(workspace_id, start_date, end_date),
            self._get_resource_utilization(workspace_id),
            self._get_billing_info(workspace_id)
        ]
        
        if include_comparison:
            tasks.append(self._get_workspace_comparison(workspace_id))
        
        results = await asyncio.gather(*tasks)
        
        response = {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "overview": results[0],
            "memberAnalytics": results[1],
            "agentUsage": results[2],
            "resourceUtilization": results[3],
            "billing": results[4]
        }
        
        if include_comparison:
            response["comparison"] = results[5]
        
        return response
    
    async def _get_overview_metrics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get workspace overview metrics"""
        
        query = """
            WITH workspace_data AS (
                SELECT 
                    w.id,
                    w.name,
                    w.created_at,
                    w.plan,
                    COUNT(DISTINCT wm.user_id) as total_members,
                    COUNT(DISTINCT wm.user_id) FILTER (
                        WHERE wm.last_active_at > NOW() - INTERVAL '7 days'
                    ) as active_members,
                    COUNT(DISTINCT wi.id) FILTER (
                        WHERE wi.status = 'pending'
                    ) as pending_invites
                FROM public.workspaces w
                LEFT JOIN public.workspace_members wm ON w.id = wm.workspace_id
                LEFT JOIN public.workspace_invites wi ON w.id = wi.workspace_id
                WHERE w.id = $1
                GROUP BY w.id, w.name, w.created_at, w.plan
            ),
            activity_data AS (
                SELECT 
                    COUNT(*) as total_activity,
                    MAX(created_at) as last_activity_at
                FROM analytics.user_activity
                WHERE workspace_id = $1
                    AND created_at BETWEEN $2 AND $3
            )
            SELECT 
                wd.*,
                ad.total_activity,
                ad.last_activity_at,
                EXTRACT(DAY FROM NOW() - wd.created_at) as days_active
            FROM workspace_data wd
            CROSS JOIN activity_data ad
        """
        
        result = await self.db.fetch_one(query, workspace_id, start_date, end_date)
        
        # Calculate health score
        health_score = await self._calculate_health_score(workspace_id)
        
        # Determine status
        status = self._determine_workspace_status(
            result['last_activity_at'],
            result['active_members'],
            health_score
        )
        
        return {
            "totalMembers": result['total_members'],
            "activeMembers": result['active_members'],
            "pendingInvites": result['pending_invites'],
            "totalActivity": result['total_activity'],
            "avgActivityPerMember": round(
                result['total_activity'] / result['total_members'] 
                if result['total_members'] > 0 else 0, 2
            ),
            "lastActivityAt": result['last_activity_at'].isoformat() if result['last_activity_at'] else None,
            "healthScore": health_score['overall'],
            "healthFactors": health_score['factors'],
            "status": status,
            "daysActive": result['days_active'],
            "createdAt": result['created_at'].isoformat()
        }
    
    async def _calculate_health_score(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Calculate workspace health score"""
        
        # Activity Score (based on daily active members)
        activity_query = """
            SELECT 
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT DATE(created_at)) as active_days
            FROM analytics.user_activity
            WHERE workspace_id = $1
                AND created_at > NOW() - INTERVAL '30 days'
        """
        activity_result = await self.db.fetch_one(activity_query, workspace_id)
        
        # Get total members for percentage
        members_query = """
            SELECT COUNT(*) as total_members
            FROM public.workspace_members
            WHERE workspace_id = $1
        """
        members_result = await self.db.fetch_one(members_query, workspace_id)
        
        # Calculate scores
        activity_score = min(100, (activity_result['active_users'] / max(members_result['total_members'], 1)) * 100)
        
        # Engagement Score (based on feature usage)
        engagement_score = await self._calculate_engagement_score(workspace_id)
        
        # Efficiency Score (based on agent success rates)
        efficiency_score = await self._calculate_efficiency_score(workspace_id)
        
        # Reliability Score (based on error rates)
        reliability_score = await self._calculate_reliability_score(workspace_id)
        
        # Overall score (weighted average)
        overall_score = (
            activity_score * 0.3 +
            engagement_score * 0.3 +
            efficiency_score * 0.2 +
            reliability_score * 0.2
        )
        
        return {
            "overall": round(overall_score),
            "factors": {
                "activity": round(activity_score),
                "engagement": round(engagement_score),
                "efficiency": round(efficiency_score),
                "reliability": round(reliability_score)
            }
        }
    
    async def _get_resource_utilization(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get resource utilization metrics"""
        
        # Credits utilization
        credits_query = """
            SELECT 
                wc.allocated_credits,
                wc.consumed_credits,
                wc.allocated_credits - wc.consumed_credits as remaining_credits,
                ARRAY_AGG(
                    JSON_BUILD_OBJECT(
                        'date', DATE(ar.started_at),
                        'credits', SUM(ar.credits_consumed)
                    ) ORDER BY DATE(ar.started_at)
                ) as daily_consumption
            FROM public.workspace_credits wc
            LEFT JOIN public.agent_runs ar ON ar.workspace_id = wc.workspace_id
                AND ar.started_at > NOW() - INTERVAL '30 days'
            WHERE wc.workspace_id = $1
            GROUP BY wc.allocated_credits, wc.consumed_credits
        """
        
        credits = await self.db.fetch_one(credits_query, workspace_id)
        
        # Storage utilization
        storage_query = """
            SELECT 
                SUM(file_size) as used_storage,
                COUNT(*) as file_count
            FROM public.workspace_files
            WHERE workspace_id = $1
        """
        
        storage = await self.db.fetch_one(storage_query, workspace_id)
        
        # API usage
        api_usage = await self._get_api_usage(workspace_id)
        
        return {
            "credits": {
                "allocated": credits['allocated_credits'] or 0,
                "consumed": credits['consumed_credits'] or 0,
                "remaining": credits['remaining_credits'] or 0,
                "utilizationRate": round(
                    (credits['consumed_credits'] / credits['allocated_credits'] * 100)
                    if credits['allocated_credits'] > 0 else 0, 2
                ),
                "dailyConsumption": credits['daily_consumption'] or []
            },
            "storage": {
                "used": storage['used_storage'] or 0,
                "limit": 10737418240,  # 10GB default
                "utilizationRate": round(
                    (storage['used_storage'] / 10737418240 * 100)
                    if storage['used_storage'] else 0, 2
                )
            },
            "apiUsage": api_usage
        }
```

### Database Schema
```sql
-- Workspace metrics aggregation
CREATE TABLE analytics.workspace_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id),
    metric_date DATE NOT NULL,
    
    -- Member metrics
    total_members INTEGER DEFAULT 0,
    active_members INTEGER DEFAULT 0,
    new_members INTEGER DEFAULT 0,
    
    -- Activity metrics
    total_activity INTEGER DEFAULT 0,
    unique_active_users INTEGER DEFAULT 0,
    avg_activity_per_user NUMERIC(10,2),
    
    -- Agent metrics
    total_agent_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    
    -- Resource metrics
    credits_consumed NUMERIC(15,2) DEFAULT 0,
    storage_used_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    
    -- Health metrics
    health_score INTEGER,
    activity_score INTEGER,
    engagement_score INTEGER,
    efficiency_score INTEGER,
    reliability_score INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_workspace_daily UNIQUE(workspace_id, metric_date)
);

-- Indexes
CREATE INDEX idx_workspace_metrics_workspace_date 
    ON analytics.workspace_metrics_daily(workspace_id, metric_date DESC);

-- Workspace comparison view
CREATE MATERIALIZED VIEW analytics.mv_workspace_comparison AS
SELECT 
    workspace_id,
    AVG(health_score) as avg_health_score,
    AVG(total_activity) as avg_activity,
    AVG(credits_consumed) as avg_credits,
    RANK() OVER (ORDER BY AVG(health_score) DESC) as health_rank,
    RANK() OVER (ORDER BY AVG(total_activity) DESC) as activity_rank,
    RANK() OVER (ORDER BY AVG(credits_consumed) ASC) as efficiency_rank
FROM analytics.workspace_metrics_daily
WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY workspace_id;

CREATE UNIQUE INDEX ON analytics.mv_workspace_comparison(workspace_id);
```

## Testing Requirements
- Unit tests for health score calculation
- Integration tests for multi-workspace queries
- Performance tests for comparison queries
- Data isolation tests
- Permission tests for admin features

## Performance Targets
- Workspace overview load: <1 second
- Member analytics: <500ms
- Resource utilization: <500ms
- Health score calculation: <200ms
- Cross-workspace comparison: <2 seconds

## Security Considerations
- Strict workspace data isolation
- Admin-only access to comparisons
- Sensitive billing data protection
- Member PII protection
- Audit logging for data access