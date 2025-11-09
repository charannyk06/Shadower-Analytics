# User Audio Interaction Specification

## Overview
Track user interactions with audio content including podcast listening patterns, music playback behavior, and audio engagement metrics without storing actual audio content.

## Database Schema

### Tables

```sql
-- Audio interaction sessions
CREATE TABLE audio_interaction_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    audio_id VARCHAR(200) NOT NULL,
    audio_type VARCHAR(50), -- podcast, music, audiobook, lecture
    audio_title VARCHAR(500),
    audio_duration_seconds INTEGER NOT NULL,
    listen_duration_seconds INTEGER DEFAULT 0,
    completion_percentage DECIMAL(5, 2) DEFAULT 0,
    play_count INTEGER DEFAULT 1,
    pause_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    rewind_count INTEGER DEFAULT 0,
    forward_count INTEGER DEFAULT 0,
    volume_changes INTEGER DEFAULT 0,
    average_volume_level DECIMAL(3, 2),
    playback_speed DECIMAL(3, 2) DEFAULT 1.0,
    background_play BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_audio_sessions_user (user_id, created_at DESC),
    INDEX idx_audio_sessions_audio (audio_id, created_at DESC),
    INDEX idx_audio_sessions_type (audio_type, created_at DESC)
);

-- Audio skip patterns
CREATE TABLE audio_skip_patterns (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    audio_id VARCHAR(200) NOT NULL,
    skip_timestamp DECIMAL(10, 2),
    skip_duration DECIMAL(10, 2),
    skip_reason VARCHAR(50), -- intro, ads, content, outro
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_skip_patterns_audio (audio_id, skip_timestamp),
    INDEX idx_skip_patterns_reason (skip_reason)
);

-- Podcast/audio series tracking
CREATE TABLE audio_series_progress (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    series_id VARCHAR(200) NOT NULL,
    series_title VARCHAR(500),
    total_episodes INTEGER,
    episodes_started INTEGER DEFAULT 0,
    episodes_completed INTEGER DEFAULT 0,
    total_listen_time_seconds BIGINT DEFAULT 0,
    average_completion_rate DECIMAL(5, 2),
    subscription_status VARCHAR(50), -- subscribed, unsubscribed, paused
    last_episode_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, series_id),
    INDEX idx_series_progress_user (user_id),
    INDEX idx_series_progress_series (series_id)
);

-- Daily audio statistics
CREATE TABLE audio_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_listen_time_minutes INTEGER DEFAULT 0,
    unique_audio_count INTEGER DEFAULT 0,
    podcasts_played INTEGER DEFAULT 0,
    music_played INTEGER DEFAULT 0,
    average_session_minutes DECIMAL(10, 2),
    most_played_type VARCHAR(50),
    peak_listening_hour INTEGER,
    background_play_percentage DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_audio_daily_stats_date (date DESC),
    INDEX idx_audio_daily_stats_user (user_id, date DESC)
);
```

## TypeScript Interfaces

