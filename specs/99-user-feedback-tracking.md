# User Feedback Tracking Specification

## Overview
Track and analyze user feedback including ratings, reviews, suggestions, and bug reports to improve product quality and user satisfaction without storing sensitive personal information.

## Database Schema

### Tables

```sql
-- Feedback submissions
CREATE TABLE feedback_submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    feedback_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    feedback_type VARCHAR(50) NOT NULL, -- rating, review, suggestion, bug, complaint, praise
    category VARCHAR(100), -- feature, performance, ui, documentation, support
    subject VARCHAR(500),
    sentiment_score DECIMAL(3, 2), -- -1 to 1
    rating INTEGER, -- 1-5 stars
    priority VARCHAR(20), -- low, medium, high, critical
    status VARCHAR(50) DEFAULT 'new', -- new, acknowledged, in_progress, resolved, closed
    source VARCHAR(50), -- in_app, email, survey, support_ticket, social
    related_feature VARCHAR(200),
    response_time_hours INTEGER,
    resolution_time_hours INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_feedback_user (user_id, created_at DESC),
    INDEX idx_feedback_type (feedback_type, created_at DESC),
    INDEX idx_feedback_status (status, priority DESC),
    INDEX idx_feedback_sentiment (sentiment_score)
);

-- Feedback responses
CREATE TABLE feedback_responses (
    id BIGSERIAL PRIMARY KEY,
    feedback_id UUID NOT NULL REFERENCES feedback_submissions(feedback_id),
    responder_id UUID,
    response_type VARCHAR(50), -- acknowledgment, clarification, solution, followup
    satisfaction_rating INTEGER, -- 1-5
    was_helpful BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_feedback_responses_feedback (feedback_id)
);

-- Feedback tags and themes
CREATE TABLE feedback_themes (
    id SERIAL PRIMARY KEY,
    theme_name VARCHAR(100) UNIQUE NOT NULL,
    theme_category VARCHAR(50),
    occurrence_count INTEGER DEFAULT 1,
    avg_sentiment DECIMAL(3, 2),
    avg_priority_score DECIMAL(3, 2),
    trending_score DECIMAL(5, 2),
    first_seen DATE DEFAULT CURRENT_DATE,
    last_seen DATE DEFAULT CURRENT_DATE,
    
    INDEX idx_feedback_themes_trending (trending_score DESC),
    INDEX idx_feedback_themes_category (theme_category)
);

-- NPS (Net Promoter Score) tracking
CREATE TABLE nps_scores (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 10),
    category VARCHAR(20) GENERATED ALWAYS AS (
        CASE 
            WHEN score >= 9 THEN 'promoter'
            WHEN score >= 7 THEN 'passive'
            ELSE 'detractor'
        END
    ) STORED,
    feedback_text TEXT,
    survey_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_nps_user (user_id, created_at DESC),
    INDEX idx_nps_score (score),
    INDEX idx_nps_category (category)
);

-- Daily feedback statistics
CREATE TABLE feedback_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_submissions INTEGER DEFAULT 0,
    ratings_count INTEGER DEFAULT 0,
    suggestions_count INTEGER DEFAULT 0,
    bugs_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3, 2),
    avg_sentiment DECIMAL(3, 2),
    nps_score DECIMAL(5, 2),
    response_rate DECIMAL(5, 2),
    avg_response_time_hours DECIMAL(10, 2),
    resolution_rate DECIMAL(5, 2),
    trending_themes TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date),
    INDEX idx_feedback_daily_date (date DESC)
);
```

## TypeScript Interfaces

