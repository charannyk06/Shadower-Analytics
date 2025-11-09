# User Keyboard Tracking Specification

## Overview
Track keyboard interaction patterns including shortcuts usage, typing patterns, and form interactions to improve user experience without capturing actual keystrokes or sensitive data.

## Database Schema

### Tables

```sql
-- Keyboard interaction sessions
CREATE TABLE keyboard_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    page_url VARCHAR(500) NOT NULL,
    total_keystrokes INTEGER DEFAULT 0,
    shortcuts_used INTEGER DEFAULT 0,
    typing_speed_wpm DECIMAL(10, 2),
    backspace_count INTEGER DEFAULT 0,
    delete_count INTEGER DEFAULT 0,
    copy_paste_count INTEGER DEFAULT 0,
    tab_navigation_count INTEGER DEFAULT 0,
    form_fields_completed INTEGER DEFAULT 0,
    session_duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_keyboard_sessions_user (user_id, created_at DESC),
    INDEX idx_keyboard_sessions_page (page_url)
);

-- Shortcut usage tracking
CREATE TABLE shortcut_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    shortcut_key VARCHAR(50) NOT NULL, -- e.g., 'Ctrl+C', 'Cmd+V'
    action_type VARCHAR(50), -- copy, paste, save, undo, redo, etc.
    element_context VARCHAR(100), -- form, textarea, editor, etc.
    usage_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_shortcut_usage_user (user_id, created_at DESC),
    INDEX idx_shortcut_usage_key (shortcut_key),
    INDEX idx_shortcut_usage_action (action_type)
);

-- Form interaction tracking
CREATE TABLE form_keyboard_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    form_id VARCHAR(200),
    field_name VARCHAR(100),
    field_type VARCHAR(50),
    keystrokes_count INTEGER DEFAULT 0,
    time_to_complete_ms INTEGER,
    corrections_count INTEGER DEFAULT 0, -- backspace/delete usage
    tab_navigations INTEGER DEFAULT 0,
    paste_events INTEGER DEFAULT 0,
    field_completed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_form_interactions_user (user_id, created_at DESC),
    INDEX idx_form_interactions_form (form_id)
);

-- Daily keyboard statistics
CREATE TABLE keyboard_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_keystrokes INTEGER DEFAULT 0,
    avg_typing_speed DECIMAL(10, 2),
    shortcuts_efficiency_score DECIMAL(5, 2),
    most_used_shortcut VARCHAR(50),
    form_completion_rate DECIMAL(5, 2),
    error_correction_rate DECIMAL(5, 2),
    productivity_score DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_keyboard_daily_stats_date (date DESC),
    INDEX idx_keyboard_daily_stats_user (user_id, date DESC)
);
```

## TypeScript Interfaces

