# Specification: Execution Metrics

## Feature Overview
Real-time and historical tracking of agent execution metrics including performance, throughput, latency, queue depth, and resource utilization.

## Technical Requirements
- Real-time execution monitoring
- Queue depth tracking
- Latency percentile calculations
- Throughput analysis
- Resource utilization metrics
- Execution pattern analysis

## Implementation Details

### Data Structure
```typescript
interface ExecutionMetrics {
  timeframe: TimeFrame;
  workspaceId: string;
  
  // Real-time Metrics
  realtime: {
    currentlyRunning: number;
    queueDepth: number;
    avgQueueWaitTime: number; // seconds
    
    // Live Status
    executionsInProgress: Array<{
      runId: string;
      agentId: string;
      agentName: string;
      userId: string;
      startedAt: string;
      elapsedTime: number;
      estimatedCompletion: string;
    }>;
    
    // Queue Status
    queuedExecutions: Array<{
      queueId: string;
      agentId: string;
      priority: number;
      queuedAt: string;
      estimatedStartTime: string;
    }>;
    
    // System Status
    systemLoad: {
      cpu: number; // percentage
      memory: number; // percentage
      workers: {
        total: number;
        busy: number;
        idle: number;
      };
    };
  };
  
  // Throughput Metrics
  throughput: {
    // Executions per time unit
    executionsPerMinute: number;
    executionsPerHour: number;
    executionsPerDay: number;
    
    // Throughput Trend
    throughputTrend: Array<{
      timestamp: string;
      value: number;
    }>;
    
    // Peak Throughput
    peakThroughput: {
      value: number;
      timestamp: string;
    };
    
    // Capacity Utilization
    capacityUtilization: number; // percentage
    maxCapacity: number;
  };
  
  // Latency Metrics
  latency: {
    // Queue Latency
    queueLatency: {
      avg: number;
      median: number;
      p50: number;
      p75: number;
      p90: number;
      p95: number;
      p99: number;
    };
    
    // Execution Latency
    executionLatency: {
      avg: number;
      median: number;
      p50: number;
      p75: number;
      p90: number;
      p95: number;
      p99: number;
    };
    
    // End-to-End Latency
    endToEndLatency: {
      avg: number;
      median: number;
      p50: number;
      p75: number;
      p90: number;
      p95: number;
      p99: number;
    };
    
    // Latency Distribution
    latencyDistribution: Array<{
      bucket: string; // "0-1s", "1-5s", etc.
      count: number;
      percentage: number;
    }>;
  };
  
  // Performance Metrics
  performance: {
    totalExecutions: number;
    successfulExecutions: number;
    failedExecutions: number;
    cancelledExecutions: number;
    
    // Success Metrics
    successRate: number;
    failureRate: number;
    cancellationRate: number;
    
    // Performance by Agent
    byAgent: Array<{
      agentId: string;
      agentName: string;
      executions: number;
      successRate: number;
      avgRuntime: number;
      errorRate: number;
    }>;
    
    // Performance by Time
    byHour: Array<{
      hour: number;
      executions: number;
      successRate: number;
      avgLatency: number;
    }>;
    
    // Performance Comparison
    vsLastPeriod: {
      executionsChange: number;
      successRateChange: number;
      latencyChange: number;
    };
  };
  
  // Execution Patterns
  patterns: {
    // Execution Timeline
    timeline: Array<{
      timestamp: string;
      executions: number;
      successRate: number;
      avgDuration: number;
    }>;
    
    // Burst Detection
    bursts: Array<{
      startTime: string;
      endTime: string;
      peakExecutions: number;
      totalExecutions: number;
      impact: 'low' | 'medium' | 'high';
    }>;
    
    // Pattern Analysis
    patterns: {
      peakHours: number[];
      quietHours: number[];
      averageDaily: number;
      weekdayAverage: number;
      weekendAverage: number;
    };
    
    // Anomalies
    anomalies: Array<{
      timestamp: string;
      type: 'spike' | 'drop' | 'failure_surge';
      severity: 'low' | 'medium' | 'high';
      description: string;
    }>;
  };
  
  // Resource Utilization
  resources: {
    // Compute Resources
    compute: {
      cpuUsage: Array<{
        timestamp: string;
        value: number;
      }>;
      memoryUsage: Array<{
        timestamp: string;
        value: number;
      }>;
      gpuUsage?: Array<{
        timestamp: string;
        value: number;
      }>;
    };
    
    // Model Usage
    modelUsage: {
      [modelName: string]: {
        calls: number;
        tokens: number;
        avgLatency: number;
        cost: number;
      };
    };
    
    // Database Load
    databaseLoad: {
      connections: number;
      queryRate: number;
      avgQueryTime: number;
    };
  };
}
```

