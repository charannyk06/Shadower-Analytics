# Specification: Error Tracking

## Feature Overview
Comprehensive error monitoring, categorization, and analysis system to identify, track, and resolve issues across agent executions and system operations.

## Technical Requirements
- Real-time error detection
- Error categorization and grouping
- Stack trace analysis
- Error impact assessment
- Recovery tracking
- Alert correlation

## Implementation Details

### Data Structure
```typescript
interface ErrorTracking {
  workspaceId: string;
  timeframe: TimeFrame;
  
  // Error Overview
  overview: {
    totalErrors: number;
    uniqueErrors: number;
    affectedUsers: number;
    affectedAgents: number;
    
    // Error Rates
    errorRate: number;
    errorRateChange: number;
    criticalErrorRate: number;
    
    // Impact Metrics
    userImpact: number; // percentage of users affected
    systemImpact: 'low' | 'medium' | 'high' | 'critical';
    estimatedRevenueLoss: number;
    
    // Recovery
    avgRecoveryTime: number; // seconds
    autoRecoveryRate: number;
    manualInterventions: number;
  };
  
  // Error Categories
  categories: {
    byType: Array<{
      type: string;
      category: 'api' | 'timeout' | 'validation' | 'auth' | 'system' | 'unknown';
      count: number;
      percentage: number;
      trend: 'increasing' | 'stable' | 'decreasing';
      severity: 'low' | 'medium' | 'high' | 'critical';
      
      // Sample Errors
      samples: Array<{
        errorId: string;
        message: string;
        stackTrace: string;
        occurredAt: string;
      }>;
    }>;
    
    bySeverity: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
    
    bySource: {
      agent: number;
      api: number;
      database: number;
      integration: number;
      system: number;
    };
  };
  
  // Error Timeline
  timeline: {
    // Temporal Distribution
    errorsByTime: Array<{
      timestamp: string;
      count: number;
      criticalCount: number;
      uniqueErrors: number;
    }>;
    
    // Error Spikes
    spikes: Array<{
      startTime: string;
      endTime: string;
      peakErrors: number;
      totalErrors: number;
      primaryCause: string;
      resolved: boolean;
    }>;
    
    // Pattern Detection
    patterns: Array<{
      pattern: string;
      frequency: number;
      lastOccurrence: string;
      correlation: string; // what it correlates with
    }>;
  };
  
  // Error Details
  errors: Array<{
    errorId: string;
    fingerprint: string; // for grouping similar errors
    
    // Basic Info
    type: string;
    message: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    status: 'new' | 'acknowledged' | 'investigating' | 'resolved' | 'ignored';
    
    // Occurrence Data
    firstSeen: string;
    lastSeen: string;
    occurrences: number;
    affectedUsers: string[];
    affectedAgents: string[];
    
    // Technical Details
    stackTrace: string;
    context: {
      agentId?: string;
      userId?: string;
      workspaceId: string;
      environment: string;
      version: string;
      metadata: Record<string, any>;
    };
    
    // Impact
    impact: {
      usersAffected: number;
      executionsAffected: number;
      creditsLost: number;
      cascadingFailures: number;
    };
    
    // Resolution
    resolution?: {
      resolvedAt: string;
      resolvedBy: string;
      resolution: string;
      rootCause: string;
      preventiveMeasures: string[];
    };
  }>;
  
  // Top Errors
  topErrors: {
    byOccurrence: Array<{
      errorId: string;
      type: string;
      count: number;
      lastSeen: string;
    }>;
    
    byImpact: Array<{
      errorId: string;
      type: string;
      usersAffected: number;
      creditsLost: number;
    }>;
    
    unresolved: Array<{
      errorId: string;
      type: string;
      age: number; // hours since first seen
      priority: number;
    }>;
  };
  
  // Error Correlations
  correlations: {
    // Error to Agent Correlation
    agentCorrelation: Array<{
      agentId: string;
      agentName: string;
      errorTypes: string[];
      errorRate: number;
      commonCause: string;
    }>;
    
    // Error to User Correlation
    userCorrelation: Array<{
      userId: string;
      errorTypes: string[];
      frequency: number;
      possibleCause: string;
    }>;
    
    // Error Chain Analysis
    errorChains: Array<{
      rootError: string;
      cascadingErrors: string[];
      totalImpact: number;
      preventable: boolean;
    }>;
  };
  
  // Recovery Analysis
  recovery: {
    // Recovery Times
    recoveryTimes: {
      automatic: {
        avg: number;
        median: number;
        p95: number;
      };
      manual: {
        avg: number;
        median: number;
        p95: number;
      };
    };
    
    // Recovery Methods
    recoveryMethods: Array<{
      method: string;
      successRate: number;
      avgTime: number;
      usageCount: number;
    }>;
    
    // Failed Recoveries
    failedRecoveries: Array<{
      errorId: string;
      attemptedMethods: string[];
      failureReason: string;
    }>;
  };
}
```

