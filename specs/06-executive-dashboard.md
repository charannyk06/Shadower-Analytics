# Specification: Executive Dashboard

## Feature Overview
High-level CEO dashboard providing comprehensive business metrics, user activity, agent performance, and financial KPIs at a glance.

## Technical Requirements
- Real-time metric updates via WebSocket
- Multiple timeframe views (24h, 7d, 30d, 90d, All-time)
- Responsive grid layout
- Export functionality (PDF/CSV)
- Customizable metric cards

## Implementation Details

### Dashboard Layout Structure
```typescript
// Component hierarchy
ExecutiveDashboard
├── DashboardHeader
│   ├── TimeframeSelector
│   ├── RefreshButton
│   └── ExportMenu
├── MetricsGrid
│   ├── MetricCard (DAU/WAU/MAU)
│   ├── MetricCard (Total Executions)
│   ├── MetricCard (Success Rate)
│   ├── MetricCard (Credits Used)
│   ├── MetricCard (Active Workspaces)
│   └── MetricCard (MRR/Revenue)
├── ChartsSection
│   ├── ExecutionTrendChart
│   ├── UserActivityChart
│   ├── RevenueChart
│   └── ErrorRateChart
├── TablesSection
│   ├── TopAgentsTable
│   ├── TopUsersTable
│   └── RecentAlertsTable
└── LiveActivityFeed
```

### Data Structure
```typescript
interface ExecutiveDashboardData {
  // Time period
  timeframe: '24h' | '7d' | '30d' | '90d' | 'all';
  period: {
    start: string;
    end: string;
  };
  
  // User Metrics
  userMetrics: {
    dau: number;
    dauChange: number; // Percentage change
    wau: number;
    wauChange: number;
    mau: number;
    mauChange: number;
    newUsers: number;
    churnedUsers: number;
    activeRate: number; // Percentage of active users
  };
  
  // Execution Metrics
  executionMetrics: {
    totalRuns: number;
    totalRunsChange: number;
    successfulRuns: number;
    failedRuns: number;
    successRate: number;
    successRateChange: number;
    avgRuntime: number; // seconds
    p95Runtime: number;
    totalCreditsUsed: number;
    creditsChange: number;
  };
  
  // Business Metrics
  businessMetrics: {
    mrr: number;
    mrrChange: number;
    arr: number;
    ltv: number;
    cac: number;
    ltvCacRatio: number;
    activeWorkspaces: number;
    paidWorkspaces: number;
    trialWorkspaces: number;
    churnRate: number;
  };
  
  // Agent Metrics
  agentMetrics: {
    totalAgents: number;
    activeAgents: number;
    topAgents: Array<{
      id: string;
      name: string;
      runs: number;
      successRate: number;
      avgRuntime: number;
    }>;
  };
  
  // Trend Data
  trends: {
    execution: TimeSeriesData[];
    users: TimeSeriesData[];
    revenue: TimeSeriesData[];
    errors: TimeSeriesData[];
  };
  
  // Alerts
  activeAlerts: Array<{
    id: string;
    type: string;
    message: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    triggeredAt: string;
  }>;
}

interface TimeSeriesData {
  timestamp: string;
  value: number;
  label?: string;
}
```

### Frontend Components

#### Main Dashboard Component
```typescript
// frontend/src/app/executive/page.tsx
'use client';

import { useState } from 'react';
import { useExecutiveDashboard } from '@/hooks/api/useExecutiveDashboard';
import { useWebSocket } from '@/hooks/useWebSocket';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { MetricsGrid } from '@/components/dashboard/MetricsGrid';
import { ChartsSection } from '@/components/dashboard/ChartsSection';
import { TablesSection } from '@/components/dashboard/TablesSection';
import { LiveActivityFeed } from '@/components/dashboard/LiveActivityFeed';
import { DashboardSkeleton } from '@/components/dashboard/DashboardSkeleton';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function ExecutiveDashboard() {
  const [timeframe, setTimeframe] = useState<'24h' | '7d' | '30d' | '90d' | 'all'>('7d');
  const { workspaceId } = useAuth();
  
  const { 
    data, 
    isLoading, 
    error, 
    refetch 
  } = useExecutiveDashboard(workspaceId, timeframe);
  
  // Real-time updates
  useWebSocket({
    workspaceId,
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'metrics_update') {
        // Trigger refetch or update local state
        refetch();
      }
    }
  });
  
  if (isLoading) return <DashboardSkeleton />;
  if (error) return <DashboardError error={error} onRetry={refetch} />;
  
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <DashboardHeader
          timeframe={timeframe}
          onTimeframeChange={setTimeframe}
          onRefresh={refetch}
          data={data}
        />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Key Metrics */}
          <MetricsGrid metrics={data} />
          
          {/* Charts */}
          <ChartsSection 
            trends={data.trends} 
            timeframe={timeframe}
          />
          
          {/* Tables and Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
            <div className="lg:col-span-2">
              <TablesSection data={data} />
            </div>
            <div>
              <LiveActivityFeed workspaceId={workspaceId} />
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
```