### Frontend Components

#### Execution Metrics Dashboard
```typescript
// frontend/src/components/execution/ExecutionMetricsDashboard.tsx
'use client';

import { useState, useEffect } from 'react';
import { useExecutionMetrics } from '@/hooks/api/useExecutionMetrics';
import { useWebSocket } from '@/hooks/useWebSocket';
import { RealtimeExecutions } from './RealtimeExecutions';
import { ThroughputChart } from './ThroughputChart';
import { LatencyDistribution } from './LatencyDistribution';
import { QueueDepthIndicator } from './QueueDepthIndicator';
import { SystemLoadMonitor } from './SystemLoadMonitor';
import { ExecutionTimeline } from './ExecutionTimeline';

export function ExecutionMetricsDashboard({ workspaceId }: { workspaceId: string }) {
  const [timeframe, setTimeframe] = useState<TimeFrame>('1h');
  const { data, isLoading, error, refetch } = useExecutionMetrics(workspaceId, timeframe);
  const [realtimeData, setRealtimeData] = useState(data?.realtime);
  
  // Real-time updates
  useWebSocket({
    workspaceId,
    onMessage: (event) => {
      const message = JSON.parse(event.data);
      if (message.event === 'execution_update') {
        setRealtimeData(message.data);
      }
    }
  });
  
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="space-y-6">
      {/* Real-time Status Bar */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {realtimeData?.currentlyRunning || 0}
            </div>
            <div className="text-sm text-gray-500">Running Now</div>
          </div>
          
          <QueueDepthIndicator 
            depth={realtimeData?.queueDepth || 0}
            waitTime={realtimeData?.avgQueueWaitTime || 0}
          />
          
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {data.throughput.executionsPerMinute}
            </div>
            <div className="text-sm text-gray-500">Per Minute</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold">
              {data.performance.successRate}%
            </div>
            <div className="text-sm text-gray-500">Success Rate</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold">
              {data.latency.executionLatency.median}s
            </div>
            <div className="text-sm text-gray-500">Median Latency</div>
          </div>
        </div>
      </div>
      
      {/* Live Executions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RealtimeExecutions executions={realtimeData?.executionsInProgress || []} />
        <SystemLoadMonitor load={realtimeData?.systemLoad} />
      </div>
      
      {/* Throughput and Latency Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ThroughputChart data={data.throughput} />
        <LatencyDistribution data={data.latency} />
      </div>
      
      {/* Execution Timeline */}
      <ExecutionTimeline 
        timeline={data.patterns.timeline}
        anomalies={data.patterns.anomalies}
      />
      
      {/* Performance Breakdown */}
      <PerformanceByAgent agents={data.performance.byAgent} />
    </div>
  );
}
```

#### Real-time Executions Component
```typescript
// frontend/src/components/execution/RealtimeExecutions.tsx
import { motion, AnimatePresence } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';

interface Execution {
  runId: string;
  agentId: string;
  agentName: string;
  userId: string;
  startedAt: string;
  elapsedTime: number;
  estimatedCompletion: string;
}

export function RealtimeExecutions({ executions }: { executions: Execution[] }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">
        Live Executions ({executions.length})
      </h3>
      
      <div className="space-y-2 max-h-96 overflow-y-auto">
        <AnimatePresence>
          {executions.map((exec) => (
            <motion.div
              key={exec.runId}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="border rounded-lg p-3 hover:bg-gray-50"
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium text-sm">{exec.agentName}</p>
                  <p className="text-xs text-gray-500">
                    Started {formatDistanceToNow(new Date(exec.startedAt))} ago
                  </p>
                </div>
                
                <div className="text-right">
                  <ProgressIndicator 
                    elapsed={exec.elapsedTime}
                    estimated={exec.estimatedCompletion}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {exec.elapsedTime}s elapsed
                  </p>
                </div>
              </div>
              
              {/* Progress Bar */}
              <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                <motion.div 
                  className="bg-blue-600 h-1.5 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ 
                    width: `${Math.min(
                      (exec.elapsedTime / parseInt(exec.estimatedCompletion)) * 100, 
                      100
                    )}%` 
                  }}
                  transition={{ duration: 1 }}
                />
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {executions.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No executions running
          </div>
        )}
      </div>
    </div>
  );
}
```

