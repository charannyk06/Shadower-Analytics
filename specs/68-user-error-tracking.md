# User Error Tracking Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track what goes wrong for users. Every error is a chance to improve. Simple error capture that helps fix real problems without complex error monitoring services.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// User-facing errors
interface UserError {
  id: string;
  userId: string;
  sessionId: string;
  timestamp: Date;
  error: ErrorDetails;
  context: ErrorContext;
  impact: ErrorImpact;
  recovery?: ErrorRecovery;
}

interface ErrorDetails {
  type: 'validation' | 'permission' | 'timeout' | 'network' | 'workflow' | 'unknown';
  code: string;
  message: string;
  userMessage?: string; // What the user actually saw
  technical?: string; // Technical details
}

interface ErrorContext {
  page: string;
  action: string;
  workflowId?: string;
  agentId?: string;
  inputData?: Record<string, any>;
  previousErrors?: string[]; // Recent error chain
}

interface ErrorImpact {
  severity: 'low' | 'medium' | 'high' | 'critical';
  userBlocked: boolean;
  workflowFailed: boolean;
  dataLoss: boolean;
}

interface ErrorRecovery {
  attempted: boolean;
  successful: boolean;
  method: string;
  userAction?: string; // What the user did to recover
}

// Error patterns
interface ErrorPattern {
  pattern: string;
  frequency: number;
  affectedUsers: number;
  commonContext: Record<string, any>;
  firstSeen: Date;
  lastSeen: Date;
}
```

#### 1.2 SQL Schema

```sql
-- Simple error tracking
CREATE TABLE user_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_id UUID,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_type VARCHAR(50) NOT NULL,
    error_code VARCHAR(100),
    error_message TEXT,
    page VARCHAR(255),
    action VARCHAR(255),
    severity VARCHAR(20),
    user_blocked BOOLEAN DEFAULT FALSE,
    workflow_id UUID,
    agent_id UUID,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Common error patterns
CREATE TABLE error_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_hash VARCHAR(64) NOT NULL UNIQUE,
    error_type VARCHAR(50),
    error_message_pattern TEXT,
    occurrence_count INTEGER DEFAULT 1,
    affected_users INTEGER DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    common_page VARCHAR(255),
    common_action VARCHAR(255)
);

-- User error summaries (daily)
CREATE TABLE daily_error_stats (
    date DATE NOT NULL,
    user_id UUID NOT NULL,
    error_count INTEGER DEFAULT 0,
    unique_errors INTEGER DEFAULT 0,
    blocked_count INTEGER DEFAULT 0,
    recovery_rate DECIMAL(5,2),
    PRIMARY KEY (date, user_id)
);

-- Minimal indexes
CREATE INDEX idx_errors_user ON user_errors(user_id, timestamp DESC);
CREATE INDEX idx_errors_type ON user_errors(error_type);
CREATE INDEX idx_errors_severity ON user_errors(severity) WHERE severity IN ('high', 'critical');
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import Counter, defaultdict
import hashlib

@dataclass
class ErrorAnalyzer:
    """Simple error analysis"""
    
    def get_user_errors(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent errors for a user"""
        return self.db.query(
            "SELECT * FROM user_errors WHERE user_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
    
    def find_error_patterns(self) -> List[Dict]:
        """Find common error patterns"""
        # Get errors from last hour
        recent_errors = self.db.query(
            "SELECT error_type, error_message, page, action "
            "FROM user_errors WHERE timestamp > NOW() - INTERVAL '1 hour'"
        )
        
        # Group similar errors
        patterns = defaultdict(list)
        for error in recent_errors:
            # Simple pattern key
            pattern_key = f"{error['error_type']}:{error['page']}:{error['action']}"
            patterns[pattern_key].append(error)
        
        # Return patterns with multiple occurrences
        return [
            {
                'pattern': key,
                'count': len(errors),
                'sample': errors[0]
            }
            for key, errors in patterns.items()
            if len(errors) > 2
        ]
    
    def get_error_cascade(self, user_id: str, session_id: str) -> List[Dict]:
        """Get chain of errors in a session"""
        return self.db.query(
            "SELECT * FROM user_errors "
            "WHERE user_id = ? AND session_id = ? "
            "ORDER BY timestamp",
            (user_id, session_id)
        )
    
    def calculate_error_rate(self, user_id: str) -> Dict:
        """User's error rate"""
        stats = self.db.query_one(
            """
            SELECT 
                COUNT(*) as total_errors,
                COUNT(DISTINCT DATE(timestamp)) as days_with_errors,
                COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as critical_errors,
                COUNT(*) FILTER (WHERE user_blocked = TRUE) as blocking_errors
            FROM user_errors 
            WHERE user_id = ? AND timestamp > NOW() - INTERVAL '7 days'
            """,
            (user_id,)
        )
        
        return {
            'weekly_errors': stats['total_errors'],
            'critical_errors': stats['critical_errors'],
            'blocking_errors': stats['blocking_errors'],
            'daily_average': stats['total_errors'] / 7
        }
    
    def find_struggling_users(self) -> List[Dict]:
        """Users having lots of errors"""
        return self.db.query(
            """
            SELECT 
                user_id,
                COUNT(*) as error_count,
                COUNT(*) FILTER (WHERE user_blocked = TRUE) as blocked_count
            FROM user_errors
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY user_id
            HAVING COUNT(*) > 5
            ORDER BY error_count DESC
            """
        )
```

### 2. API Endpoints

```python
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/errors")

@router.post("/track")
async def track_error(error: UserError):
    """Track a user error"""
    # Store error
    # Check if it's a pattern
    # Alert if critical
    pass

@router.get("/user/{user_id}")
async def get_user_errors(
    user_id: str,
    limit: int = Query(default=10)
):
    """Get user's recent errors"""
    pass

@router.get("/patterns")
async def get_error_patterns(
    time_range: str = Query(default="1h")
):
    """Get common error patterns"""
    pass

@router.get("/struggling-users")
async def get_struggling_users():
    """Users experiencing many errors"""
    pass

@router.post("/{error_id}/resolve")
async def mark_error_resolved(
    error_id: str,
    resolution: Dict
):
    """Mark an error as resolved"""
    pass

@router.get("/impact/high")
async def get_high_impact_errors():
    """Get errors blocking users"""
    pass
```

### 3. Dashboard Components

```typescript
// Global error boundary
export class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, info: ErrorInfo) {
    // Track the error
    api.post('/errors/track', {
      userId: getCurrentUser().id,
      sessionId: getSessionId(),
      error: {
        type: 'react',
        message: error.message,
        technical: error.stack
      },
      context: {
        page: window.location.pathname,
        action: 'component_render',
        component: info.componentStack
      },
      impact: {
        severity: 'high',
        userBlocked: true,
        workflowFailed: false
      }
    });
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => window.location.reload()}>
            Refresh Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Simple error logger