```typescript
// Feedback submission interface
interface FeedbackSubmission {
  id: string;
  userId: string;
  feedbackId: string;
  feedbackType: 'rating' | 'review' | 'suggestion' | 'bug' | 'complaint' | 'praise';
  category?: string;
  subject?: string;
  sentimentScore: number;
  rating?: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'acknowledged' | 'in_progress' | 'resolved' | 'closed';
  source: string;
  relatedFeature?: string;
  responseTimeHours?: number;
  resolutionTimeHours?: number;
  createdAt: Date;
  resolvedAt?: Date;
}

// Feedback statistics
interface FeedbackStatistics {
  totalSubmissions: number;
  avgRating: number;
  avgSentiment: number;
  npsScore: number;
  responseRate: number;
  resolutionRate: number;
  feedbackByType: TypeDistribution[];
  trendingThemes: Theme[];
  satisfactionTrend: TrendData[];
}

// NPS metrics
interface NPSMetrics {
  score: number;
  promoters: number;
  passives: number;
  detractors: number;
  totalResponses: number;
  trend: 'improving' | 'stable' | 'declining';
  benchmarkComparison: number;
}

// Feedback pattern
interface FeedbackPattern {
  patternType: 'satisfied' | 'engaged' | 'frustrated' | 'silent';
  confidence: number;
  characteristics: {
    feedbackFrequency: number;
    avgSentiment: number;
    primaryType: string;
    responsiveness: number;
  };
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import asyncpg
from textblob import TextBlob  # For sentiment analysis

@dataclass
class FeedbackAnalytics:
    """Analyze user feedback and satisfaction"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.priority_weights = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
    
    async def submit_feedback(
        self,
        user_id: str,
        feedback_type: str,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        rating: Optional[int] = None,
        priority: str = 'medium',
        source: str = 'in_app',
        related_feature: Optional[str] = None
    ) -> str:
        """Submit new feedback"""
        
        # Perform sentiment analysis if content provided
        sentiment_score = 0.0
        if content:
            sentiment_score = self._analyze_sentiment(content)
        
        # Auto-adjust priority based on sentiment for bugs/complaints
        if feedback_type in ['bug', 'complaint'] and sentiment_score < -0.5:
            priority = 'high' if priority == 'medium' else priority
        
        query = """
            INSERT INTO feedback_submissions (
                user_id, feedback_type, category, subject,
                sentiment_score, rating, priority, source,
                related_feature
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING feedback_id
        """
        
        async with self.db.acquire() as conn:
            feedback_id = await conn.fetchval(
                query, user_id, feedback_type, category, subject,
                sentiment_score, rating, priority, source,
                related_feature
            )
            
            # Extract and update themes
            if content:
                await self._extract_themes(conn, content, sentiment_score, priority)
            
            # Update daily stats
            await self._update_daily_stats(conn, feedback_type, rating, sentiment_score)
        
        return feedback_id
    
    async def track_nps_score(
        self,
        user_id: str,
        score: int,
        feedback_text: Optional[str] = None,
        survey_id: Optional[str] = None
    ):
        """Track NPS score"""
        if score < 0 or score > 10:
            raise ValueError("NPS score must be between 0 and 10")
        
        query = """
            INSERT INTO nps_scores (
                user_id, score, feedback_text, survey_id
            ) VALUES ($1, $2, $3, $4)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, user_id, score, feedback_text, survey_id)
            
            # Update daily NPS
            await self._update_daily_nps(conn)
    
    async def update_feedback_status(
        self,
        feedback_id: str,
        status: str,
        responder_id: Optional[str] = None,
        response_type: Optional[str] = None
    ):
        """Update feedback status"""
        query = """
            UPDATE feedback_submissions
            SET status = $2,
                response_time_hours = CASE 
                    WHEN status = 'new' AND $2 != 'new'
                    THEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / 3600
                    ELSE response_time_hours
                END,
                resolution_time_hours = CASE 
                    WHEN $2 IN ('resolved', 'closed')
                    THEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / 3600
                    ELSE resolution_time_hours
                END,
                resolved_at = CASE 
                    WHEN $2 IN ('resolved', 'closed')
                    THEN CURRENT_TIMESTAMP
                    ELSE resolved_at
                END
            WHERE feedback_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, feedback_id, status)
            
            # Track response if provided
            if responder_id and response_type:
                await self._track_response(
                    conn, feedback_id, responder_id, response_type
                )
    
    async def get_feedback_statistics(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get feedback statistics"""
        query = """
            WITH feedback_stats AS (
                SELECT 
                    COUNT(*) as total_submissions,
                    AVG(rating) as avg_rating,
                    AVG(sentiment_score) as avg_sentiment,
                    COUNT(*) FILTER (WHERE feedback_type = 'rating') as ratings,
                    COUNT(*) FILTER (WHERE feedback_type = 'suggestion') as suggestions,
                    COUNT(*) FILTER (WHERE feedback_type = 'bug') as bugs,
                    COUNT(*) FILTER (WHERE status != 'new') as responded,
                    COUNT(*) FILTER (WHERE status IN ('resolved', 'closed')) as resolved,
                    AVG(response_time_hours) as avg_response_time,
                    AVG(resolution_time_hours) as avg_resolution_time
                FROM feedback_submissions
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
            ),
            type_distribution AS (
                SELECT 
                    feedback_type,
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_sentiment
                FROM feedback_submissions
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY feedback_type
            ),
            trending AS (
                SELECT 
                    theme_name,
                    occurrence_count,
                    avg_sentiment,
                    trending_score
                FROM feedback_themes
                WHERE last_seen >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY trending_score DESC
                LIMIT 10
            )
            SELECT 
                fs.*,
                (SELECT json_agg(json_build_object(
                    'type', feedback_type,
                    'count', count,
                    'sentiment', avg_sentiment
                )) FROM type_distribution) as type_dist,
                (SELECT json_agg(json_build_object(
                    'theme', theme_name,
                    'count', occurrence_count,
                    'sentiment', avg_sentiment,
                    'score', trending_score
                )) FROM trending) as themes,
                (SELECT nps_score FROM feedback_daily_stats 
                 WHERE date = CURRENT_DATE) as current_nps
            FROM feedback_stats fs
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                row = await conn.fetchrow(
                    query % (days, user_filter, days, user_filter, days),
                    user_id
                )
            else:
                row = await conn.fetchrow(
                    query % (days, user_filter, days, user_filter, days)
                )
            
            if not row:
                return self._empty_statistics()
            
            # Get satisfaction trend
            trend = await self._get_satisfaction_trend(conn, days)
            
            return {
                'total_submissions': row['total_submissions'] or 0,
                'avg_rating': float(row['avg_rating'] or 0),
                'avg_sentiment': float(row['avg_sentiment'] or 0),
                'nps_score': float(row['current_nps'] or 0),
                'response_rate': (
                    row['responded'] / row['total_submissions'] * 100
                    if row['total_submissions'] > 0 else 0
                ),
                'resolution_rate': (
                    row['resolved'] / row['total_submissions'] * 100
                    if row['total_submissions'] > 0 else 0
                ),
                'feedback_by_type': row['type_dist'] or [],
                'trending_themes': row['themes'] or [],
                'satisfaction_trend': trend
            }
    
    async def get_nps_metrics(
        self,
        days: int = 30
    ) -> Dict:
        """Get NPS metrics"""
        query = """
            WITH nps_data AS (
                SELECT 
                    score,
                    category,
                    COUNT(*) as count
                FROM nps_scores
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY score, category
            ),
            nps_calc AS (
                SELECT 
                    SUM(CASE WHEN category = 'promoter' THEN count ELSE 0 END) as promoters,
                    SUM(CASE WHEN category = 'passive' THEN count ELSE 0 END) as passives,
                    SUM(CASE WHEN category = 'detractor' THEN count ELSE 0 END) as detractors,
                    SUM(count) as total
                FROM nps_data
            ),
            trend_data AS (
                SELECT 
                    AVG(score) as avg_score,
                    DATE(created_at) as date
                FROM nps_scores
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date
            )
            SELECT 
                nc.*,
                (nc.promoters::float / nc.total * 100 - 
                 nc.detractors::float / nc.total * 100) as nps_score,
                array_agg(td.avg_score ORDER BY td.date) as daily_scores
            FROM nps_calc nc
            CROSS JOIN trend_data td
            GROUP BY nc.promoters, nc.passives, nc.detractors, nc.total
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days))
            
            if not row or not row['total']:
                return self._empty_nps_metrics()
            
            # Determine trend
            trend = self._determine_nps_trend(row['daily_scores'])
            
            # Industry benchmark (example: 30 for SaaS)
            benchmark = 30
            
            return {
                'score': float(row['nps_score']),
                'promoters': row['promoters'],
                'passives': row['passives'],
                'detractors': row['detractors'],
                'total_responses': row['total'],
                'trend': trend,
                'benchmark_comparison': float(row['nps_score']) - benchmark
            }
    
    async def detect_feedback_pattern(
        self,
        user_id: str,
        days: int = 90
    ) -> Dict:
        """Detect user feedback pattern"""
        query = """
            SELECT 
                COUNT(*) as feedback_count,
                COUNT(*)::float / $2 as daily_frequency,
                AVG(sentiment_score) as avg_sentiment,
                AVG(rating) as avg_rating,
                MODE() WITHIN GROUP (ORDER BY feedback_type) as primary_type,
                COUNT(*) FILTER (WHERE response_time_hours IS NOT NULL) as responded_count
            FROM feedback_submissions
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % days, user_id, days)
            
            if not row or not row['feedback_count']:
                return {'pattern_type': 'silent', 'confidence': 0.5}
            
            pattern = self._determine_feedback_pattern(
                row['daily_frequency'] or 0,
                row['avg_sentiment'] or 0,
                row['avg_rating'] or 0,
                row['primary_type'] or 'unknown',
                row['responded_count'] / row['feedback_count'] if row['feedback_count'] > 0 else 0
            )
            
            return pattern
    
    async def get_theme_analysis(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Analyze feedback themes"""
        query = """
            SELECT 
                theme_name,
                theme_category,
                occurrence_count,
                avg_sentiment,
                avg_priority_score,
                trending_score,
                last_seen
            FROM feedback_themes
            WHERE 1=1
                %s
            ORDER BY trending_score DESC
            LIMIT $1
        """
        
        category_filter = "AND theme_category = $2" if category else ""
        
        async with self.db.acquire() as conn:
            if category:
                rows = await conn.fetch(query % category_filter, limit, category)
            else:
                rows = await conn.fetch(query % category_filter, limit)
            
            return [
                {
                    'theme': row['theme_name'],
                    'category': row['theme_category'],
                    'occurrences': row['occurrence_count'],
                    'sentiment': float(row['avg_sentiment']),
                    'priority': float(row['avg_priority_score']),
                    'trending_score': float(row['trending_score']),
                    'last_seen': row['last_seen'].isoformat(),
                    'urgency': self._calculate_theme_urgency(row)
                }
                for row in rows
            ]
    
    async def get_response_metrics(
        self,
        days: int = 30
    ) -> Dict:
        """Get feedback response metrics"""
        query = """
            WITH response_data AS (
                SELECT 
                    feedback_type,
                    priority,
                    AVG(response_time_hours) as avg_response_time,
                    AVG(resolution_time_hours) as avg_resolution_time,
                    COUNT(*) FILTER (WHERE response_time_hours IS NOT NULL) as responded,
                    COUNT(*) as total
                FROM feedback_submissions
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY feedback_type, priority
            )
            SELECT 
                feedback_type,
                priority,
                avg_response_time,
                avg_resolution_time,
                responded::float / total * 100 as response_rate
            FROM response_data
            ORDER BY priority DESC, feedback_type
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days)
            
            # Group by priority
            by_priority = defaultdict(list)
            for row in rows:
                by_priority[row['priority']].append({
                    'type': row['feedback_type'],
                    'avg_response_time': float(row['avg_response_time'] or 0),
                    'avg_resolution_time': float(row['avg_resolution_time'] or 0),
                    'response_rate': float(row['response_rate'] or 0)
                })
            
            return {
                'by_priority': dict(by_priority),
                'overall_avg_response': self._calculate_overall_avg(rows, 'avg_response_time'),
                'overall_avg_resolution': self._calculate_overall_avg(rows, 'avg_resolution_time'),
                'sla_compliance': self._calculate_sla_compliance(rows)
            }
    
    async def get_user_satisfaction_score(
        self,
        user_id: str
    ) -> Dict:
        """Calculate user satisfaction score"""
        query = """
            WITH user_feedback AS (
                SELECT 
                    AVG(rating) as avg_rating,
                    AVG(sentiment_score) as avg_sentiment,
                    COUNT(*) FILTER (WHERE status IN ('resolved', 'closed')) as resolved,
                    COUNT(*) as total
                FROM feedback_submissions
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days'
            ),
            user_nps AS (
                SELECT AVG(score) as avg_nps
                FROM nps_scores
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days'
            )
            SELECT 
                uf.*,
                un.avg_nps
            FROM user_feedback uf
            CROSS JOIN user_nps un
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                return {'satisfaction_score': 0, 'components': {}}
            
            # Calculate composite satisfaction score
            score = self._calculate_satisfaction_score(
                row['avg_rating'],
                row['avg_sentiment'],
                row['avg_nps'],
                row['resolved'] / row['total'] if row['total'] > 0 else 0
            )
            
            return {
                'satisfaction_score': score,
                'components': {
                    'rating': float(row['avg_rating'] or 0),
                    'sentiment': float(row['avg_sentiment'] or 0),
                    'nps': float(row['avg_nps'] or 0),
                    'resolution_rate': (row['resolved'] / row['total'] * 100) if row['total'] > 0 else 0
                },
                'level': self._get_satisfaction_level(score)
            }
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_submissions': 0,
            'avg_rating': 0,
            'avg_sentiment': 0,
            'nps_score': 0,
            'response_rate': 0,
            'resolution_rate': 0,
            'feedback_by_type': [],
            'trending_themes': [],
            'satisfaction_trend': []
        }
    
    def _empty_nps_metrics(self) -> Dict:
        """Return empty NPS metrics"""
        return {
            'score': 0,
            'promoters': 0,
            'passives': 0,
            'detractors': 0,
            'total_responses': 0,
            'trend': 'stable',
            'benchmark_comparison': 0
        }
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text"""
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity  # Returns -1 to 1
        except:
            return 0.0
    
    def _determine_feedback_pattern(
        self,
        frequency: float,
        sentiment: float,
        rating: float,
        primary_type: str,
        responsiveness: float
    ) -> Dict:
        """Determine user feedback pattern"""
        
        # Satisfied: positive sentiment, high ratings
        if sentiment > 0.3 and rating >= 4:
            pattern_type = 'satisfied'
            confidence = 0.8
        
        # Engaged: frequent feedback, mixed sentiment
        elif frequency > 0.1:
            pattern_type = 'engaged'
            confidence = 0.75
        
        # Frustrated: negative sentiment, bugs/complaints
        elif sentiment < -0.3 or primary_type in ['bug', 'complaint']:
            pattern_type = 'frustrated'
            confidence = 0.8
        
        # Silent: very low frequency
        else:
            pattern_type = 'silent'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'feedback_frequency': frequency,
                'avg_sentiment': sentiment,
                'primary_type': primary_type,
                'responsiveness': responsiveness * 100
            }
        }
    
    def _determine_nps_trend(self, daily_scores: List) -> str:
        """Determine NPS trend"""
        if not daily_scores or len(daily_scores) < 7:
            return 'stable'
        
        # Compare first half vs second half
        mid = len(daily_scores) // 2
        first_half = sum(daily_scores[:mid]) / mid
        second_half = sum(daily_scores[mid:]) / len(daily_scores[mid:])
        
        if second_half > first_half + 5:
            return 'improving'
        elif second_half < first_half - 5:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_theme_urgency(self, theme_row) -> str:
        """Calculate theme urgency based on metrics"""
        score = (
            theme_row['trending_score'] * 0.4 +
            (1 - (theme_row['avg_sentiment'] + 1) / 2) * 0.3 +  # Negative sentiment = higher urgency
            theme_row['avg_priority_score'] * 0.3
        )
        
        if score > 3:
            return 'critical'
        elif score > 2:
            return 'high'
        elif score > 1:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_satisfaction_score(
        self,
        rating: Optional[float],
        sentiment: Optional[float],
        nps: Optional[float],
        resolution_rate: float
    ) -> float:
        """Calculate composite satisfaction score"""
        score = 0
        components = 0
        
        if rating:
            score += (rating / 5) * 100 * 0.3
            components += 0.3
        
        if sentiment is not None:
            score += ((sentiment + 1) / 2) * 100 * 0.2
            components += 0.2
        
        if nps:
            score += (nps / 10) * 100 * 0.3
            components += 0.3
        
        score += resolution_rate * 100 * 0.2
        components += 0.2
        
        return score / components if components > 0 else 0
    
    def _get_satisfaction_level(self, score: float) -> str:
        """Get satisfaction level from score"""
        if score >= 85:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'fair'
        elif score >= 30:
            return 'poor'
        else:
            return 'critical'
    
    def _calculate_overall_avg(self, rows: List, field: str) -> float:
        """Calculate weighted average"""
        # Implementation
        return 0
    
    def _calculate_sla_compliance(self, rows: List) -> float:
        """Calculate SLA compliance rate"""
        # Implementation based on response time targets
        return 0
    
    async def _extract_themes(
        self,
        conn,
        content: str,
        sentiment: float,
        priority: str
    ):
        """Extract and update themes from feedback"""
        # Implementation for theme extraction
        pass
    
    async def _track_response(
        self,
        conn,
        feedback_id: str,
        responder_id: str,
        response_type: str
    ):
        """Track feedback response"""
        # Implementation
        pass
    
    async def _update_daily_stats(
        self,
        conn,
        feedback_type: str,
        rating: Optional[int],
        sentiment: float
    ):
        """Update daily feedback statistics"""
        # Implementation
        pass
    
    async def _update_daily_nps(self, conn):
        """Update daily NPS score"""
        # Implementation
        pass
    
    async def _get_satisfaction_trend(
        self,
        conn,
        days: int
    ) -> List[Dict]:
        """Get satisfaction trend data"""
        # Implementation
        return []
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/feedback", tags=["feedback-analytics"])

@router.post("/submit")
async def submit_feedback(
    user_id: str,
    feedback_type: str,
    category: Optional[str] = None,
    subject: Optional[str] = None,
    content: Optional[str] = None,
    rating: Optional[int] = None,
    priority: str = "medium",
    source: str = "in_app",
    related_feature: Optional[str] = None
):
    """Submit feedback"""
    analytics = FeedbackAnalytics(db_pool)
    feedback_id = await analytics.submit_feedback(
        user_id, feedback_type, category, subject,
        content, rating, priority, source, related_feature
    )
    return {"feedback_id": feedback_id}

@router.post("/nps")
async def track_nps(
    user_id: str,
    score: int,
    feedback_text: Optional[str] = None,
    survey_id: Optional[str] = None
):
    """Track NPS score"""
    analytics = FeedbackAnalytics(db_pool)
    await analytics.track_nps_score(user_id, score, feedback_text, survey_id)
    return {"status": "tracked"}

@router.patch("/{feedback_id}/status")
async def update_status(
    feedback_id: str,
    status: str,
    responder_id: Optional[str] = None,
    response_type: Optional[str] = None
):
    """Update feedback status"""
    analytics = FeedbackAnalytics(db_pool)
    await analytics.update_feedback_status(
        feedback_id, status, responder_id, response_type
    )
    return {"status": "updated"}

@router.get("/statistics")
async def get_statistics(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get feedback statistics"""
    analytics = FeedbackAnalytics(db_pool)
    stats = await analytics.get_feedback_statistics(user_id, days)
    return stats

@router.get("/nps-metrics")
async def get_nps_metrics(
    days: int = Query(30, ge=1, le=365)
):
    """Get NPS metrics"""
    analytics = FeedbackAnalytics(db_pool)
    metrics = await analytics.get_nps_metrics(days)
    return metrics

@router.get("/pattern/{user_id}")
async def detect_pattern(
    user_id: str,
    days: int = Query(90, ge=1, le=365)
):
    """Detect feedback pattern"""
    analytics = FeedbackAnalytics(db_pool)
    pattern = await analytics.detect_feedback_pattern(user_id, days)
    return pattern

@router.get("/themes")
async def get_themes(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Get theme analysis"""
    analytics = FeedbackAnalytics(db_pool)
    themes = await analytics.get_theme_analysis(category, limit)
    return {"themes": themes}

@router.get("/response-metrics")
async def get_response_metrics(
    days: int = Query(30, ge=1, le=365)
):
    """Get response metrics"""
    analytics = FeedbackAnalytics(db_pool)
    metrics = await analytics.get_response_metrics(days)
    return metrics

@router.get("/satisfaction/{user_id}")
async def get_satisfaction_score(user_id: str):
    """Get user satisfaction score"""
    analytics = FeedbackAnalytics(db_pool)
    score = await analytics.get_user_satisfaction_score(user_id)
    return score
```

