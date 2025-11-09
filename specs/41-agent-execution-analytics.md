# Specification: Agent Execution Analytics

## Overview
Comprehensive analytics for agent executions including performance metrics, execution patterns, failure analysis, and optimization recommendations.

## Technical Requirements

### Execution Metrics Tracking

#### Execution Data Model
```sql
-- Agent execution metrics table
CREATE TABLE analytics.agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Execution details
    trigger_type VARCHAR(50), -- 'manual', 'scheduled', 'webhook', 'api'
    trigger_source JSONB,
    input_data JSONB,
    output_data JSONB,
    
    -- Performance metrics
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    status VARCHAR(20), -- 'pending', 'running', 'success', 'failed', 'timeout'
    error_message TEXT,
    error_type VARCHAR(100),
    
    -- Resource usage
    credits_consumed INTEGER DEFAULT 0,
    tokens_used JSONB, -- {prompt: 1000, completion: 500}
    api_calls_count INTEGER DEFAULT 0,
    memory_usage_mb DECIMAL,
    
    -- Execution path
    steps_total INTEGER,
    steps_completed INTEGER,
    execution_graph JSONB,
    checkpoints JSONB[],
    
    -- Context
    environment VARCHAR(20), -- 'production', 'development', 'staging'
    runtime_mode VARCHAR(20), -- 'default', 'fast'
    version VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_executions_agent (agent_id, start_time DESC),
    INDEX idx_executions_workspace (workspace_id, start_time DESC),
    INDEX idx_executions_status (status, workspace_id),
    INDEX idx_executions_duration (duration_ms)
);

-- Execution steps detail
CREATE TABLE analytics.execution_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) REFERENCES agent_executions(execution_id),
    step_index INTEGER NOT NULL,
    step_name VARCHAR(255),
    step_type VARCHAR(50), -- 'action', 'decision', 'loop', 'api_call'
    
    -- Step metrics
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    status VARCHAR(20),
    
    -- Step data
    input JSONB,
    output JSONB,
    error JSONB,
    
    -- Resource usage
    tokens_used INTEGER,
    api_calls JSONB[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_steps_execution (execution_id, step_index),
    INDEX idx_steps_duration (duration_ms)
);
```

### Real-time Execution Monitoring

#### Execution Stream Service
```python
# backend/services/execution_analytics.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

@dataclass
class ExecutionMetrics:
    execution_id: str
    agent_id: str
    status: str
    duration_ms: int
    credits_consumed: int
    success_rate: float
    error_rate: float
    avg_step_duration: float

class ExecutionAnalyticsService:
    def __init__(self):
        self.active_executions: Dict[str, ExecutionMetrics] = {}
        self.execution_history: List[ExecutionMetrics] = []
        
    async def track_execution_start(
        self,
        execution_id: str,
        agent_id: str,
        workspace_id: str,
        trigger_type: str,
        input_data: dict
    ):
        """Track execution start"""
        await self.db.insert(
            "agent_executions",
            {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "trigger_type": trigger_type,
                "input_data": input_data,
                "start_time": datetime.utcnow(),
                "status": "running"
            }
        )
        
        # Update real-time metrics
        await self.redis.hincrby(f"agent:{agent_id}:metrics", "running_count", 1)
        
        # Publish event
        await self.publish_event(
            "execution.started",
            {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "workspace_id": workspace_id
            }
        )
    
    async def track_step_completion(
        self,
        execution_id: str,
        step_index: int,
        step_name: str,
        duration_ms: int,
        status: str,
        output: Optional[dict] = None
    ):
        """Track individual step completion"""
        await self.db.insert(
            "execution_steps",
            {
                "execution_id": execution_id,
                "step_index": step_index,
                "step_name": step_name,
                "duration_ms": duration_ms,
                "status": status,
                "output": output,
                "end_time": datetime.utcnow()
            }
        )
        
        # Update execution progress
        await self.db.execute(
            """
            UPDATE agent_executions 
            SET steps_completed = steps_completed + 1,
                updated_at = NOW()
            WHERE execution_id = %s
            """,
            [execution_id]
        )
    
    async def track_execution_complete(
        self,
        execution_id: str,
        status: str,
        output_data: Optional[dict] = None,
        error: Optional[str] = None
    ):
        """Track execution completion"""
        end_time = datetime.utcnow()
        
        # Get execution start time
        execution = await self.db.fetch_one(
            "SELECT start_time FROM agent_executions WHERE execution_id = %s",
            [execution_id]
        )
        
        duration_ms = int((end_time - execution['start_time']).total_seconds() * 1000)
        
        # Update execution record
        await self.db.execute(
            """
            UPDATE agent_executions
            SET status = %s,
                end_time = %s,
                duration_ms = %s,
                output_data = %s,
                error_message = %s,
                updated_at = NOW()
            WHERE execution_id = %s
            """,
            [status, end_time, duration_ms, output_data, error, execution_id]
        )
        
        # Update agent metrics
        await self.update_agent_metrics(execution_id, status, duration_ms)
    
    async def get_execution_analytics(
        self,
        agent_id: str,
        time_range: timedelta = timedelta(days=7)
    ) -> Dict:
        """Get comprehensive execution analytics"""
        start_date = datetime.utcnow() - time_range
        
        # Get execution statistics
        stats = await self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                AVG(duration_ms) as avg_duration,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as median_duration,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration,
                SUM(credits_consumed) as total_credits,
                AVG(credits_consumed) as avg_credits
            FROM agent_executions
            WHERE agent_id = %s AND start_time >= %s
            """,
            [agent_id, start_date]
        )
        
        # Get execution patterns
        patterns = await self.db.fetch_all(
            """
            SELECT 
                DATE_TRUNC('hour', start_time) as hour,
                COUNT(*) as execution_count,
                AVG(duration_ms) as avg_duration
            FROM agent_executions
            WHERE agent_id = %s AND start_time >= %s
            GROUP BY hour
            ORDER BY hour
            """,
            [agent_id, start_date]
        )
        
        # Get failure analysis
        failures = await self.db.fetch_all(
            """
            SELECT 
                error_type,
                COUNT(*) as count,
                AVG(duration_ms) as avg_duration_before_failure
            FROM agent_executions
            WHERE agent_id = %s 
                AND status = 'failed' 
                AND start_time >= %s
            GROUP BY error_type
            ORDER BY count DESC
            """,
            [agent_id, start_date]
        )
        
        return {
            "statistics": stats,
            "execution_patterns": patterns,
            "failure_analysis": failures,
            "success_rate": (stats['successful'] / stats['total_executions']) * 100 if stats['total_executions'] > 0 else 0
        }
```

