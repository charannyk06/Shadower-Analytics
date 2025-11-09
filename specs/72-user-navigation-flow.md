# User Navigation Flow Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track how users move through the app. Where they go, where they get lost, where they leave. Simple navigation tracking without complex analytics.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Page navigation
interface NavigationEvent {
  userId: string;
  sessionId: string;
  from: string;
  to: string;
  timestamp: Date;
  timeOnPage: number;
  method: 'click' | 'back' | 'forward' | 'direct' | 'refresh';
}

interface UserPath {
  userId: string;
  sessionId: string;
  path: string[];
  completed: boolean;
  exitPoint?: string;
  totalTime: number;
}

interface NavigationPattern {
  pattern: string[];
  frequency: number;
  avgTime: number;
  completionRate: number;
}
```

#### 1.2 SQL Schema

```sql
-- Simple navigation tracking
CREATE TABLE navigation_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    from_page VARCHAR(255),
    to_page VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    time_on_page INTEGER,
    method VARCHAR(20)
);

-- Common paths
CREATE TABLE user_paths (
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    path_hash VARCHAR(64),
    path_array TEXT[],
    completed BOOLEAN DEFAULT FALSE,
    exit_page VARCHAR(255),
    total_time INTEGER,
    PRIMARY KEY (user_id, session_id)
);

-- Daily navigation summary
CREATE TABLE daily_navigation_stats (
    date DATE NOT NULL,
    page VARCHAR(255) NOT NULL,
    visits INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    avg_time_seconds INTEGER,
    bounce_count INTEGER DEFAULT 0,
    PRIMARY KEY (date, page)
);

CREATE INDEX idx_nav_user_session ON navigation_events(user_id, session_id);
CREATE INDEX idx_nav_timestamp ON navigation_events(timestamp DESC);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class NavigationAnalyzer:
    """Where do users go?"""
    
    def get_user_journey(self, session_id: str) -> List[str]:
        """Get pages visited in session"""
        events = self.db.query(
            "SELECT to_page FROM navigation_events "
            "WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        return [e['to_page'] for e in events]
    
    def find_dead_ends(self) -> List[Dict]:
        """Pages where users leave"""
        return self.db.query(
            """
            SELECT 
                from_page as page,
                COUNT(*) as exits
            FROM navigation_events
            WHERE to_page IS NULL
            GROUP BY from_page
            HAVING COUNT(*) > 10
            ORDER BY exits DESC
            """
        )
    
    def get_popular_paths(self) -> List[Dict]:
        """Most common navigation paths"""
        return self.db.query(
            """
            SELECT 
                path_array,
                COUNT(*) as count
            FROM user_paths
            WHERE completed = TRUE
            GROUP BY path_array
            ORDER BY count DESC
            LIMIT 10
            """
        )
```

### 2. API Endpoints

```python
@router.post("/navigate")
async def track_navigation(event: NavigationEvent):
    """Track page navigation"""
    pass

@router.get("/journey/{session_id}")
async def get_user_journey(session_id: str):
    """Get navigation journey"""
    pass

@router.get("/dead-ends")
async def get_dead_ends():
    """Pages users leave from"""
    pass

@router.get("/popular-paths")
async def get_popular_paths():
    """Common navigation paths"""
    pass
```

### 3. Dashboard Components

```typescript
export const NavigationTracker: React.FC = () => {
  const [previousPage, setPreviousPage] = useState('');
  
  useEffect(() => {
    const trackNavigation = () => {
      api.post('/navigation/navigate', {
        userId: getCurrentUser().id,
        sessionId: getSessionId(),
        from: previousPage,
        to: window.location.pathname,
        timestamp: new Date(),
        timeOnPage: Date.now() - pageStartTime
      });
      
      setPreviousPage(window.location.pathname);
    };
    
    // Track on route change
    window.addEventListener('popstate', trackNavigation);
    
    return () => {
      window.removeEventListener('popstate', trackNavigation);
    };
  }, [previousPage]);
  
  return null;
};
```

## What This Tells Us

- Where users go most
- Where they get stuck
- Common user journeys
- Pages that make users leave

## Cost Optimization

- Track page changes, not every action
- Batch navigation events
- Daily summaries only
- 7-day detailed retention