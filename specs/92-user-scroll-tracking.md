# User Scroll Tracking Specification

## Overview
Track user scroll behavior to understand content engagement, reading patterns, and identify areas of interest or friction without invasive tracking.

## Database Schema

### Tables

```sql
-- Scroll events tracking
CREATE TABLE user_scroll_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    page_height INTEGER NOT NULL,
    viewport_height INTEGER NOT NULL,
    max_scroll_depth INTEGER NOT NULL,
    max_scroll_percentage DECIMAL(5, 2),
    scroll_direction VARCHAR(20), -- up, down, horizontal
    total_scroll_distance INTEGER,
    scroll_speed_avg DECIMAL(10, 2), -- pixels per second
    time_to_scroll_ms INTEGER,
    reached_bottom BOOLEAN DEFAULT false,
    bounce_scroll BOOLEAN DEFAULT false, -- Quick scroll and leave
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_scroll_events_user (user_id, created_at DESC),
    INDEX idx_scroll_events_page (page_url, created_at DESC),
    INDEX idx_scroll_events_depth (max_scroll_percentage)
);

-- Scroll milestones
CREATE TABLE scroll_milestones (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    milestone_percentage INTEGER NOT NULL, -- 25, 50, 75, 100
    reached_at TIMESTAMP WITH TIME ZONE NOT NULL,
    time_to_reach_ms INTEGER,
    pause_duration_ms INTEGER, -- Time spent at this depth
    content_element VARCHAR(200), -- Element at milestone
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_milestones_user (user_id, page_url),
    INDEX idx_milestones_percentage (milestone_percentage)
);

-- Daily scroll statistics
CREATE TABLE user_scroll_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_pages_scrolled INTEGER DEFAULT 0,
    avg_scroll_depth_percentage DECIMAL(5, 2),
    total_scroll_distance_px BIGINT DEFAULT 0,
    pages_reached_bottom INTEGER DEFAULT 0,
    bounce_scroll_count INTEGER DEFAULT 0,
    avg_time_to_bottom_ms INTEGER,
    most_scrolled_page VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_scroll_daily_stats_date (date DESC),
    INDEX idx_scroll_daily_stats_user (user_id, date DESC)
);

-- Content engagement zones
CREATE TABLE content_engagement_zones (
    id SERIAL PRIMARY KEY,
    page_url VARCHAR(500) NOT NULL,
    zone_start_percentage DECIMAL(5, 2),
    zone_end_percentage DECIMAL(5, 2),
    engagement_score DECIMAL(5, 2),
    avg_time_in_zone_ms INTEGER,
    users_reached INTEGER DEFAULT 0,
    users_engaged INTEGER DEFAULT 0,
    content_identifier VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_engagement_zones_page (page_url),
    INDEX idx_engagement_zones_score (engagement_score DESC)
);
```

## TypeScript Interfaces

