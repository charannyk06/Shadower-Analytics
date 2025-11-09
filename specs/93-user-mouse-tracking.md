# User Mouse Tracking Specification

## Overview
Track mouse movement patterns, clicks, and hover behavior to understand user interaction patterns and identify UI/UX improvements without invasive tracking.

## Database Schema

### Tables

```sql
-- Mouse movement sessions
CREATE TABLE mouse_movement_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    page_url VARCHAR(500) NOT NULL,
    total_distance_px BIGINT DEFAULT 0,
    avg_speed_px_per_sec DECIMAL(10, 2),
    total_clicks INTEGER DEFAULT 0,
    rage_clicks INTEGER DEFAULT 0,
    dead_clicks INTEGER DEFAULT 0,
    hesitation_count INTEGER DEFAULT 0,
    movement_pattern VARCHAR(50), -- linear, circular, erratic, precise
    session_duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_mouse_sessions_user (user_id, created_at DESC),
    INDEX idx_mouse_sessions_page (page_url)
);

-- Click events tracking
CREATE TABLE user_click_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    element_type VARCHAR(100),
    element_id VARCHAR(200),
    element_class VARCHAR(200),
    click_x INTEGER,
    click_y INTEGER,
    viewport_width INTEGER,
    viewport_height INTEGER,
    click_count INTEGER DEFAULT 1, -- For multi-clicks
    time_since_last_click_ms INTEGER,
    is_rage_click BOOLEAN DEFAULT false,
    is_dead_click BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_click_events_user (user_id, created_at DESC),
    INDEX idx_click_events_element (element_type, element_id),
    INDEX idx_click_events_rage (is_rage_click, created_at DESC)
);

-- Hover events tracking
CREATE TABLE user_hover_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    element_type VARCHAR(100),
    element_id VARCHAR(200),
    hover_duration_ms INTEGER,
    hover_count INTEGER DEFAULT 1,
    did_click BOOLEAN DEFAULT false,
    hover_pattern VARCHAR(50), -- quick, lingering, repeated
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_hover_events_user (user_id, created_at DESC),
    INDEX idx_hover_events_duration (hover_duration_ms)
);

-- Click heatmap aggregation
CREATE TABLE click_heatmap_data (
    id SERIAL PRIMARY KEY,
    page_url VARCHAR(500) NOT NULL,
    viewport_width INTEGER,
    viewport_height INTEGER,
    x_coordinate INTEGER,
    y_coordinate INTEGER,
    click_count INTEGER DEFAULT 1,
    unique_users INTEGER DEFAULT 1,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(page_url, viewport_width, viewport_height, x_coordinate, y_coordinate),
    INDEX idx_heatmap_page (page_url),
    INDEX idx_heatmap_count (click_count DESC)
);
```

## TypeScript Interfaces