## React Dashboard Components

```tsx
// Feedback Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, LineChart, GaugeChart } from '@/components/ui';

interface FeedbackDashboardProps {
  userId?: string;
}

export const FeedbackDashboard: React.FC<FeedbackDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<FeedbackStatistics | null>(null);
  const [nps, setNps] = useState<NPSMetrics | null>(null);
  const [themes, setThemes] = useState<any[]>([]);
  const [satisfaction, setSatisfaction] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFeedbackData();
  }, [userId]);

  const fetchFeedbackData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        `/api/analytics/feedback/statistics${userId ? `?user_id=${userId}` : ''}`,
        `/api/analytics/feedback/nps-metrics`,
        `/api/analytics/feedback/themes`,
        userId && `/api/analytics/feedback/satisfaction/${userId}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      setStats(data[0]);
      setNps(data[1]);
      setThemes(data[2].themes);
      if (userId) {
        setSatisfaction(data[3]);
      }
    } catch (error) {
      console.error('Failed to fetch feedback data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading feedback analytics...</div>;

  return (
    <div className="feedback-dashboard">
      <h2>Feedback & Satisfaction Analytics</h2>
      
      {/* Summary Stats */}
      <Grid cols={4} gap={4}>
        <Card>
          <h3>Total Feedback</h3>
          <div className="stat-value">{stats?.totalSubmissions || 0}</div>
          <div className="stat-rates">
            <span>Response: {stats?.responseRate.toFixed(1)}%</span>
            <span>Resolution: {stats?.resolutionRate.toFixed(1)}%</span>
          </div>
        </Card>
        
        <Card>
          <h3>Avg Rating</h3>
          <div className="rating-display">
            <div className="stat-value">{stats?.avgRating.toFixed(1)}/5</div>
            <div className="stars">
              {[...Array(5)].map((_, i) => (
                <span key={i} className={i < Math.round(stats?.avgRating || 0) ? 'filled' : 'empty'}>
                  ⭐
                </span>
              ))}
            </div>
          </div>
        </Card>
        
        <Card>
          <h3>NPS Score</h3>
          <GaugeChart value={nps?.score || 0} min={-100} max={100} />
          <Badge variant={nps?.trend === 'improving' ? 'success' : 
                        nps?.trend === 'declining' ? 'danger' : 'info'}>
            {nps?.trend}
          </Badge>
        </Card>
        
        <Card>
          <h3>Sentiment</h3>
          <Progress 
            value={(stats?.avgSentiment + 1) * 50} 
            max={100}
            variant={stats?.avgSentiment > 0 ? 'success' : 'warning'}
          />
          <span>{stats?.avgSentiment > 0 ? 'Positive' : 'Needs Attention'}</span>
        </Card>
      </Grid>

      {/* NPS Breakdown */}
      {nps && (
        <Card className="mt-4">
          <h3>NPS Distribution</h3>
          <div className="nps-breakdown">
            <div className="nps-category">
              <Badge variant="success">Promoters</Badge>
              <strong>{nps.promoters}</strong>
              <span>{((nps.promoters / nps.totalResponses) * 100).toFixed(1)}%</span>
            </div>
            <div className="nps-category">
              <Badge variant="warning">Passives</Badge>
              <strong>{nps.passives}</strong>
              <span>{((nps.passives / nps.totalResponses) * 100).toFixed(1)}%</span>
            </div>
            <div className="nps-category">
              <Badge variant="danger">Detractors</Badge>
              <strong>{nps.detractors}</strong>
              <span>{((nps.detractors / nps.totalResponses) * 100).toFixed(1)}%</span>
            </div>
          </div>
          <div className="benchmark-comparison">
            Industry Benchmark: {nps.benchmarkComparison > 0 ? '+' : ''}{nps.benchmarkComparison.toFixed(1)}
          </div>
        </Card>
      )}

      {/* Trending Themes */}
      {themes.length > 0 && (
        <Card className="mt-4">
          <h3>Trending Themes</h3>
          <div className="themes-list">
            {themes.slice(0, 10).map((theme, idx) => (
              <div key={idx} className="theme-item">
                <Badge variant={theme.urgency === 'critical' ? 'danger' : 
                              theme.urgency === 'high' ? 'warning' : 'info'}>
                  {theme.urgency}
                </Badge>
                <span className="theme-name">{theme.theme}</span>
                <div className="theme-metrics">
                  <span>Occurrences: {theme.occurrences}</span>
                  <span>Sentiment: {theme.sentiment.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* User Satisfaction */}
      {satisfaction && (
        <Card className="mt-4">
          <h3>User Satisfaction Score</h3>
          <div className="satisfaction-score">
            <div className="score-value">{satisfaction.satisfactionScore.toFixed(0)}</div>
            <Badge variant={satisfaction.level === 'excellent' ? 'success' :
                          satisfaction.level === 'good' ? 'info' :
                          satisfaction.level === 'fair' ? 'warning' : 'danger'}>
              {satisfaction.level}
            </Badge>
          </div>
          <Grid cols={4} gap={2} className="mt-3">
            <div>
              <span>Rating</span>
              <strong>{satisfaction.components.rating.toFixed(1)}/5</strong>
            </div>
            <div>
              <span>Sentiment</span>
              <strong>{satisfaction.components.sentiment.toFixed(2)}</strong>
            </div>
            <div>
              <span>NPS</span>
              <strong>{satisfaction.components.nps.toFixed(0)}</strong>
            </div>
            <div>
              <span>Resolution</span>
              <strong>{satisfaction.components.resolutionRate.toFixed(0)}%</strong>
            </div>
          </Grid>
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic feedback submission
2. Sentiment analysis
3. NPS tracking
4. Theme extraction
5. Response metrics

## Security Considerations
- Anonymize feedback content
- Secure sentiment analysis
- Respect privacy settings
- Role-based access to feedback
- Audit trail for responses

## Performance Optimizations
- Batch sentiment analysis
- Cache theme calculations
- Daily aggregation for stats
- Efficient NPS calculations
- Async theme extraction