#### Metric Card Component
```typescript
// frontend/src/components/dashboard/MetricCard.tsx
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';
import { motion } from 'framer-motion';
import { Tooltip } from '@/components/ui/Tooltip';

interface MetricCardProps {
  title: string;
  value: number | string;
  change?: number;
  format?: 'number' | 'currency' | 'percentage';
  icon?: React.ComponentType<{ className?: string }>;
  description?: string;
  trend?: 'up' | 'down' | 'neutral';
  loading?: boolean;
}

export function MetricCard({
  title,
  value,
  change,
  format = 'number',
  icon: Icon,
  description,
  trend,
  loading
}: MetricCardProps) {
  const formatValue = (val: number | string) => {
    if (typeof val === 'string') return val;
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val);
      
      case 'percentage':
        return `${val.toFixed(1)}%`;
      
      default:
        return val.toLocaleString();
    }
  };
  
  const getTrendColor = () => {
    if (!change) return 'text-gray-500';
    
    if (trend === 'neutral') return 'text-gray-500';
    
    // For most metrics, positive change is good
    // For error rate, churn rate, negative change is good
    const isNegativeGood = title.toLowerCase().includes('error') || 
                           title.toLowerCase().includes('churn');
    
    if (change > 0) {
      return isNegativeGood ? 'text-red-600' : 'text-green-600';
    } else {
      return isNegativeGood ? 'text-green-600' : 'text-red-600';
    }
  };
  
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {Icon && <Icon className="h-5 w-5 text-gray-400" />}
      </div>
      
      <div className="flex items-baseline justify-between">
        <p className="text-2xl font-semibold text-gray-900">
          {formatValue(value)}
        </p>
        
        {change !== undefined && (
          <div className={`flex items-center text-sm ${getTrendColor()}`}>
            {change > 0 ? (
              <ArrowUpIcon className="h-4 w-4 mr-1" />
            ) : (
              <ArrowDownIcon className="h-4 w-4 mr-1" />
            )}
            <span>{Math.abs(change).toFixed(1)}%</span>
          </div>
        )}
      </div>
      
      {description && (
        <Tooltip content={description}>
          <p className="mt-2 text-xs text-gray-500 truncate cursor-help">
            {description}
          </p>
        </Tooltip>
      )}
    </motion.div>
  );
}
```

#### Execution Trend Chart
```typescript
// frontend/src/components/charts/ExecutionTrendChart.tsx
import { 
  LineChart, 
  Line, 
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  ResponsiveContainer 
} from 'recharts';
import { format } from 'date-fns';

interface ExecutionTrendChartProps {
  data: TimeSeriesData[];
  timeframe: string;
  showSuccess?: boolean;
}

export function ExecutionTrendChart({ 
  data, 
  timeframe,
  showSuccess = true 
}: ExecutionTrendChartProps) {
  
  const formatXAxis = (timestamp: string) => {
    const date = new Date(timestamp);
    
    switch (timeframe) {
      case '24h':
        return format(date, 'HH:mm');
      case '7d':
        return format(date, 'EEE');
      case '30d':
        return format(date, 'MMM d');
      default:
        return format(date, 'MMM d');
    }
  };
  
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Execution Trends</h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="timestamp" 
            tickFormatter={formatXAxis}
            style={{ fontSize: 12 }}
          />
          <YAxis style={{ fontSize: 12 }} />
          <Tooltip 
            labelFormatter={(value) => format(new Date(value), 'PPpp')}
            contentStyle={{ 
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}
          />
          <Legend />
          
          <Line
            type="monotone"
            dataKey="total"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name="Total Executions"
          />
          
          {showSuccess && (
            <>
              <Line
                type="monotone"
                dataKey="successful"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Successful"
              />
              <Line
                type="monotone"
                dataKey="failed"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                name="Failed"
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Backend API Implementation

#### Executive Dashboard Route
```python
# backend/src/api/routes/executive.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/executive", tags=["executive"])

@router.get("/overview")
@cached(
    key_func=lambda workspace_id, timeframe, **_: 
        CacheKeys.executive_dashboard(workspace_id, timeframe),
    ttl=CacheKeys.TTL_LONG
)
@require_permission("view_executive_dashboard")
async def get_executive_overview(
    workspace_id: str,
    timeframe: str = Query("7d", regex="^(24h|7d|30d|90d|all)$"),
    current_user: Dict[str, Any] = Depends(jwt_auth.get_current_user)
) -> ExecutiveDashboardResponse:
    """Get comprehensive executive dashboard data"""
    
    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = calculate_start_date(timeframe)
    
    # Parallel fetch all metrics
    results = await asyncio.gather(
        metrics_service.get_user_metrics(workspace_id, start_date, end_date),
        metrics_service.get_execution_metrics(workspace_id, start_date, end_date),
        metrics_service.get_business_metrics(workspace_id, start_date, end_date),
        metrics_service.get_agent_metrics(workspace_id, start_date, end_date),
        metrics_service.get_trend_data(workspace_id, start_date, end_date),
        alert_service.get_active_alerts(workspace_id),
        return_exceptions=True
    )
    
    # Handle any errors
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching metric {idx}: {result}")
            results[idx] = {}
    
    return ExecutiveDashboardResponse(
        timeframe=timeframe,
        period={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        userMetrics=results[0],
        executionMetrics=results[1],
        businessMetrics=results[2],
        agentMetrics=results[3],
        trends=results[4],
        activeAlerts=results[5]
    )
```

## Testing Requirements
- Unit tests for all metric calculations
- Integration tests for data aggregation
- Performance tests for dashboard load time
- Real-time update tests
- Export functionality tests

## Performance Targets
- Initial dashboard load: <2 seconds
- Metric card update: <100ms
- Chart render: <500ms
- Real-time update latency: <1 second
- Export generation: <5 seconds

## Security Considerations
- Role-based access control (CEO/Admin only)
- Data filtering by workspace
- Audit logging for exports
- Rate limiting on API endpoints