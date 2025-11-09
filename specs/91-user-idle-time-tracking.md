# User Idle Time Tracking Specification

## Overview
Track user idle time and activity patterns to understand engagement levels, optimal timing for notifications, and identify inactive users without intrusive monitoring.

## Database Schema

### Tables

```sql
-- User activity sessions
CREATE TABLE user_activity_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    total_duration_seconds INTEGER,
    active_duration_seconds INTEGER,
    idle_duration_seconds INTEGER,
    idle_periods INTEGER DEFAULT 0,
    longest_idle_seconds INTEGER DEFAULT 0,
    activity_score DECIMAL(5, 2), -- 0-100 score
    device_type VARCHAR(50),
    browser VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_activity_sessions_user (user_id, start_time DESC),
    INDEX idx_activity_sessions_active (active_duration_seconds)
);

-- Idle events tracking
CREATE TABLE user_idle_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    idle_start TIMESTAMP WITH TIME ZONE NOT NULL,
    idle_end TIMESTAMP WITH TIME ZONE,
    idle_duration_seconds INTEGER,
    idle_reason VARCHAR(50), -- no_interaction, tab_hidden, window_blur
    activity_before VARCHAR(100), -- Last activity before idle
    activity_after VARCHAR(100), -- First activity after idle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_idle_events_user (user_id, idle_start DESC),
    INDEX idx_idle_events_session (session_id),
    INDEX idx_idle_events_duration (idle_duration_seconds)
);

-- Daily activity patterns
CREATE TABLE user_activity_daily_patterns (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_sessions INTEGER DEFAULT 0,
    total_active_minutes INTEGER DEFAULT 0,
    total_idle_minutes INTEGER DEFAULT 0,
    avg_session_duration_minutes INTEGER,
    peak_activity_hour INTEGER,
    longest_active_streak_minutes INTEGER,
    longest_idle_period_minutes INTEGER,
    engagement_score DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_activity_patterns_date (date DESC),
    INDEX idx_activity_patterns_user (user_id, date DESC)
);

-- Idle thresholds configuration
CREATE TABLE idle_thresholds (
    id SERIAL PRIMARY KEY,
    threshold_name VARCHAR(100) UNIQUE NOT NULL,
    idle_timeout_seconds INTEGER NOT NULL,
    warning_timeout_seconds INTEGER,
    auto_logout_seconds INTEGER,
    notification_before_logout BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    applies_to_roles TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## TypeScript Interfaces

```typescript
// Activity session interface
interface ActivitySession {
  id: string;
  userId: string;
  sessionId: string;
  startTime: Date;
  endTime?: Date;
  totalDurationSeconds: number;
  activeDurationSeconds: number;
  idleDurationSeconds: number;
  idlePeriods: number;
  longestIdleSeconds: number;
  activityScore: number;
  deviceType?: string;
  browser?: string;
}

// Idle event interface
interface IdleEvent {
  id: string;
  userId: string;
  sessionId: string;
  idleStart: Date;
  idleEnd?: Date;
  idleDurationSeconds?: number;
  idleReason: 'no_interaction' | 'tab_hidden' | 'window_blur';
  activityBefore?: string;
  activityAfter?: string;
}

// Activity statistics
interface ActivityStatistics {
  totalSessions: number;
  totalActiveMinutes: number;
  totalIdleMinutes: number;
  avgSessionDuration: number;
  activePercentage: number;
  idlePercentage: number;
  engagementScore: number;
  peakActivityHours: number[];
  idlePatterns: IdlePattern[];
}

// Idle pattern
interface IdlePattern {
  patternType: 'regular_break' | 'long_idle' | 'frequent_idle' | 'end_of_session';
  frequency: number;
  avgDuration: number;
  timeOfDay?: number[];
  likelihood: number;
}