export const useErrorTracking = () => {
  const trackError = (error: any, context?: any) => {
    // Don't track trivial errors
    if (error.code === 'CANCELLED') return;
    
    api.post('/errors/track', {
      userId: getCurrentUser().id,
      sessionId: getSessionId(),
      timestamp: new Date(),
      error: {
        type: error.type || 'unknown',
        code: error.code,
        message: error.message,
        userMessage: error.userMessage || error.message
      },
      context: {
        page: window.location.pathname,
        ...context
      }
    });
  };
  
  return { trackError };
};

// Error display widget
export const UserErrorWidget: React.FC<{ userId: string }> = ({ userId }) => {
  const [errors, setErrors] = useState([]);
  
  return (
    <div className="bg-red-50 p-4 rounded">
      <h3 className="text-red-800 font-bold mb-2">Recent Issues</h3>
      {errors.length === 0 ? (
        <p className="text-green-600">No recent errors! 🎉</p>
      ) : (
        <ul className="space-y-2">
          {errors.map(error => (
            <li key={error.id} className="text-sm">
              <span className="text-red-600">{error.userMessage}</span>
              <span className="text-gray-500 ml-2">
                {formatTime(error.timestamp)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// Error pattern alert
export const ErrorPatternAlert: React.FC = () => {
  const [patterns, setPatterns] = useState([]);
  
  if (patterns.length === 0) return null;
  
  return (
    <div className="bg-yellow-50 border border-yellow-200 p-4 rounded">
      <h4 className="font-bold text-yellow-800">Common Issues Detected</h4>
      {patterns.map(pattern => (
        <div key={pattern.pattern} className="mt-2">
          <span className="text-sm">{pattern.count} users affected</span>
          <span className="text-xs text-gray-600 ml-2">{pattern.sample.message}</span>
        </div>
      ))}
    </div>
  );
};
```

### 4. Error Recovery Helpers

```typescript
// Auto-retry logic
export const withRetry = async (
  fn: () => Promise<any>,
  options = { retries: 3, delay: 1000 }
) => {
  let lastError;
  
  for (let i = 0; i < options.retries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // Track retry attempt
      trackError({
        ...error,
        context: { retryAttempt: i + 1 }
      });
      
      // Wait before retry
      await new Promise(resolve => setTimeout(resolve, options.delay * (i + 1)));
    }
  }
  
  // Track final failure
  trackError({
    ...lastError,
    impact: { severity: 'high', userBlocked: true }
  });
  
  throw lastError;
};

// User-friendly error messages
const ERROR_MESSAGES = {
  'NETWORK_ERROR': 'Connection issue. Please check your internet.',
  'PERMISSION_DENIED': 'You don\'t have access to this feature.',
  'TIMEOUT': 'This is taking longer than usual. Please try again.',
  'VALIDATION_ERROR': 'Please check your input and try again.',
  'WORKFLOW_FAILED': 'The workflow couldn\'t complete. We\'ve saved your progress.'
};

export const getUserMessage = (error: any): string => {
  return ERROR_MESSAGES[error.code] || 'Something went wrong. Please try again.';
};
```

## Implementation Priority

### Phase 1 (Day 1)
- Basic error tracking
- Store in database
- User error display

### Phase 2 (Days 2-3)
- Pattern detection
- Error cascades
- Struggling user detection

### Phase 3 (Days 4-5)
- Recovery tracking
- Error summaries
- Dashboard widgets

## Cost Optimization

- Only track user-facing errors
- Batch error reports
- Daily aggregations
- Auto-delete after 30 days
- Sample similar errors (don't store duplicates)

## What This Tells Us

- What's breaking for users
- Which features are problematic
- When users get stuck
- How users recover
- What needs fixing first

## What We DON'T Track

- Stack traces for every error
- System-level errors users don't see
- Verbose debug logs
- Third-party service errors
- Expected validation errors