# User Workflow Usage Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track how users actually use workflows. What they run, how often, what works, what fails. Simple workflow usage analytics without complex tracing.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Workflow usage by user
interface UserWorkflowUsage {
  userId: string;
  workflowId: string;
  workflowName: string;
  executions: WorkflowExecution[];
  stats: UsageStats;
  patterns: UsagePattern[];
}

interface WorkflowExecution {
  id: string;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  status: 'started' | 'completed' | 'failed' | 'cancelled';
  trigger: 'manual' | 'scheduled' | 'api' | 'chained';
  inputSize?: number;
  outputSize?: number;
  cost?: number;
}

interface UsageStats {
  totalExecutions: number;
  successCount: number;
  failureCount: number;
  successRate: number;
  avgDuration: number;
  lastUsed: Date;
  frequency: 'daily' | 'weekly' | 'monthly' | 'rare';
}

interface UsagePattern {
  type: 'time_based' | 'sequence' | 'conditional';
  description: string;
  confidence: number;
}

// Workflow favorites
interface WorkflowFavorite {
  userId: string;
  workflowId: string;
  addedAt: Date;
  usageCount: number;
  lastUsed: Date;
  customName?: string;
  category?: string;
}
```

#### 1.2 SQL Schema

```sql
-- Simple workflow usage tracking
CREATE TABLE user_workflow_usage (
    user_id UUID NOT NULL,
    workflow_id UUID NOT NULL,
    workflow_name VARCHAR(255),
    execution_date DATE NOT NULL,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, workflow_id, execution_date)
);

