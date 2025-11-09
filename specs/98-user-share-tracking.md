# User Share Tracking Specification

## Overview
Track user content sharing behavior including social shares, internal shares, and collaboration patterns to understand content virality and team dynamics without storing shared content.

## Database Schema

### Tables

```sql
-- Share events tracking
CREATE TABLE share_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    share_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    content_id VARCHAR(200),
    content_type VARCHAR(50), -- document, link, image, video, post, file
    share_method VARCHAR(50), -- email, link, social, direct, team
    share_platform VARCHAR(50), -- email, slack, teams, twitter, linkedin, etc.
    recipients_count INTEGER DEFAULT 1,
    recipient_type VARCHAR(50), -- individual, team, public, organization
    share_scope VARCHAR(50), -- internal, external, public
    permissions_granted VARCHAR(50), -- view, edit, comment, download
    expiry_date TIMESTAMP WITH TIME ZONE,
    is_reshare BOOLEAN DEFAULT false,
    original_share_id UUID,
    share_successful BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_share_events_user (user_id, created_at DESC),
    INDEX idx_share_events_content (content_id),
    INDEX idx_share_events_platform (share_platform)
);

-- Share engagement tracking
CREATE TABLE share_engagement (
    id BIGSERIAL PRIMARY KEY,
    share_id UUID NOT NULL REFERENCES share_events(share_id),
    engagement_type VARCHAR(50), -- viewed, downloaded, edited, reshared, liked
    engaged_user_id UUID,
    engagement_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    time_to_engage_seconds INTEGER,
    
    INDEX idx_share_engagement_share (share_id),
    INDEX idx_share_engagement_type (engagement_type)
);

-- Content virality metrics
CREATE TABLE content_virality (
    id SERIAL PRIMARY KEY,
    content_id VARCHAR(200) UNIQUE NOT NULL,
    content_type VARCHAR(50),
    total_shares INTEGER DEFAULT 0,
    unique_sharers INTEGER DEFAULT 0,
    total_reshares INTEGER DEFAULT 0,
    viral_coefficient DECIMAL(5, 2),
    reach_count INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5, 2),
    peak_share_time TIMESTAMP WITH TIME ZONE,
    viral_score DECIMAL(5, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_virality_content (content_id),
    INDEX idx_virality_score (viral_score DESC)
);

-- Daily share statistics
CREATE TABLE share_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_shares INTEGER DEFAULT 0,
    internal_shares INTEGER DEFAULT 0,
    external_shares INTEGER DEFAULT 0,
    social_shares INTEGER DEFAULT 0,
    unique_recipients INTEGER DEFAULT 0,
    content_items_shared INTEGER DEFAULT 0,
    most_used_platform VARCHAR(50),
    avg_recipients_per_share DECIMAL(5, 2),
    reshare_rate DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_share_daily_stats_date (date DESC),
    INDEX idx_share_daily_stats_user (user_id, date DESC)
);
```

## TypeScript Interfaces

