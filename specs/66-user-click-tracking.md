# User Click Tracking Analytics Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Simple, lightweight click tracking system that captures user interactions without complex infrastructure. Every click tells a story about user intent and workflow patterns. No bullshit, just raw user behavior data.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Simple click event
interface ClickEvent {
  id: string;
  userId: string;
  sessionId: string;
  timestamp: Date;
  element: ClickedElement;
  position: ClickPosition;
  context: ClickContext;
}

interface ClickedElement {
  type: 'button' | 'link' | 'input' | 'card' | 'menu' | 'other';
  id?: string;
  text?: string;
  href?: string;
  action?: string;
  value?: string;
}

interface ClickPosition {
  x: number;
  y: number;
  screenX: number;
  screenY: number;
  elementX: number;
  elementY: number;
}

interface ClickContext {
  page: string;
  section: string;
  workflowId?: string;
  agentId?: string;
  previousClick?: string;
  timeFromPrevious?: number;
}

// Click patterns
interface ClickPattern {
  userId: string;
  pattern: string[];
  frequency: number;
  avgTimeBetween: number;
  outcome: 'completed' | 'abandoned' | 'error';
}

// Heat map data
interface ClickHeatmap {
  page: string;
  clicks: HeatmapPoint[];
  hotspots: Hotspot[];
  deadZones: DeadZone[];
}

interface HeatmapPoint {
  x: number;
  y: number;
  count: number;
  users: number;
}
```

#### 1.2 SQL Schema

```sql
-- Super simple click tracking
CREATE TABLE click_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    page VARCHAR(255) NOT NULL,
    element_type VARCHAR(50),
    element_id VARCHAR(255),
    element_text TEXT,
    position_x INTEGER,
    position_y INTEGER,
    workflow_id UUID,
    agent_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Click sequences for pattern detection
CREATE TABLE click_sequences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    sequence TEXT[], -- Array of element IDs/actions
    duration_ms INTEGER,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Daily aggregates to save costs
CREATE TABLE daily_click_stats (
    date DATE NOT NULL,
    page VARCHAR(255) NOT NULL,
    total_clicks INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    avg_clicks_per_user DECIMAL(10,2),
    most_clicked_element VARCHAR(255),
    PRIMARY KEY (date, page)
);

-- Indexes only what we need
CREATE INDEX idx_clicks_user_time ON click_events(user_id, timestamp DESC);
CREATE INDEX idx_clicks_page ON click_events(page);
CREATE INDEX idx_sequences_user ON click_sequences(user_id);
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import Counter, defaultdict
import numpy as np

@dataclass
class ClickAnalyzer:
    """Dead simple click analysis"""
    
    def get_user_journey(self, user_id: str, session_id: str) -> List[Dict]:
        """What did the user click on?"""
        # Just return the click sequence
        return self.db.query(
            "SELECT * FROM click_events WHERE user_id = ? AND session_id = ? ORDER BY timestamp",
            (user_id, session_id)
        )
    
    def find_rage_clicks(self, clicks: List[Dict]) -> List[Dict]:
        """User frustration = rapid clicks on same element"""
        rage_clicks = []
        for i in range(len(clicks) - 2):
            if (clicks[i]['element_id'] == clicks[i+1]['element_id'] == clicks[i+2]['element_id']
                and (clicks[i+2]['timestamp'] - clicks[i]['timestamp']).seconds < 2):
                rage_clicks.append({
                    'element': clicks[i]['element_id'],
                    'count': 3,
                    'timestamp': clicks[i]['timestamp']
                })
        return rage_clicks
    
    def get_popular_paths(self, limit: int = 10) -> List[Dict]:
        """Most common click sequences"""
        sequences = self.db.query(
            "SELECT sequence, COUNT(*) as count FROM click_sequences "
            "WHERE completed = TRUE GROUP BY sequence ORDER BY count DESC LIMIT ?",
            (limit,)
        )
        return sequences
    
    def calculate_heatmap(self, page: str) -> Dict:
        """Where do people click most?"""
        clicks = self.db.query(
            "SELECT position_x, position_y FROM click_events WHERE page = ?",
            (page,)
        )
        
        # Simple grid aggregation
        grid_size = 50
        heatmap = defaultdict(int)
        for click in clicks:
            grid_x = click['position_x'] // grid_size
            grid_y = click['position_y'] // grid_size
            heatmap[(grid_x, grid_y)] += 1
        
        return {
            'page': page,
            'heatmap': dict(heatmap),
            'hotspots': self._find_hotspots(heatmap)
        }