### Frontend Components

#### Agent Execution Dashboard
```typescript
// frontend/components/analytics/AgentExecutionDashboard.tsx
interface AgentExecutionDashboardProps {
    agentId: string;
    timeRange: DateRange;
}

export function AgentExecutionDashboard({
    agentId,
    timeRange
}: AgentExecutionDashboardProps) {
    const { data: executionData } = useAgentExecutions(agentId, timeRange);
    const { data: liveExecutions } = useLiveExecutions(agentId);
    
    return (
        <div className="execution-dashboard">
            {/* Real-time execution monitor */}
            <LiveExecutionMonitor 
                executions={liveExecutions}
                onExecutionClick={(id) => navigateToExecution(id)}
            />
            
            {/* Key metrics cards */}
            <div className="metrics-grid">
                <MetricCard
                    title="Total Executions"
                    value={executionData?.total}
                    change={executionData?.change}
                    icon={<PlayIcon />}
                />
                <MetricCard
                    title="Success Rate"
                    value={`${executionData?.successRate}%`}
                    change={executionData?.successChange}
                    icon={<CheckCircleIcon />}
                />
                <MetricCard
                    title="Avg Duration"
                    value={formatDuration(executionData?.avgDuration)}
                    change={executionData?.durationChange}
                    icon={<ClockIcon />}
                />
                <MetricCard
                    title="Credits Used"
                    value={executionData?.creditsUsed}
                    change={executionData?.creditsChange}
                    icon={<CreditCardIcon />}
                />
            </div>
            
            {/* Execution timeline */}
            <ExecutionTimeline
                executions={executionData?.recent}
                onExecutionSelect={handleExecutionSelect}
            />
            
            {/* Performance charts */}
            <div className="charts-grid">
                <ExecutionTrendChart data={executionData?.trends} />
                <DurationDistribution data={executionData?.durations} />
                <FailureAnalysis data={executionData?.failures} />
                <ResourceUsageChart data={executionData?.resources} />
            </div>
            
            {/* Execution details table */}
            <ExecutionTable
                executions={executionData?.executions}
                onSort={handleSort}
                onFilter={handleFilter}
            />
        </div>
    );
}

// Live execution monitor component
interface LiveExecutionMonitorProps {
    executions: LiveExecution[];
    onExecutionClick: (id: string) => void;
}

function LiveExecutionMonitor({ 
    executions, 
    onExecutionClick 
}: LiveExecutionMonitorProps) {
    return (
        <div className="live-monitor">
            <h3>Active Executions</h3>
            <div className="execution-list">
                {executions.map(exec => (
                    <LiveExecutionCard
                        key={exec.id}
                        execution={exec}
                        onClick={() => onExecutionClick(exec.id)}
                    />
                ))}
            </div>
        </div>
    );
}

// Execution timeline visualization
function ExecutionTimeline({ executions, onExecutionSelect }) {
    return (
        <div className="timeline-container">
            <Timeline>
                {executions.map(exec => (
                    <TimelineItem
                        key={exec.id}
                        time={exec.startTime}
                        status={exec.status}
                        onClick={() => onExecutionSelect(exec)}
                    >
                        <div className="timeline-content">
                            <span className="execution-name">{exec.name}</span>
                            <span className="duration">{formatDuration(exec.duration)}</span>
                            <ExecutionStatusBadge status={exec.status} />
                        </div>
                    </TimelineItem>
                ))}
            </Timeline>
        </div>
    );
}
```