```typescript
// Audio interaction session
interface AudioInteractionSession {
  id: string;
  userId: string;
  sessionId: string;
  audioId: string;
  audioType?: 'podcast' | 'music' | 'audiobook' | 'lecture';
  audioTitle?: string;
  audioDurationSeconds: number;
  listenDurationSeconds: number;
  completionPercentage: number;
  playCount: number;
  pauseCount: number;
  skipCount: number;
  rewindCount: number;
  forwardCount: number;
  volumeChanges: number;
  averageVolumeLevel?: number;
  playbackSpeed: number;
  backgroundPlay: boolean;
  createdAt: Date;
  endedAt?: Date;
}

// Audio skip pattern
interface AudioSkipPattern {
  userId: string;
  sessionId: string;
  audioId: string;
  skipTimestamp: number;
  skipDuration: number;
  skipReason?: 'intro' | 'ads' | 'content' | 'outro';
}

// Audio series progress
interface AudioSeriesProgress {
  userId: string;
  seriesId: string;
  seriesTitle?: string;
  totalEpisodes?: number;
  episodesStarted: number;
  episodesCompleted: number;
  totalListenTimeSeconds: number;
  averageCompletionRate: number;
  subscriptionStatus: 'subscribed' | 'unsubscribed' | 'paused';
  lastEpisodeDate?: Date;
}

// Audio listening statistics
interface AudioStatistics {
  totalListenTimeMinutes: number;
  uniqueAudioCount: number;
  favoriteGenres: GenreStats[];
  listeningPattern: ListeningPattern;
  podcastMetrics?: PodcastMetrics;
  musicMetrics?: MusicMetrics;
  peakListeningTimes: TimeSlot[];
}

// Listening pattern
interface ListeningPattern {
  patternType: 'commuter' | 'background' | 'focused' | 'casual';
  confidence: number;
  characteristics: {
    avgSessionLength: number;
    preferredSpeed: number;
    skipFrequency: number;
    backgroundPlayPercentage: number;
  };
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import asyncpg

@dataclass
class AudioAnalytics:
    """Analyze audio listening patterns and engagement"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.skip_thresholds = {
            'intro': (0, 60),  # First 60 seconds
            'outro': (-60, 0),  # Last 60 seconds
            'ads': (60, -60),   # Middle content
        }
    
    async def start_audio_session(
        self,
        user_id: str,
        audio_id: str,
        audio_duration: int,
        audio_type: Optional[str] = None,
        audio_title: Optional[str] = None
    ) -> str:
        """Start a new audio listening session"""
        query = """
            INSERT INTO audio_interaction_sessions (
                user_id, audio_id, audio_duration_seconds,
                audio_type, audio_title
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING session_id
        """
        
        async with self.db.acquire() as conn:
            session_id = await conn.fetchval(
                query, user_id, audio_id, audio_duration, audio_type, audio_title
            )
        
        return session_id
    
    async def track_audio_skip(
        self,
        user_id: str,
        session_id: str,
        audio_id: str,
        skip_timestamp: float,
        skip_duration: float
    ):
        """Track audio skip pattern"""
        # Determine skip reason based on timestamp
        skip_reason = self._determine_skip_reason(skip_timestamp, skip_duration)
        
        query = """
            INSERT INTO audio_skip_patterns (
                user_id, session_id, audio_id,
                skip_timestamp, skip_duration, skip_reason
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, user_id, session_id, audio_id,
                skip_timestamp, skip_duration, skip_reason
            )
            
            # Update session skip count
            await self._update_session_skips(conn, session_id)
    
    async def update_audio_session(
        self,
        session_id: str,
        listen_duration: int,
        completion_percentage: float,
        play_count: int = 1,
        pause_count: int = 0,
        volume_level: Optional[float] = None,
        playback_speed: float = 1.0,
        background_play: bool = False
    ):
        """Update audio session with listening data"""
        query = """
            UPDATE audio_interaction_sessions
            SET listen_duration_seconds = $2,
                completion_percentage = $3,
                play_count = $4,
                pause_count = $5,
                average_volume_level = $6,
                playback_speed = $7,
                background_play = $8,
                ended_at = CURRENT_TIMESTAMP
            WHERE session_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, session_id, listen_duration, completion_percentage,
                play_count, pause_count, volume_level, playback_speed,
                background_play
            )
            
            # Update series progress if applicable
            await self._update_series_progress(conn, session_id)
            
            # Update daily stats
            await self._update_daily_stats(conn, session_id)
    
    async def get_audio_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user audio listening statistics"""
        query = """
            WITH audio_stats AS (
                SELECT 
                    SUM(listen_duration_seconds) / 60 as total_listen_minutes,
                    COUNT(DISTINCT audio_id) as unique_audio,
                    COUNT(*) FILTER (WHERE audio_type = 'podcast') as podcast_count,
                    COUNT(*) FILTER (WHERE audio_type = 'music') as music_count,
                    AVG(completion_percentage) as avg_completion,
                    AVG(playback_speed) as avg_speed,
                    SUM(CASE WHEN background_play THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as background_percentage
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            favorite_types AS (
                SELECT 
                    audio_type,
                    COUNT(*) as play_count,
                    SUM(listen_duration_seconds) as total_time
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND audio_type IS NOT NULL
                GROUP BY audio_type
                ORDER BY play_count DESC
            ),
            peak_hours AS (
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    COUNT(*) as session_count
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM created_at)
                ORDER BY session_count DESC
                LIMIT 3
            )
            SELECT 
                a.*,
                (SELECT json_agg(json_build_object(
                    'type', audio_type,
                    'count', play_count,
                    'total_time', total_time
                )) FROM favorite_types) as favorites,
                (SELECT array_agg(hour ORDER BY session_count DESC) FROM peak_hours) as peak_hours
            FROM audio_stats a
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            # Get listening pattern
            pattern = await self._detect_listening_pattern(conn, user_id, days)
            
            # Get podcast metrics if applicable
            podcast_metrics = None
            if row['podcast_count'] and row['podcast_count'] > 0:
                podcast_metrics = await self._get_podcast_metrics(conn, user_id, days)
            
            return {
                'total_listen_time_minutes': row['total_listen_minutes'] or 0,
                'unique_audio_count': row['unique_audio'] or 0,
                'favorite_genres': row['favorites'] or [],
                'listening_pattern': pattern,
                'podcast_metrics': podcast_metrics,
                'music_metrics': None,  # Would be implemented similarly
                'peak_listening_times': row['peak_hours'] or []
            }
    
    async def detect_listening_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user listening pattern"""
        query = """
            SELECT 
                AVG(listen_duration_seconds / 60) as avg_session_minutes,
                AVG(playback_speed) as avg_speed,
                AVG(skip_count) as avg_skips,
                SUM(CASE WHEN background_play THEN 1 ELSE 0 END)::float / COUNT(*) as background_ratio,
                EXTRACT(HOUR FROM created_at) as hour,
                COUNT(*) as session_count
            FROM audio_interaction_sessions
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM created_at)
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days, user_id)
            
            if not rows:
                return {'pattern_type': 'unknown', 'confidence': 0}
            
            # Analyze listening times
            morning_sessions = sum(r['session_count'] for r in rows if 6 <= r['hour'] < 10)
            evening_sessions = sum(r['session_count'] for r in rows if 17 <= r['hour'] < 20)
            total_sessions = sum(r['session_count'] for r in rows)
            
            # Calculate averages
            avg_session = sum(r['avg_session_minutes'] * r['session_count'] for r in rows) / total_sessions
            avg_speed = sum(r['avg_speed'] * r['session_count'] for r in rows) / total_sessions
            avg_skips = sum(r['avg_skips'] * r['session_count'] for r in rows) / total_sessions
            background_ratio = sum(r['background_ratio'] * r['session_count'] for r in rows) / total_sessions
            
            pattern = self._determine_listening_pattern(
                avg_session,
                avg_speed,
                avg_skips,
                background_ratio,
                morning_sessions / total_sessions if total_sessions > 0 else 0,
                evening_sessions / total_sessions if total_sessions > 0 else 0
            )
            
            return pattern
    
    async def get_skip_analysis(
        self,
        audio_id: Optional[str] = None,
        audio_type: Optional[str] = None
    ) -> Dict:
        """Analyze skip patterns"""
        query = """
            WITH skip_stats AS (
                SELECT 
                    skip_reason,
                    COUNT(*) as skip_count,
                    AVG(skip_duration) as avg_skip_duration,
                    COUNT(DISTINCT user_id) as unique_users
                FROM audio_skip_patterns
                WHERE 1=1
                    %s
                    %s
                GROUP BY skip_reason
            ),
            common_skips AS (
                SELECT 
                    FLOOR(skip_timestamp / 30) * 30 as timestamp_bucket,
                    COUNT(*) as skip_count
                FROM audio_skip_patterns
                WHERE 1=1
                    %s
                    %s
                GROUP BY FLOOR(skip_timestamp / 30) * 30
                HAVING COUNT(*) > 5
                ORDER BY timestamp_bucket
            )
            SELECT 
                (SELECT json_agg(json_build_object(
                    'reason', skip_reason,
                    'count', skip_count,
                    'avg_duration', avg_skip_duration,
                    'users', unique_users
                )) FROM skip_stats) as skip_reasons,
                (SELECT json_agg(json_build_object(
                    'timestamp', timestamp_bucket,
                    'count', skip_count
                ) ORDER BY timestamp_bucket) FROM common_skips) as common_skip_points
        """
        
        audio_filter = "AND audio_id = $1" if audio_id else ""
        type_filter = "AND audio_type = $2" if audio_type else ""
        
        async with self.db.acquire() as conn:
            params = []
            if audio_id:
                params.append(audio_id)
            if audio_type:
                params.append(audio_type)
            
            row = await conn.fetchrow(
                query % (audio_filter, type_filter, audio_filter, type_filter),
                *params
            )
            
            return {
                'skip_reasons': row['skip_reasons'] or [],
                'common_skip_points': row['common_skip_points'] or [],
                'recommendations': self._generate_skip_recommendations(row)
            }
    
    async def get_series_progress(
        self,
        user_id: str,
        series_id: Optional[str] = None
    ) -> List[Dict]:
        """Get podcast/audio series progress"""
        query = """
            SELECT 
                series_id,
                series_title,
                total_episodes,
                episodes_started,
                episodes_completed,
                total_listen_time_seconds,
                average_completion_rate,
                subscription_status,
                last_episode_date
            FROM audio_series_progress
            WHERE user_id = $1
                %s
            ORDER BY last_episode_date DESC
        """
        
        series_filter = "AND series_id = $2" if series_id else ""
        
        async with self.db.acquire() as conn:
            if series_id:
                rows = await conn.fetch(query % series_filter, user_id, series_id)
            else:
                rows = await conn.fetch(query % series_filter, user_id)
            
            return [
                {
                    'series_id': row['series_id'],
                    'series_title': row['series_title'],
                    'total_episodes': row['total_episodes'],
                    'episodes_started': row['episodes_started'],
                    'episodes_completed': row['episodes_completed'],
                    'total_listen_time_seconds': row['total_listen_time_seconds'],
                    'average_completion_rate': row['average_completion_rate'],
                    'subscription_status': row['subscription_status'],
                    'last_episode_date': row['last_episode_date'].isoformat() if row['last_episode_date'] else None,
                    'progress_percentage': (
                        row['episodes_completed'] / row['total_episodes'] * 100
                        if row['total_episodes'] > 0 else 0
                    )
                }
                for row in rows
            ]
    
    async def get_playback_preferences(
        self,
        user_id: str
    ) -> Dict:
        """Get user playback preferences"""
        query = """
            WITH speed_stats AS (
                SELECT 
                    playback_speed,
                    COUNT(*) as usage_count,
                    audio_type
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY playback_speed, audio_type
            ),
            volume_stats AS (
                SELECT 
                    AVG(average_volume_level) as avg_volume,
                    STDDEV(average_volume_level) as volume_variance
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND average_volume_level IS NOT NULL
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            ),
            background_stats AS (
                SELECT 
                    audio_type,
                    SUM(CASE WHEN background_play THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as background_percentage
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY audio_type
            )
            SELECT 
                (SELECT json_agg(json_build_object(
                    'speed', playback_speed,
                    'count', usage_count,
                    'type', audio_type
                ) ORDER BY usage_count DESC) FROM speed_stats) as speed_preferences,
                (SELECT avg_volume FROM volume_stats) as average_volume,
                (SELECT volume_variance FROM volume_stats) as volume_consistency,
                (SELECT json_agg(json_build_object(
                    'type', audio_type,
                    'background_percentage', background_percentage
                )) FROM background_stats) as background_preferences
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            return {
                'speed_preferences': row['speed_preferences'] or [],
                'average_volume': row['average_volume'] or 0.5,
                'volume_consistency': row['volume_consistency'] or 0,
                'background_preferences': row['background_preferences'] or [],
                'preferred_speed': self._get_preferred_speed(row['speed_preferences'])
            }
    
    async def get_listening_streaks(
        self,
        user_id: str
    ) -> Dict:
        """Get listening streak information"""
        query = """
            WITH daily_listens AS (
                SELECT 
                    DATE(created_at) as listen_date,
                    COUNT(*) as sessions,
                    SUM(listen_duration_seconds) / 60 as minutes
                FROM audio_interaction_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days'
                GROUP BY DATE(created_at)
            ),
            streaks AS (
                SELECT 
                    listen_date,
                    listen_date - (ROW_NUMBER() OVER (ORDER BY listen_date))::int as streak_group
                FROM daily_listens
            )
            SELECT 
                MIN(listen_date) as streak_start,
                MAX(listen_date) as streak_end,
                COUNT(*) as streak_length
            FROM streaks
            GROUP BY streak_group
            ORDER BY streak_length DESC
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            
            current_streak = 0
            longest_streak = 0
            
            if rows:
                # Check if most recent streak is current
                most_recent = rows[0]
                if most_recent['streak_end'] >= datetime.now().date() - timedelta(days=1):
                    current_streak = most_recent['streak_length']
                
                longest_streak = max(row['streak_length'] for row in rows)
            
            return {
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'streak_history': [
                    {
                        'start': row['streak_start'].isoformat(),
                        'end': row['streak_end'].isoformat(),
                        'length': row['streak_length']
                    }
                    for row in rows[:10]  # Top 10 streaks
                ]
            }
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_listen_time_minutes': 0,
            'unique_audio_count': 0,
            'favorite_genres': [],
            'listening_pattern': {'pattern_type': 'unknown', 'confidence': 0},
            'podcast_metrics': None,
            'music_metrics': None,
            'peak_listening_times': []
        }
    
    def _determine_skip_reason(self, timestamp: float, duration: float) -> str:
        """Determine reason for skip based on timing"""
        if timestamp < 60:
            return 'intro'
        elif timestamp > duration - 60:
            return 'outro'
        else:
            return 'content'
    
    def _determine_listening_pattern(
        self,
        avg_session: float,
        avg_speed: float,
        avg_skips: float,
        background_ratio: float,
        morning_ratio: float,
        evening_ratio: float
    ) -> Dict:
        """Determine listening pattern type"""
        
        # Commuter: morning/evening peaks, medium sessions
        if (morning_ratio > 0.3 or evening_ratio > 0.3) and 15 < avg_session < 45:
            pattern_type = 'commuter'
            confidence = 0.8
        
        # Background: high background play, long sessions
        elif background_ratio > 0.6 and avg_session > 30:
            pattern_type = 'background'
            confidence = 0.75
        
        # Focused: low skips, normal speed, low background
        elif avg_skips < 2 and 0.9 < avg_speed < 1.1 and background_ratio < 0.3:
            pattern_type = 'focused'
            confidence = 0.8
        
        # Casual: everything else
        else:
            pattern_type = 'casual'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'avg_session_length': avg_session,
                'preferred_speed': avg_speed,
                'skip_frequency': avg_skips,
                'background_play_percentage': background_ratio * 100
            }
        }
    
    def _generate_skip_recommendations(self, data: dict) -> List[str]:
        """Generate recommendations based on skip analysis"""
        recommendations = []
        
        if data and data.get('skip_reasons'):
            reasons = data['skip_reasons']
            for reason in reasons:
                if reason['reason'] == 'intro' and reason['count'] > 10:
                    recommendations.append("Consider shorter intros - high skip rate detected")
                elif reason['reason'] == 'ads' and reason['count'] > 20:
                    recommendations.append("Ad placement may be causing user friction")
        
        return recommendations
    
    def _get_preferred_speed(self, speed_prefs: List) -> float:
        """Get most preferred playback speed"""
        if not speed_prefs:
            return 1.0
        
        # Weight by usage count
        total_weight = sum(pref['count'] for pref in speed_prefs)
        if total_weight == 0:
            return 1.0
        
        weighted_speed = sum(
            pref['speed'] * pref['count'] for pref in speed_prefs
        ) / total_weight
        
        return weighted_speed
    
    async def _update_session_skips(self, conn, session_id: str):
        """Update session skip count"""
        # Implementation
        pass
    
    async def _update_series_progress(self, conn, session_id: str):
        """Update audio series progress"""
        # Implementation
        pass
    
    async def _update_daily_stats(self, conn, session_id: str):
        """Update daily audio statistics"""
        # Implementation
        pass
    
    async def _detect_listening_pattern(
        self,
        conn,
        user_id: str,
        days: int
    ) -> Dict:
        """Detect listening pattern from database"""
        return await self.detect_listening_pattern(user_id, days)
    
    async def _get_podcast_metrics(
        self,
        conn,
        user_id: str,
        days: int
    ) -> Dict:
        """Get podcast-specific metrics"""
        # Implementation
        return {}
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/audio", tags=["audio-analytics"])

@router.post("/session/start")
async def start_audio_session(
    user_id: str,
    audio_id: str,
    audio_duration: int,
    audio_type: Optional[str] = None,
    audio_title: Optional[str] = None
):
    """Start audio session"""
    analytics = AudioAnalytics(db_pool)
    session_id = await analytics.start_audio_session(
        user_id, audio_id, audio_duration, audio_type, audio_title
    )
    return {"session_id": session_id}

@router.post("/skip")
async def track_audio_skip(
    user_id: str,
    session_id: str,
    audio_id: str,
    skip_timestamp: float,
    skip_duration: float
):
    """Track audio skip"""
    analytics = AudioAnalytics(db_pool)
    await analytics.track_audio_skip(
        user_id, session_id, audio_id, skip_timestamp, skip_duration
    )
    return {"status": "tracked"}

@router.patch("/session/{session_id}")
async def update_audio_session(
    session_id: str,
    listen_duration: int,
    completion_percentage: float,
    play_count: int = 1,
    pause_count: int = 0,
    volume_level: Optional[float] = None,
    playback_speed: float = 1.0,
    background_play: bool = False
):
    """Update audio session"""
    analytics = AudioAnalytics(db_pool)
    await analytics.update_audio_session(
        session_id, listen_duration, completion_percentage,
        play_count, pause_count, volume_level, playback_speed,
        background_play
    )
    return {"status": "updated"}

@router.get("/statistics/{user_id}")
async def get_audio_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get audio statistics"""
    analytics = AudioAnalytics(db_pool)
    stats = await analytics.get_audio_statistics(user_id, days)
    return stats

@router.get("/pattern/{user_id}")
async def detect_listening_pattern(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect listening pattern"""
    analytics = AudioAnalytics(db_pool)
    pattern = await analytics.detect_listening_pattern(user_id, days)
    return pattern

@router.get("/skip-analysis")
async def get_skip_analysis(
    audio_id: Optional[str] = None,
    audio_type: Optional[str] = None
):
    """Get skip analysis"""
    analytics = AudioAnalytics(db_pool)
    analysis = await analytics.get_skip_analysis(audio_id, audio_type)
    return analysis

@router.get("/series-progress/{user_id}")
async def get_series_progress(
    user_id: str,
    series_id: Optional[str] = None
):
    """Get series progress"""
    analytics = AudioAnalytics(db_pool)
    progress = await analytics.get_series_progress(user_id, series_id)
    return {"series": progress}

@router.get("/preferences/{user_id}")
async def get_playback_preferences(user_id: str):
    """Get playback preferences"""
    analytics = AudioAnalytics(db_pool)
    preferences = await analytics.get_playback_preferences(user_id)
    return preferences

@router.get("/streaks/{user_id}")
async def get_listening_streaks(user_id: str):
    """Get listening streaks"""
    analytics = AudioAnalytics(db_pool)
    streaks = await analytics.get_listening_streaks(user_id)
    return streaks
```