```typescript
// Share event interface
interface ShareEvent {
  id: string;
  userId: string;
  shareId: string;
  contentId?: string;
  contentType?: 'document' | 'link' | 'image' | 'video' | 'post' | 'file';
  shareMethod: 'email' | 'link' | 'social' | 'direct' | 'team';
  sharePlatform?: string;
  recipientsCount: number;
  recipientType: 'individual' | 'team' | 'public' | 'organization';
  shareScope: 'internal' | 'external' | 'public';
  permissionsGranted?: 'view' | 'edit' | 'comment' | 'download';
  expiryDate?: Date;
  isReshare: boolean;
  originalShareId?: string;
  shareSuccessful: boolean;
  createdAt: Date;
}

// Share statistics
interface ShareStatistics {
  totalShares: number;
  internalShares: number;
  externalShares: number;
  socialShares: number;
  uniqueRecipients: number;
  contentItemsShared: number;
  mostUsedPlatforms: PlatformUsage[];
  sharePattern: SharePattern;
  viralContent: ViralContent[];
}

// Share pattern
interface SharePattern {
  patternType: 'broadcaster' | 'collaborator' | 'curator' | 'minimal';
  confidence: number;
  characteristics: {
    avgRecipientsPerShare: number;
    shareFrequency: number;
    reshareRate: number;
    externalShareRate: number;
  };
}

// Viral content metrics
interface ViralContent {
  contentId: string;
  contentType: string;
  totalShares: number;
  uniqueSharers: number;
  viralCoefficient: number;
  reachCount: number;
  engagementRate: number;
  viralScore: number;
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
class ShareAnalytics:
    """Analyze content sharing patterns and virality"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.virality_threshold = 1.0  # Viral coefficient threshold
    
    async def track_share_event(
        self,
        user_id: str,
        content_id: Optional[str],
        content_type: Optional[str],
        share_method: str,
        share_platform: Optional[str],
        recipients_count: int = 1,
        recipient_type: str = 'individual',
        share_scope: str = 'internal',
        permissions: Optional[str] = 'view',
        expiry_date: Optional[datetime] = None,
        is_reshare: bool = False,
        original_share_id: Optional[str] = None
    ) -> str:
        """Track a share event"""
        query = """
            INSERT INTO share_events (
                user_id, content_id, content_type, share_method,
                share_platform, recipients_count, recipient_type,
                share_scope, permissions_granted, expiry_date,
                is_reshare, original_share_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING share_id
        """
        
        async with self.db.acquire() as conn:
            share_id = await conn.fetchval(
                query, user_id, content_id, content_type, share_method,
                share_platform, recipients_count, recipient_type,
                share_scope, permissions, expiry_date,
                is_reshare, original_share_id
            )
            
            # Update virality metrics if content_id exists
            if content_id:
                await self._update_virality_metrics(
                    conn, content_id, content_type, is_reshare
                )
            
            # Update daily stats
            await self._update_daily_stats(conn, user_id)
        
        return share_id
    
    async def track_share_engagement(
        self,
        share_id: str,
        engagement_type: str,
        engaged_user_id: Optional[str] = None,
        time_to_engage: Optional[int] = None
    ):
        """Track engagement with shared content"""
        query = """
            INSERT INTO share_engagement (
                share_id, engagement_type, engaged_user_id,
                time_to_engage_seconds
            ) VALUES ($1, $2, $3, $4)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query, share_id, engagement_type, 
                engaged_user_id, time_to_engage
            )
            
            # Update virality engagement metrics
            await self._update_engagement_metrics(conn, share_id)
    
    async def get_share_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user share statistics"""
        query = """
            WITH share_stats AS (
                SELECT 
                    COUNT(*) as total_shares,
                    COUNT(*) FILTER (WHERE share_scope = 'internal') as internal_shares,
                    COUNT(*) FILTER (WHERE share_scope = 'external') as external_shares,
                    COUNT(*) FILTER (WHERE share_method = 'social') as social_shares,
                    SUM(recipients_count) as total_recipients,
                    COUNT(DISTINCT content_id) as unique_content,
                    COUNT(*) FILTER (WHERE is_reshare) as reshares,
                    AVG(recipients_count) as avg_recipients
                FROM share_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            platform_usage AS (
                SELECT 
                    share_platform,
                    COUNT(*) as usage_count
                FROM share_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND share_platform IS NOT NULL
                GROUP BY share_platform
                ORDER BY usage_count DESC
                LIMIT 5
            ),
            viral_content AS (
                SELECT 
                    cv.content_id,
                    cv.content_type,
                    cv.total_shares,
                    cv.viral_coefficient,
                    cv.viral_score
                FROM content_virality cv
                JOIN share_events se ON cv.content_id = se.content_id
                WHERE se.user_id = $1
                    AND se.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                ORDER BY cv.viral_score DESC
                LIMIT 5
            )
            SELECT 
                s.*,
                (SELECT json_agg(json_build_object(
                    'platform', share_platform,
                    'count', usage_count
                )) FROM platform_usage) as platforms,
                (SELECT json_agg(json_build_object(
                    'content_id', content_id,
                    'type', content_type,
                    'shares', total_shares,
                    'viral_coefficient', viral_coefficient,
                    'score', viral_score
                )) FROM viral_content) as viral_items
            FROM share_stats s
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days, days), user_id)
            
            if not row:
                return self._empty_statistics()
            
            # Detect share pattern
            pattern = await self._detect_share_pattern(conn, user_id, days)
            
            return {
                'total_shares': row['total_shares'] or 0,
                'internal_shares': row['internal_shares'] or 0,
                'external_shares': row['external_shares'] or 0,
                'social_shares': row['social_shares'] or 0,
                'unique_recipients': row['total_recipients'] or 0,
                'content_items_shared': row['unique_content'] or 0,
                'most_used_platforms': row['platforms'] or [],
                'share_pattern': pattern,
                'viral_content': row['viral_items'] or []
            }
    
    async def detect_share_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user sharing pattern"""
        query = """
            SELECT 
                AVG(recipients_count) as avg_recipients,
                COUNT(*)::float / $2 as daily_shares,
                SUM(CASE WHEN is_reshare THEN 1 ELSE 0 END)::float / COUNT(*) as reshare_ratio,
                SUM(CASE WHEN share_scope = 'external' THEN 1 ELSE 0 END)::float / COUNT(*) as external_ratio,
                COUNT(DISTINCT share_platform) as platform_diversity
            FROM share_events
            WHERE user_id = $1
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % days, user_id, days)
            
            if not row or row['daily_shares'] == 0:
                return {'pattern_type': 'minimal', 'confidence': 0.5}
            
            pattern = self._determine_share_pattern(
                row['avg_recipients'] or 1,
                row['daily_shares'] or 0,
                row['reshare_ratio'] or 0,
                row['external_ratio'] or 0,
                row['platform_diversity'] or 1
            )
            
            return pattern
    
    async def get_virality_metrics(
        self,
        content_id: str
    ) -> Dict:
        """Get content virality metrics"""
        query = """
            SELECT 
                content_type,
                total_shares,
                unique_sharers,
                total_reshares,
                viral_coefficient,
                reach_count,
                engagement_rate,
                viral_score
            FROM content_virality
            WHERE content_id = $1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, content_id)
            
            if not row:
                # Calculate from share events
                metrics = await self._calculate_virality_metrics(conn, content_id)
                return metrics
            
            return {
                'content_id': content_id,
                'content_type': row['content_type'],
                'total_shares': row['total_shares'],
                'unique_sharers': row['unique_sharers'],
                'total_reshares': row['total_reshares'],
                'viral_coefficient': float(row['viral_coefficient']),
                'reach_count': row['reach_count'],
                'engagement_rate': float(row['engagement_rate']),
                'viral_score': float(row['viral_score']),
                'is_viral': float(row['viral_coefficient']) > self.virality_threshold
            }
    
    async def get_share_network(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user's sharing network"""
        query = """
            WITH share_connections AS (
                SELECT 
                    se1.user_id as sharer,
                    se2.user_id as resharer,
                    COUNT(*) as share_count
                FROM share_events se1
                JOIN share_events se2 ON se1.share_id = se2.original_share_id
                WHERE se1.user_id = $1
                    AND se1.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY se1.user_id, se2.user_id
            ),
            recipient_patterns AS (
                SELECT 
                    recipient_type,
                    COUNT(*) as count,
                    AVG(recipients_count) as avg_size
                FROM share_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY recipient_type
            )
            SELECT 
                (SELECT COUNT(DISTINCT resharer) FROM share_connections) as network_size,
                (SELECT SUM(share_count) FROM share_connections) as total_reshares,
                (SELECT json_agg(json_build_object(
                    'type', recipient_type,
                    'count', count,
                    'avg_size', avg_size
                )) FROM recipient_patterns) as recipient_patterns
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            return {
                'network_size': row['network_size'] or 0,
                'total_reshares_generated': row['total_reshares'] or 0,
                'influence_score': self._calculate_influence_score(
                    row['network_size'] or 0,
                    row['total_reshares'] or 0
                ),
                'recipient_patterns': row['recipient_patterns'] or []
            }
    
    async def get_share_timing_analysis(
        self,
        user_id: Optional[str] = None
    ) -> Dict:
        """Analyze optimal sharing times"""
        query = """
            WITH share_timing AS (
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    EXTRACT(DOW FROM created_at) as day_of_week,
                    COUNT(*) as share_count,
                    AVG(recipients_count) as avg_reach
                FROM share_events se
                LEFT JOIN share_engagement eng ON se.share_id = eng.share_id
                WHERE 1=1
                    %s
                    AND se.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM created_at), EXTRACT(DOW FROM created_at)
            ),
            engagement_timing AS (
                SELECT 
                    EXTRACT(HOUR FROM se.created_at) as share_hour,
                    COUNT(eng.id) as engagement_count
                FROM share_events se
                JOIN share_engagement eng ON se.share_id = eng.share_id
                WHERE 1=1
                    %s
                    AND se.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM se.created_at)
            )
            SELECT 
                (SELECT json_agg(json_build_object(
                    'hour', hour,
                    'day', day_of_week,
                    'shares', share_count,
                    'avg_reach', avg_reach
                ) ORDER BY share_count DESC) FROM share_timing) as timing_data,
                (SELECT json_agg(json_build_object(
                    'hour', share_hour,
                    'engagements', engagement_count
                ) ORDER BY engagement_count DESC) FROM engagement_timing) as engagement_data
        """
        
        user_filter = "AND se.user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                row = await conn.fetchrow(query % (user_filter, user_filter), user_id)
            else:
                row = await conn.fetchrow(query % (user_filter, user_filter))
            
            # Find optimal times
            optimal_times = self._find_optimal_share_times(
                row['timing_data'] or [],
                row['engagement_data'] or []
            )
            
            return {
                'timing_distribution': row['timing_data'] or [],
                'engagement_by_hour': row['engagement_data'] or [],
                'optimal_share_times': optimal_times
            }
    
    async def get_collaboration_metrics(
        self,
        team_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get team collaboration metrics"""
        query = """
            WITH team_shares AS (
                SELECT 
                    user_id,
                    COUNT(*) as share_count,
                    SUM(CASE WHEN recipient_type = 'team' THEN 1 ELSE 0 END) as team_shares,
                    SUM(CASE WHEN share_scope = 'internal' THEN 1 ELSE 0 END) as internal_shares
                FROM share_events
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND recipient_type IN ('team', 'organization')
                GROUP BY user_id
            ),
            collaboration_stats AS (
                SELECT 
                    COUNT(DISTINCT user_id) as active_sharers,
                    AVG(share_count) as avg_shares_per_user,
                    AVG(team_shares::float / share_count) as team_share_ratio,
                    STDDEV(share_count) as share_variance
                FROM team_shares
            )
            SELECT * FROM collaboration_stats
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % days)
            
            if not row:
                return self._empty_collaboration_metrics()
            
            collaboration_score = self._calculate_collaboration_score(
                row['active_sharers'] or 0,
                row['team_share_ratio'] or 0,
                row['share_variance'] or 0
            )
            
            return {
                'active_sharers': row['active_sharers'] or 0,
                'avg_shares_per_user': float(row['avg_shares_per_user'] or 0),
                'team_share_ratio': float(row['team_share_ratio'] or 0),
                'collaboration_score': collaboration_score,
                'collaboration_level': self._get_collaboration_level(collaboration_score)
            }
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_shares': 0,
            'internal_shares': 0,
            'external_shares': 0,
            'social_shares': 0,
            'unique_recipients': 0,
            'content_items_shared': 0,
            'most_used_platforms': [],
            'share_pattern': {'pattern_type': 'minimal', 'confidence': 0},
            'viral_content': []
        }
    
    def _empty_collaboration_metrics(self) -> Dict:
        """Return empty collaboration metrics"""
        return {
            'active_sharers': 0,
            'avg_shares_per_user': 0,
            'team_share_ratio': 0,
            'collaboration_score': 0,
            'collaboration_level': 'low'
        }
    
    def _determine_share_pattern(
        self,
        avg_recipients: float,
        daily_shares: float,
        reshare_ratio: float,
        external_ratio: float,
        platform_diversity: int
    ) -> Dict:
        """Determine sharing pattern type"""
        
        # Broadcaster: high recipients, high frequency
        if avg_recipients > 10 and daily_shares > 5:
            pattern_type = 'broadcaster'
            confidence = 0.8
        
        # Collaborator: moderate sharing, mostly internal
        elif daily_shares > 2 and external_ratio < 0.2:
            pattern_type = 'collaborator'
            confidence = 0.75
        
        # Curator: high reshare ratio
        elif reshare_ratio > 0.5:
            pattern_type = 'curator'
            confidence = 0.7
        
        # Minimal sharer
        else:
            pattern_type = 'minimal'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'avg_recipients_per_share': avg_recipients,
                'share_frequency': daily_shares,
                'reshare_rate': reshare_ratio * 100,
                'external_share_rate': external_ratio * 100
            }
        }
    
    def _calculate_influence_score(
        self,
        network_size: int,
        reshares: int
    ) -> float:
        """Calculate user influence score"""
        if network_size == 0:
            return 0
        
        # Simple influence calculation
        score = (network_size * 0.3 + reshares * 0.7)
        return min(score, 100)
    
    def _find_optimal_share_times(
        self,
        timing_data: List,
        engagement_data: List
    ) -> List[Dict]:
        """Find optimal times for sharing"""
        if not timing_data or not engagement_data:
            return []
        
        # Combine timing and engagement data
        engagement_by_hour = {
            e['hour']: e['engagements'] 
            for e in engagement_data
        }
        
        # Score each time slot
        scored_times = []
        for timing in timing_data[:20]:  # Top 20 time slots
            hour = timing['hour']
            score = (
                timing['shares'] * 0.4 +
                timing['avg_reach'] * 0.3 +
                engagement_by_hour.get(hour, 0) * 0.3
            )
            scored_times.append({
                'hour': hour,
                'day': timing['day'],
                'score': score
            })
        
        # Return top 3
        scored_times.sort(key=lambda x: x['score'], reverse=True)
        return scored_times[:3]
    
    def _calculate_collaboration_score(
        self,
        active_sharers: int,
        team_share_ratio: float,
        variance: float
    ) -> float:
        """Calculate collaboration score"""
        score = 0
        
        # More active sharers is better
        score += min(active_sharers * 2, 40)
        
        # Higher team share ratio is better
        score += team_share_ratio * 40
        
        # Lower variance (more equal participation) is better
        if variance > 0:
            score += max(0, 20 - variance)
        
        return min(score, 100)
    
    def _get_collaboration_level(self, score: float) -> str:
        """Get collaboration level from score"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'moderate'
        elif score >= 20:
            return 'low'
        else:
            return 'minimal'
    
    async def _update_virality_metrics(
        self,
        conn,
        content_id: str,
        content_type: Optional[str],
        is_reshare: bool
    ):
        """Update content virality metrics"""
        # Implementation
        pass
    
    async def _update_engagement_metrics(
        self,
        conn,
        share_id: str
    ):
        """Update engagement metrics for shared content"""
        # Implementation
        pass
    
    async def _update_daily_stats(
        self,
        conn,
        user_id: str
    ):
        """Update daily share statistics"""
        # Implementation
        pass
    
    async def _calculate_virality_metrics(
        self,
        conn,
        content_id: str
    ) -> Dict:
        """Calculate virality metrics from events"""
        # Implementation
        return {}
    
    async def _detect_share_pattern(
        self,
        conn,
        user_id: str,
        days: int
    ) -> Dict:
        """Detect share pattern from database"""
        return await self.detect_share_pattern(user_id, days)
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/share", tags=["share-analytics"])

@router.post("/track")
async def track_share_event(
    user_id: str,
    share_method: str,
    recipients_count: int = 1,
    content_id: Optional[str] = None,
    content_type: Optional[str] = None,
    share_platform: Optional[str] = None,
    recipient_type: str = "individual",
    share_scope: str = "internal",
    permissions: Optional[str] = "view",
    expiry_date: Optional[datetime] = None,
    is_reshare: bool = False,
    original_share_id: Optional[str] = None
):
    """Track share event"""
    analytics = ShareAnalytics(db_pool)
    share_id = await analytics.track_share_event(
        user_id, content_id, content_type, share_method,
        share_platform, recipients_count, recipient_type,
        share_scope, permissions, expiry_date,
        is_reshare, original_share_id
    )
    return {"share_id": share_id}

@router.post("/engagement")
async def track_share_engagement(
    share_id: str,
    engagement_type: str,
    engaged_user_id: Optional[str] = None,
    time_to_engage: Optional[int] = None
):
    """Track share engagement"""
    analytics = ShareAnalytics(db_pool)
    await analytics.track_share_engagement(
        share_id, engagement_type, engaged_user_id, time_to_engage
    )
    return {"status": "tracked"}

@router.get("/statistics/{user_id}")
async def get_share_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get share statistics"""
    analytics = ShareAnalytics(db_pool)
    stats = await analytics.get_share_statistics(user_id, days)
    return stats

@router.get("/pattern/{user_id}")
async def detect_share_pattern(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Detect share pattern"""
    analytics = ShareAnalytics(db_pool)
    pattern = await analytics.detect_share_pattern(user_id, days)
    return pattern

@router.get("/virality/{content_id}")
async def get_virality_metrics(content_id: str):
    """Get content virality metrics"""
    analytics = ShareAnalytics(db_pool)
    metrics = await analytics.get_virality_metrics(content_id)
    return metrics

@router.get("/network/{user_id}")
async def get_share_network(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get sharing network"""
    analytics = ShareAnalytics(db_pool)
    network = await analytics.get_share_network(user_id, days)
    return network

@router.get("/timing-analysis")
async def get_share_timing(user_id: Optional[str] = None):
    """Get share timing analysis"""
    analytics = ShareAnalytics(db_pool)
    timing = await analytics.get_share_timing_analysis(user_id)
    return timing

@router.get("/collaboration")
async def get_collaboration_metrics(
    team_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get collaboration metrics"""
    analytics = ShareAnalytics(db_pool)
    metrics = await analytics.get_collaboration_metrics(team_id, days)
    return metrics
```