### Backend Implementation

#### Execution Metrics Service
```python
# backend/src/services/metrics/execution_metrics.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import numpy as np

class ExecutionMetricsService:
    def __init__(self, db, redis_client, monitoring_service):
        self.db = db
        self.redis = redis_client
        self.monitoring = monitoring_service
    
    async def get_execution_metrics(
        self,
        workspace_id: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Get comprehensive execution metrics"""
        
        end_time = datetime.utcnow()
        start_time = self._calculate_start_time(timeframe)
        
        # Parallel fetch all metrics
        results = await asyncio.gather(
            self._get_realtime_metrics(workspace_id),
            self._get_throughput_metrics(workspace_id, start_time, end_time),
            self._get_latency_metrics(workspace_id, start_time, end_time),
            self._get_performance_metrics(workspace_id, start_time, end_time),
            self._get_execution_patterns(workspace_id, start_time, end_time),
            self._get_resource_utilization(workspace_id)
        )
        
        return {
            "timeframe": timeframe,
            "workspaceId": workspace_id,
            "realtime": results[0],
            "throughput": results[1],
            "latency": results[2],
            "performance": results[3],
            "patterns": results[4],
            "resources": results[5]
        }
    
    async def _get_realtime_metrics(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get real-time execution status"""
        
        # Get currently running executions
        running_query = """
            SELECT 
                run_id,
                agent_id,
                a.name as agent_name,
                user_id,
                started_at,
                EXTRACT(EPOCH FROM (NOW() - started_at)) as elapsed_time,
                estimated_runtime
            FROM public.agent_runs ar
            JOIN public.agents a ON ar.agent_id = a.id
            WHERE ar.workspace_id = $1
                AND ar.status = 'running'
            ORDER BY ar.started_at DESC
        """
        
        running = await self.db.fetch_all(running_query, workspace_id)
        
        # Get queued executions
        queue_query = """
            SELECT 
                queue_id,
                agent_id,
                priority,
                queued_at,
                estimated_start_time
            FROM public.execution_queue
            WHERE workspace_id = $1
                AND status = 'queued'
            ORDER BY priority DESC, queued_at ASC
        """
        
        queued = await self.db.fetch_all(queue_query, workspace_id)
        
        # Get system load from monitoring service
        system_load = await self.monitoring.get_system_load()
        
        # Calculate average queue wait time
        avg_wait_time = 0
        if queued:
            wait_times = [
                (datetime.utcnow() - q['queued_at']).total_seconds() 
                for q in queued
            ]
            avg_wait_time = np.mean(wait_times)
        
        return {
            "currentlyRunning": len(running),
            "queueDepth": len(queued),
            "avgQueueWaitTime": round(avg_wait_time, 2),
            "executionsInProgress": [
                {
                    "runId": r['run_id'],
                    "agentId": r['agent_id'],
                    "agentName": r['agent_name'],
                    "userId": r['user_id'],
                    "startedAt": r['started_at'].isoformat(),
                    "elapsedTime": round(r['elapsed_time'], 2),
                    "estimatedCompletion": str(r['estimated_runtime'])
                }
                for r in running
            ],
            "queuedExecutions": [
                {
                    "queueId": q['queue_id'],
                    "agentId": q['agent_id'],
                    "priority": q['priority'],
                    "queuedAt": q['queued_at'].isoformat(),
                    "estimatedStartTime": q['estimated_start_time'].isoformat() if q['estimated_start_time'] else None
                }
                for q in queued
            ],
            "systemLoad": system_load
        }
    
    async def _get_latency_metrics(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate latency percentiles"""
        
        query = """
            SELECT 
                -- Queue Latency (time from queue to start)
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY queue_wait_seconds) as queue_p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY queue_wait_seconds) as queue_p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY queue_wait_seconds) as queue_p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY queue_wait_seconds) as queue_p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY queue_wait_seconds) as queue_p99,
                AVG(queue_wait_seconds) as queue_avg,
                
                -- Execution Latency (time to complete)
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as exec_p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as exec_p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as exec_p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as exec_p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as exec_p99,
                AVG(runtime_seconds) as exec_avg,
                
                -- End-to-end Latency
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_latency_seconds) as e2e_p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY total_latency_seconds) as e2e_p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_latency_seconds) as e2e_p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_seconds) as e2e_p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_seconds) as e2e_p99,
                AVG(total_latency_seconds) as e2e_avg
            FROM public.agent_runs
            WHERE workspace_id = $1
                AND started_at BETWEEN $2 AND $3
                AND status IN ('completed', 'failed')
        """
        
        result = await self.db.fetch_one(query, workspace_id, start_time, end_time)
        
        # Calculate latency distribution
        distribution_query = """
            SELECT 
                CASE 
                    WHEN runtime_seconds < 1 THEN '0-1s'
                    WHEN runtime_seconds < 5 THEN '1-5s'
                    WHEN runtime_seconds < 10 THEN '5-10s'
                    WHEN runtime_seconds < 30 THEN '10-30s'
                    WHEN runtime_seconds < 60 THEN '30-60s'
                    ELSE '60s+'
                END as bucket,
                COUNT(*) as count
            FROM public.agent_runs
            WHERE workspace_id = $1
                AND started_at BETWEEN $2 AND $3
            GROUP BY bucket
            ORDER BY bucket
        """
        
        distribution = await self.db.fetch_all(distribution_query, workspace_id, start_time, end_time)
        
        total = sum(d['count'] for d in distribution)
        
        return {
            "queueLatency": {
                "avg": round(result['queue_avg'] or 0, 2),
                "median": round(result['queue_p50'] or 0, 2),
                "p50": round(result['queue_p50'] or 0, 2),
                "p75": round(result['queue_p75'] or 0, 2),
                "p90": round(result['queue_p90'] or 0, 2),
                "p95": round(result['queue_p95'] or 0, 2),
                "p99": round(result['queue_p99'] or 0, 2)
            },
            "executionLatency": {
                "avg": round(result['exec_avg'] or 0, 2),
                "median": round(result['exec_p50'] or 0, 2),
                "p50": round(result['exec_p50'] or 0, 2),
                "p75": round(result['exec_p75'] or 0, 2),
                "p90": round(result['exec_p90'] or 0, 2),
                "p95": round(result['exec_p95'] or 0, 2),
                "p99": round(result['exec_p99'] or 0, 2)
            },
            "endToEndLatency": {
                "avg": round(result['e2e_avg'] or 0, 2),
                "median": round(result['e2e_p50'] or 0, 2),
                "p50": round(result['e2e_p50'] or 0, 2),
                "p75": round(result['e2e_p75'] or 0, 2),
                "p90": round(result['e2e_p90'] or 0, 2),
                "p95": round(result['e2e_p95'] or 0, 2),
                "p99": round(result['e2e_p99'] or 0, 2)
            },
            "latencyDistribution": [
                {
                    "bucket": d['bucket'],
                    "count": d['count'],
                    "percentage": round(d['count'] / total * 100, 2) if total > 0 else 0
                }
                for d in distribution
            ]
        }
```