```typescript
// Mouse movement session
interface MouseMovementSession {
  id: string;
  userId: string;
  sessionId: string;
  pageUrl: string;
  totalDistancePx: number;
  avgSpeedPxPerSec: number;
  totalClicks: number;
  rageClicks: number;
  deadClicks: number;
  hesitationCount: number;
  movementPattern: 'linear' | 'circular' | 'erratic' | 'precise';
  sessionDurationSeconds: number;
}

// Click event
interface ClickEvent {
  id: string;
  userId: string;
  sessionId: string;
  pageUrl: string;
  elementType?: string;
  elementId?: string;
  elementClass?: string;
  clickX: number;
  clickY: number;
  viewportWidth: number;
  viewportHeight: number;
  clickCount: number;
  timeSinceLastClickMs?: number;
  isRageClick: boolean;
  isDeadClick: boolean;
  createdAt: Date;
}

// Hover event
interface HoverEvent {
  id: string;
  userId: string;
  sessionId: string;
  pageUrl: string;
  elementType?: string;
  elementId?: string;
  hoverDurationMs: number;
  hoverCount: number;
  didClick: boolean;
  hoverPattern: 'quick' | 'lingering' | 'repeated';
}

// Mouse statistics
interface MouseStatistics {
  totalSessions: number;
  avgDistancePerSession: number;
  avgSpeedPxPerSec: number;
  totalClicks: number;
  rageClickRate: number;
  deadClickRate: number;
  mostClickedElements: ElementClick[];
  movementPatterns: PatternDistribution;
}

// Click heatmap point
interface HeatmapPoint {
  x: number;
  y: number;
  intensity: number;
  clickCount: number;
  uniqueUsers: number;
}

// Mouse behavior pattern
interface MousePattern {
  patternType: 'power_user' | 'explorer' | 'hesitant' | 'frustrated';
  confidence: number;
  indicators: {
    clickPrecision: number;
    movementEfficiency: number;
    rageClickFrequency: number;
    hesitationFrequency: number;
  };
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math
import asyncpg

@dataclass
class MouseAnalytics:
    """Analyze mouse movement and interaction patterns"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.rage_click_threshold = 3  # clicks within 1 second
        self.dead_click_threshold = 5000  # 5 seconds without action
    
    async def start_mouse_session(
        self,
        user_id: str,
        page_url: str
    ) -> str:
        """Start a new mouse tracking session"""
        query = """
            INSERT INTO mouse_movement_sessions (
                user_id, page_url
            ) VALUES ($1, $2)
            RETURNING session_id
        """
        
        async with self.db.acquire() as conn:
            session_id = await conn.fetchval(query, user_id, page_url)
        
        return session_id
    
    async def track_click_event(
        self,
        user_id: str,
        session_id: str,
        page_url: str,
        click_x: int,
        click_y: int,
        viewport_width: int,
        viewport_height: int,
        element_type: Optional[str] = None,
        element_id: Optional[str] = None,
        element_class: Optional[str] = None,
        time_since_last: Optional[int] = None
    ) -> Dict:
        """Track a click event"""
        
        # Detect rage clicks (multiple clicks in quick succession)
        is_rage = False
        if time_since_last and time_since_last < 1000:
            # Check recent clicks
            recent_clicks = await self._get_recent_clicks(session_id, 1000)
            if len(recent_clicks) >= self.rage_click_threshold:
                is_rage = True
        
        # Detect dead clicks (clicks with no effect)
        is_dead = await self._is_dead_click(element_type, element_id)
        
        query = """
            INSERT INTO user_click_events (
                user_id, session_id, page_url, element_type,
                element_id, element_class, click_x, click_y,
                viewport_width, viewport_height, time_since_last_click_ms,
                is_rage_click, is_dead_click
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            click_id = await conn.fetchval(
                query, user_id, session_id, page_url, element_type,
                element_id, element_class, click_x, click_y,
                viewport_width, viewport_height, time_since_last,
                is_rage, is_dead
            )
            
            # Update heatmap data
            await self._update_heatmap(
                conn, page_url, click_x, click_y, 
                viewport_width, viewport_height, user_id
            )
            
            # Update session statistics
            await self._update_session_stats(conn, session_id, is_rage, is_dead)
        
        return {
            'click_id': click_id,
            'is_rage_click': is_rage,
            'is_dead_click': is_dead
        }
    
    async def track_hover_event(
        self,
        user_id: str,
        session_id: str,
        page_url: str,
        element_type: Optional[str],
        element_id: Optional[str],
        hover_duration: int,
        did_click: bool = False
    ) -> int:
        """Track a hover event"""
        
        # Determine hover pattern
        if hover_duration < 500:
            pattern = 'quick'
        elif hover_duration > 3000:
            pattern = 'lingering'
        else:
            pattern = 'normal'
        
        query = """
            INSERT INTO user_hover_events (
                user_id, session_id, page_url, element_type,
                element_id, hover_duration_ms, did_click, hover_pattern
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, session_id, element_id) 
            DO UPDATE SET 
                hover_count = user_hover_events.hover_count + 1,
                hover_duration_ms = user_hover_events.hover_duration_ms + EXCLUDED.hover_duration_ms,
                did_click = user_hover_events.did_click OR EXCLUDED.did_click
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            hover_id = await conn.fetchval(
                query, user_id, session_id, page_url, element_type,
                element_id, hover_duration, did_click, pattern
            )
        
        return hover_id
    
    async def update_mouse_session(
        self,
        session_id: str,
        total_distance: int,
        movement_pattern: Optional[str] = None,
        hesitation_count: int = 0
    ):
        """Update mouse session with movement data"""
        query = """
            UPDATE mouse_movement_sessions
            SET total_distance_px = $2,
                movement_pattern = COALESCE($3, movement_pattern),
                hesitation_count = hesitation_count + $4,
                avg_speed_px_per_sec = CASE 
                    WHEN session_duration_seconds > 0 
                    THEN $2::float / session_duration_seconds
                    ELSE 0
                END,
                session_duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))
            WHERE session_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, session_id, total_distance, movement_pattern, hesitation_count)
    
    async def get_mouse_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get mouse interaction statistics"""
        query = """
            WITH session_stats AS (
                SELECT 
                    COUNT(*) as total_sessions,
                    AVG(total_distance_px) as avg_distance,
                    AVG(avg_speed_px_per_sec) as avg_speed,
                    SUM(total_clicks) as total_clicks,
                    SUM(rage_clicks) as rage_clicks,
                    SUM(dead_clicks) as dead_clicks
                FROM mouse_movement_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            top_elements AS (
                SELECT 
                    element_type,
                    element_id,
                    COUNT(*) as click_count
                FROM user_click_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND element_type IS NOT NULL
                GROUP BY element_type, element_id
                ORDER BY click_count DESC
                LIMIT 10
            ),
            patterns AS (
                SELECT 
                    movement_pattern,
                    COUNT(*) as count
                FROM mouse_movement_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND movement_pattern IS NOT NULL
                GROUP BY movement_pattern
            )
            SELECT 
                s.*,
                (SELECT json_agg(json_build_object(
                    'element_type', element_type,
                    'element_id', element_id,
                    'click_count', click_count
                )) FROM top_elements) as top_elements,
                (SELECT json_object_agg(movement_pattern, count) FROM patterns) as patterns
            FROM session_stats s
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            total_clicks = row['total_clicks'] or 0
            rage_clicks = row['rage_clicks'] or 0
            dead_clicks = row['dead_clicks'] or 0
            
            return {
                'total_sessions': row['total_sessions'] or 0,
                'avg_distance_per_session': row['avg_distance'] or 0,
                'avg_speed_px_per_sec': row['avg_speed'] or 0,
                'total_clicks': total_clicks,
                'rage_click_rate': (rage_clicks / total_clicks * 100) if total_clicks > 0 else 0,
                'dead_click_rate': (dead_clicks / total_clicks * 100) if total_clicks > 0 else 0,
                'most_clicked_elements': row['top_elements'] or [],
                'movement_patterns': row['patterns'] or {}
            }
    
    async def detect_mouse_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user mouse behavior pattern"""
        query = """
            SELECT 
                AVG(avg_speed_px_per_sec) as avg_speed,
                AVG(total_distance_px) as avg_distance,
                AVG(rage_clicks::float / NULLIF(total_clicks, 0)) as rage_rate,
                AVG(dead_clicks::float / NULLIF(total_clicks, 0)) as dead_rate,
                AVG(hesitation_count) as avg_hesitation,
                COUNT(*) as session_count
            FROM mouse_movement_sessions
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow(query % days, user_id)
            
            if not stats or not stats['session_count']:
                return {'pattern_type': 'unknown', 'confidence': 0}
            
            # Analyze click precision
            precision_query = """
                SELECT 
                    STDDEV(click_x) as x_variance,
                    STDDEV(click_y) as y_variance
                FROM user_click_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """
            
            precision = await conn.fetchrow(precision_query % days, user_id)
            
            pattern = self._determine_mouse_pattern(
                stats['avg_speed'] or 0,
                stats['avg_distance'] or 0,
                stats['rage_rate'] or 0,
                stats['dead_rate'] or 0,
                stats['avg_hesitation'] or 0,
                precision['x_variance'] or 0,
                precision['y_variance'] or 0
            )
            
            return pattern
    
    async def get_click_heatmap(
        self,
        page_url: str,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
        grid_size: int = 20
    ) -> List[Dict]:
        """Get click heatmap data for a page"""
        query = """
            SELECT 
                x_coordinate,
                y_coordinate,
                click_count,
                unique_users
            FROM click_heatmap_data
            WHERE page_url = $1
                %s
                %s
            ORDER BY click_count DESC
            LIMIT 1000
        """
        
        width_filter = "AND viewport_width = $2" if viewport_width else ""
        height_filter = "AND viewport_height = $3" if viewport_height else ""
        
        async with self.db.acquire() as conn:
            params = [page_url]
            if viewport_width:
                params.append(viewport_width)
            if viewport_height:
                params.append(viewport_height)
            
            rows = await conn.fetch(query % (width_filter, height_filter), *params)
            
            # Aggregate into grid cells
            heatmap = self._aggregate_to_grid(rows, grid_size)
            
            return heatmap
    
    async def get_rage_click_areas(
        self,
        page_url: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Identify areas with high rage click rates"""
        query = """
            WITH rage_areas AS (
                SELECT 
                    page_url,
                    element_type,
                    element_id,
                    COUNT(*) as rage_click_count,
                    COUNT(DISTINCT user_id) as affected_users,
                    AVG(click_x) as avg_x,
                    AVG(click_y) as avg_y
                FROM user_click_events
                WHERE is_rage_click = true
                    %s
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY page_url, element_type, element_id
                HAVING COUNT(*) > 3
                ORDER BY rage_click_count DESC
                LIMIT $1
            )
            SELECT * FROM rage_areas
        """
        
        page_filter = "AND page_url = $2" if page_url else ""
        
        async with self.db.acquire() as conn:
            if page_url:
                rows = await conn.fetch(query % page_filter, limit, page_url)
            else:
                rows = await conn.fetch(query % page_filter, limit)
            
            return [
                {
                    'page_url': row['page_url'],
                    'element_type': row['element_type'],
                    'element_id': row['element_id'],
                    'rage_click_count': row['rage_click_count'],
                    'affected_users': row['affected_users'],
                    'location': {
                        'x': row['avg_x'],
                        'y': row['avg_y']
                    },
                    'severity': self._get_rage_severity(row['rage_click_count'])
                }
                for row in rows
            ]
    
    async def get_hover_insights(
        self,
        page_url: str,
        min_duration: int = 1000
    ) -> List[Dict]:
        """Get insights from hover behavior"""
        query = """
            SELECT 
                element_type,
                element_id,
                COUNT(*) as hover_count,
                AVG(hover_duration_ms) as avg_duration,
                COUNT(*) FILTER (WHERE did_click) as click_count,
                COUNT(DISTINCT user_id) as unique_users
            FROM user_hover_events
            WHERE page_url = $1
                AND hover_duration_ms >= $2
            GROUP BY element_type, element_id
            HAVING COUNT(*) > 5
            ORDER BY hover_count DESC
            LIMIT 20
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, page_url, min_duration)
            
            return [
                {
                    'element_type': row['element_type'],
                    'element_id': row['element_id'],
                    'hover_count': row['hover_count'],
                    'avg_duration': row['avg_duration'],
                    'click_conversion': (
                        row['click_count'] / row['hover_count'] * 100 
                        if row['hover_count'] > 0 else 0
                    ),
                    'unique_users': row['unique_users'],
                    'engagement_level': self._get_hover_engagement(row['avg_duration'])
                }
                for row in rows
            ]
    
    async def get_dead_click_elements(
        self,
        page_url: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get elements with high dead click rates"""
        query = """
            SELECT 
                page_url,
                element_type,
                element_id,
                element_class,
                COUNT(*) as dead_click_count,
                COUNT(DISTINCT user_id) as affected_users
            FROM user_click_events
            WHERE is_dead_click = true
                %s
            GROUP BY page_url, element_type, element_id, element_class
            HAVING COUNT(*) > 2
            ORDER BY dead_click_count DESC
            LIMIT $1
        """
        
        page_filter = "AND page_url = $2" if page_url else ""
        
        async with self.db.acquire() as conn:
            if page_url:
                rows = await conn.fetch(query % page_filter, limit, page_url)
            else:
                rows = await conn.fetch(query % page_filter, limit)
            
            return [
                {
                    'page_url': row['page_url'],
                    'element_type': row['element_type'],
                    'element_id': row['element_id'],
                    'element_class': row['element_class'],
                    'dead_click_count': row['dead_click_count'],
                    'affected_users': row['affected_users'],
                    'issue_type': self._classify_dead_click_issue(row)
                }
                for row in rows
            ]
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_sessions': 0,
            'avg_distance_per_session': 0,
            'avg_speed_px_per_sec': 0,
            'total_clicks': 0,
            'rage_click_rate': 0,
            'dead_click_rate': 0,
            'most_clicked_elements': [],
            'movement_patterns': {}
        }
    
    def _determine_mouse_pattern(
        self,
        avg_speed: float,
        avg_distance: float,
        rage_rate: float,
        dead_rate: float,
        hesitation: float,
        x_variance: float,
        y_variance: float
    ) -> Dict:
        """Determine mouse behavior pattern"""
        
        # Calculate indicators
        click_precision = 100 - min((x_variance + y_variance) / 2, 100)
        movement_efficiency = min(avg_distance / 10000 * 100, 100) if avg_distance else 0
        rage_frequency = rage_rate * 100 if rage_rate else 0
        hesitation_frequency = min(hesitation * 10, 100)
        
        # Power user: high precision, efficient movement, low rage clicks
        if click_precision > 70 and rage_frequency < 5 and movement_efficiency > 60:
            pattern_type = 'power_user'
            confidence = 0.8
        
        # Explorer: high movement, moderate precision
        elif avg_distance > 50000 and click_precision > 50:
            pattern_type = 'explorer'
            confidence = 0.7
        
        # Hesitant: high hesitation, low efficiency
        elif hesitation_frequency > 50 and movement_efficiency < 40:
            pattern_type = 'hesitant'
            confidence = 0.7
        
        # Frustrated: high rage clicks, dead clicks
        elif rage_frequency > 20 or dead_rate > 0.1:
            pattern_type = 'frustrated'
            confidence = 0.8
        
        else:
            pattern_type = 'normal'
            confidence = 0.5
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'indicators': {
                'click_precision': click_precision,
                'movement_efficiency': movement_efficiency,
                'rage_click_frequency': rage_frequency,
                'hesitation_frequency': hesitation_frequency
            }
        }
    
    def _aggregate_to_grid(self, points: List, grid_size: int) -> List[Dict]:
        """Aggregate click points to grid cells"""
        grid = defaultdict(lambda: {'clicks': 0, 'users': set()})
        
        for point in points:
            grid_x = (point['x_coordinate'] // grid_size) * grid_size
            grid_y = (point['y_coordinate'] // grid_size) * grid_size
            key = (grid_x, grid_y)
            
            grid[key]['clicks'] += point['click_count']
            grid[key]['users'].add(point.get('user_id', 'unknown'))
        
        # Convert to list and calculate intensity
        max_clicks = max(g['clicks'] for g in grid.values()) if grid else 1
        
        return [
            {
                'x': x,
                'y': y,
                'click_count': data['clicks'],
                'unique_users': len(data['users']),
                'intensity': data['clicks'] / max_clicks
            }
            for (x, y), data in grid.items()
        ]
    
    def _get_rage_severity(self, count: int) -> str:
        """Get rage click severity level"""
        if count > 50:
            return 'critical'
        elif count > 20:
            return 'high'
        elif count > 10:
            return 'medium'
        else:
            return 'low'
    
    def _get_hover_engagement(self, duration: float) -> str:
        """Get hover engagement level"""
        if duration > 5000:
            return 'very_high'
        elif duration > 3000:
            return 'high'
        elif duration > 1500:
            return 'medium'
        elif duration > 500:
            return 'low'
        else:
            return 'very_low'
    
    def _classify_dead_click_issue(self, row: dict) -> str:
        """Classify dead click issue type"""
        if row['element_type'] in ['div', 'span', 'p']:
            return 'non_interactive_element'
        elif row['element_type'] in ['button', 'a'] and row['dead_click_count'] > 10:
            return 'broken_interaction'
        else:
            return 'unclear_ui'
    
    async def _get_recent_clicks(self, session_id: str, timeframe_ms: int) -> List:
        """Get recent clicks within timeframe"""
        # Implementation
        return []
    
    async def _is_dead_click(self, element_type: Optional[str], element_id: Optional[str]) -> bool:
        """Determine if click is dead"""
        # Implementation
        return False
    
    async def _update_heatmap(
        self,
        conn,
        page_url: str,
        x: int,
        y: int,
        width: int,
        height: int,
        user_id: str
    ):
        """Update click heatmap data"""
        # Implementation
        pass
    
    async def _update_session_stats(
        self,
        conn,
        session_id: str,
        is_rage: bool,
        is_dead: bool
    ):
        """Update session statistics"""
        # Implementation
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/mouse", tags=["mouse-analytics"])

@router.post("/session/start")
async def start_mouse_session(
    user_id: str,
    page_url: str
):
    """Start mouse tracking session"""
    analytics = MouseAnalytics(db_pool)
    session_id = await analytics.start_mouse_session(user_id, page_url)
    return {"session_id": session_id}

@router.post("/click")
async def track_click(
    user_id: str,
    session_id: str,
    page_url: str,
    click_x: int,
    click_y: int,
    viewport_width: int,
    viewport_height: int,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    element_class: Optional[str] = None,
    time_since_last: Optional[int] = None
):
    """Track click event"""
    analytics = MouseAnalytics(db_pool)
    result = await analytics.track_click_event(
        user_id, session_id, page_url, click_x, click_y,
        viewport_width, viewport_height, element_type,
        element_id, element_class, time_since_last
    )
    return result

@router.post("/hover")
async def track_hover(
    user_id: str,
    session_id: str,
    page_url: str,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    hover_duration: int = 0,
    did_click: bool = False
):
    """Track hover event"""
    analytics = MouseAnalytics(db_pool)
    hover_id = await analytics.track_hover_event(
        user_id, session_id, page_url, element_type,
        element_id, hover_duration, did_click
    )
    return {"hover_id": hover_id}

@router.patch("/session/{session_id}")
async def update_session(
    session_id: str,
    total_distance: int,
    movement_pattern: Optional[str] = None,
    hesitation_count: int = 0
):
    """Update mouse session"""
    analytics = MouseAnalytics(db_pool)
    await analytics.update_mouse_session(
        session_id, total_distance, movement_pattern, hesitation_count
    )
    return {"status": "updated"}

@router.get("/statistics/{user_id}")
async def get_mouse_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get mouse statistics"""
    analytics = MouseAnalytics(db_pool)
    stats = await analytics.get_mouse_statistics(user_id, days)
    return stats

@router.get("/pattern/{user_id}")
async def detect_mouse_pattern(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect mouse behavior pattern"""
    analytics = MouseAnalytics(db_pool)
    pattern = await analytics.detect_mouse_pattern(user_id, days)
    return pattern

@router.get("/heatmap/{page_url:path}")
async def get_click_heatmap(
    page_url: str,
    viewport_width: Optional[int] = None,
    viewport_height: Optional[int] = None,
    grid_size: int = Query(20, ge=10, le=100)
):
    """Get click heatmap"""
    analytics = MouseAnalytics(db_pool)
    heatmap = await analytics.get_click_heatmap(
        page_url, viewport_width, viewport_height, grid_size
    )
    return {"heatmap": heatmap}

@router.get("/rage-clicks")
async def get_rage_click_areas(
    page_url: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Get rage click areas"""
    analytics = MouseAnalytics(db_pool)
    areas = await analytics.get_rage_click_areas(page_url, limit)
    return {"rage_areas": areas}
```

