# User Clipboard Tracking Specification

## Overview
Track user clipboard interactions including copy, cut, and paste events to understand content sharing patterns and improve user experience without storing sensitive clipboard content.

## Database Schema

### Tables

```sql
-- Clipboard interaction events
CREATE TABLE user_clipboard_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR(20) NOT NULL, -- copy, cut, paste
    content_type VARCHAR(50), -- text, image, file, url, code
    content_length INTEGER, -- Length/size of content
    content_hash VARCHAR(64), -- Hash for duplicate detection, no actual content
    source_element VARCHAR(100), -- Element type copied from
    target_element VARCHAR(100), -- Element type pasted to
    source_page VARCHAR(255),
    target_page VARCHAR(255),
    is_internal BOOLEAN DEFAULT true, -- Within app or external
    time_to_paste_ms INTEGER, -- Time between copy and paste
    session_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_clipboard_events_user (user_id, created_at DESC),
    INDEX idx_clipboard_events_type (event_type, created_at DESC),
    INDEX idx_clipboard_events_session (session_id)
);

-- Daily clipboard statistics
CREATE TABLE user_clipboard_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    copy_count INTEGER DEFAULT 0,
    cut_count INTEGER DEFAULT 0,
    paste_count INTEGER DEFAULT 0,
    unique_content_items INTEGER DEFAULT 0,
    cross_page_pastes INTEGER DEFAULT 0,
    external_pastes INTEGER DEFAULT 0,
    avg_time_to_paste_ms INTEGER,
    most_copied_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_clipboard_daily_stats_date (date DESC),
    INDEX idx_clipboard_daily_stats_user (user_id, date DESC)
);

-- Clipboard patterns
CREATE TABLE clipboard_patterns (
    id SERIAL PRIMARY KEY,
    user_id UUID,
    pattern_type VARCHAR(50), -- frequent_copy, quick_paste, multi_copy, etc.
    pattern_data JSONB,
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_clipboard_patterns_user (user_id),
    INDEX idx_clipboard_patterns_type (pattern_type)
);

-- Common clipboard content types
CREATE TABLE clipboard_content_types (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    content_type VARCHAR(50),
    content_category VARCHAR(50), -- email, phone, url, code_snippet, etc.
    copy_count INTEGER DEFAULT 1,
    paste_count INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 1,
    is_sensitive BOOLEAN DEFAULT false,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_content_types_hash (content_hash),
    INDEX idx_content_types_category (content_category)
);
```

## TypeScript Interfaces

