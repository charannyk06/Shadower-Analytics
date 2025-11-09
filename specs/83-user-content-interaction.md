# User Content Interaction Specification

## Overview
Track how users interact with content without complex content management systems. Focus on what content users view, share, and engage with.

## TypeScript Interfaces

```typescript
// Content interaction event
interface ContentInteraction {
  interaction_id: string;
  user_id: string;
  content_id: string;
  content_type: string;
  action: 'view' | 'like' | 'share' | 'comment' | 'download' | 'bookmark';
  timestamp: Date;
  duration_seconds?: number;
  referrer?: string;
}

// Content engagement metrics
interface ContentEngagement {
  content_id: string;
  total_views: number;
  unique_viewers: number;
  total_likes: number;
  total_shares: number;
  total_comments: number;
  avg_view_duration: number;
  engagement_rate: number;
}

// User content preferences
interface UserContentPreferences {
  user_id: string;
  preferred_types: string[];
  avg_view_duration: number;
  most_active_hour: number;
  interaction_count: number;
  favorite_content_ids: string[];
}

// Content popularity
interface ContentPopularity {
  content_id: string;
  content_type: string;
  popularity_score: number;
  trending_rank?: number;
  peak_hour: number;
  viral_coefficient: number;
}
```

## SQL Schema

```sql
-- Content interactions table
CREATE TABLE content_interactions (
    interaction_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    content_type VARCHAR(50),
    action VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    referrer VARCHAR(255)
);

-- Content engagement summary
CREATE TABLE content_engagement (
    content_id VARCHAR(255) PRIMARY KEY,
    content_type VARCHAR(50),
    total_views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_downloads INTEGER DEFAULT 0,
    total_bookmarks INTEGER DEFAULT 0,
    avg_view_duration INTEGER DEFAULT 0,
    last_interaction TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User content preferences
CREATE TABLE user_content_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    preferred_types TEXT[],
    avg_view_duration INTEGER DEFAULT 0,
    most_active_hour INTEGER,
    total_interactions INTEGER DEFAULT 0,
    favorite_content_ids TEXT[],
    last_interaction TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily content statistics
CREATE TABLE daily_content_stats (
    date DATE NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    PRIMARY KEY (date, content_id)
);

-- Trending content
CREATE TABLE trending_content (
    date DATE NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    content_type VARCHAR(50),
    popularity_score DECIMAL(10,2) DEFAULT 0,
    trending_rank INTEGER,
    viral_coefficient DECIMAL(5,2) DEFAULT 0,
    PRIMARY KEY (date, content_id)
);

-- Basic indexes
CREATE INDEX idx_interactions_user ON content_interactions(user_id);
CREATE INDEX idx_interactions_content ON content_interactions(content_id);
CREATE INDEX idx_interactions_timestamp ON content_interactions(timestamp DESC);
CREATE INDEX idx_interactions_action ON content_interactions(action);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import math

@dataclass
class ContentMetrics:
    """Content engagement metrics"""
    content_id: str
    engagement_score: float
    viral_potential: float
    retention_rate: float
    share_ratio: float

class ContentTracker:
    """Simple content interaction tracking"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def track_interaction(
        self,
        user_id: str,
        content_id: str,
        content_type: str,
        action: str,
        duration_seconds: Optional[int] = None,
        referrer: Optional[str] = None
    ) -> bool:
        """Track user content interaction"""
        query = """
        INSERT INTO content_interactions
        (user_id, content_id, content_type, action, duration_seconds, referrer)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.db.execute(query, (
                user_id, content_id, content_type, 
                action, duration_seconds, referrer
            ))
            
            # Update engagement metrics
            self.update_engagement(content_id, content_type, action, duration_seconds)
            
            # Update user preferences
            self.update_user_preferences(user_id, content_type, duration_seconds)
            
            return True
        except Exception as e:
            print(f"Error tracking interaction: {e}")
            return False
    
    def update_engagement(
        self, 
        content_id: str, 
        content_type: str,
        action: str, 
        duration: Optional[int] = None
    ) -> None:
        """Update content engagement metrics"""
        # Check if content exists
        existing = self.get_content_engagement(content_id)
        
        if not existing:
            # Create new engagement record
            query = """
            INSERT INTO content_engagement
            (content_id, content_type)
            VALUES (%s, %s)
            """
            self.db.execute(query, (content_id, content_type))
        
        # Update based on action
        update_fields = []
        if action == 'view':
            update_fields.append("total_views = total_views + 1")
        elif action == 'like':
            update_fields.append("total_likes = total_likes + 1")
        elif action == 'share':
            update_fields.append("total_shares = total_shares + 1")
        elif action == 'comment':
            update_fields.append("total_comments = total_comments + 1")
        elif action == 'download':
            update_fields.append("total_downloads = total_downloads + 1")
        elif action == 'bookmark':
            update_fields.append("total_bookmarks = total_bookmarks + 1")
        
        if duration and action == 'view':
            update_fields.append(f"""
                avg_view_duration = 
                    CASE 
                        WHEN total_views > 0 
                        THEN ((avg_view_duration * total_views + {duration}) / (total_views + 1))::INTEGER
                        ELSE {duration}
                    END
            """)
        
        if update_fields:
            query = f"""
            UPDATE content_engagement
            SET {', '.join(update_fields)},
                last_interaction = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE content_id = %s
            """
            self.db.execute(query, (content_id,))
        
        # Update unique viewers if view action
        if action == 'view':
            self.update_unique_viewers(content_id)
    
    def update_unique_viewers(self, content_id: str) -> None:
        """Update unique viewer count"""
        query = """
        UPDATE content_engagement
        SET unique_viewers = (
            SELECT COUNT(DISTINCT user_id)
            FROM content_interactions
            WHERE content_id = %s
            AND action = 'view'
        )
        WHERE content_id = %s
        """
        self.db.execute(query, (content_id, content_id))
    
    def update_user_preferences(
        self, 
        user_id: str, 
        content_type: str,
        duration: Optional[int] = None
    ) -> None:
        """Update user content preferences"""
        # Get current preferences
        query = """
        SELECT preferred_types, avg_view_duration, total_interactions
        FROM user_content_preferences
        WHERE user_id = %s
        """
        
        result = self.db.fetchone(query, (user_id,))
        
        if not result:
            # Create new preference record
            query = """
            INSERT INTO user_content_preferences
            (user_id, preferred_types, avg_view_duration, total_interactions, most_active_hour)
            VALUES (%s, %s, %s, 1, EXTRACT(HOUR FROM CURRENT_TIMESTAMP))
            """
            self.db.execute(query, (user_id, [content_type], duration or 0))
        else:
            # Update existing preferences
            preferred_types = result['preferred_types'] or []
            if content_type not in preferred_types:
                preferred_types.append(content_type)
            
            # Update average duration
            new_avg = result['avg_view_duration']
            if duration:
                total_interactions = result['total_interactions']
                new_avg = ((new_avg * total_interactions + duration) / (total_interactions + 1))
            
            query = """
            UPDATE user_content_preferences
            SET 
                preferred_types = %s,
                avg_view_duration = %s,
                total_interactions = total_interactions + 1,
                most_active_hour = EXTRACT(HOUR FROM CURRENT_TIMESTAMP),
                last_interaction = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """
            self.db.execute(query, (preferred_types, int(new_avg), user_id))
        
        # Update favorite content
        self.update_favorite_content(user_id)
    
    def update_favorite_content(self, user_id: str, limit: int = 10) -> None:
        """Update user's favorite content based on interactions"""
        query = """
        WITH user_favorites AS (
            SELECT 
                content_id,
                COUNT(*) as interaction_count,
                COUNT(CASE WHEN action = 'like' THEN 1 END) * 3 +
                COUNT(CASE WHEN action = 'share' THEN 1 END) * 2 +
                COUNT(CASE WHEN action = 'view' THEN 1 END) as score
            FROM content_interactions
            WHERE user_id = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY content_id
            ORDER BY score DESC
            LIMIT %s
        )
        UPDATE user_content_preferences
        SET favorite_content_ids = (
            SELECT ARRAY_AGG(content_id)
            FROM user_favorites
        )
        WHERE user_id = %s
        """
        self.db.execute(query, (user_id, limit, user_id))
    
    def get_content_engagement(self, content_id: str) -> Optional[Dict]:
        """Get engagement metrics for content"""
        query = """
        SELECT * FROM content_engagement
        WHERE content_id = %s
        """
        return self.db.fetchone(query, (content_id,))
    
    def get_user_recommendations(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get content recommendations for user"""
        # Get user preferences
        query = """
        SELECT preferred_types, favorite_content_ids
        FROM user_content_preferences
        WHERE user_id = %s
        """
        
        prefs = self.db.fetchone(query, (user_id,))
        
        if not prefs:
            # Return popular content for new users
            return self.get_trending_content(limit)
        
        # Find similar content based on user preferences
        query = """
        WITH user_viewed AS (
            SELECT DISTINCT content_id
            FROM content_interactions
            WHERE user_id = %s
        ),
        similar_users AS (
            SELECT DISTINCT ci.user_id
            FROM content_interactions ci
            WHERE ci.content_id = ANY(%s)
            AND ci.user_id != %s
            LIMIT 100
        )
        SELECT 
            ce.content_id,
            ce.content_type,
            ce.total_views,
            ce.total_likes,
            ce.avg_view_duration,
            COUNT(ci.user_id) as similar_user_interactions
        FROM content_engagement ce
        JOIN content_interactions ci ON ce.content_id = ci.content_id
        WHERE ci.user_id IN (SELECT user_id FROM similar_users)
        AND ce.content_id NOT IN (SELECT content_id FROM user_viewed)
        AND ce.content_type = ANY(%s)
        GROUP BY ce.content_id, ce.content_type, ce.total_views, 
                 ce.total_likes, ce.avg_view_duration
        ORDER BY similar_user_interactions DESC, ce.total_likes DESC
        LIMIT %s
        """
        
        return self.db.fetchall(query, (
            user_id, 
            prefs['favorite_content_ids'] or [],
            user_id,
            prefs['preferred_types'] or [],
            limit
        ))
    
    def calculate_popularity_score(self, content_id: str) -> float:
        """Calculate content popularity score"""
        query = """
        SELECT 
            total_views,
            unique_viewers,
            total_likes,
            total_shares,
            total_comments,
            avg_view_duration,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_interaction))/3600 as hours_since_interaction
        FROM content_engagement
        WHERE content_id = %s
        """
        
        result = self.db.fetchone(query, (content_id,))
        
        if not result:
            return 0.0
        
        # Calculate weighted score
        score = (
            result['total_views'] * 1 +
            result['unique_viewers'] * 2 +
            result['total_likes'] * 3 +
            result['total_shares'] * 5 +
            result['total_comments'] * 4
        )
        
        # Apply time decay
        decay_factor = math.exp(-result['hours_since_interaction'] / 168)  # Weekly decay
        
        # Apply duration bonus
        duration_bonus = min(result['avg_view_duration'] / 60, 10)  # Cap at 10 minutes
        
        return score * decay_factor * (1 + duration_bonus/10)
    
    def get_trending_content(self, limit: int = 20) -> List[Dict]:
        """Get trending content"""
        query = """
        WITH content_scores AS (
            SELECT 
                ce.content_id,
                ce.content_type,
                ce.total_views,
                ce.total_likes,
                ce.total_shares,
                (ce.total_likes::FLOAT / NULLIF(ce.total_views, 0) * 100) as engagement_rate,
                (ce.total_shares::FLOAT / NULLIF(ce.total_views, 0)) as viral_coefficient,
                COUNT(DISTINCT DATE(ci.timestamp)) as active_days,
                MAX(ci.timestamp) as last_activity
            FROM content_engagement ce
            JOIN content_interactions ci ON ce.content_id = ci.content_id
            WHERE ci.timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY ce.content_id, ce.content_type, ce.total_views, 
                     ce.total_likes, ce.total_shares
        )
        SELECT 
            content_id,
            content_type,
            total_views,
            total_likes,
            total_shares,
            engagement_rate,
            viral_coefficient,
            (total_views * 1 + total_likes * 3 + total_shares * 5) as popularity_score
        FROM content_scores
        WHERE active_days >= 2  -- Active for at least 2 days
        ORDER BY popularity_score DESC
        LIMIT %s
        """
        
        return self.db.fetchall(query, (limit,))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily content statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_content_stats
        (date, content_id, views, unique_viewers, likes, shares, engagement_rate)
        SELECT 
            %s as date,
            content_id,
            COUNT(CASE WHEN action = 'view' THEN 1 END) as views,
            COUNT(DISTINCT CASE WHEN action = 'view' THEN user_id END) as unique_viewers,
            COUNT(CASE WHEN action = 'like' THEN 1 END) as likes,
            COUNT(CASE WHEN action = 'share' THEN 1 END) as shares,
            CASE 
                WHEN COUNT(CASE WHEN action = 'view' THEN 1 END) > 0
                THEN (COUNT(CASE WHEN action IN ('like', 'share', 'comment') THEN 1 END)::FLOAT / 
                      COUNT(CASE WHEN action = 'view' THEN 1 END) * 100)
                ELSE 0
            END as engagement_rate
        FROM content_interactions
        WHERE DATE(timestamp) = %s
        GROUP BY content_id
        ON CONFLICT (date, content_id)
        DO UPDATE SET
            views = EXCLUDED.views,
            unique_viewers = EXCLUDED.unique_viewers,
            likes = EXCLUDED.likes,
            shares = EXCLUDED.shares,
            engagement_rate = EXCLUDED.engagement_rate
        """
        
        self.db.execute(query, (target_date, target_date))
        
        # Update trending content
        self.update_trending_content(target_date)
    
    def update_trending_content(self, date: datetime) -> None:
        """Update trending content for the day"""
        trending = self.get_trending_content(50)
        
        for idx, content in enumerate(trending):
            query = """
            INSERT INTO trending_content
            (date, content_id, content_type, popularity_score, trending_rank, viral_coefficient)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, content_id)
            DO UPDATE SET
                popularity_score = EXCLUDED.popularity_score,
                trending_rank = EXCLUDED.trending_rank,
                viral_coefficient = EXCLUDED.viral_coefficient
            """
            
            self.db.execute(query, (
                date,
                content['content_id'],
                content['content_type'],
                content['popularity_score'],
                idx + 1,
                content['viral_coefficient']
            ))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body
from typing import List, Optional

router = APIRouter(prefix="/api/content", tags=["content"])

@router.post("/interact")
async def track_content_interaction(
    user_id: str = Body(...),
    content_id: str = Body(...),
    content_type: str = Body(...),
    action: str = Body(...),
    duration_seconds: Optional[int] = Body(None),
    referrer: Optional[str] = Body(None)
):
    """Track content interaction"""
    valid_actions = ['view', 'like', 'share', 'comment', 'download', 'bookmark']
    
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of {valid_actions}")
    
    tracker = ContentTracker(db)
    success = tracker.track_interaction(
        user_id, content_id, content_type, 
        action, duration_seconds, referrer
    )
    
    return {"success": success, "action": action, "content_id": content_id}

@router.get("/engagement/{content_id}")
async def get_content_engagement(content_id: str):
    """Get engagement metrics for content"""
    tracker = ContentTracker(db)
    engagement = tracker.get_content_engagement(content_id)
    
    if not engagement:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Calculate engagement rate
    if engagement['total_views'] > 0:
        engagement['engagement_rate'] = (
            (engagement['total_likes'] + engagement['total_shares'] + engagement['total_comments']) 
            / engagement['total_views'] * 100
        )
    else:
        engagement['engagement_rate'] = 0
    
    return engagement

@router.get("/user/{user_id}/recommendations")
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """Get content recommendations for user"""
    tracker = ContentTracker(db)
    recommendations = tracker.get_user_recommendations(user_id, limit)
    
    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "count": len(recommendations)
    }

@router.get("/trending")
async def get_trending_content(
    limit: int = Query(20, ge=1, le=100)
):
    """Get trending content"""
    tracker = ContentTracker(db)
    trending = tracker.get_trending_content(limit)
    
    return {
        "trending": trending,
        "count": len(trending)
    }

@router.get("/user/{user_id}/history")
async def get_user_content_history(
    user_id: str,
    action: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=30)
):
    """Get user's content interaction history"""
    where_conditions = ["user_id = %s"]
    params = [user_id]
    
    if action:
        where_conditions.append("action = %s")
        params.append(action)
    
    where_conditions.append("timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'")
    params.append(days)
    
    query = f"""
    SELECT 
        content_id,
        content_type,
        action,
        timestamp,
        duration_seconds
    FROM content_interactions
    WHERE {' AND '.join(where_conditions)}
    ORDER BY timestamp DESC
    LIMIT 100
    """
    
    history = db.fetchall(query, tuple(params))
    
    return {
        "user_id": user_id,
        "history": history,
        "count": len(history)
    }

@router.get("/user/{user_id}/preferences")
async def get_user_content_preferences(user_id: str):
    """Get user content preferences"""
    query = """
    SELECT 
        user_id,
        preferred_types,
        avg_view_duration,
        most_active_hour,
        total_interactions,
        favorite_content_ids,
        last_interaction
    FROM user_content_preferences
    WHERE user_id = %s
    """
    
    result = db.fetchone(query, (user_id,))
    
    if not result:
        return {
            "user_id": user_id,
            "preferences": None,
            "message": "No preferences found"
        }
    
    return result

@router.get("/stats/daily")
async def get_daily_content_stats(
    date: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None)
):
    """Get daily content statistics"""
    target_date = date or datetime.now().date().isoformat()
    
    where_conditions = ["date = %s"]
    params = [target_date]
    
    if content_id:
        where_conditions.append("content_id = %s")
        params.append(content_id)
    
    query = f"""
    SELECT 
        content_id,
        views,
        unique_viewers,
        likes,
        shares,
        engagement_rate
    FROM daily_content_stats
    WHERE {' AND '.join(where_conditions)}
    ORDER BY views DESC
    LIMIT 100
    """
    
    stats = db.fetchall(query, tuple(params))
    
    return {
        "date": target_date,
        "stats": stats,
        "count": len(stats)
    }

@router.post("/calculate-daily")
async def calculate_daily_stats(
    date: Optional[str] = Body(None)
):
    """Calculate daily content statistics"""
    tracker = ContentTracker(db)
    target_date = datetime.fromisoformat(date) if date else datetime.now()
    tracker.calculate_daily_stats(target_date)
    
    return {"status": "calculated", "date": target_date.isoformat()}
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { TrendingUp, Heart, Share2, MessageCircle, Download, Bookmark } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ContentEngagement {
  contentId: string;
  contentType: string;
  totalViews: number;
  totalLikes: number;
  totalShares: number;
  totalComments: number;
  engagementRate: number;
  avgViewDuration: number;
}

interface TrendingContent {
  contentId: string;
  contentType: string;
  totalViews: number;
  totalLikes: number;
  totalShares: number;
  engagementRate: number;
  popularityScore: number;
}

export const ContentInteractionDashboard: React.FC = () => {
  const [trending, setTrending] = useState<TrendingContent[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [preferences, setPreferences] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchContentData();
  }, []);

  const fetchContentData = async () => {
    try {
      const [trendingRes, recsRes, historyRes, prefsRes] = await Promise.all([
        fetch('/api/content/trending?limit=10'),
        fetch(`/api/content/user/${userId}/recommendations`),
        fetch(`/api/content/user/${userId}/history?days=7`),
        fetch(`/api/content/user/${userId}/preferences`)
      ]);

      const trendingData = await trendingRes.json();
      const recsData = await recsRes.json();
      const historyData = await historyRes.json();
      const prefsData = await prefsRes.json();

      setTrending(trendingData.trending);
      setRecommendations(recsData.recommendations);
      setHistory(historyData.history);
      setPreferences(prefsData);
    } catch (error) {
      console.error('Error fetching content data:', error);
    } finally {
      setLoading(false);
    }
  };

  const trackInteraction = async (contentId: string, action: string) => {
    try {
      await fetch('/api/content/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          content_id: contentId,
          content_type: 'article',
          action: action
        })
      });
      
      // Refresh data
      fetchContentData();
    } catch (error) {
      console.error('Error tracking interaction:', error);
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'like':
        return <Heart className="w-4 h-4 text-red-500" />;
      case 'share':
        return <Share2 className="w-4 h-4 text-blue-500" />;
      case 'comment':
        return <MessageCircle className="w-4 h-4 text-green-500" />;
      case 'download':
        return <Download className="w-4 h-4 text-purple-500" />;
      case 'bookmark':
        return <Bookmark className="w-4 h-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  if (loading) return <div>Loading content data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Content Interaction Analytics</h2>

      {/* User Preferences Summary */}
      {preferences && preferences.preferences && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Your Content Preferences</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{preferences.total_interactions || 0}</div>
              <div className="text-sm text-gray-500">Total Interactions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {Math.round(preferences.avg_view_duration / 60)} min
              </div>
              <div className="text-sm text-gray-500">Avg View Time</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {preferences.most_active_hour || 0}:00
              </div>
              <div className="text-sm text-gray-500">Most Active Hour</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {preferences.preferred_types?.length || 0}
              </div>
              <div className="text-sm text-gray-500">Content Types</div>
            </div>
          </div>
        </div>
      )}

      {/* Trending Content */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Trending Content
          </h3>
        </div>
        <div className="space-y-3">
          {trending.slice(0, 5).map((content, idx) => (
            <div key={content.contentId} className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center space-x-3">
                <span className="text-lg font-bold text-gray-400">#{idx + 1}</span>
                <div>
                  <div className="font-medium">{content.contentId}</div>
                  <div className="text-sm text-gray-500">{content.contentType}</div>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-600">
                  {content.totalViews} views
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => trackInteraction(content.contentId, 'like')}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    <Heart className="w-4 h-4" />
                  </button>
                  <span className="text-sm">{content.totalLikes}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => trackInteraction(content.contentId, 'share')}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    <Share2 className="w-4 h-4" />
                  </button>
                  <span className="text-sm">{content.totalShares}</span>
                </div>
                <div className="text-sm font-medium text-green-600">
                  {content.engagementRate.toFixed(1)}% engagement
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Content */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recommended For You</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {recommendations.map((content) => (
            <div key={content.content_id} className="p-4 border rounded hover:shadow-md transition">
              <div className="font-medium mb-2">{content.content_id}</div>
              <div className="text-sm text-gray-500 mb-3">{content.content_type}</div>
              <div className="flex justify-between text-sm">
                <span>{content.total_views} views</span>
                <span>{content.total_likes} likes</span>
              </div>
              <div className="mt-3 flex space-x-2">
                <button
                  onClick={() => trackInteraction(content.content_id, 'view')}
                  className="flex-1 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                >
                  View
                </button>
                <button
                  onClick={() => trackInteraction(content.content_id, 'bookmark')}
                  className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200"
                >
                  <Bookmark className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interaction History */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Action</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Content</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Duration</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Time</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {history.slice(0, 10).map((item, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getActionIcon(item.action)}
                      <span className="text-sm capitalize">{item.action}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">{item.content_id}</td>
                  <td className="px-4 py-2 text-sm">{item.content_type}</td>
                  <td className="px-4 py-2 text-sm">
                    {item.duration_seconds 
                      ? `${Math.round(item.duration_seconds / 60)} min`
                      : '-'}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic interaction tracking
- **Phase 2**: Engagement metrics calculation
- **Phase 3**: Recommendation engine
- **Phase 4**: Trending content detection

## Performance Considerations
- Batch processing for engagement updates
- Daily aggregation for statistics
- Limited recommendation computation (cached)
- Efficient popularity scoring algorithm

## Security Considerations
- No PII in content interactions
- Rate limiting on interaction tracking
- Content ID validation
- User permission checks for content access

## Monitoring and Alerts
- Alert on viral content (high share rate)
- Daily engagement report
- Weekly trending content summary
- Monitor for unusual interaction patterns

## Dependencies
- PostgreSQL for data storage
- FastAPI for REST endpoints
- Math library for scoring algorithms
- React with Recharts for visualization