## React Dashboard Components

```tsx
// Mouse Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, HeatMap, Table } from '@/components/ui';

interface MouseDashboardProps {
  userId?: string;
  pageUrl?: string;
}

export const MouseDashboard: React.FC<MouseDashboardProps> = ({ userId, pageUrl }) => {
  const [stats, setStats] = useState<MouseStatistics | null>(null);
  const [pattern, setPattern] = useState<MousePattern | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [rageAreas, setRageAreas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMouseData();
  }, [userId, pageUrl]);

  const fetchMouseData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/mouse/statistics/${userId}`,
        userId && `/api/analytics/mouse/pattern/${userId}`,
        pageUrl && `/api/analytics/mouse/heatmap/${encodeURIComponent(pageUrl)}`,
        `/api/analytics/mouse/rage-clicks${pageUrl ? `?page_url=${pageUrl}` : ''}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      let idx = 0;
      if (userId) {
        setStats(data[idx++]);
        setPattern(data[idx++]);
      }
      if (pageUrl) {
        setHeatmap(data[idx++].heatmap);
      }
      setRageAreas(data[idx].rage_areas);
    } catch (error) {
      console.error('Failed to fetch mouse data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading mouse analytics...</div>;

  return (
    <div className="mouse-dashboard">
      <h2>Mouse Interaction Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Total Clicks</h3>
              <div className="stat-value">{stats.totalClicks}</div>
              <span className="stat-label">
                {stats.totalSessions} sessions
              </span>
            </Card>
            
            <Card>
              <h3>Rage Click Rate</h3>
              <div className="stat-value">{stats.rageClickRate.toFixed(1)}%</div>
              <Badge variant={stats.rageClickRate > 5 ? 'danger' : 'success'}>
                {stats.rageClickRate > 5 ? 'High' : 'Normal'}
              </Badge>
            </Card>
            
            <Card>
              <h3>Dead Click Rate</h3>
              <div className="stat-value">{stats.deadClickRate.toFixed(1)}%</div>
              <Badge variant={stats.deadClickRate > 3 ? 'warning' : 'success'}>
                {stats.deadClickRate > 3 ? 'Issues' : 'Good'}
              </Badge>
            </Card>
            
            <Card>
              <h3>Avg Speed</h3>
              <div className="stat-value">
                {stats.avgSpeedPxPerSec.toFixed(0)} px/s
              </div>
              <span className="stat-label">
                {(stats.avgDistancePerSession / 1000).toFixed(1)}k px avg distance
              </span>
            </Card>
          </Grid>

          {/* Mouse Pattern */}
          {pattern && (
            <Card className="mt-4">
              <h3>User Mouse Pattern</h3>
              <div className="pattern-display">
                <Badge variant="primary" size="large">
                  {pattern.patternType}
                </Badge>
                <span className="confidence">
                  {(pattern.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              
              <Grid cols={4} gap={2} className="mt-3">
                <div>
                  <Progress 
                    value={pattern.indicators.clickPrecision} 
                    max={100}
                    label="Click Precision"
                  />
                </div>
                <div>
                  <Progress 
                    value={pattern.indicators.movementEfficiency} 
                    max={100}
                    label="Movement Efficiency"
                  />
                </div>
                <div>
                  <Progress 
                    value={pattern.indicators.rageClickFrequency} 
                    max={100}
                    variant="danger"
                    label="Rage Clicks"
                  />
                </div>
                <div>
                  <Progress 
                    value={pattern.indicators.hesitationFrequency} 
                    max={100}
                    variant="warning"
                    label="Hesitation"
                  />
                </div>
              </Grid>
            </Card>
          )}
        </>
      )}

      {/* Click Heatmap */}
      {heatmap.length > 0 && (
        <Card className="mt-4">
          <h3>Click Heatmap</h3>
          <HeatMap
            data={heatmap}
            width={1200}
            height={800}
          />
        </Card>
      )}

      {/* Rage Click Areas */}
      {rageAreas.length > 0 && (
        <Card className="mt-4">
          <h3>Rage Click Problem Areas</h3>
          <Table>
            <thead>
              <tr>
                <th>Page</th>
                <th>Element</th>
                <th>Rage Clicks</th>
                <th>Affected Users</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {rageAreas.map((area, idx) => (
                <tr key={idx}>
                  <td>{area.page_url}</td>
                  <td>
                    {area.element_type}
                    {area.element_id && ` #${area.element_id}`}
                  </td>
                  <td>{area.rage_click_count}</td>
                  <td>{area.affected_users}</td>
                  <td>
                    <Badge variant={
                      area.severity === 'critical' ? 'danger' :
                      area.severity === 'high' ? 'warning' : 'info'
                    }>
                      {area.severity}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic click tracking
2. Rage click detection
3. Heatmap generation
4. Hover tracking
5. Pattern detection

## Security Considerations
- No recording of sensitive data
- Anonymize click positions
- Respect privacy settings
- Rate limit event tracking
- Secure session management

## Performance Optimizations
- Batch mouse events
- Client-side aggregation
- Efficient heatmap queries
- Cache pattern detection
- Throttle event sending