## React Dashboard Components

```tsx
// Audio Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, LineChart, BarChart } from '@/components/ui';

interface AudioDashboardProps {
  userId?: string;
}

export const AudioDashboard: React.FC<AudioDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<AudioStatistics | null>(null);
  const [preferences, setPreferences] = useState<any>(null);
  const [streaks, setStreaks] = useState<any>(null);
  const [seriesProgress, setSeriesProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAudioData();
  }, [userId]);

  const fetchAudioData = async () => {
    setLoading(true);
    try {
      if (!userId) {
        setLoading(false);
        return;
      }

      const responses = await Promise.all([
        fetch(`/api/analytics/audio/statistics/${userId}`),
        fetch(`/api/analytics/audio/preferences/${userId}`),
        fetch(`/api/analytics/audio/streaks/${userId}`),
        fetch(`/api/analytics/audio/series-progress/${userId}`)
      ]);

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      setStats(data[0]);
      setPreferences(data[1]);
      setStreaks(data[2]);
      setSeriesProgress(data[3].series);
    } catch (error) {
      console.error('Failed to fetch audio data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading audio analytics...</div>;
  if (!userId) return <div>Please select a user to view audio analytics</div>;

  return (
    <div className="audio-dashboard">
      <h2>Audio Listening Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Total Listen Time</h3>
              <div className="stat-value">
                {Math.floor(stats.totalListenTimeMinutes / 60)}h {stats.totalListenTimeMinutes % 60}m
              </div>
            </Card>
            
            <Card>
              <h3>Unique Audio</h3>
              <div className="stat-value">{stats.uniqueAudioCount}</div>
              {stats.listeningPattern && (
                <Badge variant="primary">
                  {stats.listeningPattern.patternType} listener
                </Badge>
              )}
            </Card>
            
            <Card>
              <h3>Current Streak</h3>
              <div className="stat-value">{streaks?.currentStreak || 0} days</div>
              <span className="stat-label">
                Longest: {streaks?.longestStreak || 0} days
              </span>
            </Card>
            
            <Card>
              <h3>Peak Hours</h3>
              <div className="peak-hours">
                {stats.peakListeningTimes?.map(hour => (
                  <Badge key={hour} variant="info">{hour}:00</Badge>
                ))}
              </div>
            </Card>
          </Grid>

          {/* Playback Preferences */}
          {preferences && (
            <Card className="mt-4">
              <h3>Playback Preferences</h3>
              <Grid cols={3} gap={4}>
                <div>
                  <span>Preferred Speed</span>
                  <strong>{preferences.preferredSpeed.toFixed(1)}x</strong>
                </div>
                <div>
                  <span>Average Volume</span>
                  <Progress value={preferences.averageVolume * 100} max={100} />
                </div>
                <div>
                  <span>Background Play</span>
                  {preferences.backgroundPreferences?.map((pref: any) => (
                    <div key={pref.type}>
                      <span>{pref.type}: </span>
                      <strong>{pref.backgroundPercentage.toFixed(0)}%</strong>
                    </div>
                  ))}
                </div>
              </Grid>
            </Card>
          )}

          {/* Series Progress */}
          {seriesProgress.length > 0 && (
            <Card className="mt-4">
              <h3>Podcast/Series Progress</h3>
              <div className="series-list">
                {seriesProgress.map(series => (
                  <div key={series.seriesId} className="series-item">
                    <div className="series-info">
                      <h4>{series.seriesTitle || series.seriesId}</h4>
                      <Badge variant={series.subscriptionStatus === 'subscribed' ? 'success' : 'secondary'}>
                        {series.subscriptionStatus}
                      </Badge>
                    </div>
                    <Progress 
                      value={series.progressPercentage} 
                      max={100}
                      label={`${series.episodesCompleted}/${series.totalEpisodes || '?'} episodes`}
                    />
                    <span className="series-stats">
                      {Math.floor(series.totalListenTimeSeconds / 3600)}h listened • 
                      {series.averageCompletionRate.toFixed(0)}% avg completion
                    </span>
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
```

## Implementation Priority
1. Basic audio session tracking
2. Skip pattern detection
3. Series progress tracking
4. Playback preference analysis
5. Streak calculation

## Security Considerations
- No audio content storage
- Anonymize listening data
- Respect privacy settings
- Secure session handling
- Rate limit event tracking

## Performance Optimizations
- Batch audio events
- Client-side buffering
- Efficient skip detection
- Cache listening patterns
- Daily aggregation for stats