```typescript
// Keyboard session interface
interface KeyboardSession {
  id: string;
  userId: string;
  sessionId: string;
  pageUrl: string;
  totalKeystrokes: number;
  shortcutsUsed: number;
  typingSpeedWpm: number;
  backspaceCount: number;
  deleteCount: number;
  copyPasteCount: number;
  tabNavigationCount: number;
  formFieldsCompleted: number;
  sessionDurationSeconds: number;
}

// Shortcut usage interface
interface ShortcutUsage {
  userId: string;
  sessionId: string;
  shortcutKey: string;
  actionType?: string;
  elementContext?: string;
  usageCount: number;
}

// Form keyboard interaction
interface FormKeyboardInteraction {
  userId: string;
  sessionId: string;
  formId?: string;
  fieldName?: string;
  fieldType?: string;
  keystrokesCount: number;
  timeToCompleteMs?: number;
  correctionsCount: number;
  tabNavigations: number;
  pasteEvents: number;
  fieldCompleted: boolean;
}

// Keyboard statistics
interface KeyboardStatistics {
  totalKeystrokes: number;
  avgTypingSpeed: number;
  shortcutsEfficiencyScore: number;
  mostUsedShortcuts: ShortcutSummary[];
  formCompletionRate: number;
  errorCorrectionRate: number;
  productivityScore: number;
  typingPattern: TypingPattern;
}

// Typing pattern
interface TypingPattern {
  patternType: 'fast_accurate' | 'fast_error_prone' | 'slow_careful' | 'hunt_and_peck';
  confidence: number;
  characteristics: {
    speed: number;
    accuracy: number;
    shortcutUsage: number;
    navigationEfficiency: number;
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
class KeyboardAnalytics:
    """Analyze keyboard interaction patterns"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.wpm_calculation_threshold = 10  # Minimum keystrokes for WPM calc
    
    async def start_keyboard_session(
        self,
        user_id: str,
        page_url: str
    ) -> str:
        """Start a new keyboard tracking session"""
        query = """
            INSERT INTO keyboard_sessions (
                user_id, page_url
            ) VALUES ($1, $2)
            RETURNING session_id
        """
        
        async with self.db.acquire() as conn:
            session_id = await conn.fetchval(query, user_id, page_url)
        
        return session_id
    
    async def track_shortcut_usage(
        self,
        user_id: str,
        session_id: str,
        shortcut_key: str,
        action_type: Optional[str] = None,
        element_context: Optional[str] = None
    ):
        """Track keyboard shortcut usage"""
        query = """
            INSERT INTO shortcut_usage (
                user_id, session_id, shortcut_key, action_type, element_context
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, session_id, shortcut_key) 
            DO UPDATE SET usage_count = shortcut_usage.usage_count + 1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, user_id, session_id, shortcut_key, 
                action_type, element_context
            )
            
            # Update session stats
            await self._update_session_shortcuts(conn, session_id)
    
    async def track_form_interaction(
        self,
        user_id: str,
        session_id: str,
        form_id: Optional[str],
        field_name: Optional[str],
        field_type: Optional[str],
        keystrokes: int = 0,
        corrections: int = 0,
        tab_navigations: int = 0,
        paste_events: int = 0,
        time_to_complete: Optional[int] = None,
        completed: bool = False
    ) -> int:
        """Track form field keyboard interaction"""
        query = """
            INSERT INTO form_keyboard_interactions (
                user_id, session_id, form_id, field_name, field_type,
                keystrokes_count, corrections_count, tab_navigations,
                paste_events, time_to_complete_ms, field_completed
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            interaction_id = await conn.fetchval(
                query, user_id, session_id, form_id, field_name, field_type,
                keystrokes, corrections, tab_navigations, paste_events,
                time_to_complete, completed
            )
            
            # Update session form count if completed
            if completed:
                await self._update_session_forms(conn, session_id)
        
        return interaction_id
    
    async def update_keyboard_session(
        self,
        session_id: str,
        total_keystrokes: int,
        backspace_count: int = 0,
        delete_count: int = 0,
        copy_paste_count: int = 0,
        tab_navigation_count: int = 0,
        typing_speed_wpm: Optional[float] = None
    ):
        """Update keyboard session statistics"""
        query = """
            UPDATE keyboard_sessions
            SET total_keystrokes = $2,
                backspace_count = $3,
                delete_count = $4,
                copy_paste_count = $5,
                tab_navigation_count = $6,
                typing_speed_wpm = COALESCE($7, typing_speed_wpm),
                session_duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))
            WHERE session_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, session_id, total_keystrokes, backspace_count,
                delete_count, copy_paste_count, tab_navigation_count,
                typing_speed_wpm
            )
            
            # Update daily stats
            await self._update_daily_stats(conn, session_id)
    
    async def get_keyboard_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get keyboard interaction statistics"""
        query = """
            WITH keyboard_stats AS (
                SELECT 
                    SUM(total_keystrokes) as total_keystrokes,
                    AVG(typing_speed_wpm) as avg_typing_speed,
                    SUM(shortcuts_used) as total_shortcuts,
                    SUM(backspace_count + delete_count) as total_corrections,
                    SUM(form_fields_completed) as forms_completed,
                    COUNT(*) as session_count
                FROM keyboard_sessions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            top_shortcuts AS (
                SELECT 
                    shortcut_key,
                    action_type,
                    SUM(usage_count) as total_usage
                FROM shortcut_usage
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY shortcut_key, action_type
                ORDER BY total_usage DESC
                LIMIT 10
            ),
            form_stats AS (
                SELECT 
                    COUNT(*) as total_fields,
                    COUNT(*) FILTER (WHERE field_completed) as completed_fields,
                    AVG(time_to_complete_ms) as avg_completion_time
                FROM form_keyboard_interactions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            )
            SELECT 
                k.*,
                f.total_fields,
                f.completed_fields,
                f.avg_completion_time,
                (SELECT json_agg(json_build_object(
                    'shortcut', shortcut_key,
                    'action', action_type,
                    'usage', total_usage
                )) FROM top_shortcuts) as top_shortcuts
            FROM keyboard_stats k
            CROSS JOIN form_stats f
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            # Calculate scores
            efficiency_score = self._calculate_efficiency_score(
                row['total_shortcuts'] or 0,
                row['total_keystrokes'] or 1,
                row['avg_typing_speed'] or 0
            )
            
            form_completion_rate = (
                (row['completed_fields'] / row['total_fields'] * 100)
                if row['total_fields'] > 0 else 0
            )
            
            error_correction_rate = (
                (row['total_corrections'] / row['total_keystrokes'] * 100)
                if row['total_keystrokes'] > 0 else 0
            )
            
            # Detect typing pattern
            typing_pattern = await self._detect_typing_pattern(conn, user_id, days)
            
            return {
                'total_keystrokes': row['total_keystrokes'] or 0,
                'avg_typing_speed': row['avg_typing_speed'] or 0,
                'shortcuts_efficiency_score': efficiency_score,
                'most_used_shortcuts': row['top_shortcuts'] or [],
                'form_completion_rate': form_completion_rate,
                'error_correction_rate': error_correction_rate,
                'productivity_score': self._calculate_productivity_score(
                    efficiency_score, form_completion_rate, error_correction_rate
                ),
                'typing_pattern': typing_pattern
            }
    
    async def detect_typing_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user typing pattern"""
        query = """
            SELECT 
                AVG(typing_speed_wpm) as avg_speed,
                AVG((backspace_count + delete_count)::float / NULLIF(total_keystrokes, 0)) as error_rate,
                AVG(shortcuts_used::float / NULLIF(session_duration_seconds, 0)) as shortcut_frequency,
                AVG(tab_navigation_count::float / NULLIF(form_fields_completed, 0)) as nav_efficiency
            FROM keyboard_sessions
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                AND total_keystrokes > 0
        """
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow(query % days, user_id)
            
            if not stats or not stats['avg_speed']:
                return {'pattern_type': 'unknown', 'confidence': 0}
            
            pattern = self._determine_typing_pattern(
                stats['avg_speed'] or 0,
                stats['error_rate'] or 0,
                stats['shortcut_frequency'] or 0,
                stats['nav_efficiency'] or 0
            )
            
            return pattern
    
    async def get_shortcut_insights(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get insights about shortcut usage"""
        query = """
            WITH shortcut_stats AS (
                SELECT 
                    shortcut_key,
                    action_type,
                    element_context,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(usage_count) as total_usage,
                    AVG(usage_count) as avg_usage_per_user
                FROM shortcut_usage
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY shortcut_key, action_type, element_context
            ),
            efficiency_gain AS (
                SELECT 
                    u.user_id,
                    COUNT(DISTINCT s.shortcut_key) as shortcuts_known,
                    SUM(s.usage_count) as total_shortcut_uses,
                    AVG(k.typing_speed_wpm) as typing_speed
                FROM shortcut_usage s
                JOIN keyboard_sessions k ON s.session_id = k.session_id
                WHERE s.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY u.user_id
            )
            SELECT 
                (SELECT json_agg(json_build_object(
                    'shortcut', shortcut_key,
                    'action', action_type,
                    'context', element_context,
                    'usage', total_usage,
                    'users', unique_users
                ) ORDER BY total_usage DESC) FROM shortcut_stats) as popular_shortcuts,
                AVG(eg.shortcuts_known) as avg_shortcuts_known,
                CORR(eg.total_shortcut_uses, eg.typing_speed) as shortcut_speed_correlation
            FROM efficiency_gain eg
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                row = await conn.fetchrow(query % (days, user_filter, days), user_id)
            else:
                row = await conn.fetchrow(query % (days, user_filter, days))
            
            return {
                'popular_shortcuts': row['popular_shortcuts'] or [],
                'avg_shortcuts_known': row['avg_shortcuts_known'] or 0,
                'shortcut_speed_correlation': row['shortcut_speed_correlation'] or 0,
                'efficiency_insights': self._generate_efficiency_insights(row)
            }
    
    async def get_form_completion_analysis(
        self,
        form_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Analyze form completion patterns"""
        query = """
            WITH form_metrics AS (
                SELECT 
                    form_id,
                    field_name,
                    field_type,
                    COUNT(*) as attempts,
                    COUNT(*) FILTER (WHERE field_completed) as completions,
                    AVG(time_to_complete_ms) as avg_time,
                    AVG(corrections_count) as avg_corrections,
                    AVG(paste_events) as avg_pastes
                FROM form_keyboard_interactions
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY form_id, field_name, field_type
            ),
            problem_fields AS (
                SELECT 
                    field_name,
                    field_type,
                    attempts - completions as abandonment_count,
                    avg_corrections
                FROM form_metrics
                WHERE (completions::float / attempts) < 0.8
                    OR avg_corrections > 5
                ORDER BY abandonment_count DESC
                LIMIT 10
            )
            SELECT 
                AVG(completions::float / attempts) as overall_completion_rate,
                AVG(avg_time) as overall_avg_time,
                AVG(avg_corrections) as overall_avg_corrections,
                (SELECT json_agg(json_build_object(
                    'field', field_name,
                    'type', field_type,
                    'abandonments', abandonment_count,
                    'avg_corrections', avg_corrections
                )) FROM problem_fields) as problem_fields
            FROM form_metrics
        """
        
        form_filter = "AND form_id = $1" if form_id else ""
        
        async with self.db.acquire() as conn:
            if form_id:
                row = await conn.fetchrow(query % (days, form_filter), form_id)
            else:
                row = await conn.fetchrow(query % (days, form_filter))
            
            return {
                'overall_completion_rate': row['overall_completion_rate'] or 0,
                'overall_avg_time_ms': row['overall_avg_time'] or 0,
                'overall_avg_corrections': row['overall_avg_corrections'] or 0,
                'problem_fields': row['problem_fields'] or [],
                'recommendations': self._generate_form_recommendations(row)
            }
    
    async def get_typing_speed_distribution(
        self,
        days: int = 30
    ) -> Dict:
        """Get typing speed distribution across users"""
        query = """
            WITH speed_buckets AS (
                SELECT 
                    CASE 
                        WHEN typing_speed_wpm < 20 THEN '< 20 WPM'
                        WHEN typing_speed_wpm < 40 THEN '20-40 WPM'
                        WHEN typing_speed_wpm < 60 THEN '40-60 WPM'
                        WHEN typing_speed_wpm < 80 THEN '60-80 WPM'
                        ELSE '> 80 WPM'
                    END as speed_range,
                    COUNT(DISTINCT user_id) as user_count,
                    AVG(shortcuts_used) as avg_shortcuts
                FROM keyboard_sessions
                WHERE typing_speed_wpm IS NOT NULL
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY speed_range
            )
            SELECT * FROM speed_buckets
            ORDER BY 
                CASE speed_range
                    WHEN '< 20 WPM' THEN 1
                    WHEN '20-40 WPM' THEN 2
                    WHEN '40-60 WPM' THEN 3
                    WHEN '60-80 WPM' THEN 4
                    ELSE 5
                END
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days)
            
            total_users = sum(row['user_count'] for row in rows)
            
            return {
                'distribution': [
                    {
                        'speed_range': row['speed_range'],
                        'user_count': row['user_count'],
                        'percentage': (row['user_count'] / total_users * 100) if total_users > 0 else 0,
                        'avg_shortcuts': row['avg_shortcuts']
                    }
                    for row in rows
                ]
            }
    
    async def get_productivity_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Get productivity trends over time"""
        query = """
            SELECT 
                date,
                total_keystrokes,
                avg_typing_speed,
                shortcuts_efficiency_score,
                form_completion_rate,
                productivity_score
            FROM keyboard_daily_stats
            WHERE user_id = $1
                AND date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days, user_id)
            
            return [
                {
                    'date': row['date'].isoformat(),
                    'keystrokes': row['total_keystrokes'],
                    'typing_speed': row['avg_typing_speed'],
                    'shortcuts_score': row['shortcuts_efficiency_score'],
                    'form_completion': row['form_completion_rate'],
                    'productivity': row['productivity_score']
                }
                for row in rows
            ]
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_keystrokes': 0,
            'avg_typing_speed': 0,
            'shortcuts_efficiency_score': 0,
            'most_used_shortcuts': [],
            'form_completion_rate': 0,
            'error_correction_rate': 0,
            'productivity_score': 0,
            'typing_pattern': {'pattern_type': 'unknown', 'confidence': 0}
        }
    
    def _calculate_efficiency_score(
        self,
        shortcuts: int,
        keystrokes: int,
        speed: float
    ) -> float:
        """Calculate keyboard efficiency score"""
        score = 0.0
        
        # Shortcut usage contributes 40 points
        if keystrokes > 0:
            shortcut_ratio = shortcuts / keystrokes * 100
            score += min(shortcut_ratio * 4, 40)
        
        # Typing speed contributes 60 points
        if speed > 0:
            if speed >= 60:
                score += 60
            elif speed >= 40:
                score += 40
            elif speed >= 20:
                score += 20
            else:
                score += 10
        
        return min(score, 100)
    
    def _calculate_productivity_score(
        self,
        efficiency: float,
        form_completion: float,
        error_rate: float
    ) -> float:
        """Calculate overall productivity score"""
        score = 0.0
        
        # Efficiency contributes 40%
        score += efficiency * 0.4
        
        # Form completion contributes 40%
        score += form_completion * 0.4
        
        # Low error rate contributes 20%
        score += max(0, (20 - error_rate))
        
        return min(score, 100)
    
    def _determine_typing_pattern(
        self,
        speed: float,
        error_rate: float,
        shortcut_freq: float,
        nav_efficiency: float
    ) -> Dict:
        """Determine typing pattern based on metrics"""
        
        accuracy = 100 - (error_rate * 100) if error_rate else 100
        
        # Fast and accurate
        if speed >= 50 and accuracy >= 95:
            pattern_type = 'fast_accurate'
            confidence = 0.9
        
        # Fast but error-prone
        elif speed >= 50 and accuracy < 95:
            pattern_type = 'fast_error_prone'
            confidence = 0.8
        
        # Slow and careful
        elif speed < 50 and accuracy >= 95:
            pattern_type = 'slow_careful'
            confidence = 0.8
        
        # Hunt and peck
        elif speed < 30:
            pattern_type = 'hunt_and_peck'
            confidence = 0.7
        
        else:
            pattern_type = 'average'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'speed': speed,
                'accuracy': accuracy,
                'shortcut_usage': shortcut_freq * 100 if shortcut_freq else 0,
                'navigation_efficiency': nav_efficiency * 100 if nav_efficiency else 0
            }
        }
    
    def _generate_efficiency_insights(self, data: dict) -> List[str]:
        """Generate efficiency insights"""
        insights = []
        
        if data.get('shortcut_speed_correlation', 0) > 0.5:
            insights.append("Strong correlation between shortcut usage and typing speed")
        
        if data.get('avg_shortcuts_known', 0) < 5:
            insights.append("Users could benefit from shortcut training")
        
        return insights
    
    def _generate_form_recommendations(self, data: dict) -> List[str]:
        """Generate form improvement recommendations"""
        recommendations = []
        
        if data.get('overall_avg_corrections', 0) > 5:
            recommendations.append("High correction rate suggests validation issues")
        
        if data.get('overall_completion_rate', 0) < 0.7:
            recommendations.append("Low completion rate - consider simplifying forms")
        
        return recommendations
    
    async def _detect_typing_pattern(self, conn, user_id: str, days: int) -> Dict:
        """Detect typing pattern from database"""
        # Implementation
        return await self.detect_typing_pattern(user_id, days)
    
    async def _update_session_shortcuts(self, conn, session_id: str):
        """Update session shortcut count"""
        # Implementation
        pass
    
    async def _update_session_forms(self, conn, session_id: str):
        """Update session form completion count"""
        # Implementation
        pass
    
    async def _update_daily_stats(self, conn, session_id: str):
        """Update daily keyboard statistics"""
        # Implementation
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/keyboard", tags=["keyboard-analytics"])

@router.post("/session/start")
async def start_keyboard_session(
    user_id: str,
    page_url: str
):
    """Start keyboard tracking session"""
    analytics = KeyboardAnalytics(db_pool)
    session_id = await analytics.start_keyboard_session(user_id, page_url)
    return {"session_id": session_id}

@router.post("/shortcut")
async def track_shortcut(
    user_id: str,
    session_id: str,
    shortcut_key: str,
    action_type: Optional[str] = None,
    element_context: Optional[str] = None
):
    """Track shortcut usage"""
    analytics = KeyboardAnalytics(db_pool)
    await analytics.track_shortcut_usage(
        user_id, session_id, shortcut_key, action_type, element_context
    )
    return {"status": "tracked"}

@router.post("/form")
async def track_form_interaction(
    user_id: str,
    session_id: str,
    form_id: Optional[str] = None,
    field_name: Optional[str] = None,
    field_type: Optional[str] = None,
    keystrokes: int = 0,
    corrections: int = 0,
    tab_navigations: int = 0,
    paste_events: int = 0,
    time_to_complete: Optional[int] = None,
    completed: bool = False
):
    """Track form keyboard interaction"""
    analytics = KeyboardAnalytics(db_pool)
    interaction_id = await analytics.track_form_interaction(
        user_id, session_id, form_id, field_name, field_type,
        keystrokes, corrections, tab_navigations, paste_events,
        time_to_complete, completed
    )
    return {"interaction_id": interaction_id}

@router.patch("/session/{session_id}")
async def update_keyboard_session(
    session_id: str,
    total_keystrokes: int,
    backspace_count: int = 0,
    delete_count: int = 0,
    copy_paste_count: int = 0,
    tab_navigation_count: int = 0,
    typing_speed_wpm: Optional[float] = None
):
    """Update keyboard session"""
    analytics = KeyboardAnalytics(db_pool)
    await analytics.update_keyboard_session(
        session_id, total_keystrokes, backspace_count,
        delete_count, copy_paste_count, tab_navigation_count,
        typing_speed_wpm
    )
    return {"status": "updated"}

@router.get("/statistics/{user_id}")
async def get_keyboard_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get keyboard statistics"""
    analytics = KeyboardAnalytics(db_pool)
    stats = await analytics.get_keyboard_statistics(user_id, days)
    return stats

@router.get("/pattern/{user_id}")
async def detect_typing_pattern(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect typing pattern"""
    analytics = KeyboardAnalytics(db_pool)
    pattern = await analytics.detect_typing_pattern(user_id, days)
    return pattern

@router.get("/shortcuts/insights")
async def get_shortcut_insights(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get shortcut usage insights"""
    analytics = KeyboardAnalytics(db_pool)
    insights = await analytics.get_shortcut_insights(user_id, days)
    return insights

@router.get("/forms/analysis")
async def get_form_completion_analysis(
    form_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Analyze form completion"""
    analytics = KeyboardAnalytics(db_pool)
    analysis = await analytics.get_form_completion_analysis(form_id, days)
    return analysis

@router.get("/typing-speed/distribution")
async def get_typing_speed_distribution(
    days: int = Query(30, ge=1, le=365)
):
    """Get typing speed distribution"""
    analytics = KeyboardAnalytics(db_pool)
    distribution = await analytics.get_typing_speed_distribution(days)
    return distribution

@router.get("/productivity/trends/{user_id}")
async def get_productivity_trends(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get productivity trends"""
    analytics = KeyboardAnalytics(db_pool)
    trends = await analytics.get_productivity_trends(user_id, days)
    return {"trends": trends}
```