```typescript
// Scroll event interface
interface ScrollEvent {
  id: string;
  userId: string;
  sessionId: string;
  pageUrl: string;
  pageHeight: number;
  viewportHeight: number;
  maxScrollDepth: number;
  maxScrollPercentage: number;
  scrollDirection: 'up' | 'down' | 'horizontal';
  totalScrollDistance: number;
  scrollSpeedAvg: number;
  timeToScrollMs: number;
  reachedBottom: boolean;
  bounceScroll: boolean;
  createdAt: Date;
}

// Scroll milestone
interface ScrollMilestone {
  userId: string;
  sessionId: string;
  pageUrl: string;
  milestonePercentage: 25 | 50 | 75 | 100;
  reachedAt: Date;
  timeToReachMs: number;
  pauseDurationMs: number;
  contentElement?: string;
}

// Scroll statistics
interface ScrollStatistics {
  totalPagesScrolled: number;
  avgScrollDepthPercentage: number;
  totalScrollDistancePx: number;
  pagesReachedBottom: number;
  bounceScrollCount: number;
  avgTimeToBottomMs: number;
  mostScrolledPage?: string;
  engagementScore: number;
}

// Content engagement zone
interface ContentEngagementZone {
  pageUrl: string;
  zoneStartPercentage: number;
  zoneEndPercentage: number;
  engagementScore: number;
  avgTimeInZoneMs: number;
  usersReached: number;
  usersEngaged: number;
  contentIdentifier?: string;
}

// Scroll behavior pattern
interface ScrollPattern {
  patternType: 'skimmer' | 'reader' | 'scanner' | 'searcher';
  confidence: number;
  characteristics: {
    avgScrollSpeed: number;
    avgDepth: number;
    pauseFrequency: number;
    backScrollFrequency: number;
  };
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import asyncpg

@dataclass
class ScrollAnalytics:
    """Analyze user scroll behavior and content engagement"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.milestone_thresholds = [25, 50, 75, 100]
    
    async def track_scroll_event(
        self,
        user_id: str,
        session_id: str,
        page_url: str,
        page_height: int,
        viewport_height: int,
        max_scroll_depth: int,
        scroll_direction: str = 'down',
        total_distance: Optional[int] = None,
        time_to_scroll: Optional[int] = None
    ) -> Dict:
        """Track a scroll event"""
        max_percentage = (max_scroll_depth / page_height * 100) if page_height > 0 else 0
        reached_bottom = max_percentage >= 95
        
        # Detect bounce scroll (quick scroll without engagement)
        bounce_scroll = (
            time_to_scroll and time_to_scroll < 3000 and 
            max_percentage < 30 and not reached_bottom
        )
        
        # Calculate average scroll speed
        scroll_speed = (
            total_distance / (time_to_scroll / 1000) 
            if total_distance and time_to_scroll and time_to_scroll > 0 
            else 0
        )
        
        query = """
            INSERT INTO user_scroll_events (
                user_id, session_id, page_url, page_height,
                viewport_height, max_scroll_depth, max_scroll_percentage,
                scroll_direction, total_scroll_distance, scroll_speed_avg,
                time_to_scroll_ms, reached_bottom, bounce_scroll
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            event_id = await conn.fetchval(
                query, user_id, session_id, page_url, page_height,
                viewport_height, max_scroll_depth, max_percentage,
                scroll_direction, total_distance, scroll_speed,
                time_to_scroll, reached_bottom, bounce_scroll
            )
            
            # Track milestones
            await self._track_milestones(
                conn, user_id, session_id, page_url, max_percentage
            )
            
            # Update engagement zones
            await self._update_engagement_zones(
                conn, page_url, max_percentage, time_to_scroll
            )
            
            # Update daily stats
            await self._update_daily_stats(conn, user_id, page_url, event_id)
        
        return {
            'event_id': event_id,
            'max_percentage': max_percentage,
            'reached_bottom': reached_bottom,
            'bounce_scroll': bounce_scroll
        }
    
    async def track_scroll_milestone(
        self,
        user_id: str,
        session_id: str,
        page_url: str,
        milestone: int,
        time_to_reach: int,
        pause_duration: Optional[int] = None,
        content_element: Optional[str] = None
    ):
        """Track when user reaches scroll milestone"""
        query = """
            INSERT INTO scroll_milestones (
                user_id, session_id, page_url, milestone_percentage,
                reached_at, time_to_reach_ms, pause_duration_ms,
                content_element
            ) VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, $5, $6, $7)
            ON CONFLICT DO NOTHING
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, user_id, session_id, page_url, milestone,
                time_to_reach, pause_duration, content_element
            )
    
    async def get_scroll_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user scroll statistics"""
        query = """
            WITH scroll_stats AS (
                SELECT 
                    COUNT(DISTINCT page_url) as pages_scrolled,
                    AVG(max_scroll_percentage) as avg_depth,
                    SUM(total_scroll_distance) as total_distance,
                    COUNT(*) FILTER (WHERE reached_bottom) as reached_bottom,
                    COUNT(*) FILTER (WHERE bounce_scroll) as bounce_count,
                    AVG(time_to_scroll_ms) FILTER (WHERE reached_bottom) as avg_time_to_bottom
                FROM user_scroll_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            top_page AS (
                SELECT page_url, COUNT(*) as scroll_count
                FROM user_scroll_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY page_url
                ORDER BY scroll_count DESC
                LIMIT 1
            )
            SELECT 
                s.*,
                t.page_url as most_scrolled
            FROM scroll_stats s
            LEFT JOIN top_page t ON true
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(
                row['avg_depth'] or 0,
                row['reached_bottom'] or 0,
                row['bounce_count'] or 0,
                row['pages_scrolled'] or 0
            )
            
            return {
                'total_pages_scrolled': row['pages_scrolled'] or 0,
                'avg_scroll_depth_percentage': row['avg_depth'] or 0,
                'total_scroll_distance_px': row['total_distance'] or 0,
                'pages_reached_bottom': row['reached_bottom'] or 0,
                'bounce_scroll_count': row['bounce_count'] or 0,
                'avg_time_to_bottom_ms': row['avg_time_to_bottom'] or 0,
                'most_scrolled_page': row['most_scrolled'],
                'engagement_score': engagement_score
            }
    
    async def detect_scroll_patterns(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user scroll behavior patterns"""
        query = """
            SELECT 
                AVG(scroll_speed_avg) as avg_speed,
                AVG(max_scroll_percentage) as avg_depth,
                COUNT(*) FILTER (WHERE scroll_direction = 'up') as up_scrolls,
                COUNT(*) as total_scrolls,
                STDDEV(max_scroll_percentage) as depth_variance,
                COUNT(DISTINCT page_url) as unique_pages
            FROM user_scroll_events
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow(query % days, user_id)
            
            if not stats or not stats['total_scrolls']:
                return {'pattern_type': 'unknown', 'confidence': 0}
            
            # Analyze pause behavior
            pause_query = """
                SELECT 
                    AVG(pause_duration_ms) as avg_pause,
                    COUNT(*) as pause_count
                FROM scroll_milestones
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND pause_duration_ms > 1000
            """
            
            pauses = await conn.fetchrow(pause_query % days, user_id)
            
            # Determine pattern type
            pattern = self._determine_scroll_pattern(
                stats['avg_speed'] or 0,
                stats['avg_depth'] or 0,
                stats['up_scrolls'] or 0,
                stats['total_scrolls'] or 1,
                pauses['avg_pause'] or 0,
                pauses['pause_count'] or 0
            )
            
            return pattern
    
    async def get_content_engagement_zones(
        self,
        page_url: str
    ) -> List[Dict]:
        """Get engagement zones for a page"""
        query = """
            SELECT 
                zone_start_percentage,
                zone_end_percentage,
                engagement_score,
                avg_time_in_zone_ms,
                users_reached,
                users_engaged,
                content_identifier
            FROM content_engagement_zones
            WHERE page_url = $1
            ORDER BY zone_start_percentage
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, page_url)
            
            return [
                {
                    'zone_start': row['zone_start_percentage'],
                    'zone_end': row['zone_end_percentage'],
                    'engagement_score': row['engagement_score'],
                    'avg_time_in_zone': row['avg_time_in_zone_ms'],
                    'users_reached': row['users_reached'],
                    'users_engaged': row['users_engaged'],
                    'content': row['content_identifier'],
                    'engagement_level': self._get_engagement_level(row['engagement_score'])
                }
                for row in rows
            ]
    
    async def get_scroll_depth_distribution(
        self,
        page_url: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get scroll depth distribution"""
        query = """
            WITH depth_buckets AS (
                SELECT 
                    CASE 
                        WHEN max_scroll_percentage < 25 THEN '0-25%'
                        WHEN max_scroll_percentage < 50 THEN '25-50%'
                        WHEN max_scroll_percentage < 75 THEN '50-75%'
                        WHEN max_scroll_percentage < 100 THEN '75-99%'
                        ELSE '100%'
                    END as depth_bucket,
                    COUNT(*) as user_count,
                    AVG(time_to_scroll_ms) as avg_time
                FROM user_scroll_events
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY depth_bucket
            )
            SELECT * FROM depth_buckets
            ORDER BY 
                CASE depth_bucket
                    WHEN '0-25%%' THEN 1
                    WHEN '25-50%%' THEN 2
                    WHEN '50-75%%' THEN 3
                    WHEN '75-99%%' THEN 4
                    ELSE 5
                END
        """
        
        page_filter = "AND page_url = $1" if page_url else ""
        
        async with self.db.acquire() as conn:
            if page_url:
                rows = await conn.fetch(query % (days, page_filter), page_url)
            else:
                rows = await conn.fetch(query % (days, page_filter))
            
            total = sum(row['user_count'] for row in rows)
            
            return {
                'distribution': [
                    {
                        'depth_range': row['depth_bucket'],
                        'user_count': row['user_count'],
                        'percentage': (row['user_count'] / total * 100) if total > 0 else 0,
                        'avg_time_ms': row['avg_time']
                    }
                    for row in rows
                ]
            }
    
    async def get_milestone_funnel(
        self,
        page_url: str,
        days: int = 30
    ) -> List[Dict]:
        """Get scroll milestone funnel for a page"""
        query = """
            WITH milestone_stats AS (
                SELECT 
                    milestone_percentage,
                    COUNT(DISTINCT user_id) as users_reached,
                    AVG(time_to_reach_ms) as avg_time_to_reach,
                    AVG(pause_duration_ms) as avg_pause
                FROM scroll_milestones
                WHERE page_url = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY milestone_percentage
            ),
            total_users AS (
                SELECT COUNT(DISTINCT user_id) as total
                FROM user_scroll_events
                WHERE page_url = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            )
            SELECT 
                m.*,
                t.total,
                (m.users_reached::float / t.total * 100) as reach_percentage
            FROM milestone_stats m
            CROSS JOIN total_users t
            ORDER BY m.milestone_percentage
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % (days, days), page_url)
            
            return [
                {
                    'milestone': row['milestone_percentage'],
                    'users_reached': row['users_reached'],
                    'reach_percentage': row['reach_percentage'],
                    'avg_time_to_reach': row['avg_time_to_reach'],
                    'avg_pause_duration': row['avg_pause'],
                    'drop_off': self._calculate_dropoff(rows, idx)
                }
                for idx, row in enumerate(rows)
            ]
    
    async def identify_problem_areas(
        self,
        page_url: str,
        threshold: float = 30.0
    ) -> List[Dict]:
        """Identify areas where users stop scrolling"""
        query = """
            WITH stop_points AS (
                SELECT 
                    FLOOR(max_scroll_percentage / 10) * 10 as depth_range,
                    COUNT(*) as stop_count,
                    AVG(max_scroll_percentage) as avg_stop_point
                FROM user_scroll_events
                WHERE page_url = $1
                    AND NOT reached_bottom
                    AND max_scroll_percentage < $2
                GROUP BY FLOOR(max_scroll_percentage / 10) * 10
                HAVING COUNT(*) > 5
            )
            SELECT * FROM stop_points
            ORDER BY stop_count DESC
            LIMIT 5
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, page_url, threshold)
            
            return [
                {
                    'depth_range': f"{row['depth_range']}-{row['depth_range'] + 10}%",
                    'stop_count': row['stop_count'],
                    'avg_stop_point': row['avg_stop_point'],
                    'severity': self._get_problem_severity(row['stop_count'])
                }
                for row in rows
            ]
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_pages_scrolled': 0,
            'avg_scroll_depth_percentage': 0,
            'total_scroll_distance_px': 0,
            'pages_reached_bottom': 0,
            'bounce_scroll_count': 0,
            'avg_time_to_bottom_ms': 0,
            'most_scrolled_page': None,
            'engagement_score': 0
        }
    
    def _calculate_engagement_score(
        self,
        avg_depth: float,
        reached_bottom: int,
        bounces: int,
        pages: int
    ) -> float:
        """Calculate scroll engagement score"""
        score = 0.0
        
        # Depth contributes up to 40 points
        score += min(avg_depth * 0.4, 40)
        
        # Reaching bottom contributes up to 30 points
        if pages > 0:
            bottom_rate = reached_bottom / pages
            score += bottom_rate * 30
        
        # Low bounce rate contributes up to 30 points
        if pages > 0:
            bounce_rate = bounces / pages
            score += (1 - bounce_rate) * 30
        
        return min(score, 100)
    
    def _determine_scroll_pattern(
        self,
        avg_speed: float,
        avg_depth: float,
        up_scrolls: int,
        total_scrolls: int,
        avg_pause: float,
        pause_count: int
    ) -> Dict:
        """Determine scroll behavior pattern"""
        back_scroll_ratio = up_scrolls / total_scrolls if total_scrolls > 0 else 0
        pause_frequency = pause_count / total_scrolls if total_scrolls > 0 else 0
        
        # Reader: slow speed, high depth, many pauses
        if avg_speed < 500 and avg_depth > 70 and pause_frequency > 0.3:
            return {
                'pattern_type': 'reader',
                'confidence': 0.8,
                'characteristics': {
                    'avg_scroll_speed': avg_speed,
                    'avg_depth': avg_depth,
                    'pause_frequency': pause_frequency,
                    'back_scroll_frequency': back_scroll_ratio
                }
            }
        
        # Skimmer: fast speed, moderate depth
        elif avg_speed > 1000 and 40 < avg_depth < 70:
            return {
                'pattern_type': 'skimmer',
                'confidence': 0.7,
                'characteristics': {
                    'avg_scroll_speed': avg_speed,
                    'avg_depth': avg_depth,
                    'pause_frequency': pause_frequency,
                    'back_scroll_frequency': back_scroll_ratio
                }
            }
        
        # Scanner: moderate speed, low depth, few pauses
        elif 500 < avg_speed < 1000 and avg_depth < 50:
            return {
                'pattern_type': 'scanner',
                'confidence': 0.7,
                'characteristics': {
                    'avg_scroll_speed': avg_speed,
                    'avg_depth': avg_depth,
                    'pause_frequency': pause_frequency,
                    'back_scroll_frequency': back_scroll_ratio
                }
            }
        
        # Searcher: high back-scroll ratio
        elif back_scroll_ratio > 0.2:
            return {
                'pattern_type': 'searcher',
                'confidence': 0.6,
                'characteristics': {
                    'avg_scroll_speed': avg_speed,
                    'avg_depth': avg_depth,
                    'pause_frequency': pause_frequency,
                    'back_scroll_frequency': back_scroll_ratio
                }
            }
        
        else:
            return {
                'pattern_type': 'mixed',
                'confidence': 0.5,
                'characteristics': {
                    'avg_scroll_speed': avg_speed,
                    'avg_depth': avg_depth,
                    'pause_frequency': pause_frequency,
                    'back_scroll_frequency': back_scroll_ratio
                }
            }
    
    def _get_engagement_level(self, score: float) -> str:
        """Get engagement level from score"""
        if score >= 80:
            return 'very_high'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        elif score >= 20:
            return 'low'
        else:
            return 'very_low'
    
    def _calculate_dropoff(self, rows: List, index: int) -> float:
        """Calculate dropoff rate between milestones"""
        if index == 0 or index >= len(rows):
            return 0.0
        
        prev_users = rows[index - 1]['users_reached']
        curr_users = rows[index]['users_reached']
        
        if prev_users == 0:
            return 0.0
        
        return ((prev_users - curr_users) / prev_users) * 100
    
    def _get_problem_severity(self, stop_count: int) -> str:
        """Determine problem severity based on stop count"""
        if stop_count > 100:
            return 'critical'
        elif stop_count > 50:
            return 'high'
        elif stop_count > 20:
            return 'medium'
        else:
            return 'low'
    
    async def _track_milestones(
        self,
        conn,
        user_id: str,
        session_id: str,
        page_url: str,
        max_percentage: float
    ):
        """Track milestone achievements"""
        # Implementation for milestone tracking
        pass
    
    async def _update_engagement_zones(
        self,
        conn,
        page_url: str,
        max_percentage: float,
        time_spent: Optional[int]
    ):
        """Update content engagement zones"""
        # Implementation for zone updates
        pass
    
    async def _update_daily_stats(
        self,
        conn,
        user_id: str,
        page_url: str,
        event_id: int
    ):
        """Update daily scroll statistics"""
        # Implementation for daily stats
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/scroll", tags=["scroll-analytics"])

@router.post("/track")
async def track_scroll_event(
    user_id: str,
    session_id: str,
    page_url: str,
    page_height: int,
    viewport_height: int,
    max_scroll_depth: int,
    scroll_direction: str = "down",
    total_distance: Optional[int] = None,
    time_to_scroll: Optional[int] = None
):
    """Track scroll event"""
    analytics = ScrollAnalytics(db_pool)
    result = await analytics.track_scroll_event(
        user_id, session_id, page_url, page_height,
        viewport_height, max_scroll_depth, scroll_direction,
        total_distance, time_to_scroll
    )
    return result

@router.post("/milestone")
async def track_scroll_milestone(
    user_id: str,
    session_id: str,
    page_url: str,
    milestone: int,
    time_to_reach: int,
    pause_duration: Optional[int] = None,
    content_element: Optional[str] = None
):
    """Track scroll milestone"""
    analytics = ScrollAnalytics(db_pool)
    await analytics.track_scroll_milestone(
        user_id, session_id, page_url, milestone,
        time_to_reach, pause_duration, content_element
    )
    return {"status": "milestone_tracked"}

@router.get("/statistics/{user_id}")
async def get_scroll_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get scroll statistics"""
    analytics = ScrollAnalytics(db_pool)
    stats = await analytics.get_scroll_statistics(user_id, days)
    return stats

@router.get("/patterns/{user_id}")
async def detect_scroll_patterns(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect scroll patterns"""
    analytics = ScrollAnalytics(db_pool)
    pattern = await analytics.detect_scroll_patterns(user_id, days)
    return pattern

@router.get("/engagement-zones/{page_url:path}")
async def get_content_engagement_zones(page_url: str):
    """Get content engagement zones"""
    analytics = ScrollAnalytics(db_pool)
    zones = await analytics.get_content_engagement_zones(page_url)
    return {"zones": zones}

@router.get("/depth-distribution")
async def get_scroll_depth_distribution(
    page_url: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get scroll depth distribution"""
    analytics = ScrollAnalytics(db_pool)
    distribution = await analytics.get_scroll_depth_distribution(page_url, days)
    return distribution

@router.get("/milestone-funnel/{page_url:path}")
async def get_milestone_funnel(
    page_url: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get milestone funnel"""
    analytics = ScrollAnalytics(db_pool)
    funnel = await analytics.get_milestone_funnel(page_url, days)
    return {"funnel": funnel}

@router.get("/problem-areas/{page_url:path}")
async def identify_problem_areas(
    page_url: str,
    threshold: float = Query(30.0, ge=0, le=100)
):
    """Identify problem areas"""
    analytics = ScrollAnalytics(db_pool)
    problems = await analytics.identify_problem_areas(page_url, threshold)
    return {"problem_areas": problems}
```

