# Specification: Agent Analytics

## Feature Overview
Comprehensive analytics for individual AI agents, tracking performance metrics, usage patterns, error rates, and optimization opportunities.

## Technical Requirements
- Real-time agent performance monitoring
- Historical performance trending
- Error analysis and categorization
- User satisfaction tracking
- Cost efficiency metrics
- Comparative analysis between agents

## Implementation Details

### Data Structure
```typescript
interface AgentAnalytics {
  agentId: string;
  agentName: string;
  agentType: string;
  workspaceId: string;
  timeframe: TimeFrame;
  
  // Performance Metrics
  performance: {
    totalRuns: number;
    successfulRuns: number;
    failedRuns: number;
    cancelledRuns: number;
    successRate: number;
    availabilityRate: number;
    
    // Runtime Statistics
    runtime: {
      average: number;
      median: number;
      min: number;
      max: number;
      p50: number;
      p75: number;
      p90: number;
      p95: number;
      p99: number;
      standardDeviation: number;
    };
    
    // Throughput
    throughput: {
      runsPerHour: number;
      runsPerDay: number;
      peakConcurrency: number;
      avgConcurrency: number;
    };
  };
  
  // Resource Usage
  resources: {
    totalCreditsConsumed: number;
    avgCreditsPerRun: number;
    totalTokensUsed: number;
    avgTokensPerRun: number;
    costPerRun: number;
    totalCost: number;
    
    // Model Usage Breakdown
    modelUsage: {
      [modelName: string]: {
        calls: number;
        tokens: number;
        credits: number;
      };
    };
  };
  
  // Error Analysis
  errors: {
    totalErrors: number;
    errorRate: number;
    
    // Error Categories
    errorsByType: {
      [errorType: string]: {
        count: number;
        percentage: number;
        lastOccurred: string;
        exampleMessage: string;
      };
    };
    
    // Error Patterns
    errorPatterns: Array<{
      pattern: string;
      frequency: number;
      impact: 'low' | 'medium' | 'high';
      suggestedFix: string;
    }>;
    
    // Recovery Metrics
    meanTimeToRecovery: number;
    autoRecoveryRate: number;
  };
  
  // User Interaction
  userMetrics: {
    uniqueUsers: number;
    totalInteractions: number;
    avgInteractionsPerUser: number;
    
    // Satisfaction
    userRatings: {
      average: number;
      total: number;
      distribution: {
        1: number;
        2: number;
        3: number;
        4: number;
        5: number;
      };
    };
    
    // Feedback
    feedback: Array<{
      userId: string;
      rating: number;
      comment: string;
      timestamp: string;
    }>;
    
    // Usage Patterns
    usageByHour: number[];
    usageByDayOfWeek: number[];
    topUsers: Array<{
      userId: string;
      runCount: number;
      successRate: number;
    }>;
  };
  
  // Comparative Analysis
  comparison: {
    vsWorkspaceAverage: {
      successRate: number;
      runtime: number;
      creditEfficiency: number;
    };
    
    vsAllAgents: {
      rank: number;
      percentile: number;
    };
    
    vsPreviousPeriod: {
      runsChange: number;
      successRateChange: number;
      runtimeChange: number;
      costChange: number;
    };
  };
  
  // Optimization Suggestions
  optimizations: Array<{
    type: 'performance' | 'cost' | 'reliability';
    title: string;
    description: string;
    estimatedImpact: string;
    effort: 'low' | 'medium' | 'high';
  }>;
  
  // Time Series Data
  trends: {
    daily: TimeSeriesMetric[];
    hourly: TimeSeriesMetric[];
  };
}

interface TimeSeriesMetric {
  timestamp: string;
  runs: number;
  successRate: number;
  avgRuntime: number;
  credits: number;
  errors: number;
}
```

### Frontend Components