## React Dashboard Components

```tsx
// Keyboard Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, LineChart, BarChart, Table } from '@/components/ui';

interface KeyboardDashboardProps {
  userId?: string;
}

export const KeyboardDashboard: React.FC<KeyboardDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<KeyboardStatistics | null>(null);
  const [pattern, setPattern] = useState<TypingPattern | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [distribution, setDistribution] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKeyboardData();
  }, [userId]);

  const fetchKeyboardData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/keyboard/statistics/${userId}`,
        userId && `/api/analytics/keyboard/pattern/${userId}`,
        userId && `/api/analytics/keyboard/productivity/trends/${userId}`,
        `/api/analytics/keyboard/typing-speed/distribution`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      if (userId) {
        setStats(data[0]);
        setPattern(data[0].typing_pattern);
        setTrends(data[1].trends);
        setDistribution(data[2]);
      } else {
        setDistribution(data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch keyboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading keyboard analytics...</div>;

  return (
    <div className="keyboard-dashboard">
      <h2>Keyboard Interaction Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Total Keystrokes</h3>
              <div className="stat-value">{stats.totalKeystrokes.toLocaleString()}</div>
              <span className="stat-label">
                {stats.avgTypingSpeed.toFixed(0)} WPM avg
              </span>
            </Card>
            
            <Card>
              <h3>Productivity Score</h3>
              <div className="stat-value">{stats.productivityScore.toFixed(0)}</div>
              <Progress 
                value={stats.productivityScore} 
                max={100}
                variant={stats.productivityScore > 70 ? 'success' : 'warning'}
              />
            </Card>
            
            <Card>
              <h3>Shortcut Efficiency</h3>
              <div className="stat-value">{stats.shortcutsEfficiencyScore.toFixed(0)}%</div>
              <Badge variant="info">
                {stats.mostUsedShortcuts.length} shortcuts
              </Badge>
            </Card>
            
            <Card>
              <h3>Form Completion</h3>
              <div className="stat-value">{stats.formCompletionRate.toFixed(1)}%</div>
              <span className="stat-label">
                {stats.errorCorrectionRate.toFixed(1)}% corrections
              </span>
            </Card>
          </Grid>

          {/* Typing Pattern */}
          {pattern && (
            <Card className="mt-4">
              <h3>Typing Pattern Analysis</h3>
              <div className="pattern-display">
                <Badge variant="primary" size="large">
                  {pattern.patternType.replace('_', ' ')}
                </Badge>
                <span className="confidence">
                  {(pattern.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              
              <Grid cols={4} gap={2} className="mt-3">
                <div>
                  <span>Speed</span>
                  <strong>{pattern.characteristics.speed.toFixed(0)} WPM</strong>
                </div>
                <div>
                  <span>Accuracy</span>
                  <strong>{pattern.characteristics.accuracy.toFixed(1)}%</strong>
                </div>
                <div>
                  <span>Shortcut Usage</span>
                  <strong>{pattern.characteristics.shortcutUsage.toFixed(1)}%</strong>
                </div>
                <div>
                  <span>Navigation</span>
                  <strong>{pattern.characteristics.navigationEfficiency.toFixed(1)}%</strong>
                </div>
              </Grid>
            </Card>
          )}

          {/* Most Used Shortcuts */}
          {stats.mostUsedShortcuts.length > 0 && (
            <Card className="mt-4">
              <h3>Most Used Shortcuts</h3>
              <Table>
                <thead>
                  <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                    <th>Usage Count</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.mostUsedShortcuts.slice(0, 10).map((shortcut, idx) => (
                    <tr key={idx}>
                      <td><code>{shortcut.shortcut}</code></td>
                      <td>{shortcut.action || 'N/A'}</td>
                      <td>{shortcut.usage}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          )}
        </>
      )}

      {/* Productivity Trends */}
      {trends.length > 0 && (
        <Card className="mt-4">
          <h3>Productivity Trends</h3>
          <LineChart
            data={trends}
            xKey="date"
            yKeys={['productivity', 'typing_speed', 'shortcuts_score']}
            height={300}
          />
        </Card>
      )}

      {/* Typing Speed Distribution */}
      {distribution && (
        <Card className="mt-4">
          <h3>Typing Speed Distribution</h3>
          <BarChart
            data={distribution.distribution}
            xKey="speed_range"
            yKey="user_count"
            height={300}
          />
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic keystroke counting
2. Shortcut tracking
3. Form interaction tracking
4. Typing speed calculation
5. Pattern detection

## Security Considerations
- No actual keystroke logging
- No password field tracking
- Anonymize sensitive forms
- Respect privacy settings
- Secure session handling

## Performance Optimizations
- Batch keyboard events
- Client-side aggregation
- Efficient shortcut detection
- Cache typing patterns
- Throttle event updates