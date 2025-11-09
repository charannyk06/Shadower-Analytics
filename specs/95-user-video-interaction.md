# User Video Interaction Specification

## Overview
Track user interactions with video content including play patterns, engagement levels, and viewing behavior to optimize video content and placement without intrusive monitoring.

## Database Schema

### Tables

```sql
-- Video interaction sessions
CREATE TABLE video_interaction_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    video_id VARCHAR(200) NOT NULL,
    video_url VARCHAR(500),
    video_title VARCHAR(500),
    video_duration_seconds INTEGER NOT NULL,
    watch_duration_seconds INTEGER DEFAULT 0,
    completion_percentage DECIMAL(5, 2) DEFAULT 0,
    play_count INTEGER DEFAULT 1,
    pause_count INTEGER DEFAULT 0,
    seek_count INTEGER DEFAULT 0,
    replay_count INTEGER DEFAULT 0,
    quality_changes INTEGER DEFAULT 0,
    selected_quality VARCHAR(20),
    average_playback_rate DECIMAL(3, 2) DEFAULT 1.0,
    engagement_score DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_video_sessions_user (user_id, created_at DESC),
    INDEX idx_video_sessions_video (video_id, created_at DESC),
    INDEX idx_video_sessions_completion (completion_percentage DESC)
);

-- Video interaction events
CREATE TABLE video_interaction_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    video_id VARCHAR(200) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- play, pause, seek, end, quality_change, etc.
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    video_time_seconds DECIMAL(10, 2),
    event_data JSONB, -- Additional event-specific data
    
    INDEX idx_video_events_session (session_id, event_timestamp),
    INDEX idx_video_events_type (event_type, created_at DESC)
);

-- Video engagement metrics
CREATE TABLE video_engagement_metrics (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(200) UNIQUE NOT NULL,
    total_views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    total_watch_time_seconds BIGINT DEFAULT 0,
    average_completion_percentage DECIMAL(5, 2) DEFAULT 0,
    average_engagement_score DECIMAL(5, 2) DEFAULT 0,
    drop_off_points JSONB, -- Array of time points where users commonly stop
    replay_segments JSONB, -- Array of segments that are frequently replayed
    peak_concurrent_viewers INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_engagement_metrics_video (video_id),
    INDEX idx_engagement_metrics_score (average_engagement_score DESC)
);

-- Daily video statistics
CREATE TABLE video_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    video_id VARCHAR(200),
    views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    total_watch_time_minutes INTEGER DEFAULT 0,
    completions INTEGER DEFAULT 0,
    average_watch_percentage DECIMAL(5, 2),
    engagement_score DECIMAL(5, 2),
    most_replayed_segment VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, video_id),
    INDEX idx_video_daily_stats_date (date DESC),
    INDEX idx_video_daily_stats_video (video_id, date DESC)
);
```

## TypeScript Interfaces