#### Agent Analytics Dashboard
```typescript
// frontend/src/app/agents/[id]/page.tsx
'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useAgentAnalytics } from '@/hooks/api/useAgentAnalytics';
import { AgentHeader } from '@/components/agents/AgentHeader';
import { PerformanceMetrics } from '@/components/agents/PerformanceMetrics';
import { RuntimeDistribution } from '@/components/agents/RuntimeDistribution';
import { ErrorAnalysis } from '@/components/agents/ErrorAnalysis';
import { UserSatisfaction } from '@/components/agents/UserSatisfaction';
import { CostAnalysis } from '@/components/agents/CostAnalysis';
import { OptimizationSuggestions } from '@/components/agents/OptimizationSuggestions';
import { AgentComparison } from '@/components/agents/AgentComparison';
import { TimeframeSelector } from '@/components/common/TimeframeSelector';

export default function AgentAnalyticsPage() {
  const { id } = useParams();
  const [timeframe, setTimeframe] = useState<TimeFrame>('7d');
  const [compareWith, setCompareWith] = useState<string | null>(null);
  
  const { data, isLoading, error } = useAgentAnalytics(id as string, timeframe);
  
  if (isLoading) return <AgentAnalyticsSkeleton />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* Header with agent info and actions */}
      <AgentHeader 
        agent={data} 
        onExport={() => exportAnalytics(data)}
        onShare={() => shareAnalytics(data)}
      />
      
      {/* Timeframe selector */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <TimeframeSelector 
          value={timeframe} 
          onChange={setTimeframe} 
        />
      </div>
      
      {/* Main content grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        {/* Performance Overview */}
        <PerformanceMetrics metrics={data.performance} />
        
        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RuntimeDistribution runtime={data.performance.runtime} />
          <ErrorAnalysis errors={data.errors} />
        </div>
        
        {/* User Metrics */}
        <UserSatisfaction userMetrics={data.userMetrics} />
        
        {/* Cost Analysis */}
        <CostAnalysis resources={data.resources} />
        
        {/* Comparison */}
        <AgentComparison 
          comparison={data.comparison}
          agentId={id as string}
          compareWith={compareWith}
          onCompareChange={setCompareWith}
        />
        
        {/* Optimization Suggestions */}
        <OptimizationSuggestions 
          suggestions={data.optimizations}
          onImplement={(suggestion) => implementOptimization(suggestion)}
        />
      </div>
    </div>
  );
}
```

#### Runtime Distribution Chart
```typescript
// frontend/src/components/agents/RuntimeDistribution.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card } from '@/components/ui/Card';

interface RuntimeDistributionProps {
  runtime: AgentAnalytics['performance']['runtime'];
}

export function RuntimeDistribution({ runtime }: RuntimeDistributionProps) {
  const data = [
    { label: 'Min', value: runtime.min, fill: '#10b981' },
    { label: 'P50', value: runtime.p50, fill: '#3b82f6' },
    { label: 'P75', value: runtime.p75, fill: '#6366f1' },
    { label: 'P90', value: runtime.p90, fill: '#f59e0b' },
    { label: 'P95', value: runtime.p95, fill: '#f97316' },
    { label: 'P99', value: runtime.p99, fill: '#ef4444' },
    { label: 'Max', value: runtime.max, fill: '#dc2626' },
  ];
  
  return (
    <Card title="Runtime Distribution" description="Execution time percentiles">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis 
            label={{ value: 'Seconds', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip 
            formatter={(value) => `${value}s`}
            labelFormatter={(label) => `${label}th percentile`}
          />
          <Bar dataKey="value" fill={(entry) => entry.fill} />
        </BarChart>
      </ResponsiveContainer>
      
      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Average:</span>
          <span className="ml-2 font-medium">{runtime.average.toFixed(2)}s</span>
        </div>
        <div>
          <span className="text-gray-500">Median:</span>
          <span className="ml-2 font-medium">{runtime.median.toFixed(2)}s</span>
        </div>
        <div>
          <span className="text-gray-500">Std Dev:</span>
          <span className="ml-2 font-medium">{runtime.standardDeviation.toFixed(2)}s</span>
        </div>
      </div>
    </Card>
  );
}
```

### Backend Implementation