-- Individual executions (keep minimal)
CREATE TABLE workflow_executions_simple (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    workflow_id UUID NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(20),
    trigger_type VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- User favorites
CREATE TABLE workflow_favorites (
    user_id UUID NOT NULL,
    workflow_id UUID NOT NULL,
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    custom_name VARCHAR(255),
    category VARCHAR(100),
    PRIMARY KEY (user_id, workflow_id)
);

-- Workflow sequences (what users run together)
CREATE TABLE workflow_sequences (
    user_id UUID NOT NULL,
    sequence_id UUID NOT NULL,
    workflow_ids UUID[],
    execution_order INTEGER[],
    frequency INTEGER DEFAULT 1,
    last_executed TIMESTAMPTZ,
    PRIMARY KEY (user_id, sequence_id)
);

-- Simple indexes
CREATE INDEX idx_usage_user ON user_workflow_usage(user_id);
CREATE INDEX idx_usage_date ON user_workflow_usage(execution_date DESC);
CREATE INDEX idx_executions_user ON workflow_executions_simple(user_id, start_time DESC);
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict

@dataclass
class WorkflowUsageAnalyzer:
    """Simple workflow usage analysis"""
    
    def get_user_workflows(self, user_id: str) -> List[Dict]:
        """What workflows does this user run?"""
        return self.db.query(
            """
            SELECT 
                workflow_id,
                workflow_name,
                SUM(execution_count) as total_runs,
                SUM(success_count) as successes,
                AVG(CASE WHEN execution_count > 0 
                    THEN total_duration_seconds / execution_count 
                    ELSE 0 END) as avg_duration,
                MAX(execution_date) as last_used
            FROM user_workflow_usage
            WHERE user_id = ?
            GROUP BY workflow_id, workflow_name
            ORDER BY total_runs DESC
            """,
            (user_id,)
        )
    
    def get_popular_workflows(self) -> List[Dict]:
        """Most used workflows across all users"""
        return self.db.query(
            """
            SELECT 
                workflow_id,
                workflow_name,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(execution_count) as total_executions,
                AVG(success_count::FLOAT / NULLIF(execution_count, 0)) as avg_success_rate
            FROM user_workflow_usage
            WHERE execution_date > CURRENT_DATE - INTERVAL '7 days'
            GROUP BY workflow_id, workflow_name
            ORDER BY total_executions DESC
            LIMIT 10
            """
        )
    
    def find_workflow_sequences(self, user_id: str) -> List[Dict]:
        """What workflows does user run together?"""
        # Get recent executions
        executions = self.db.query(
            """
            SELECT workflow_id, start_time
            FROM workflow_executions_simple
            WHERE user_id = ? AND start_time > NOW() - INTERVAL '7 days'
            ORDER BY start_time
            """,
            (user_id,)
        )
        
        # Find sequences (workflows run within 5 minutes)
        sequences = []
        current_sequence = []
        last_time = None
        
        for exec in executions:
            if last_time and (exec['start_time'] - last_time).seconds > 300:
                if len(current_sequence) > 1:
                    sequences.append(current_sequence)
                current_sequence = []
            
            current_sequence.append(exec['workflow_id'])
            last_time = exec['start_time']
        
        if len(current_sequence) > 1:
            sequences.append(current_sequence)
        
        # Count sequence frequencies
        sequence_counts = Counter(tuple(seq) for seq in sequences)
        
        return [
            {'sequence': list(seq), 'count': count}
            for seq, count in sequence_counts.most_common(5)
        ]
    
    def get_workflow_success_rate(self, workflow_id: str) -> Dict:
        """How reliable is this workflow?"""
        stats = self.db.query_one(
            """
            SELECT 
                SUM(execution_count) as total,
                SUM(success_count) as successes,
                SUM(failure_count) as failures,
                COUNT(DISTINCT user_id) as unique_users
            FROM user_workflow_usage
            WHERE workflow_id = ? AND execution_date > CURRENT_DATE - INTERVAL '30 days'
            """,
            (workflow_id,)
        )
        
        if not stats or stats['total'] == 0:
            return {'success_rate': 0, 'sample_size': 0}
        
        return {
            'success_rate': stats['successes'] / stats['total'],
            'failure_rate': stats['failures'] / stats['total'],
            'total_executions': stats['total'],
            'unique_users': stats['unique_users']
        }
    
    def identify_abandoned_workflows(self) -> List[Dict]:
        """Workflows that users tried but stopped using"""
        return self.db.query(
            """
            SELECT 
                workflow_id,
                workflow_name,
                COUNT(DISTINCT user_id) as users_who_abandoned,
                AVG(execution_count) as avg_tries_before_abandon
            FROM user_workflow_usage
            WHERE execution_date < CURRENT_DATE - INTERVAL '30 days'
            AND workflow_id NOT IN (
                SELECT DISTINCT workflow_id 
                FROM user_workflow_usage 
                WHERE execution_date > CURRENT_DATE - INTERVAL '7 days'
            )
            GROUP BY workflow_id, workflow_name
            HAVING COUNT(DISTINCT user_id) > 5
            """
        )
```

### 2. API Endpoints

```python
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/workflow-usage")

@router.post("/track")
async def track_workflow_execution(
    user_id: str,
    workflow_id: str,
    status: str,
    duration: Optional[int] = None
):
    """Track a workflow execution"""
    pass

@router.get("/user/{user_id}")
async def get_user_workflows(user_id: str):
    """Get workflows used by user"""
    pass

@router.get("/user/{user_id}/favorites")
async def get_user_favorites(user_id: str):
    """Get user's favorite workflows"""
    pass

@router.post("/user/{user_id}/favorites")
async def add_to_favorites(
    user_id: str,
    workflow_id: str
):
    """Add workflow to favorites"""
    pass

@router.get("/popular")
async def get_popular_workflows():
    """Most popular workflows"""
    pass

@router.get("/sequences/{user_id}")
async def get_workflow_sequences(user_id: str):
    """Common workflow sequences for user"""
    pass

@router.get("/abandoned")
async def get_abandoned_workflows():
    """Workflows users stopped using"""
    pass

@router.get("/success-rate/{workflow_id}")
async def get_workflow_success_rate(workflow_id: str):
    """Get workflow reliability"""
    pass
```

### 3. Dashboard Components

```typescript
export const WorkflowUsageTracker: React.FC = () => {
  // Auto-track workflow executions
  const trackExecution = (workflowId: string, status: string) => {
    api.post('/workflow-usage/track', {
      userId: getCurrentUser().id,
      workflowId,
      status,
      duration: Date.now() - startTime
    });
  };
  
  return null;
};

export const MyWorkflows: React.FC = () => {
  const [workflows, setWorkflows] = useState([]);
  const [favorites, setFavorites] = useState([]);
  
  return (
    <div className="space-y-4">
      {/* Favorite workflows */}
      <div>
        <h3 className="font-bold mb-2">Favorites</h3>
        <div className="grid grid-cols-3 gap-2">
          {favorites.map(wf => (
            <button
              key={wf.workflowId}
              className="p-2 border rounded hover:bg-gray-50"
              onClick={() => runWorkflow(wf.workflowId)}
            >
              <div className="font-medium">{wf.customName || wf.workflowName}</div>
              <div className="text-xs text-gray-500">Used {wf.usageCount} times</div>
            </button>
          ))}
        </div>
      </div>
      
      {/* Recent workflows */}
      <div>
        <h3 className="font-bold mb-2">Recent</h3>
        <div className="space-y-1">
          {workflows.slice(0, 5).map(wf => (
            <div key={wf.workflowId} className="flex justify-between p-2 hover:bg-gray-50">
              <span>{wf.workflowName}</span>
              <span className="text-sm text-gray-500">
                {wf.successRate}% success
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const WorkflowSuccessIndicator: React.FC<{ workflowId: string }> = ({ workflowId }) => {
  const [stats, setStats] = useState(null);
  
  if (!stats) return null;
  
  const color = stats.successRate > 90 ? 'green' : 
                stats.successRate > 70 ? 'yellow' : 'red';
  
  return (
    <div className={`inline-flex items-center text-${color}-600`}>
      <div className="w-2 h-2 rounded-full bg-current mr-1" />
      <span className="text-sm">{stats.successRate}% reliable</span>
    </div>
  );
};

export const WorkflowSequenceDetector: React.FC = () => {
  const [sequences, setSequences] = useState([]);
  
  return (
    <div className="bg-blue-50 p-3 rounded">
      <h4 className="font-medium mb-2">Detected Patterns</h4>
      {sequences.map((seq, i) => (
        <div key={i} className="text-sm mb-1">
          <span className="text-gray-600">You often run:</span>
          {seq.sequence.map(wf => wf.name).join(' → ')}
          <button className="ml-2 text-blue-600 text-xs">
            Save as template
          </button>
        </div>
      ))}
    </div>
  );
};
```

### 4. Usage Insights

```typescript
// Simple usage insights generator
export const generateUsageInsights = (usage: UserWorkflowUsage[]) => {
  const insights = [];
  
  // Most used workflow
  const mostUsed = usage.sort((a, b) => b.stats.totalExecutions - a.stats.totalExecutions)[0];
  if (mostUsed) {
    insights.push({
      type: 'most_used',
      message: `You use "${mostUsed.workflowName}" the most (${mostUsed.stats.totalExecutions} times)`,
      action: 'Add to favorites'
    });
  }
  
  // Low success rate workflows
  const struggling = usage.filter(u => u.stats.successRate < 50 && u.stats.totalExecutions > 5);
  if (struggling.length > 0) {
    insights.push({
      type: 'struggling',
      message: `"${struggling[0].workflowName}" fails often. Need help?`,
      action: 'View troubleshooting'
    });
  }
  
  // Unused workflows
  const unused = usage.filter(u => 
    new Date().getTime() - new Date(u.stats.lastUsed).getTime() > 30 * 24 * 60 * 60 * 1000
  );
  if (unused.length > 0) {
    insights.push({
      type: 'unused',
      message: `You haven't used ${unused.length} workflows in 30+ days`,
      action: 'Clean up'
    });
  }
  
  return insights;
};
```

## Implementation Priority

### Phase 1 (Day 1)
- Track workflow executions
- Store basic usage data
- Success/failure counts

### Phase 2 (Days 2-3)
- User favorites
- Popular workflows
- Success rates

### Phase 3 (Days 4-5)
- Sequence detection
- Abandoned workflows
- Usage insights

## Cost Optimization

- Daily aggregation of usage stats
- Keep individual executions for 7 days only
- Store only workflow ID, not full details
- Batch updates to usage counters
- No real-time streaming

## What This Tells Us

- Which workflows are actually valuable
- What users do repeatedly (automate these!)
- Which workflows fail often (fix these!)
- User workflow preferences
- Common workflow combinations

## What We DON'T Need

- Full execution traces
- Detailed step-by-step logs
- Input/output data storage
- Complex dependency graphs
- Real-time execution monitoring