```typescript
// Video interaction session
interface VideoInteractionSession {
  id: string;
  userId: string;
  sessionId: string;
  videoId: string;
  videoUrl?: string;
  videoTitle?: string;
  videoDurationSeconds: number;
  watchDurationSeconds: number;
  completionPercentage: number;
  playCount: number;
  pauseCount: number;
  seekCount: number;
  replayCount: number;
  qualityChanges: number;
  selectedQuality?: string;
  averagePlaybackRate: number;
  engagementScore: number;
  createdAt: Date;
  endedAt?: Date;
}

// Video interaction event
interface VideoInteractionEvent {
  id: string;
  userId: string;
  sessionId: string;
  videoId: string;
  eventType: 'play' | 'pause' | 'seek' | 'end' | 'quality_change' | 'fullscreen' | 'replay';
  eventTimestamp: Date;
  videoTimeSeconds: number;
  eventData?: any;
}

// Video engagement metrics
interface VideoEngagementMetrics {
  videoId: string;
  totalViews: number;
  uniqueViewers: number;
  totalWatchTimeSeconds: number;
  averageCompletionPercentage: number;
  averageEngagementScore: number;
  dropOffPoints: TimePoint[];
  replaySegments: VideoSegment[];
  peakConcurrentViewers: number;
}

// Video statistics
interface VideoStatistics {
  totalVideosWatched: number;
  totalWatchTimeMinutes: number;
  averageCompletionRate: number;
  favoriteVideos: VideoSummary[];
  watchPatterns: WatchPattern[];
  engagementLevel: 'high' | 'medium' | 'low';
}

// Watch pattern
interface WatchPattern {
  patternType: 'binge_watcher' | 'casual_viewer' | 'completionist' | 'sampler';
  confidence: number;
  characteristics: {
    avgSessionLength: number;
    completionRate: number;
    replayFrequency: number;
    seekBehavior: number;
  };
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json
import asyncpg

@dataclass
class VideoAnalytics:
    """Analyze video interaction patterns and engagement"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.engagement_weights = {
            'completion': 0.4,
            'interaction': 0.3,
            'replay': 0.2,
            'quality': 0.1
        }
    
    async def start_video_session(
        self,
        user_id: str,
        video_id: str,
        video_duration: int,
        video_url: Optional[str] = None,
        video_title: Optional[str] = None
    ) -> str:
        """Start a new video interaction session"""
        query = """
            INSERT INTO video_interaction_sessions (
                user_id, video_id, video_duration_seconds,
                video_url, video_title
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING session_id
        """
        
        async with self.db.acquire() as conn:
            session_id = await conn.fetchval(
                query, user_id, video_id, video_duration, video_url, video_title
            )
        
        return session_id
    
    async def track_video_event(
        self,
        user_id: str,
        session_id: str,
        video_id: str,
        event_type: str,
        video_time: float,
        event_data: Optional[Dict] = None
    ) -> int:
        """Track a video interaction event"""
        query = """
            INSERT INTO video_interaction_events (
                user_id, session_id, video_id, event_type,
                video_time_seconds, event_data
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            event_id = await conn.fetchval(
                query, user_id, session_id, video_id, event_type,
                video_time, json.dumps(event_data) if event_data else None
            )
            
            # Update session based on event
            await self._update_session_from_event(
                conn, session_id, event_type, video_time, event_data
            )
            
            # Track engagement metrics
            if event_type in ['pause', 'seek', 'end']:
                await self._update_engagement_metrics(
                    conn, video_id, session_id, event_type, video_time
                )
        
        return event_id
    
    async def end_video_session(
        self,
        session_id: str,
        watch_duration: int,
        completion_percentage: float
    ):
        """End a video session and calculate final metrics"""
        query = """
            WITH session_events AS (
                SELECT 
                    COUNT(*) FILTER (WHERE event_type = 'play') as plays,
                    COUNT(*) FILTER (WHERE event_type = 'pause') as pauses,
                    COUNT(*) FILTER (WHERE event_type = 'seek') as seeks,
                    COUNT(*) FILTER (WHERE event_type = 'replay') as replays,
                    COUNT(*) FILTER (WHERE event_type = 'quality_change') as quality_changes
                FROM video_interaction_events
                WHERE session_id = $1
            )
            UPDATE video_interaction_sessions s
            SET watch_duration_seconds = $2,
                completion_percentage = $3,
                play_count = COALESCE(e.plays, 1),
                pause_count = COALESCE(e.pauses, 0),
                seek_count = COALESCE(e.seeks, 0),
                replay_count = COALESCE(e.replays, 0),
                quality_changes = COALESCE(e.quality_changes, 0),
                engagement_score = $4,
                ended_at = CURRENT_TIMESTAMP
            FROM session_events e
            WHERE s.session_id = $1
        """
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            completion_percentage, watch_duration
        )
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, session_id, watch_duration, 
                completion_percentage, engagement_score
            )
            
            # Update daily stats
            await self._update_daily_stats(conn, session_id)
    
    async def get_video_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user video statistics"""
        query = """
            WITH video_stats AS (
                SELECT 
                    COUNT(DISTINCT video_id) as videos_watched,
                    SUM(watch_duration_seconds) / 60 as total_watch_minutes,
                    AVG(completion_percentage) as avg_completion,
                    COUNT(*) as total_sessions,
                    AVG(engagement_score) as avg_engagement
                FROM video_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            favorite_videos AS (
                SELECT 
                    video_id,
                    video_title,
                    COUNT(*) as watch_count,
                    SUM(watch_duration_seconds) as total_watch_time,
                    AVG(completion_percentage) as avg_completion
                FROM video_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY video_id, video_title
                ORDER BY watch_count DESC
                LIMIT 10
            )
            SELECT 
                s.*,
                (SELECT json_agg(json_build_object(
                    'video_id', video_id,
                    'title', video_title,
                    'watch_count', watch_count,
                    'total_time', total_watch_time,
                    'avg_completion', avg_completion
                )) FROM favorite_videos) as favorites
            FROM video_stats s
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            # Detect watch patterns
            watch_patterns = await self._detect_watch_patterns(conn, user_id, days)
            
            # Determine engagement level
            engagement_level = self._determine_engagement_level(
                row['avg_engagement'] or 0
            )
            
            return {
                'total_videos_watched': row['videos_watched'] or 0,
                'total_watch_time_minutes': row['total_watch_minutes'] or 0,
                'average_completion_rate': row['avg_completion'] or 0,
                'favorite_videos': row['favorites'] or [],
                'watch_patterns': watch_patterns,
                'engagement_level': engagement_level
            }
    
    async def detect_watch_patterns(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Detect user video watching patterns"""
        query = """
            SELECT 
                AVG(watch_duration_seconds / 60) as avg_session_minutes,
                AVG(completion_percentage) as avg_completion,
                AVG(replay_count) as avg_replays,
                AVG(seek_count) as avg_seeks,
                COUNT(*) as session_count,
                STDDEV(completion_percentage) as completion_variance
            FROM video_interaction_sessions
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow(query % days, user_id)
            
            if not stats or not stats['session_count']:
                return []
            
            pattern = self._determine_watch_pattern(
                stats['avg_session_minutes'] or 0,
                stats['avg_completion'] or 0,
                stats['avg_replays'] or 0,
                stats['avg_seeks'] or 0,
                stats['completion_variance'] or 0
            )
            
            return [pattern]
    
    async def get_video_engagement_metrics(
        self,
        video_id: str
    ) -> Dict:
        """Get engagement metrics for a video"""
        query = """
            SELECT 
                total_views,
                unique_viewers,
                total_watch_time_seconds,
                average_completion_percentage,
                average_engagement_score,
                drop_off_points,
                replay_segments,
                peak_concurrent_viewers
            FROM video_engagement_metrics
            WHERE video_id = $1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, video_id)
            
            if not row:
                # Calculate from sessions
                metrics = await self._calculate_video_metrics(conn, video_id)
                return metrics
            
            return {
                'video_id': video_id,
                'total_views': row['total_views'],
                'unique_viewers': row['unique_viewers'],
                'total_watch_time_seconds': row['total_watch_time_seconds'],
                'average_completion_percentage': row['average_completion_percentage'],
                'average_engagement_score': row['average_engagement_score'],
                'drop_off_points': json.loads(row['drop_off_points']) if row['drop_off_points'] else [],
                'replay_segments': json.loads(row['replay_segments']) if row['replay_segments'] else [],
                'peak_concurrent_viewers': row['peak_concurrent_viewers']
            }
    
    async def get_drop_off_analysis(
        self,
        video_id: str,
        bucket_seconds: int = 10
    ) -> List[Dict]:
        """Analyze where users stop watching"""
        query = """
            WITH watch_times AS (
                SELECT 
                    watch_duration_seconds,
                    video_duration_seconds,
                    completion_percentage
                FROM video_interaction_sessions
                WHERE video_id = $1
                    AND watch_duration_seconds > 0
            ),
            time_buckets AS (
                SELECT 
                    (watch_duration_seconds / $2) * $2 as time_bucket,
                    COUNT(*) as drop_count,
                    AVG(completion_percentage) as avg_completion
                FROM watch_times
                WHERE completion_percentage < 95
                GROUP BY (watch_duration_seconds / $2) * $2
            )
            SELECT 
                time_bucket,
                drop_count,
                avg_completion,
                SUM(drop_count) OVER (ORDER BY time_bucket) as cumulative_drops
            FROM time_buckets
            ORDER BY time_bucket
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, video_id, bucket_seconds)
            
            return [
                {
                    'time_seconds': row['time_bucket'],
                    'drop_count': row['drop_count'],
                    'avg_completion': row['avg_completion'],
                    'cumulative_drops': row['cumulative_drops'],
                    'severity': self._get_dropoff_severity(row['drop_count'])
                }
                for row in rows
            ]
    
    async def get_replay_segments(
        self,
        video_id: str
    ) -> List[Dict]:
        """Identify frequently replayed video segments"""
        query = """
            WITH seek_events AS (
                SELECT 
                    video_time_seconds,
                    LAG(video_time_seconds) OVER (
                        PARTITION BY session_id ORDER BY event_timestamp
                    ) as prev_time
                FROM video_interaction_events
                WHERE video_id = $1
                    AND event_type = 'seek'
            ),
            replay_segments AS (
                SELECT 
                    FLOOR(prev_time / 10) * 10 as segment_start,
                    FLOOR(video_time_seconds / 10) * 10 as segment_end,
                    COUNT(*) as replay_count
                FROM seek_events
                WHERE prev_time > video_time_seconds  -- Backward seek
                GROUP BY FLOOR(prev_time / 10) * 10, FLOOR(video_time_seconds / 10) * 10
                HAVING COUNT(*) > 2
            )
            SELECT * FROM replay_segments
            ORDER BY replay_count DESC
            LIMIT 10
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, video_id)
            
            return [
                {
                    'segment_start': row['segment_start'],
                    'segment_end': row['segment_end'],
                    'replay_count': row['replay_count'],
                    'importance': self._get_segment_importance(row['replay_count'])
                }
                for row in rows
            ]
    
    async def get_quality_preferences(
        self,
        user_id: Optional[str] = None
    ) -> Dict:
        """Get video quality preferences"""
        query = """
            WITH quality_stats AS (
                SELECT 
                    selected_quality,
                    COUNT(*) as selection_count,
                    AVG(watch_duration_seconds) as avg_watch_time,
                    AVG(completion_percentage) as avg_completion
                FROM video_interaction_sessions
                WHERE selected_quality IS NOT NULL
                    %s
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY selected_quality
            )
            SELECT 
                selected_quality,
                selection_count,
                avg_watch_time,
                avg_completion,
                selection_count::float / SUM(selection_count) OVER () * 100 as percentage
            FROM quality_stats
            ORDER BY selection_count DESC
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                rows = await conn.fetch(query % user_filter, user_id)
            else:
                rows = await conn.fetch(query % user_filter)
            
            return {
                'quality_distribution': [
                    {
                        'quality': row['selected_quality'],
                        'count': row['selection_count'],
                        'percentage': row['percentage'],
                        'avg_watch_time': row['avg_watch_time'],
                        'avg_completion': row['avg_completion']
                    }
                    for row in rows
                ]
            }
    
    async def get_concurrent_viewers(
        self,
        video_id: str,
        time_window_minutes: int = 5
    ) -> List[Dict]:
        """Get concurrent viewer data for a video"""
        query = """
            WITH time_slots AS (
                SELECT 
                    date_trunc('minute', created_at) as time_slot,
                    COUNT(DISTINCT user_id) as concurrent_viewers
                FROM video_interaction_sessions
                WHERE video_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s minutes'
                GROUP BY date_trunc('minute', created_at)
            )
            SELECT 
                time_slot,
                concurrent_viewers,
                MAX(concurrent_viewers) OVER () as peak_viewers
            FROM time_slots
            ORDER BY time_slot DESC
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % time_window_minutes, video_id)
            
            return [
                {
                    'time': row['time_slot'].isoformat(),
                    'viewers': row['concurrent_viewers'],
                    'is_peak': row['concurrent_viewers'] == row['peak_viewers']
                }
                for row in rows
            ]
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_videos_watched': 0,
            'total_watch_time_minutes': 0,
            'average_completion_rate': 0,
            'favorite_videos': [],
            'watch_patterns': [],
            'engagement_level': 'low'
        }
    
    def _calculate_engagement_score(
        self,
        completion: float,
        watch_duration: int
    ) -> float:
        """Calculate video engagement score"""
        score = 0.0
        
        # Completion contributes 40%
        score += completion * 0.4
        
        # Watch duration contributes 30%
        if watch_duration > 300:  # More than 5 minutes
            score += 30
        elif watch_duration > 60:
            score += 20
        else:
            score += 10
        
        # Additional factors would be calculated from events
        score += 30  # Placeholder for interaction score
        
        return min(score, 100)
    
    def _determine_watch_pattern(
        self,
        avg_session: float,
        avg_completion: float,
        avg_replays: float,
        avg_seeks: float,
        variance: float
    ) -> Dict:
        """Determine video watching pattern"""
        
        # Binge watcher: long sessions, high completion
        if avg_session > 30 and avg_completion > 80:
            pattern_type = 'binge_watcher'
            confidence = 0.8
        
        # Completionist: very high completion, low variance
        elif avg_completion > 90 and variance < 10:
            pattern_type = 'completionist'
            confidence = 0.85
        
        # Sampler: low completion, high seeks
        elif avg_completion < 30 and avg_seeks > 5:
            pattern_type = 'sampler'
            confidence = 0.7
        
        # Casual viewer: moderate everything
        else:
            pattern_type = 'casual_viewer'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'avg_session_length': avg_session,
                'completion_rate': avg_completion,
                'replay_frequency': avg_replays,
                'seek_behavior': avg_seeks
            }
        }
    
    def _determine_engagement_level(self, avg_engagement: float) -> str:
        """Determine engagement level"""
        if avg_engagement >= 80:
            return 'high'
        elif avg_engagement >= 50:
            return 'medium'
        else:
            return 'low'
    
    def _get_dropoff_severity(self, count: int) -> str:
        """Get drop-off severity"""
        if count > 50:
            return 'critical'
        elif count > 20:
            return 'high'
        elif count > 10:
            return 'medium'
        else:
            return 'low'
    
    def _get_segment_importance(self, replay_count: int) -> str:
        """Get segment importance based on replays"""
        if replay_count > 20:
            return 'very_high'
        elif replay_count > 10:
            return 'high'
        elif replay_count > 5:
            return 'medium'
        else:
            return 'low'
    
    async def _update_session_from_event(
        self,
        conn,
        session_id: str,
        event_type: str,
        video_time: float,
        event_data: Optional[Dict]
    ):
        """Update session based on event"""
        # Implementation
        pass
    
    async def _update_engagement_metrics(
        self,
        conn,
        video_id: str,
        session_id: str,
        event_type: str,
        video_time: float
    ):
        """Update video engagement metrics"""
        # Implementation
        pass
    
    async def _update_daily_stats(self, conn, session_id: str):
        """Update daily video statistics"""
        # Implementation
        pass
    
    async def _calculate_video_metrics(self, conn, video_id: str) -> Dict:
        """Calculate video metrics from sessions"""
        # Implementation
        return {}
    
    async def _detect_watch_patterns(
        self,
        conn,
        user_id: str,
        days: int
    ) -> List[Dict]:
        """Detect watch patterns"""
        return await self.detect_watch_patterns(user_id, days)
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/video", tags=["video-analytics"])

@router.post("/session/start")
async def start_video_session(
    user_id: str,
    video_id: str,
    video_duration: int,
    video_url: Optional[str] = None,
    video_title: Optional[str] = None
):
    """Start video session"""
    analytics = VideoAnalytics(db_pool)
    session_id = await analytics.start_video_session(
        user_id, video_id, video_duration, video_url, video_title
    )
    return {"session_id": session_id}

@router.post("/event")
async def track_video_event(
    user_id: str,
    session_id: str,
    video_id: str,
    event_type: str,
    video_time: float,
    event_data: Optional[dict] = None
):
    """Track video event"""
    analytics = VideoAnalytics(db_pool)
    event_id = await analytics.track_video_event(
        user_id, session_id, video_id, event_type, video_time, event_data
    )
    return {"event_id": event_id}

@router.post("/session/end")
async def end_video_session(
    session_id: str,
    watch_duration: int,
    completion_percentage: float
):
    """End video session"""
    analytics = VideoAnalytics(db_pool)
    await analytics.end_video_session(
        session_id, watch_duration, completion_percentage
    )
    return {"status": "session_ended"}

@router.get("/statistics/{user_id}")
async def get_video_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get video statistics"""
    analytics = VideoAnalytics(db_pool)
    stats = await analytics.get_video_statistics(user_id, days)
    return stats

@router.get("/patterns/{user_id}")
async def detect_watch_patterns(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect watch patterns"""
    analytics = VideoAnalytics(db_pool)
    patterns = await analytics.detect_watch_patterns(user_id, days)
    return {"patterns": patterns}

@router.get("/metrics/{video_id}")
async def get_video_engagement_metrics(video_id: str):
    """Get video engagement metrics"""
    analytics = VideoAnalytics(db_pool)
    metrics = await analytics.get_video_engagement_metrics(video_id)
    return metrics

@router.get("/dropoff/{video_id}")
async def get_drop_off_analysis(
    video_id: str,
    bucket_seconds: int = Query(10, ge=5, le=60)
):
    """Get drop-off analysis"""
    analytics = VideoAnalytics(db_pool)
    analysis = await analytics.get_drop_off_analysis(video_id, bucket_seconds)
    return {"drop_off_points": analysis}

@router.get("/replays/{video_id}")
async def get_replay_segments(video_id: str):
    """Get replay segments"""
    analytics = VideoAnalytics(db_pool)
    segments = await analytics.get_replay_segments(video_id)
    return {"replay_segments": segments}
```