#### Agent Analytics Service
```python
# backend/src/services/analytics/agent_analytics.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

class AgentAnalyticsService:
    def __init__(self, db, cache_service):
        self.db = db
        self.cache = cache_service
    
    async def get_agent_analytics(
        self,
        agent_id: str,
        timeframe: str,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for an agent"""
        
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(timeframe)
        
        # Parallel fetch all metrics
        results = await asyncio.gather(
            self._get_performance_metrics(agent_id, start_date, end_date),
            self._get_resource_usage(agent_id, start_date, end_date),
            self._get_error_analysis(agent_id, start_date, end_date),
            self._get_user_metrics(agent_id, start_date, end_date),
            self._get_comparison_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_optimization_suggestions(agent_id),
            self._get_trend_data(agent_id, start_date, end_date)
        )
        
        return {
            "agentId": agent_id,
            "timeframe": timeframe,
            "performance": results[0],
            "resources": results[1],
            "errors": results[2],
            "userMetrics": results[3],
            "comparison": results[4],
            "optimizations": results[5],
            "trends": results[6]
        }
    
    async def _get_performance_metrics(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate performance metrics"""
        
        query = """
            SELECT 
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_runs,
                AVG(runtime_seconds) as avg_runtime,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as median_runtime,
                MIN(runtime_seconds) as min_runtime,
                MAX(runtime_seconds) as max_runtime,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99,
                STDDEV(runtime_seconds) as std_dev,
                COUNT(DISTINCT DATE_TRUNC('hour', started_at)) as active_hours,
                MAX(concurrent_runs) as peak_concurrency
            FROM public.agent_runs
            WHERE agent_id = $1 
                AND started_at BETWEEN $2 AND $3
        """
        
        result = await self.db.fetch_one(query, agent_id, start_date, end_date)
        
        success_rate = 0
        if result['total_runs'] > 0:
            success_rate = (result['successful_runs'] / result['total_runs']) * 100
        
        # Calculate throughput
        hours_in_period = (end_date - start_date).total_seconds() / 3600
        runs_per_hour = result['total_runs'] / hours_in_period if hours_in_period > 0 else 0
        
        return {
            "totalRuns": result['total_runs'],
            "successfulRuns": result['successful_runs'],
            "failedRuns": result['failed_runs'],
            "cancelledRuns": result['cancelled_runs'],
            "successRate": round(success_rate, 2),
            "runtime": {
                "average": round(result['avg_runtime'] or 0, 2),
                "median": round(result['median_runtime'] or 0, 2),
                "min": round(result['min_runtime'] or 0, 2),
                "max": round(result['max_runtime'] or 0, 2),
                "p50": round(result['p50'] or 0, 2),
                "p75": round(result['p75'] or 0, 2),
                "p90": round(result['p90'] or 0, 2),
                "p95": round(result['p95'] or 0, 2),
                "p99": round(result['p99'] or 0, 2),
                "standardDeviation": round(result['std_dev'] or 0, 2)
            },
            "throughput": {
                "runsPerHour": round(runs_per_hour, 2),
                "runsPerDay": round(runs_per_hour * 24, 2),
                "peakConcurrency": result['peak_concurrency'] or 0
            }
        }
    
    async def _get_error_analysis(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze error patterns and recovery"""
        
        # Get error breakdown
        error_query = """
            SELECT 
                error_type,
                COUNT(*) as count,
                MAX(error_message) as example_message,
                MAX(created_at) as last_occurred
            FROM public.agent_errors
            WHERE agent_id = $1 
                AND created_at BETWEEN $2 AND $3
            GROUP BY error_type
            ORDER BY count DESC
        """
        
        errors = await self.db.fetch_all(error_query, agent_id, start_date, end_date)
        
        total_errors = sum(e['count'] for e in errors)
        
        errors_by_type = {}
        for error in errors:
            errors_by_type[error['error_type']] = {
                "count": error['count'],
                "percentage": round((error['count'] / total_errors * 100) if total_errors > 0 else 0, 2),
                "lastOccurred": error['last_occurred'].isoformat(),
                "exampleMessage": error['example_message'][:200]
            }
        
        # Analyze error patterns
        patterns = await self._analyze_error_patterns(agent_id, start_date, end_date)
        
        # Calculate recovery metrics
        recovery_query = """
            SELECT 
                AVG(recovery_time_seconds) as mttr,
                COUNT(*) FILTER (WHERE auto_recovered = true) as auto_recovered,
                COUNT(*) as total_failures
            FROM public.agent_failures
            WHERE agent_id = $1 
                AND created_at BETWEEN $2 AND $3
        """
        
        recovery = await self.db.fetch_one(recovery_query, agent_id, start_date, end_date)
        
        return {
            "totalErrors": total_errors,
            "errorRate": round((total_errors / (total_errors + recovery['total_failures']) * 100) if recovery['total_failures'] > 0 else 0, 2),
            "errorsByType": errors_by_type,
            "errorPatterns": patterns,
            "meanTimeToRecovery": round(recovery['mttr'] or 0, 2),
            "autoRecoveryRate": round((recovery['auto_recovered'] / recovery['total_failures'] * 100) if recovery['total_failures'] > 0 else 0, 2)
        }
    
    async def _get_optimization_suggestions(
        self,
        agent_id: str
    ) -> List[Dict[str, Any]]:
        """Generate optimization suggestions based on analytics"""
        
        suggestions = []
        
        # Analyze recent performance
        recent_stats = await self._get_recent_stats(agent_id)
        
        # Performance optimizations
        if recent_stats['avg_runtime'] > 30:
            suggestions.append({
                "type": "performance",
                "title": "Reduce execution timeout",
                "description": "Average runtime exceeds 30 seconds. Consider optimizing prompts or breaking into smaller tasks.",
                "estimatedImpact": "20-30% runtime reduction",
                "effort": "medium"
            })
        
        # Cost optimizations
        if recent_stats['avg_tokens_per_run'] > 10000:
            suggestions.append({
                "type": "cost",
                "title": "Optimize token usage",
                "description": "High token consumption detected. Consider using more concise prompts or caching responses.",
                "estimatedImpact": "15-25% cost reduction",
                "effort": "low"
            })
        
        # Reliability optimizations
        if recent_stats['error_rate'] > 5:
            suggestions.append({
                "type": "reliability",
                "title": "Implement retry logic",
                "description": "Error rate above 5%. Add retry mechanisms for transient failures.",
                "estimatedImpact": "50% error reduction",
                "effort": "low"
            })
        
        return suggestions
```