## React Dashboard Components

```tsx
// Share Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, NetworkGraph, HeatMap } from '@/components/ui';

interface ShareDashboardProps {
  userId?: string;
}

export const ShareDashboard: React.FC<ShareDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<ShareStatistics | null>(null);
  const [network, setNetwork] = useState<any>(null);
  const [timing, setTiming] = useState<any>(null);
  const [collaboration, setCollaboration] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchShareData();
  }, [userId]);

  const fetchShareData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/share/statistics/${userId}`,
        userId && `/api/analytics/share/network/${userId}`,
        `/api/analytics/share/timing-analysis${userId ? `?user_id=${userId}` : ''}`,
        `/api/analytics/share/collaboration`
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
        setNetwork(data[idx++]);
      }
      setTiming(data[idx++]);
      setCollaboration(data[idx]);
    } catch (error) {
      console.error('Failed to fetch share data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading share analytics...</div>;

  return (
    <div className="share-dashboard">
      <h2>Share & Collaboration Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Total Shares</h3>
              <div className="stat-value">{stats.totalShares}</div>
              <Badge variant="primary">
                {stats.sharePattern.patternType}
              </Badge>
            </Card>
            
            <Card>
              <h3>Share Distribution</h3>
              <div className="share-types">
                <span>Internal: {stats.internalShares}</span>
                <span>External: {stats.externalShares}</span>
                <span>Social: {stats.socialShares}</span>
              </div>
            </Card>
            
            <Card>
              <h3>Recipients Reached</h3>
              <div className="stat-value">{stats.uniqueRecipients}</div>
              <span className="stat-label">
                {stats.contentItemsShared} items shared
              </span>
            </Card>
            
            <Card>
              <h3>Top Platforms</h3>
              <div className="platform-list">
                {stats.mostUsedPlatforms.slice(0, 3).map(platform => (
                  <Badge key={platform.platform} variant="info">
                    {platform.platform}: {platform.count}
                  </Badge>
                ))}
              </div>
            </Card>
          </Grid>

          {/* Viral Content */}
          {stats.viralContent.length > 0 && (
            <Card className="mt-4">
              <h3>Viral Content</h3>
              <div className="viral-list">
                {stats.viralContent.map(content => (
                  <div key={content.content_id} className="viral-item">
                    <span>{content.type}: {content.content_id}</span>
                    <Badge variant={content.viral_coefficient > 1 ? 'success' : 'warning'}>
                      K={content.viral_coefficient.toFixed(2)}
                    </Badge>
                    <span>{content.shares} shares</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Sharing Network */}
      {network && (
        <Card className="mt-4">
          <h3>Sharing Network</h3>
          <div className="network-metrics">
            <div>Network Size: {network.networkSize}</div>
            <div>Reshares Generated: {network.totalResharesGenerated}</div>
            <div>Influence Score: {network.influenceScore.toFixed(0)}</div>
          </div>
        </Card>
      )}

      {/* Optimal Timing */}
      {timing && (
        <Card className="mt-4">
          <h3>Optimal Share Times</h3>
          <div className="timing-recommendations">
            {timing.optimalShareTimes.map((time: any, idx: number) => (
              <Badge key={idx} variant="success">
                Day {time.day}, {time.hour}:00
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Collaboration Metrics */}
      {collaboration && (
        <Card className="mt-4">
          <h3>Team Collaboration</h3>
          <Grid cols={3} gap={4}>
            <div>
              <span>Active Sharers</span>
              <strong>{collaboration.activeSharers}</strong>
            </div>
            <div>
              <span>Collaboration Score</span>
              <Progress value={collaboration.collaborationScore} max={100} />
              <Badge variant={collaboration.collaborationLevel === 'excellent' ? 'success' : 'warning'}>
                {collaboration.collaborationLevel}
              </Badge>
            </div>
            <div>
              <span>Team Share Ratio</span>
              <strong>{(collaboration.teamShareRatio * 100).toFixed(1)}%</strong>
            </div>
          </Grid>
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic share event tracking
2. Engagement tracking
3. Virality calculation
4. Network analysis
5. Collaboration metrics

## Security Considerations
- No content storage
- Anonymize recipient data
- Respect sharing permissions
- Audit trail for shares
- Rate limiting

## Performance Optimizations
- Batch share events
- Cache virality scores
- Efficient network queries
- Daily aggregation
- Async engagement updates