## React Dashboard Components

```tsx
// Video Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, LineChart, HeatMap } from '@/components/ui';

interface VideoDashboardProps {
  userId?: string;
  videoId?: string;
}

export const VideoDashboard: React.FC<VideoDashboardProps> = ({ userId, videoId }) => {
  const [stats, setStats] = useState<VideoStatistics | null>(null);
  const [metrics, setMetrics] = useState<VideoEngagementMetrics | null>(null);
  const [dropoff, setDropoff] = useState<any[]>([]);
  const [replays, setReplays] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVideoData();
  }, [userId, videoId]);

  const fetchVideoData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/video/statistics/${userId}`,
        videoId && `/api/analytics/video/metrics/${videoId}`,
        videoId && `/api/analytics/video/dropoff/${videoId}`,
        videoId && `/api/analytics/video/replays/${videoId}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      let idx = 0;
      if (userId) setStats(data[idx++]);
      if (videoId) {
        setMetrics(data[idx++]);
        setDropoff(data[idx++].drop_off_points);
        setReplays(data[idx].replay_segments);
      }
    } catch (error) {
      console.error('Failed to fetch video data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading video analytics...</div>;

  return (
    <div className="video-dashboard">
      <h2>Video Interaction Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Videos Watched</h3>
              <div className="stat-value">{stats.totalVideosWatched}</div>
              <Badge variant={stats.engagementLevel === 'high' ? 'success' : 'warning'}>
                {stats.engagementLevel} engagement
              </Badge>
            </Card>
            
            <Card>
              <h3>Watch Time</h3>
              <div className="stat-value">
                {Math.floor(stats.totalWatchTimeMinutes / 60)}h {stats.totalWatchTimeMinutes % 60}m
              </div>
            </Card>
            
            <Card>
              <h3>Completion Rate</h3>
              <div className="stat-value">{stats.averageCompletionRate.toFixed(1)}%</div>
              <Progress value={stats.averageCompletionRate} max={100} />
            </Card>
            
            <Card>
              <h3>Watch Pattern</h3>
              {stats.watchPatterns[0] && (
                <Badge variant="primary">
                  {stats.watchPatterns[0].patternType.replace('_', ' ')}
                </Badge>
              )}
            </Card>
          </Grid>
        </>
      )}

      {metrics && (
        <>
          <Card className="mt-4">
            <h3>Video Engagement Metrics</h3>
            <Grid cols={3} gap={4}>
              <div>
                <span>Total Views</span>
                <strong>{metrics.totalViews}</strong>
              </div>
              <div>
                <span>Unique Viewers</span>
                <strong>{metrics.uniqueViewers}</strong>
              </div>
              <div>
                <span>Avg Completion</span>
                <strong>{metrics.averageCompletionPercentage.toFixed(1)}%</strong>
              </div>
            </Grid>
          </Card>

          {/* Drop-off Analysis */}
          {dropoff.length > 0 && (
            <Card className="mt-4">
              <h3>Drop-off Analysis</h3>
              <LineChart
                data={dropoff}
                xKey="time_seconds"
                yKey="cumulative_drops"
                height={300}
              />
            </Card>
          )}

          {/* Replay Segments */}
          {replays.length > 0 && (
            <Card className="mt-4">
              <h3>Most Replayed Segments</h3>
              <div className="replay-segments">
                {replays.map((segment, idx) => (
                  <div key={idx} className="segment-bar">
                    <span>{formatTime(segment.segment_start)} - {formatTime(segment.segment_end)}</span>
                    <Badge variant={segment.importance === 'very_high' ? 'danger' : 'info'}>
                      {segment.replay_count} replays
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};
```

## Implementation Priority
1. Basic video session tracking
2. Event tracking (play, pause, seek)
3. Completion rate calculation
4. Drop-off analysis
5. Replay segment detection

## Security Considerations
- No recording of video content
- Anonymize viewing data
- Respect privacy settings
- Secure session handling
- Rate limit event tracking

## Performance Optimizations
- Batch video events
- Client-side buffering
- Efficient metric queries
- Cache engagement scores
- Aggregate analytics daily