// Engagement metrics
interface EngagementMetrics {
  dailyActiveTime: number;
  weeklyActiveTime: number;
  monthlyActiveTime: number;
  consistencyScore: number;
  activityTrend: 'increasing' | 'stable' | 'decreasing';
  riskOfChurn: number;
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
class IdleTimeAnalytics:
    """Analyze user idle time and activity patterns"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.default_idle_threshold = 300  # 5 minutes
    
    async def start_activity_session(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        browser: Optional[str] = None
    ) -> str:
        """Start a new activity session"""
        query = """
            INSERT INTO user_activity_sessions (
                user_id, start_time, device_type, browser
            ) VALUES ($1, CURRENT_TIMESTAMP, $2, $3)
            RETURNING session_id
        """
        
        async with self.db.acquire() as conn:
            session_id = await conn.fetchval(query, user_id, device_type, browser)
        
        return session_id
    
    async def track_idle_event(
        self,
        user_id: str,
        session_id: str,
        idle_start: datetime,
        idle_reason: str = 'no_interaction',
        activity_before: Optional[str] = None
    ) -> int:
        """Track an idle event"""
        query = """
            INSERT INTO user_idle_events (
                user_id, session_id, idle_start, idle_reason, activity_before
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            event_id = await conn.fetchval(
                query, user_id, session_id, idle_start, idle_reason, activity_before
            )
        
        return event_id
    
    async def end_idle_event(
        self,
        event_id: int,
        activity_after: Optional[str] = None
    ):
        """End an idle event"""
        query = """
            UPDATE user_idle_events
            SET idle_end = CURRENT_TIMESTAMP,
                idle_duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - idle_start)),
                activity_after = $2
            WHERE id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, event_id, activity_after)
    
    async def end_activity_session(
        self,
        session_id: str
    ):
        """End an activity session and calculate metrics"""
        query = """
            WITH session_metrics AS (
                SELECT 
                    start_time,
                    CURRENT_TIMESTAMP as end_time,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time)) as total_duration,
                    COUNT(ie.id) as idle_periods,
                    COALESCE(SUM(ie.idle_duration_seconds), 0) as total_idle,
                    COALESCE(MAX(ie.idle_duration_seconds), 0) as longest_idle
                FROM user_activity_sessions s
                LEFT JOIN user_idle_events ie ON s.session_id = ie.session_id
                WHERE s.session_id = $1
                GROUP BY s.session_id, s.start_time
            )
            UPDATE user_activity_sessions
            SET end_time = sm.end_time,
                total_duration_seconds = sm.total_duration,
                idle_duration_seconds = sm.total_idle,
                active_duration_seconds = sm.total_duration - sm.total_idle,
                idle_periods = sm.idle_periods,
                longest_idle_seconds = sm.longest_idle,
                activity_score = CASE 
                    WHEN sm.total_duration > 0 
                    THEN ((sm.total_duration - sm.total_idle)::float / sm.total_duration) * 100
                    ELSE 0
                END
            FROM session_metrics sm
            WHERE session_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, session_id)
            
            # Update daily patterns
            await self._update_daily_patterns(conn, session_id)
    
    async def get_activity_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user activity statistics"""
        query = """
            WITH activity_stats AS (
                SELECT 
                    COUNT(DISTINCT session_id) as total_sessions,
                    SUM(active_duration_seconds) / 60 as total_active_minutes,
                    SUM(idle_duration_seconds) / 60 as total_idle_minutes,
                    AVG(total_duration_seconds) / 60 as avg_session_duration,
                    AVG(activity_score) as avg_activity_score
                FROM user_activity_sessions
                WHERE user_id = $1
                    AND start_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            peak_hours AS (
                SELECT 
                    EXTRACT(HOUR FROM start_time) as hour,
                    SUM(active_duration_seconds) as active_time
                FROM user_activity_sessions
                WHERE user_id = $1
                    AND start_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM start_time)
                ORDER BY active_time DESC
                LIMIT 3
            )
            SELECT 
                a.*,
                array_agg(p.hour ORDER BY p.active_time DESC) as peak_hours
            FROM activity_stats a
            CROSS JOIN peak_hours p
            GROUP BY a.total_sessions, a.total_active_minutes, 
                     a.total_idle_minutes, a.avg_session_duration, 
                     a.avg_activity_score
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            total_time = (row['total_active_minutes'] or 0) + (row['total_idle_minutes'] or 0)
            
            # Detect idle patterns
            idle_patterns = await self._detect_idle_patterns(conn, user_id, days)
            
            return {
                'total_sessions': row['total_sessions'] or 0,
                'total_active_minutes': row['total_active_minutes'] or 0,
                'total_idle_minutes': row['total_idle_minutes'] or 0,
                'avg_session_duration': row['avg_session_duration'] or 0,
                'active_percentage': (
                    (row['total_active_minutes'] / total_time * 100) 
                    if total_time > 0 else 0
                ),
                'idle_percentage': (
                    (row['total_idle_minutes'] / total_time * 100) 
                    if total_time > 0 else 0
                ),
                'engagement_score': row['avg_activity_score'] or 0,
                'peak_activity_hours': row['peak_hours'] or [],
                'idle_patterns': idle_patterns
            }
    
    async def detect_idle_patterns(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Detect user idle patterns"""
        patterns = []
        
        # Regular break pattern
        regular_breaks = await self._detect_regular_breaks(user_id, days)
        if regular_breaks:
            patterns.append(regular_breaks)
        
        # Long idle pattern
        long_idles = await self._detect_long_idles(user_id, days)
        if long_idles:
            patterns.append(long_idles)
        
        # Frequent idle pattern
        frequent_idles = await self._detect_frequent_idles(user_id, days)
        if frequent_idles:
            patterns.append(frequent_idles)
        
        # End of session pattern
        end_session = await self._detect_end_session_pattern(user_id, days)
        if end_session:
            patterns.append(end_session)
        
        return patterns
    
    async def get_engagement_metrics(
        self,
        user_id: str
    ) -> Dict:
        """Calculate user engagement metrics"""
        query = """
            WITH time_metrics AS (
                SELECT 
                    SUM(CASE 
                        WHEN start_time >= CURRENT_TIMESTAMP - INTERVAL '1 day'
                        THEN active_duration_seconds / 60
                        ELSE 0
                    END) as daily_active,
                    SUM(CASE 
                        WHEN start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                        THEN active_duration_seconds / 60
                        ELSE 0
                    END) as weekly_active,
                    SUM(CASE 
                        WHEN start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                        THEN active_duration_seconds / 60
                        ELSE 0
                    END) as monthly_active
                FROM user_activity_sessions
                WHERE user_id = $1
            ),
            consistency AS (
                SELECT 
                    COUNT(DISTINCT DATE(start_time)) as active_days
                FROM user_activity_sessions
                WHERE user_id = $1
                    AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            ),
            trend AS (
                SELECT 
                    SUM(CASE 
                        WHEN start_time >= CURRENT_TIMESTAMP - INTERVAL '15 days'
                        THEN active_duration_seconds
                        ELSE 0
                    END) as recent_active,
                    SUM(CASE 
                        WHEN start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                            AND start_time < CURRENT_TIMESTAMP - INTERVAL '15 days'
                        THEN active_duration_seconds
                        ELSE 0
                    END) as previous_active
                FROM user_activity_sessions
                WHERE user_id = $1
            )
            SELECT 
                t.daily_active,
                t.weekly_active,
                t.monthly_active,
                c.active_days,
                tr.recent_active,
                tr.previous_active
            FROM time_metrics t
            CROSS JOIN consistency c
            CROSS JOIN trend tr
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            # Calculate consistency score (active days / 30)
            consistency_score = (row['active_days'] / 30 * 100) if row else 0
            
            # Determine activity trend
            if row and row['recent_active'] and row['previous_active']:
                ratio = row['recent_active'] / row['previous_active']
                if ratio > 1.1:
                    trend = 'increasing'
                elif ratio < 0.9:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Calculate churn risk (0-100)
            churn_risk = self._calculate_churn_risk(
                row['daily_active'] if row else 0,
                row['weekly_active'] if row else 0,
                consistency_score,
                trend
            )
            
            return {
                'daily_active_time': row['daily_active'] if row else 0,
                'weekly_active_time': row['weekly_active'] if row else 0,
                'monthly_active_time': row['monthly_active'] if row else 0,
                'consistency_score': consistency_score,
                'activity_trend': trend,
                'risk_of_churn': churn_risk
            }
    
    async def get_idle_time_distribution(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get idle time distribution"""
        query = """
            WITH idle_buckets AS (
                SELECT 
                    CASE 
                        WHEN idle_duration_seconds < 60 THEN '< 1 min'
                        WHEN idle_duration_seconds < 300 THEN '1-5 min'
                        WHEN idle_duration_seconds < 600 THEN '5-10 min'
                        WHEN idle_duration_seconds < 1800 THEN '10-30 min'
                        WHEN idle_duration_seconds < 3600 THEN '30-60 min'
                        ELSE '> 1 hour'
                    END as duration_bucket,
                    COUNT(*) as count,
                    AVG(idle_duration_seconds) as avg_duration
                FROM user_idle_events
                WHERE idle_duration_seconds IS NOT NULL
                    AND idle_start >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY duration_bucket
            )
            SELECT * FROM idle_buckets
            ORDER BY 
                CASE duration_bucket
                    WHEN '< 1 min' THEN 1
                    WHEN '1-5 min' THEN 2
                    WHEN '5-10 min' THEN 3
                    WHEN '10-30 min' THEN 4
                    WHEN '30-60 min' THEN 5
                    ELSE 6
                END
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                rows = await conn.fetch(query % (days, user_filter), user_id)
            else:
                rows = await conn.fetch(query % (days, user_filter))
            
            return {
                'distribution': [
                    {
                        'bucket': row['duration_bucket'],
                        'count': row['count'],
                        'avg_duration': row['avg_duration'],
                        'percentage': 0  # Will be calculated
                    }
                    for row in rows
                ]
            }
    
    async def get_activity_heatmap(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict]:
        """Get activity heatmap data"""
        query = """
            WITH hourly_activity AS (
                SELECT 
                    EXTRACT(DOW FROM start_time) as day_of_week,
                    EXTRACT(HOUR FROM start_time) as hour,
                    SUM(active_duration_seconds) / 60 as active_minutes
                FROM user_activity_sessions
                WHERE user_id = $1
                    AND start_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM start_time), EXTRACT(HOUR FROM start_time)
            )
            SELECT * FROM hourly_activity
            ORDER BY day_of_week, hour
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days, user_id)
            
            return [
                {
                    'day': self._day_name(row['day_of_week']),
                    'hour': int(row['hour']),
                    'value': row['active_minutes'],
                    'intensity': self._calculate_intensity(row['active_minutes'])
                }
                for row in rows
            ]
    
    async def check_idle_timeout(
        self,
        user_id: str,
        last_activity: datetime
    ) -> Dict:
        """Check if user should be logged out due to idle timeout"""
        query = """
            SELECT 
                idle_timeout_seconds,
                warning_timeout_seconds,
                auto_logout_seconds,
                notification_before_logout
            FROM idle_thresholds
            WHERE is_active = true
            ORDER BY idle_timeout_seconds ASC
            LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            threshold = await conn.fetchrow(query)
            
            if not threshold:
                return {'should_logout': False}
            
            idle_duration = (datetime.utcnow() - last_activity).total_seconds()
            
            return {
                'should_logout': idle_duration >= threshold['auto_logout_seconds'],
                'should_warn': idle_duration >= threshold['warning_timeout_seconds'],
                'is_idle': idle_duration >= threshold['idle_timeout_seconds'],
                'idle_duration': idle_duration,
                'time_until_logout': max(0, threshold['auto_logout_seconds'] - idle_duration),
                'notification_before_logout': threshold['notification_before_logout']
            }
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_sessions': 0,
            'total_active_minutes': 0,
            'total_idle_minutes': 0,
            'avg_session_duration': 0,
            'active_percentage': 0,
            'idle_percentage': 0,
            'engagement_score': 0,
            'peak_activity_hours': [],
            'idle_patterns': []
        }
    
    def _calculate_churn_risk(
        self,
        daily_active: float,
        weekly_active: float,
        consistency: float,
        trend: str
    ) -> float:
        """Calculate risk of user churn"""
        risk = 0.0
        
        # Low daily activity increases risk
        if daily_active < 10:  # Less than 10 minutes
            risk += 30
        elif daily_active < 30:
            risk += 15
        
        # Low weekly activity increases risk
        if weekly_active < 60:  # Less than 1 hour per week
            risk += 25
        elif weekly_active < 180:
            risk += 10
        
        # Low consistency increases risk
        if consistency < 20:  # Active less than 20% of days
            risk += 25
        elif consistency < 50:
            risk += 10
        
        # Decreasing trend increases risk
        if trend == 'decreasing':
            risk += 20
        elif trend == 'stable':
            risk += 5
        
        return min(risk, 100)
    
    def _day_name(self, day_num: int) -> str:
        """Convert day number to name"""
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        return days[int(day_num)]
    
    def _calculate_intensity(self, minutes: float) -> str:
        """Calculate activity intensity level"""
        if minutes < 5:
            return 'very_low'
        elif minutes < 15:
            return 'low'
        elif minutes < 30:
            return 'medium'
        elif minutes < 60:
            return 'high'
        else:
            return 'very_high'
    
    async def _detect_idle_patterns(
        self,
        conn,
        user_id: str,
        days: int
    ) -> List[Dict]:
        """Detect various idle patterns"""
        # Implementation for pattern detection
        return []
    
    async def _detect_regular_breaks(self, user_id: str, days: int) -> Optional[Dict]:
        """Detect regular break pattern"""
        # Implementation
        pass
    
    async def _detect_long_idles(self, user_id: str, days: int) -> Optional[Dict]:
        """Detect long idle pattern"""
        # Implementation
        pass
    
    async def _detect_frequent_idles(self, user_id: str, days: int) -> Optional[Dict]:
        """Detect frequent idle pattern"""
        # Implementation
        pass
    
    async def _detect_end_session_pattern(self, user_id: str, days: int) -> Optional[Dict]:
        """Detect end of session idle pattern"""
        # Implementation
        pass
    
    async def _update_daily_patterns(self, conn, session_id: str):
        """Update daily activity patterns"""
        # Implementation
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/analytics/idle", tags=["idle-analytics"])

@router.post("/session/start")
async def start_activity_session(
    user_id: str,
    device_type: Optional[str] = None,
    browser: Optional[str] = None
):
    """Start a new activity session"""
    analytics = IdleTimeAnalytics(db_pool)
    session_id = await analytics.start_activity_session(user_id, device_type, browser)
    return {"session_id": session_id}

@router.post("/event/start")
async def track_idle_start(
    user_id: str,
    session_id: str,
    idle_reason: str = "no_interaction",
    activity_before: Optional[str] = None
):
    """Track idle event start"""
    analytics = IdleTimeAnalytics(db_pool)
    event_id = await analytics.track_idle_event(
        user_id, session_id, datetime.utcnow(), idle_reason, activity_before
    )
    return {"event_id": event_id}

@router.post("/event/end")
async def track_idle_end(
    event_id: int,
    activity_after: Optional[str] = None
):
    """End idle event"""
    analytics = IdleTimeAnalytics(db_pool)
    await analytics.end_idle_event(event_id, activity_after)
    return {"status": "idle_ended"}

@router.post("/session/end")
async def end_activity_session(session_id: str):
    """End activity session"""
    analytics = IdleTimeAnalytics(db_pool)
    await analytics.end_activity_session(session_id)
    return {"status": "session_ended"}

@router.get("/statistics/{user_id}")
async def get_activity_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get activity statistics"""
    analytics = IdleTimeAnalytics(db_pool)
    stats = await analytics.get_activity_statistics(user_id, days)
    return stats

@router.get("/patterns/{user_id}")
async def detect_idle_patterns(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect idle patterns"""
    analytics = IdleTimeAnalytics(db_pool)
    patterns = await analytics.detect_idle_patterns(user_id, days)
    return {"patterns": patterns}

@router.get("/engagement/{user_id}")
async def get_engagement_metrics(user_id: str):
    """Get engagement metrics"""
    analytics = IdleTimeAnalytics(db_pool)
    metrics = await analytics.get_engagement_metrics(user_id)
    return metrics

@router.get("/distribution")
async def get_idle_distribution(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get idle time distribution"""
    analytics = IdleTimeAnalytics(db_pool)
    distribution = await analytics.get_idle_time_distribution(user_id, days)
    return distribution

@router.get("/heatmap/{user_id}")
async def get_activity_heatmap(
    user_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """Get activity heatmap"""
    analytics = IdleTimeAnalytics(db_pool)
    heatmap = await analytics.get_activity_heatmap(user_id, days)
    return {"heatmap": heatmap}
```

## React Dashboard Components

```tsx
// Idle Time Analytics Dashboard
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, HeatMap, PieChart, LineChart } from '@/components/ui';

interface IdleDashboardProps {
  userId?: string;
}

export const IdleDashboard: React.FC<IdleDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<ActivityStatistics | null>(null);
  const [engagement, setEngagement] = useState<EngagementMetrics | null>(null);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [distribution, setDistribution] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIdleData();
  }, [userId]);

  const fetchIdleData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/idle/statistics/${userId}`,
        userId && `/api/analytics/idle/engagement/${userId}`,
        userId && `/api/analytics/idle/heatmap/${userId}`,
        `/api/analytics/idle/distribution${userId ? `?user_id=${userId}` : ''}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      if (userId) {
        setStats(data[0]);
        setEngagement(data[1]);
        setHeatmap(data[2].heatmap);
        setDistribution(data[3]);
      } else {
        setDistribution(data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch idle data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading idle time analytics...</div>;

  return (
    <div className="idle-dashboard">
      <h2>Activity & Idle Time Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Total Sessions</h3>
              <div className="stat-value">{stats.totalSessions}</div>
              <span className="stat-label">
                Avg: {stats.avgSessionDuration.toFixed(0)} min
              </span>
            </Card>
            
            <Card>
              <h3>Active Time</h3>
              <div className="stat-value">{stats.totalActiveMinutes.toFixed(0)} min</div>
              <Progress 
                value={stats.activePercentage} 
                max={100}
                variant="success"
              />
              <span>{stats.activePercentage.toFixed(1)}% active</span>
            </Card>
            
            <Card>
              <h3>Idle Time</h3>
              <div className="stat-value">{stats.totalIdleMinutes.toFixed(0)} min</div>
              <Progress 
                value={stats.idlePercentage} 
                max={100}
                variant="warning"
              />
              <span>{stats.idlePercentage.toFixed(1)}% idle</span>
            </Card>
            
            <Card>
              <h3>Engagement Score</h3>
              <div className="stat-value">{stats.engagementScore.toFixed(0)}</div>
              <Badge variant={stats.engagementScore > 70 ? 'success' : 'warning'}>
                {stats.engagementScore > 70 ? 'High' : 'Medium'}
              </Badge>
            </Card>
          </Grid>

          {/* Engagement Metrics */}
          {engagement && (
            <Card className="mt-4">
              <h3>Engagement Metrics</h3>
              <Grid cols={3} gap={4}>
                <div>
                  <h4>Activity Timeline</h4>
                  <div className="timeline-stats">
                    <div>Daily: {engagement.dailyActiveTime} min</div>
                    <div>Weekly: {engagement.weeklyActiveTime} min</div>
                    <div>Monthly: {engagement.monthlyActiveTime} min</div>
                  </div>
                </div>
                
                <div>
                  <h4>Consistency</h4>
                  <Progress 
                    value={engagement.consistencyScore} 
                    max={100}
                    variant={engagement.consistencyScore > 50 ? 'success' : 'warning'}
                  />
                  <span>{engagement.consistencyScore.toFixed(0)}% consistent</span>
                </div>
                
                <div>
                  <h4>Churn Risk</h4>
                  <Progress 
                    value={engagement.riskOfChurn} 
                    max={100}
                    variant={engagement.riskOfChurn > 50 ? 'danger' : 'success'}
                  />
                  <Badge variant={engagement.activityTrend === 'increasing' ? 'success' : 
                                engagement.activityTrend === 'decreasing' ? 'danger' : 'info'}>
                    {engagement.activityTrend}
                  </Badge>
                </div>
              </Grid>
            </Card>
          )}

          {/* Activity Heatmap */}
          {heatmap.length > 0 && (
            <Card className="mt-4">
              <h3>Activity Heatmap</h3>
              <HeatMap
                data={heatmap}
                xKey="hour"
                yKey="day"
                valueKey="value"
                height={300}
              />
            </Card>
          )}
        </>
      )}

      {/* Idle Time Distribution */}
      {distribution && (
        <Card className="mt-4">
          <h3>Idle Time Distribution</h3>
          <PieChart
            data={distribution.distribution.map((d: any) => ({
              name: d.bucket,
              value: d.count,
              percentage: d.percentage
            }))}
            height={300}
          />
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic session tracking
2. Idle event detection
3. Activity statistics calculation
4. Pattern detection
5. Engagement scoring

## Security Considerations
- Respect user privacy settings
- No keystroke logging
- Aggregate data for reporting
- Secure session management
- Prevent session hijacking

## Performance Optimizations
- Batch idle event updates
- Use client-side idle detection
- Daily aggregation for reports
- Efficient session queries
- Cache engagement scores