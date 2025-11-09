# User Session Tracking Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track user sessions to understand how they interact with the system. Simple session management that captures what matters without expensive infrastructure.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Basic session info
interface UserSession {
  id: string;
  userId: string;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  device: DeviceInfo;
  entry: EntryPoint;
  exit?: ExitPoint;
  actions: number;
  errors: number;
}

interface DeviceInfo {
  type: 'desktop' | 'mobile' | 'tablet';
  browser: string;
  os: string;
  screenSize?: string;
}

interface EntryPoint {
  page: string;
  source: 'direct' | 'internal' | 'external';
  referrer?: string;
  campaign?: string;
}

interface ExitPoint {
  page: string;
  reason: 'logout' | 'timeout' | 'error' | 'navigation';
  lastAction?: string;
}

// Session activity
interface SessionActivity {
  sessionId: string;
  timestamp: Date;
  action: string;
  details?: Record<string, any>;
  duration: number; // Time since last action
}

// Session patterns
interface SessionPattern {
  type: 'power_user' | 'explorer' | 'task_focused' | 'confused';
  indicators: string[];
  confidence: number;
}
```

#### 1.2 SQL Schema

```sql
-- Simple session tracking
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    start_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    device_type VARCHAR(20),
    browser VARCHAR(50),
    entry_page VARCHAR(255),
    exit_page VARCHAR(255),
    action_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    workflow_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Key session events only
CREATE TABLE session_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Daily session summaries
CREATE TABLE daily_session_stats (
    date DATE NOT NULL PRIMARY KEY,
    total_sessions INTEGER,
    unique_users INTEGER,
    avg_duration_seconds INTEGER,
    bounce_rate DECIMAL(5,2),
    error_rate DECIMAL(5,2),
    most_common_entry VARCHAR(255),
    most_common_exit VARCHAR(255)
);

-- Minimal indexes
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_date ON user_sessions(start_time::date);
CREATE INDEX idx_events_session ON session_events(session_id);
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional

@dataclass
class SessionAnalyzer:
    """Simple session analysis"""
    
    def get_active_sessions(self) -> List[Dict]:
        """Current active sessions"""
        return self.db.query(
            "SELECT * FROM user_sessions WHERE end_time IS NULL "
            "AND start_time > NOW() - INTERVAL '30 minutes'"
        )
    
    def calculate_session_duration(self, session_id: str) -> int:
        """How long was the session?"""
        session = self.db.query_one(
            "SELECT start_time, end_time FROM user_sessions WHERE id = ?",
            (session_id,)
        )
        if session['end_time']:
            return (session['end_time'] - session['start_time']).seconds
        return (datetime.now() - session['start_time']).seconds
    
    def identify_bounce_sessions(self) -> List[Dict]:
        """Sessions that ended immediately"""
        return self.db.query(
            "SELECT * FROM user_sessions "
            "WHERE duration_seconds < 30 AND action_count <= 1"
        )
    
    def get_user_session_pattern(self, user_id: str) -> Dict:
        """What's this user's typical session like?"""
        sessions = self.db.query(
            "SELECT * FROM user_sessions WHERE user_id = ? "
            "ORDER BY start_time DESC LIMIT 20",
            (user_id,)
        )
        
        if not sessions:
            return {'pattern': 'new_user'}
        
        avg_duration = sum(s['duration_seconds'] or 0 for s in sessions) / len(sessions)
        avg_actions = sum(s['action_count'] for s in sessions) / len(sessions)
        
        # Simple pattern detection
        if avg_duration > 1800 and avg_actions > 50:
            return {'pattern': 'power_user', 'avg_duration': avg_duration}
        elif avg_duration < 300:
            return {'pattern': 'quick_checker', 'avg_duration': avg_duration}
        elif sessions[0]['error_count'] > 5:
            return {'pattern': 'struggling_user', 'errors': sessions[0]['error_count']}
        else:
            return {'pattern': 'regular_user', 'avg_duration': avg_duration}
    
    def find_abandoned_workflows(self, session_id: str) -> List[Dict]:
        """Which workflows were started but not completed?"""
        return self.db.query(
            """
            SELECT DISTINCT workflow_id 
            FROM workflow_executions 
            WHERE session_id = ? 
            AND status != 'completed'
            """,
            (session_id,)
        )
```

### 2. API Endpoints

```python
from fastapi import APIRouter, HTTPException
from typing import List, Optional

router = APIRouter(prefix="/api/v1/sessions")

@router.post("/start")
async def start_session(user_id: str, device: DeviceInfo):
    """Start a new session"""
    # Create session, return session ID
    pass

@router.post("/{session_id}/heartbeat")
async def session_heartbeat(session_id: str):
    """Keep session alive (called every 5 min)"""
    pass

@router.post("/{session_id}/end")
async def end_session(session_id: str, reason: str):
    """End a session"""
    pass