## React Dashboard Components

```tsx
// Scroll Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, FunnelChart, HeatMap, BarChart } from '@/components/ui';

interface ScrollDashboardProps {
  userId?: string;
  pageUrl?: string;
}

export const ScrollDashboard: React.FC<ScrollDashboardProps> = ({ userId, pageUrl }) => {
  const [stats, setStats] = useState<ScrollStatistics | null>(null);
  const [pattern, setPattern] = useState<ScrollPattern | null>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [funnel, setFunnel] = useState<any[]>([]);
  const [zones, setZones] = useState<ContentEngagementZone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScrollData();
  }, [userId, pageUrl]);

  const fetchScrollData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/scroll/statistics/${userId}`,
        userId && `/api/analytics/scroll/patterns/${userId}`,
        `/api/analytics/scroll/depth-distribution${pageUrl ? `?page_url=${pageUrl}` : ''}`,
        pageUrl && `/api/analytics/scroll/milestone-funnel/${encodeURIComponent(pageUrl)}`,
        pageUrl && `/api/analytics/scroll/engagement-zones/${encodeURIComponent(pageUrl)}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      let dataIndex = 0;
      if (userId) {
        setStats(data[dataIndex++]);
        setPattern(data[dataIndex++]);
      }
      setDistribution(data[dataIndex++]);
      if (pageUrl) {
        setFunnel(data[dataIndex++].funnel);
        setZones(data[dataIndex++].zones);
      }
    } catch (error) {
      console.error('Failed to fetch scroll data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading scroll analytics...</div>;

  return (
    <div className="scroll-dashboard">
      <h2>Scroll Behavior Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Pages Scrolled</h3>
              <div className="stat-value">{stats.totalPagesScrolled}</div>
              <span className="stat-label">
                {stats.mostScrolledPage || 'N/A'}
              </span>
            </Card>
            
            <Card>
              <h3>Avg Scroll Depth</h3>
              <div className="stat-value">
                {stats.avgScrollDepthPercentage.toFixed(1)}%
              </div>
              <Progress 
                value={stats.avgScrollDepthPercentage} 
                max={100}
                variant={stats.avgScrollDepthPercentage > 50 ? 'success' : 'warning'}
              />
            </Card>
            
            <Card>
              <h3>Engagement Score</h3>
              <div className="stat-value">{stats.engagementScore.toFixed(0)}</div>
              <Badge variant={stats.engagementScore > 70 ? 'success' : 'warning'}>
                {stats.engagementScore > 70 ? 'High' : 'Medium'}
              </Badge>
            </Card>
            
            <Card>
              <h3>Reached Bottom</h3>
              <div className="stat-value">{stats.pagesReachedBottom}</div>
              <span className="stat-label">
                {stats.bounceScrollCount} bounces
              </span>
            </Card>
          </Grid>

          {/* Scroll Pattern */}
          {pattern && (
            <Card className="mt-4">
              <h3>Scroll Behavior Pattern</h3>
              <div className="pattern-display">
                <Badge variant="primary" size="large">
                  {pattern.patternType}
                </Badge>
                <span className="confidence">
                  {(pattern.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              
              <Grid cols={4} gap={2} className="mt-3">
                <div className="characteristic">
                  <span>Avg Speed</span>
                  <strong>{pattern.characteristics.avgScrollSpeed.toFixed(0)} px/s</strong>
                </div>
                <div className="characteristic">
                  <span>Avg Depth</span>
                  <strong>{pattern.characteristics.avgDepth.toFixed(1)}%</strong>
                </div>
                <div className="characteristic">
                  <span>Pause Frequency</span>
                  <strong>{(pattern.characteristics.pauseFrequency * 100).toFixed(0)}%</strong>
                </div>
                <div className="characteristic">
                  <span>Back Scroll</span>
                  <strong>{(pattern.characteristics.backScrollFrequency * 100).toFixed(0)}%</strong>
                </div>
              </Grid>
            </Card>
          )}
        </>
      )}

      {/* Scroll Depth Distribution */}
      {distribution && (
        <Card className="mt-4">
          <h3>Scroll Depth Distribution</h3>
          <BarChart
            data={distribution.distribution}
            xKey="depth_range"
            yKey="user_count"
            height={300}
          />
        </Card>
      )}

      {/* Milestone Funnel */}
      {funnel.length > 0 && (
        <Card className="mt-4">
          <h3>Scroll Milestone Funnel</h3>
          <FunnelChart
            data={funnel.map(m => ({
              name: `${m.milestone}%`,
              value: m.users_reached,
              percentage: m.reach_percentage,
              dropoff: m.drop_off
            }))}
            height={400}
          />
        </Card>
      )}

      {/* Engagement Zones */}
      {zones.length > 0 && (
        <Card className="mt-4">
          <h3>Content Engagement Zones</h3>
          <div className="zones-visualization">
            {zones.map((zone, idx) => (
              <div key={idx} className="zone-bar">
                <div 
                  className={`zone-indicator ${zone.engagement_level}`}
                  style={{
                    left: `${zone.zoneStart}%`,
                    width: `${zone.zoneEnd - zone.zoneStart}%`
                  }}
                >
                  <span className="zone-score">
                    {zone.engagementScore.toFixed(0)}
                  </span>
                </div>
                <div className="zone-info">
                  <span>{zone.content}</span>
                  <Badge>{zone.usersEngaged} engaged</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic scroll event tracking
2. Milestone detection
3. Depth distribution analysis
4. Pattern recognition
5. Problem area identification

## Security Considerations
- No content scraping
- Respect privacy settings
- Anonymous aggregation
- Secure session handling
- Rate limiting for events

## Performance Optimizations
- Debounce scroll events
- Batch event updates
- Client-side aggregation
- Efficient milestone queries
- Cache engagement zones