```typescript
// Clipboard event interface
interface ClipboardEvent {
  id: string;
  userId: string;
  eventType: 'copy' | 'cut' | 'paste';
  contentType?: 'text' | 'image' | 'file' | 'url' | 'code';
  contentLength?: number;
  contentHash?: string;
  sourceElement?: string;
  targetElement?: string;
  sourcePage?: string;
  targetPage?: string;
  isInternal: boolean;
  timeToPasteMs?: number;
  sessionId: string;
  createdAt: Date;
}

// Clipboard statistics
interface ClipboardStatistics {
  copyCount: number;
  cutCount: number;
  pasteCount: number;
  uniqueContentItems: number;
  crossPagePastes: number;
  externalPastes: number;
  avgTimeToPasteMs: number;
  mostCopiedType?: string;
  copyPasteRatio: number;
  efficiencyScore: number;
}

// Clipboard pattern
interface ClipboardPattern {
  userId: string;
  patternType: 'frequent_copy' | 'quick_paste' | 'multi_copy' | 'copy_chain' | 'external_share';
  patternData: {
    frequency?: number;
    avgTimeMs?: number;
    contentTypes?: string[];
    pages?: string[];
  };
  occurrenceCount: number;
  firstSeen: Date;
  lastSeen: Date;
}

// Content flow analysis
interface ContentFlow {
  sourcePage: string;
  targetPage: string;
  flowCount: number;
  avgTimeToPaste: number;
  contentTypes: string[];
  isFrequent: boolean;
}

// Clipboard efficiency metrics
interface ClipboardEfficiency {
  avgCopyToPasteTime: number;
  abandonedCopies: number;
  duplicateCopies: number;
  pasteSuccessRate: number;
  crossAppSharing: number;
  productivityScore: number;
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import asyncpg

@dataclass
class ClipboardAnalytics:
    """Analyze clipboard usage patterns and behaviors"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.copy_cache = {}  # Track copies for paste matching
    
    async def track_clipboard_event(
        self,
        user_id: str,
        event_type: str,
        content_type: Optional[str] = None,
        content_length: Optional[int] = None,
        source_element: Optional[str] = None,
        target_element: Optional[str] = None,
        page: str = None,
        session_id: str = None
    ) -> Dict:
        """Track a clipboard event"""
        
        # Generate content hash for tracking (not storing actual content)
        content_hash = self._generate_content_hash(user_id, content_type, content_length)
        
        if event_type == 'copy' or event_type == 'cut':
            # Store in cache for paste matching
            self.copy_cache[f"{user_id}:{session_id}"] = {
                'hash': content_hash,
                'time': datetime.utcnow(),
                'page': page,
                'type': content_type
            }
            
            query = """
                INSERT INTO user_clipboard_events (
                    user_id, event_type, content_type, content_length,
                    content_hash, source_element, source_page, session_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            async with self.db.acquire() as conn:
                event_id = await conn.fetchval(
                    query, user_id, event_type, content_type, content_length,
                    content_hash, source_element, page, session_id
                )
                
                # Update content type tracking
                await self._update_content_type(conn, content_hash, content_type, 'copy')
            
        elif event_type == 'paste':
            # Check for matching copy
            cache_key = f"{user_id}:{session_id}"
            copy_data = self.copy_cache.get(cache_key)
            
            time_to_paste = None
            is_internal = True
            
            if copy_data:
                time_diff = datetime.utcnow() - copy_data['time']
                time_to_paste = int(time_diff.total_seconds() * 1000)
                is_internal = copy_data['page'] == page
            
            query = """
                INSERT INTO user_clipboard_events (
                    user_id, event_type, content_type, content_length,
                    content_hash, target_element, target_page, 
                    is_internal, time_to_paste_ms, session_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """
            
            async with self.db.acquire() as conn:
                event_id = await conn.fetchval(
                    query, user_id, event_type, content_type, content_length,
                    content_hash, target_element, page, 
                    is_internal, time_to_paste, session_id
                )
                
                # Update content type tracking
                await self._update_content_type(conn, content_hash, content_type, 'paste')
        
        # Update daily stats
        await self._update_daily_stats(user_id, event_type)
        
        return {"event_id": event_id, "tracked": True}
    
    async def get_clipboard_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get clipboard usage statistics"""
        query = """
            WITH clipboard_stats AS (
                SELECT 
                    COUNT(*) FILTER (WHERE event_type = 'copy') as copy_count,
                    COUNT(*) FILTER (WHERE event_type = 'cut') as cut_count,
                    COUNT(*) FILTER (WHERE event_type = 'paste') as paste_count,
                    COUNT(DISTINCT content_hash) as unique_content,
                    COUNT(*) FILTER (WHERE event_type = 'paste' AND NOT is_internal) as cross_page,
                    COUNT(*) FILTER (WHERE event_type = 'paste' AND source_page IS NULL) as external,
                    AVG(time_to_paste_ms) FILTER (WHERE time_to_paste_ms IS NOT NULL) as avg_time_to_paste
                FROM user_clipboard_events
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            content_types AS (
                SELECT content_type, COUNT(*) as count
                FROM user_clipboard_events
                WHERE user_id = $1
                    AND event_type = 'copy'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND content_type IS NOT NULL
                GROUP BY content_type
                ORDER BY count DESC
                LIMIT 1
            )
            SELECT 
                cs.*,
                ct.content_type as most_copied_type
            FROM clipboard_stats cs
            LEFT JOIN content_types ct ON true
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            copy_count = row['copy_count'] or 0
            paste_count = row['paste_count'] or 0
            
            return {
                'copy_count': copy_count,
                'cut_count': row['cut_count'] or 0,
                'paste_count': paste_count,
                'unique_content_items': row['unique_content'] or 0,
                'cross_page_pastes': row['cross_page'] or 0,
                'external_pastes': row['external'] or 0,
                'avg_time_to_paste_ms': row['avg_time_to_paste'] or 0,
                'most_copied_type': row['most_copied_type'],
                'copy_paste_ratio': (copy_count / paste_count) if paste_count > 0 else 0,
                'efficiency_score': self._calculate_efficiency_score(row)
            }
    
    async def get_content_flow(
        self,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Analyze content flow between pages"""
        query = """
            WITH copy_paste_pairs AS (
                SELECT 
                    c.source_page,
                    p.target_page,
                    COUNT(*) as flow_count,
                    AVG(p.time_to_paste_ms) as avg_time,
                    array_agg(DISTINCT c.content_type) as content_types
                FROM user_clipboard_events c
                JOIN user_clipboard_events p ON 
                    p.content_hash = c.content_hash
                    AND p.event_type = 'paste'
                    AND c.event_type IN ('copy', 'cut')
                    AND p.created_at > c.created_at
                WHERE c.source_page IS NOT NULL
                    AND p.target_page IS NOT NULL
                    %s
                GROUP BY c.source_page, p.target_page
                ORDER BY flow_count DESC
                LIMIT $1
            )
            SELECT * FROM copy_paste_pairs
        """
        
        user_filter = "AND c.user_id = $2" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                rows = await conn.fetch(query % user_filter, limit, user_id)
            else:
                rows = await conn.fetch(query % user_filter, limit)
            
            return [
                {
                    'source_page': row['source_page'],
                    'target_page': row['target_page'],
                    'flow_count': row['flow_count'],
                    'avg_time_to_paste': row['avg_time'],
                    'content_types': row['content_types'],
                    'is_frequent': row['flow_count'] > 10
                }
                for row in rows
            ]
    
    async def detect_clipboard_patterns(
        self,
        user_id: str
    ) -> List[Dict]:
        """Detect clipboard usage patterns"""
        patterns = []
        
        # Frequent copy pattern
        frequent_copy = await self._detect_frequent_copy_pattern(user_id)
        if frequent_copy:
            patterns.append(frequent_copy)
        
        # Quick paste pattern
        quick_paste = await self._detect_quick_paste_pattern(user_id)
        if quick_paste:
            patterns.append(quick_paste)
        
        # Multi-copy pattern
        multi_copy = await self._detect_multi_copy_pattern(user_id)
        if multi_copy:
            patterns.append(multi_copy)
        
        # Copy chain pattern
        copy_chain = await self._detect_copy_chain_pattern(user_id)
        if copy_chain:
            patterns.append(copy_chain)
        
        return patterns
    
    async def get_clipboard_efficiency(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Calculate clipboard efficiency metrics"""
        query = """
            WITH copy_events AS (
                SELECT 
                    content_hash,
                    created_at as copy_time
                FROM user_clipboard_events
                WHERE user_id = $1
                    AND event_type = 'copy'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            paste_events AS (
                SELECT 
                    content_hash,
                    created_at as paste_time,
                    time_to_paste_ms
                FROM user_clipboard_events
                WHERE user_id = $1
                    AND event_type = 'paste'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            efficiency_metrics AS (
                SELECT 
                    AVG(pe.time_to_paste_ms) as avg_copy_to_paste,
                    COUNT(DISTINCT ce.content_hash) - COUNT(DISTINCT pe.content_hash) as abandoned,
                    COUNT(ce.content_hash) - COUNT(DISTINCT ce.content_hash) as duplicates
                FROM copy_events ce
                LEFT JOIN paste_events pe ON ce.content_hash = pe.content_hash
            )
            SELECT * FROM efficiency_metrics
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            # Get additional metrics
            cross_app_query = """
                SELECT COUNT(*) as cross_app
                FROM user_clipboard_events
                WHERE user_id = $1
                    AND event_type = 'paste'
                    AND NOT is_internal
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """
            
            cross_app = await conn.fetchval(cross_app_query % days, user_id)
            
            return {
                'avg_copy_to_paste_time': row['avg_copy_to_paste'] or 0,
                'abandoned_copies': row['abandoned'] or 0,
                'duplicate_copies': row['duplicates'] or 0,
                'paste_success_rate': self._calculate_paste_success_rate(row),
                'cross_app_sharing': cross_app or 0,
                'productivity_score': self._calculate_productivity_score(row, cross_app)
            }
    
    async def get_popular_content_types(
        self,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict]:
        """Get most popular content types across all users"""
        query = """
            SELECT 
                content_type,
                content_category,
                copy_count,
                paste_count,
                unique_users,
                CASE 
                    WHEN paste_count > 0 THEN copy_count::float / paste_count
                    ELSE 0
                END as reuse_ratio
            FROM clipboard_content_types
            WHERE last_seen >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ORDER BY copy_count DESC
            LIMIT $1
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days, limit)
            
            return [
                {
                    'content_type': row['content_type'],
                    'content_category': row['content_category'],
                    'copy_count': row['copy_count'],
                    'paste_count': row['paste_count'],
                    'unique_users': row['unique_users'],
                    'reuse_ratio': row['reuse_ratio']
                }
                for row in rows
            ]
    
    def _generate_content_hash(
        self, 
        user_id: str, 
        content_type: Optional[str], 
        content_length: Optional[int]
    ) -> str:
        """Generate hash for content tracking without storing actual content"""
        hash_input = f"{user_id}:{content_type}:{content_length}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def _calculate_efficiency_score(self, stats: dict) -> float:
        """Calculate clipboard efficiency score"""
        if not stats:
            return 0.0
        
        score = 0.0
        
        # Factor in paste success
        if stats['copy_count'] and stats['paste_count']:
            paste_ratio = stats['paste_count'] / stats['copy_count']
            score += min(paste_ratio * 30, 30)  # Max 30 points
        
        # Factor in time efficiency
        if stats['avg_time_to_paste']:
            if stats['avg_time_to_paste'] < 5000:  # Less than 5 seconds
                score += 30
            elif stats['avg_time_to_paste'] < 30000:  # Less than 30 seconds
                score += 20
            else:
                score += 10
        
        # Factor in cross-page usage
        if stats['cross_page']:
            score += min(stats['cross_page'] * 2, 20)  # Max 20 points
        
        # Factor in unique content
        if stats['unique_content']:
            score += min(stats['unique_content'], 20)  # Max 20 points
        
        return min(score, 100)  # Cap at 100
    
    def _calculate_paste_success_rate(self, metrics: dict) -> float:
        """Calculate paste success rate"""
        if not metrics or not metrics.get('abandoned'):
            return 100.0
        
        total = metrics.get('abandoned', 0) + metrics.get('duplicates', 0)
        if total == 0:
            return 100.0
        
        return max(0, 100 - (metrics['abandoned'] / total * 100))
    
    def _calculate_productivity_score(self, metrics: dict, cross_app: int) -> float:
        """Calculate productivity score based on clipboard usage"""
        score = 50.0  # Base score
        
        # Quick copy-paste increases productivity
        if metrics and metrics.get('avg_copy_to_paste'):
            if metrics['avg_copy_to_paste'] < 3000:
                score += 20
            elif metrics['avg_copy_to_paste'] < 10000:
                score += 10
        
        # Cross-app sharing indicates advanced usage
        if cross_app > 0:
            score += min(cross_app * 2, 15)
        
        # Penalize abandoned copies
        if metrics and metrics.get('abandoned'):
            score -= min(metrics['abandoned'] * 0.5, 10)
        
        # Penalize excessive duplicates
        if metrics and metrics.get('duplicates'):
            score -= min(metrics['duplicates'] * 0.3, 5)
        
        return max(0, min(score, 100))
    
    async def _detect_frequent_copy_pattern(self, user_id: str) -> Optional[Dict]:
        """Detect frequent copy pattern"""
        # Implementation for pattern detection
        pass
    
    async def _detect_quick_paste_pattern(self, user_id: str) -> Optional[Dict]:
        """Detect quick paste pattern"""
        # Implementation for pattern detection
        pass
    
    async def _detect_multi_copy_pattern(self, user_id: str) -> Optional[Dict]:
        """Detect multi-copy pattern"""
        # Implementation for pattern detection
        pass
    
    async def _detect_copy_chain_pattern(self, user_id: str) -> Optional[Dict]:
        """Detect copy chain pattern"""
        # Implementation for pattern detection
        pass
    
    async def _update_content_type(
        self, 
        conn, 
        content_hash: str, 
        content_type: Optional[str],
        action: str
    ):
        """Update content type tracking"""
        # Implementation for content type updates
        pass
    
    async def _update_daily_stats(self, user_id: str, event_type: str):
        """Update daily statistics"""
        # Implementation for daily stats
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/clipboard", tags=["clipboard-analytics"])

@router.post("/track")
async def track_clipboard_event(
    user_id: str,
    event_type: str,
    content_type: Optional[str] = None,
    content_length: Optional[int] = None,
    source_element: Optional[str] = None,
    target_element: Optional[str] = None,
    page: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Track clipboard event"""
    analytics = ClipboardAnalytics(db_pool)
    result = await analytics.track_clipboard_event(
        user_id, event_type, content_type, content_length,
        source_element, target_element, page, session_id
    )
    return result

@router.get("/stats/{user_id}")
async def get_clipboard_stats(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get clipboard usage statistics"""
    analytics = ClipboardAnalytics(db_pool)
    stats = await analytics.get_clipboard_stats(user_id, days)
    return stats

@router.get("/content-flow")
async def get_content_flow(
    user_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Get content flow analysis"""
    analytics = ClipboardAnalytics(db_pool)
    flow = await analytics.get_content_flow(user_id, limit)
    return {"content_flows": flow}

@router.get("/patterns/{user_id}")
async def detect_clipboard_patterns(user_id: str):
    """Detect clipboard usage patterns"""
    analytics = ClipboardAnalytics(db_pool)
    patterns = await analytics.detect_clipboard_patterns(user_id)
    return {"patterns": patterns}

@router.get("/efficiency/{user_id}")
async def get_clipboard_efficiency(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get clipboard efficiency metrics"""
    analytics = ClipboardAnalytics(db_pool)
    efficiency = await analytics.get_clipboard_efficiency(user_id, days)
    return efficiency

@router.get("/popular-content")
async def get_popular_content_types(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50)
):
    """Get popular content types"""
    analytics = ClipboardAnalytics(db_pool)
    types = await analytics.get_popular_content_types(days, limit)
    return {"popular_types": types}
```