### Frontend Components

#### Error Tracking Dashboard
```typescript
// frontend/src/app/errors/page.tsx
'use client';

import { useState } from 'react';
import { useErrorTracking } from '@/hooks/api/useErrorTracking';
import { ErrorOverview } from '@/components/errors/ErrorOverview';
import { ErrorTimeline } from '@/components/errors/ErrorTimeline';
import { ErrorList } from '@/components/errors/ErrorList';
import { ErrorDetails } from '@/components/errors/ErrorDetails';
import { ErrorCorrelations } from '@/components/errors/ErrorCorrelations';
import { RecoveryAnalysis } from '@/components/errors/RecoveryAnalysis';
import { ErrorAlerts } from '@/components/errors/ErrorAlerts';

export default function ErrorTrackingDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('24h');
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const { workspaceId } = useAuth();
  
  const { data, isLoading, error } = useErrorTracking(
    workspaceId, 
    timeframe, 
    severityFilter
  );
  
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Error Tracking</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and resolve system errors and exceptions
          </p>
        </div>
        
        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />
          <SeverityFilter value={severityFilter} onChange={setSeverityFilter} />
        </div>
        
        {/* Overview Cards */}
        <ErrorOverview overview={data.overview} />
        
        {/* Error Timeline */}
        <ErrorTimeline 
          timeline={data.timeline}
          onSpikeClick={(spike) => analyzeSpikeDetails(spike)}
        />
        
        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Error List */}
          <div className="lg:col-span-2">
            <ErrorList 
              errors={data.errors}
              topErrors={data.topErrors}
              onErrorSelect={setSelectedError}
              selectedError={selectedError}
            />
          </div>
          
          {/* Error Details Panel */}
          <div>
            {selectedError ? (
              <ErrorDetails 
                error={data.errors.find(e => e.errorId === selectedError)}
                onResolve={(errorId) => resolveError(errorId)}
                onIgnore={(errorId) => ignoreError(errorId)}
              />
            ) : (
              <ErrorCorrelations correlations={data.correlations} />
            )}
          </div>
        </div>
        
        {/* Recovery Analysis */}
        <RecoveryAnalysis recovery={data.recovery} />
        
        {/* Active Alerts */}
        <ErrorAlerts workspaceId={workspaceId} />
      </div>
    </div>
  );
}
```