```

### 2. API Endpoints

```python
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/clicks")

@router.post("/track")
async def track_click(event: ClickEvent):
    """Track a single click"""
    # Just store it, no complex processing
    pass

@router.post("/track/batch")
async def track_clicks_batch(events: List[ClickEvent]):
    """Track multiple clicks at once (saves API calls)"""
    pass

@router.get("/user/{user_id}/journey")
async def get_user_journey(
    user_id: str,
    session_id: Optional[str] = None
):
    """Get user's click journey"""
    pass

@router.get("/patterns/rage-clicks")
async def get_rage_clicks(
    time_range: str = Query(default="1h")
):
    """Find rage click patterns (user frustration)"""
    pass

@router.get("/heatmap/{page}")
async def get_page_heatmap(page: str):
    """Get click heatmap for a page"""
    pass

@router.get("/popular-paths")
async def get_popular_paths(
    limit: int = Query(default=10)
):
    """Most common user paths"""
    pass
```

### 3. Dashboard Components

```typescript
export const ClickTracker: React.FC = () => {
  useEffect(() => {
    // Simple click listener
    const trackClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      
      // Only track meaningful elements
      if (!target.id && !target.textContent?.trim()) return;
      
      // Batch clicks to reduce API calls
      clickBuffer.push({
        timestamp: new Date(),
        element: {
          type: target.tagName.toLowerCase(),
          id: target.id,
          text: target.textContent?.substring(0, 50)
        },
        position: { x: e.clientX, y: e.clientY }
      });
      
      // Send batch every 5 seconds or 10 clicks
      if (clickBuffer.length >= 10) {
        sendClicks();
      }
    };
    
    document.addEventListener('click', trackClick);
    return () => document.removeEventListener('click', trackClick);
  }, []);
  
  return null; // Invisible component
};

export const ClickHeatmap: React.FC = () => {
  const [heatmapData, setHeatmapData] = useState(null);
  
  return (
    <div className="relative">
      {/* Overlay heatmap on actual page */}
      <canvas 
        className="absolute inset-0 pointer-events-none opacity-50"
        ref={drawHeatmap}
      />
    </div>
  );
};
```

### 4. Real-time Monitoring (Lightweight)

```typescript
// No complex WebSocket, just periodic fetches
export const useClickStream = (userId: string) => {
  const [clicks, setClicks] = useState<ClickEvent[]>([]);
  
  useEffect(() => {
    // Fetch every 10 seconds
    const interval = setInterval(async () => {
      const newClicks = await fetch(`/api/v1/clicks/user/${userId}/recent`);
      setClicks(prev => [...prev, ...newClicks]);
    }, 10000);
    
    return () => clearInterval(interval);
  }, [userId]);
  
  return clicks;
};
```

## Implementation Priority

### Phase 1 (Days 1-3)
- Basic click tracking
- Session tracking
- Store in database

### Phase 2 (Days 4-7)
- Pattern detection
- Rage click detection
- Popular paths

### Phase 3 (Week 2)
- Heatmap generation
- Daily aggregations
- Basic dashboard

## Cost Optimization

- Batch click events (reduce API calls)
- Daily aggregations (reduce storage)
- Only index essential columns
- Archive old data to S3
- Sample data for heatmaps (not every click)

## What This Tells Us

- Where users get stuck (rage clicks)
- Most used features (popular elements)
- Abandoned workflows (incomplete sequences)
- UI dead zones (no clicks)
- User efficiency (time between clicks)

## What We DON'T Track

- Mouse movements (expensive, low value)
- Hover events (too many)
- Scroll depth (unless specifically needed)
- Time on page (derived from clicks)
- Complex attribution (keep it simple)