## React Dashboard Components

```tsx
// Clipboard Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Badge, Progress, Table, Sankey, LineChart } from '@/components/ui';

interface ClipboardDashboardProps {
  userId?: string;
}

export const ClipboardDashboard: React.FC<ClipboardDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<ClipboardStatistics | null>(null);
  const [contentFlow, setContentFlow] = useState<ContentFlow[]>([]);
  const [efficiency, setEfficiency] = useState<ClipboardEfficiency | null>(null);
  const [patterns, setPatterns] = useState<ClipboardPattern[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClipboardData();
  }, [userId]);

  const fetchClipboardData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/clipboard/stats/${userId}`,
        `/api/analytics/clipboard/content-flow${userId ? `?user_id=${userId}` : ''}`,
        userId && `/api/analytics/clipboard/efficiency/${userId}`,
        userId && `/api/analytics/clipboard/patterns/${userId}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      if (userId) {
        setStats(data[0]);
        setContentFlow(data[1].content_flows);
        setEfficiency(data[2]);
        setPatterns(data[3].patterns);
      } else {
        setContentFlow(data[0].content_flows);
      }
    } catch (error) {
      console.error('Failed to fetch clipboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading clipboard analytics...</div>;

  return (
    <div className="clipboard-dashboard">
      <h2>Clipboard Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Copy Actions</h3>
              <div className="stat-value">{stats.copyCount}</div>
              <span className="stat-label">
                {stats.cutCount} cuts
              </span>
            </Card>
            
            <Card>
              <h3>Paste Actions</h3>
              <div className="stat-value">{stats.pasteCount}</div>
              <Badge variant={stats.copyPasteRatio > 1 ? 'warning' : 'success'}>
                {stats.copyPasteRatio.toFixed(2)} ratio
              </Badge>
            </Card>
            
            <Card>
              <h3>Efficiency Score</h3>
              <div className="stat-value">{stats.efficiencyScore.toFixed(0)}</div>
              <Progress value={stats.efficiencyScore} max={100} />
            </Card>
            
            <Card>
              <h3>Avg Time to Paste</h3>
              <div className="stat-value">
                {(stats.avgTimeToPasteMs / 1000).toFixed(1)}s
              </div>
              <span className="stat-label">
                {stats.mostCopiedType || 'N/A'} most copied
              </span>
            </Card>
          </Grid>

          {/* Clipboard Efficiency */}
          {efficiency && (
            <Card className="mt-4">
              <h3>Clipboard Efficiency</h3>
              <Grid cols={3} gap={4}>
                <div className="efficiency-metric">
                  <span className="metric-label">Productivity Score</span>
                  <div className="metric-value">
                    {efficiency.productivityScore.toFixed(0)}
                    <Progress 
                      value={efficiency.productivityScore} 
                      max={100}
                      variant={efficiency.productivityScore > 70 ? 'success' : 'warning'}
                    />
                  </div>
                </div>
                
                <div className="efficiency-metric">
                  <span className="metric-label">Paste Success Rate</span>
                  <div className="metric-value">
                    {efficiency.pasteSuccessRate.toFixed(1)}%
                  </div>
                </div>
                
                <div className="efficiency-metric">
                  <span className="metric-label">Cross-App Sharing</span>
                  <div className="metric-value">
                    {efficiency.crossAppSharing}
                    <Badge variant="info">events</Badge>
                  </div>
                </div>
              </Grid>
              
              <div className="efficiency-details mt-4">
                <div className="detail-item">
                  <span>Abandoned Copies:</span>
                  <Badge variant="warning">{efficiency.abandonedCopies}</Badge>
                </div>
                <div className="detail-item">
                  <span>Duplicate Copies:</span>
                  <Badge variant="info">{efficiency.duplicateCopies}</Badge>
                </div>
              </div>
            </Card>
          )}

          {/* Usage Patterns */}
          {patterns.length > 0 && (
            <Card className="mt-4">
              <h3>Detected Patterns</h3>
              <div className="patterns-grid">
                {patterns.map(pattern => (
                  <div key={pattern.patternType} className="pattern-card">
                    <Badge variant="primary">{pattern.patternType}</Badge>
                    <div className="pattern-details">
                      <span>Occurrences: {pattern.occurrenceCount}</span>
                      {pattern.patternData.frequency && (
                        <span>Frequency: {pattern.patternData.frequency}/hour</span>
                      )}
                      {pattern.patternData.avgTimeMs && (
                        <span>Avg Time: {(pattern.patternData.avgTimeMs / 1000).toFixed(1)}s</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Content Flow Visualization */}
      <Card className="mt-4">
        <h3>Content Flow Between Pages</h3>
        <div className="flow-visualization">
          <Sankey
            data={contentFlow.map(flow => ({
              source: flow.sourcePage,
              target: flow.targetPage,
              value: flow.flowCount
            }))}
            height={400}
          />
        </div>
        
        <Table className="mt-4">
          <thead>
            <tr>
              <th>Source</th>
              <th>Target</th>
              <th>Count</th>
              <th>Avg Time</th>
              <th>Types</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {contentFlow.slice(0, 10).map((flow, idx) => (
              <tr key={idx}>
                <td>{flow.sourcePage}</td>
                <td>{flow.targetPage}</td>
                <td>{flow.flowCount}</td>
                <td>{(flow.avgTimeToPaste / 1000).toFixed(1)}s</td>
                <td>
                  {flow.contentTypes.map(type => (
                    <Badge key={type} variant="secondary">{type}</Badge>
                  ))}
                </td>
                <td>
                  {flow.isFrequent && <Badge variant="success">Frequent</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* Clipboard Timeline */}
      <Card className="mt-4">
        <h3>Clipboard Activity Timeline</h3>
        <LineChart
          data={[]} // Would be populated with time-series data
          xKey="time"
          yKeys={['copies', 'pastes']}
          height={300}
        />
      </Card>
    </div>
  );
};
```

## Implementation Priority
1. Basic clipboard event tracking
2. Copy-paste time measurement
3. Content flow analysis
4. Pattern detection
5. Efficiency scoring

## Security Considerations
- Never store actual clipboard content
- Use hashing for duplicate detection
- Respect user privacy settings
- Detect potential data exfiltration patterns
- Monitor for unusual clipboard activity

## Performance Optimizations
- Use memory cache for copy-paste matching
- Batch event tracking updates
- Daily aggregation for statistics
- Limit pattern detection to active users
- Efficient content flow queries