@router.post("/{session_id}/event")
async def track_session_event(session_id: str, event: Dict):
    """Track important session events only"""
    pass

@router.get("/active")
async def get_active_sessions():
    """Get currently active sessions"""
    pass

@router.get("/user/{user_id}/current")
async def get_user_current_session(user_id: str):
    """Get user's current session"""
    pass

@router.get("/user/{user_id}/history")
async def get_user_session_history(
    user_id: str,
    limit: int = 10
):
    """Get user's session history"""
    pass

@router.get("/patterns/{user_id}")
async def get_user_patterns(user_id: str):
    """Get user's session patterns"""
    pass
```

### 3. Dashboard Components

```typescript
export const SessionTracker: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  useEffect(() => {
    // Start session on mount
    const startSession = async () => {
      const session = await api.post('/sessions/start', {
        userId: currentUser.id,
        device: getDeviceInfo()
      });
      setSessionId(session.id);
      localStorage.setItem('sessionId', session.id);
    };
    
    startSession();
    
    // Heartbeat every 5 minutes
    const heartbeat = setInterval(() => {
      if (sessionId) {
        api.post(`/sessions/${sessionId}/heartbeat`);
      }
    }, 5 * 60 * 1000);
    
    // End session on unmount
    return () => {
      clearInterval(heartbeat);
      if (sessionId) {
        api.post(`/sessions/${sessionId}/end`, { reason: 'navigation' });
      }
    };
  }, []);
  
  return null;
};

export const ActiveSessionsWidget: React.FC = () => {
  const [activeSessions, setActiveSessions] = useState([]);
  
  return (
    <div className="bg-white p-4 rounded shadow">
      <h3 className="text-lg font-bold mb-2">Active Now</h3>
      <div className="text-3xl font-bold">{activeSessions.length}</div>
      <div className="text-sm text-gray-500">users online</div>
    </div>
  );
};

export const SessionTimeline: React.FC<{ userId: string }> = ({ userId }) => {
  const [sessions, setSessions] = useState([]);
  
  return (
    <div className="space-y-2">
      {sessions.map(session => (
        <div key={session.id} className="flex items-center space-x-4 p-2 border rounded">
          <div className="text-sm">
            {formatDuration(session.duration)}
          </div>
          <div className="flex-1">
            <div className="h-2 bg-blue-500 rounded" 
                 style={{ width: `${Math.min(session.actions * 2, 100)}%` }} />
          </div>
          <div className="text-xs text-gray-500">
            {session.actions} actions
          </div>
        </div>
      ))}
    </div>
  );
};
```

### 4. Session Management

```typescript
// Simple session manager
class SessionManager {
  private sessionId: string | null = null;
  private lastActivity: Date = new Date();
  private activityBuffer: any[] = [];
  
  start(userId: string): void {
    this.sessionId = generateId();
    this.lastActivity = new Date();
    
    // Store in localStorage for recovery
    localStorage.setItem('session', JSON.stringify({
      id: this.sessionId,
      userId,
      startTime: this.lastActivity
    }));
  }
  
  trackActivity(action: string, data?: any): void {
    if (!this.sessionId) return;
    
    const now = new Date();
    const timeSinceLastActivity = now.getTime() - this.lastActivity.getTime();
    
    // If more than 30 minutes, start new session
    if (timeSinceLastActivity > 30 * 60 * 1000) {
      this.end('timeout');
      this.start(this.getCurrentUserId());
    }
    
    this.lastActivity = now;
    
    // Buffer activities to reduce API calls
    this.activityBuffer.push({ action, data, timestamp: now });
    
    if (this.activityBuffer.length >= 5) {
      this.flush();
    }
  }
  
  private flush(): void {
    if (this.activityBuffer.length === 0) return;
    
    api.post(`/sessions/${this.sessionId}/events`, {
      events: this.activityBuffer
    });
    
    this.activityBuffer = [];
  }
  
  end(reason: string): void {
    this.flush();
    api.post(`/sessions/${this.sessionId}/end`, { reason });
    this.sessionId = null;
    localStorage.removeItem('session');
  }
}
```

## Implementation Priority

### Phase 1 (Days 1-2)
- Session start/end tracking
- Basic session storage
- Heartbeat mechanism

### Phase 2 (Days 3-4)
- Activity tracking
- Duration calculation
- Device info capture

### Phase 3 (Days 5-7)
- Pattern detection
- Session summaries
- Basic dashboard

## Cost Optimization

- Only track key events, not every action
- Buffer events and batch send
- Use heartbeat instead of constant connection
- Daily aggregations for historical data
- Auto-cleanup sessions older than 30 days

## What This Tells Us

- When users are active
- How long they stay
- What makes them leave
- Which features they use together
- User engagement levels

## What We DON'T Need

- Real-time presence (expensive)
- Detailed mouse tracking
- Every single page view
- Complex session replay
- Cross-device session linking