### Database Schema
```sql
-- Execution metrics table
CREATE TABLE analytics.execution_metrics_minute (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    minute TIMESTAMPTZ NOT NULL,
    
    -- Throughput metrics
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    
    -- Latency metrics (in milliseconds)
    avg_queue_latency INTEGER,
    p50_queue_latency INTEGER,
    p95_queue_latency INTEGER,
    avg_execution_latency INTEGER,
    p50_execution_latency INTEGER,
    p95_execution_latency INTEGER,
    
    -- Queue metrics
    max_queue_depth INTEGER DEFAULT 0,
    avg_queue_depth NUMERIC(10,2),
    
    -- System metrics
    avg_cpu_usage NUMERIC(5,2),
    avg_memory_usage NUMERIC(5,2),
    active_workers INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_execution_minute UNIQUE(workspace_id, minute)
);

-- Indexes
CREATE INDEX idx_execution_metrics_workspace_minute 
    ON analytics.execution_metrics_minute(workspace_id, minute DESC);
```

## Testing Requirements
- Load tests for high throughput scenarios
- Latency measurement accuracy tests
- Queue depth tracking tests
- Real-time update tests
- Performance under stress tests

## Performance Targets
- Real-time metrics update: <100ms
- Throughput calculation: <200ms
- Latency percentiles: <500ms
- Pattern detection: <1 second
- Dashboard load: <2 seconds

## Security Considerations
- Rate limiting on metrics endpoints
- Queue visibility restrictions
- Resource usage data protection
- Execution details privacy