#### Agent Comparison Service
```python
# backend/src/services/analytics/agent_comparison.py
class AgentComparisonService:
    async def compare_agents(
        self,
        agent_ids: List[str],
        metrics: List[str],
        timeframe: str
    ) -> Dict[str, Any]:
        """Compare multiple agents across specified metrics"""
        
        comparisons = {}
        
        for metric in metrics:
            if metric == 'success_rate':
                comparisons[metric] = await self._compare_success_rates(agent_ids, timeframe)
            elif metric == 'runtime':
                comparisons[metric] = await self._compare_runtimes(agent_ids, timeframe)
            elif metric == 'cost':
                comparisons[metric] = await self._compare_costs(agent_ids, timeframe)
            elif metric == 'usage':
                comparisons[metric] = await self._compare_usage(agent_ids, timeframe)
        
        return {
            "agents": agent_ids,
            "timeframe": timeframe,
            "comparisons": comparisons,
            "winner": self._determine_best_performer(comparisons)
        }
```

### Database Schema
```sql
-- Agent performance aggregation table
CREATE TABLE analytics.agent_performance_hourly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id),
    hour TIMESTAMPTZ NOT NULL,
    
    -- Execution metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_runtime_seconds NUMERIC(10,2),
    p50_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),
    
    -- Resource metrics
    total_credits NUMERIC(15,2),
    total_tokens INTEGER,
    
    -- User metrics
    unique_users INTEGER DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    sum_ratings INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_agent_hour UNIQUE(agent_id, hour)
);

-- Indexes for fast queries
CREATE INDEX idx_agent_performance_agent_hour 
    ON analytics.agent_performance_hourly(agent_id, hour DESC);
```

## Testing Requirements
- Unit tests for metric calculations
- Performance tests for percentile calculations
- Integration tests for comparison logic
- Load tests for large datasets
- Accuracy tests for statistical functions

## Performance Targets
- Analytics load time: <1 second
- Percentile calculation: <100ms
- Comparison query: <500ms
- Suggestion generation: <200ms

## Security Considerations
- Agent access restricted to workspace members
- PII filtering in error messages
- Rate limiting on expensive queries
- Audit logging for data exports