### Execution Pattern Analysis

```python
# backend/services/execution_patterns.py
class ExecutionPatternAnalyzer:
    async def analyze_patterns(
        self,
        agent_id: str,
        workspace_id: str
    ) -> Dict:
        """Analyze execution patterns for optimization"""
        
        # Time-based patterns
        hourly_patterns = await self.db.fetch_all(
            """
            SELECT 
                EXTRACT(HOUR FROM start_time) as hour,
                COUNT(*) as execution_count,
                AVG(duration_ms) as avg_duration,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_rate
            FROM agent_executions
            WHERE agent_id = %s
            GROUP BY hour
            ORDER BY hour
            """,
            [agent_id]
        )
        
        # Input pattern analysis
        input_patterns = await self.db.fetch_all(
            """
            SELECT 
                jsonb_object_keys(input_data) as input_key,
                COUNT(*) as usage_count,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_rate
            FROM agent_executions
            WHERE agent_id = %s
            GROUP BY input_key
            ORDER BY usage_count DESC
            """,
            [agent_id]
        )
        
        # Execution path analysis
        path_analysis = await self.db.fetch_all(
            """
            SELECT 
                execution_graph->>'path' as execution_path,
                COUNT(*) as frequency,
                AVG(duration_ms) as avg_duration,
                AVG(credits_consumed) as avg_credits
            FROM agent_executions
            WHERE agent_id = %s AND execution_graph IS NOT NULL
            GROUP BY execution_path
            ORDER BY frequency DESC
            LIMIT 10
            """,
            [agent_id]
        )
        
        # Bottleneck detection
        bottlenecks = await self.db.fetch_all(
            """
            SELECT 
                s.step_name,
                AVG(s.duration_ms) as avg_duration,
                COUNT(*) as execution_count,
                STDDEV(s.duration_ms) as duration_variance
            FROM execution_steps s
            JOIN agent_executions e ON s.execution_id = e.execution_id
            WHERE e.agent_id = %s
            GROUP BY s.step_name
            HAVING AVG(s.duration_ms) > 1000
            ORDER BY avg_duration DESC
            """,
            [agent_id]
        )
        
        return {
            "hourly_patterns": hourly_patterns,
            "input_patterns": input_patterns,
            "execution_paths": path_analysis,
            "bottlenecks": bottlenecks,
            "optimization_suggestions": self.generate_suggestions(
                hourly_patterns,
                bottlenecks
            )
        }
    
    def generate_suggestions(
        self,
        patterns: List[Dict],
        bottlenecks: List[Dict]
    ) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        # Check for peak hour optimization
        peak_hours = [p for p in patterns if p['execution_count'] > 100]
        if peak_hours:
            suggestions.append(
                f"Consider scaling during peak hours: {', '.join(str(h['hour']) for h in peak_hours)}"
            )
        
        # Check for bottlenecks
        if bottlenecks:
            worst_bottleneck = bottlenecks[0]
            suggestions.append(
                f"Optimize step '{worst_bottleneck['step_name']}' - "
                f"averaging {worst_bottleneck['avg_duration']}ms"
            )
        
        return suggestions
```

## Implementation Priority
1. Execution tracking infrastructure
2. Real-time monitoring dashboard
3. Pattern analysis engine
4. Performance optimization
5. Failure analysis and recovery

## Success Metrics
- Execution tracking accuracy: 100%
- Real-time latency < 100ms
- Pattern detection accuracy > 95%
- Dashboard load time < 2s