#### Error Details Panel
```typescript
// frontend/src/components/errors/ErrorDetails.tsx
import { useState } from 'react';
import { Disclosure } from '@headlessui/react';
import { ChevronRightIcon } from '@heroicons/react/20/solid';
import { formatDistanceToNow } from 'date-fns';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ErrorDetailsProps {
  error: ErrorData;
  onResolve: (errorId: string) => void;
  onIgnore: (errorId: string) => void;
}

export function ErrorDetails({ error, onResolve, onIgnore }: ErrorDetailsProps) {
  const [isResolving, setIsResolving] = useState(false);
  const [resolution, setResolution] = useState('');
  
  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800'
    };
    return colors[severity] || colors.medium;
  };
  
  const getStatusColor = (status: string) => {
    const colors = {
      new: 'bg-blue-100 text-blue-800',
      acknowledged: 'bg-purple-100 text-purple-800',
      investigating: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      ignored: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || colors.new;
  };
  
  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Error Details
          </h3>
          <div className="flex gap-2">
            <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(error.severity)}`}>
              {error.severity.toUpperCase()}
            </span>
            <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(error.status)}`}>
              {error.status.toUpperCase()}
            </span>
          </div>
        </div>
        
        <p className="text-sm font-mono text-gray-700 mb-2">
          {error.type}
        </p>
        
        <p className="text-sm text-gray-600">
          {error.message}
        </p>
        
        {/* Occurrence Info */}
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">First seen:</span>
            <span className="ml-2 text-gray-900">
              {formatDistanceToNow(new Date(error.firstSeen))} ago
            </span>
          </div>
          <div>
            <span className="text-gray-500">Last seen:</span>
            <span className="ml-2 text-gray-900">
              {formatDistanceToNow(new Date(error.lastSeen))} ago
            </span>
          </div>
          <div>
            <span className="text-gray-500">Occurrences:</span>
            <span className="ml-2 text-gray-900 font-medium">
              {error.occurrences.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Users affected:</span>
            <span className="ml-2 text-gray-900 font-medium">
              {error.affectedUsers.length}
            </span>
          </div>
        </div>
      </div>
      
      {/* Stack Trace */}
      <Disclosure>
        {({ open }) => (
          <>
            <Disclosure.Button className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50">
              <span className="text-sm font-medium text-gray-900">
                Stack Trace
              </span>
              <ChevronRightIcon 
                className={`h-5 w-5 text-gray-400 transition-transform ${
                  open ? 'rotate-90' : ''
                }`} 
              />
            </Disclosure.Button>
            <Disclosure.Panel className="px-6 pb-4">
              <div className="rounded-lg bg-gray-900 p-4 overflow-x-auto">
                <SyntaxHighlighter
                  language="javascript"
                  style={tomorrow}
                  customStyle={{ 
                    margin: 0, 
                    background: 'transparent',
                    fontSize: '12px'
                  }}
                >
                  {error.stackTrace}
                </SyntaxHighlighter>
              </div>
            </Disclosure.Panel>
          </>
        )}
      </Disclosure>
      
      {/* Context */}
      <Disclosure>
        {({ open }) => (
          <>
            <Disclosure.Button className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 border-t">
              <span className="text-sm font-medium text-gray-900">
                Context & Metadata
              </span>
              <ChevronRightIcon 
                className={`h-5 w-5 text-gray-400 transition-transform ${
                  open ? 'rotate-90' : ''
                }`} 
              />
            </Disclosure.Button>
            <Disclosure.Panel className="px-6 pb-4">
              <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                {JSON.stringify(error.context, null, 2)}
              </pre>
            </Disclosure.Panel>
          </>
        )}
      </Disclosure>
      
      {/* Impact */}
      <div className="px-6 py-4 border-t">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Impact Analysis</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Affected Executions:</span>
            <span className="text-gray-900">{error.impact.executionsAffected}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Credits Lost:</span>
            <span className="text-gray-900">{error.impact.creditsLost}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Cascading Failures:</span>
            <span className="text-gray-900">{error.impact.cascadingFailures}</span>
          </div>
        </div>
      </div>
      
      {/* Actions */}
      {error.status !== 'resolved' && (
        <div className="px-6 py-4 border-t">
          {!isResolving ? (
            <div className="flex gap-2">
              <button
                onClick={() => setIsResolving(true)}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Mark as Resolved
              </button>
              <button
                onClick={() => onIgnore(error.errorId)}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Ignore
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="Describe the resolution..."
                className="w-full px-3 py-2 border rounded-lg resize-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onResolve(error.errorId);
                    setIsResolving(false);
                  }}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Confirm Resolution
                </button>
                <button
                  onClick={() => setIsResolving(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### Backend Implementation

#### Error Tracking Service
```python
# backend/src/services/analytics/error_tracking.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import re

class ErrorTrackingService:
    def __init__(self, db, cache_service, alert_service):
        self.db = db
        self.cache = cache_service
        self.alerts = alert_service
    
    async def track_error(
        self,
        error_data: Dict[str, Any]
    ) -> str:
        """Track a new error occurrence"""
        
        # Generate error fingerprint for grouping
        fingerprint = self._generate_fingerprint(error_data)
        
        # Check if error already exists
        existing = await self._get_error_by_fingerprint(fingerprint)
        
        if existing:
            # Update existing error
            await self._update_error_occurrence(existing['error_id'], error_data)
            error_id = existing['error_id']
        else:
            # Create new error entry
            error_id = await self._create_new_error(fingerprint, error_data)
        
        # Check for alert conditions
        await self._check_error_alerts(error_id, error_data)
        
        # Update real-time metrics
        await self._update_error_metrics(error_data['workspace_id'])
        
        return error_id
    
    async def get_error_tracking(
        self,
        workspace_id: str,
        timeframe: str,
        severity_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive error tracking data"""
        
        end_time = datetime.utcnow()
        start_time = self._calculate_start_time(timeframe)
        
        # Build filter conditions
        filters = {
            'workspace_id': workspace_id,
            'start_time': start_time,
            'end_time': end_time
        }
        
        if severity_filter and severity_filter != 'all':
            filters['severity'] = severity_filter
        
        # Parallel fetch all data
        results = await asyncio.gather(
            self._get_error_overview(filters),
            self._get_error_categories(filters),
            self._get_error_timeline(filters),
            self._get_error_list(filters),
            self._get_top_errors(filters),
            self._get_error_correlations(filters),
            self._get_recovery_analysis(filters)
        )
        
        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "overview": results[0],
            "categories": results[1],
            "timeline": results[2],
            "errors": results[3],
            "topErrors": results[4],
            "correlations": results[5],
            "recovery": results[6]
        }
    
    def _generate_fingerprint(
        self,
        error_data: Dict[str, Any]
    ) -> str:
        """Generate unique fingerprint for error grouping"""
        
        # Extract key components for fingerprinting
        error_type = error_data.get('type', '')
        
        # Normalize stack trace (remove line numbers and specific values)
        stack_trace = error_data.get('stack_trace', '')
        normalized_stack = re.sub(r':\d+:\d+', '', stack_trace)
        normalized_stack = re.sub(r'"[^"]*"', '""', normalized_stack)
        normalized_stack = re.sub(r'\d+', 'N', normalized_stack)
        
        # Create fingerprint
        fingerprint_data = f"{error_type}:{normalized_stack[:500]}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    async def _check_error_alerts(
        self,
        error_id: str,
        error_data: Dict[str, Any]
    ):
        """Check if error triggers any alerts"""
        
        # Check error rate threshold
        error_rate = await self._calculate_error_rate(error_data['workspace_id'])
        
        if error_rate > 5.0:  # 5% error rate threshold
            await self.alerts.trigger_alert({
                'type': 'high_error_rate',
                'workspace_id': error_data['workspace_id'],
                'error_id': error_id,
                'error_rate': error_rate,
                'severity': 'high'
            })
        
        # Check for error spike
        recent_errors = await self._count_recent_errors(
            error_data['workspace_id'],
            minutes=5
        )
        
        baseline = await self._get_error_baseline(error_data['workspace_id'])
        
        if recent_errors > baseline * 3:  # 3x baseline indicates spike
            await self.alerts.trigger_alert({
                'type': 'error_spike',
                'workspace_id': error_data['workspace_id'],
                'error_count': recent_errors,
                'baseline': baseline,
                'severity': 'high'
            })
    
    async def resolve_error(
        self,
        error_id: str,
        resolution_data: Dict[str, Any]
    ):
        """Mark an error as resolved"""
        
        query = """
            UPDATE analytics.errors
            SET 
                status = 'resolved',
                resolved_at = NOW(),
                resolved_by = $2,
                resolution = $3,
                root_cause = $4,
                preventive_measures = $5,
                updated_at = NOW()
            WHERE error_id = $1
        """
        
        await self.db.execute(
            query,
            error_id,
            resolution_data['resolved_by'],
            resolution_data['resolution'],
            resolution_data.get('root_cause'),
            resolution_data.get('preventive_measures', [])
        )
        
        # Clear related alerts
        await self.alerts.clear_error_alerts(error_id)
```

### Database Schema
```sql
-- Errors table
CREATE TABLE analytics.errors (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint VARCHAR(32) NOT NULL,
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Error details
    error_type VARCHAR(100) NOT NULL,
    message TEXT,
    severity VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'new',
    
    -- Occurrence tracking
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,
    
    -- Technical details
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    
    -- Impact
    users_affected TEXT[] DEFAULT '{}',
    agents_affected TEXT[] DEFAULT '{}',
    executions_affected INTEGER DEFAULT 0,
    credits_lost NUMERIC(10,2) DEFAULT 0,
    
    -- Resolution
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES public.users(id),
    resolution TEXT,
    root_cause TEXT,
    preventive_measures TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_error_fingerprint UNIQUE(fingerprint, workspace_id)
);

-- Indexes
CREATE INDEX idx_errors_workspace_status 
    ON analytics.errors(workspace_id, status);

CREATE INDEX idx_errors_severity_last_seen 
    ON analytics.errors(severity, last_seen DESC);

CREATE INDEX idx_errors_fingerprint 
    ON analytics.errors(fingerprint);

-- Error occurrences table (for detailed tracking)
CREATE TABLE analytics.error_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id UUID REFERENCES analytics.errors(error_id),
    
    -- Occurrence details
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID REFERENCES public.users(id),
    agent_id UUID REFERENCES public.agents(id),
    run_id UUID,
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_error_occurrences_error 
    ON analytics.error_occurrences(error_id, occurred_at DESC);
```

## Testing Requirements
- Error fingerprinting accuracy tests
- Alert triggering tests
- Error grouping tests
- Recovery tracking tests
- Performance tests for large error volumes

## Performance Targets
- Error tracking: <100ms
- Error list query: <500ms
- Timeline generation: <1 second
- Correlation analysis: <2 seconds
- Alert detection: <500ms

## Security Considerations
- Sanitize error messages for PII
- Limit stack trace exposure
- Access control for error resolution
- Audit logging for error actions