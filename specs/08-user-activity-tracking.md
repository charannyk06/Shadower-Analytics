# Specification: User Activity Tracking

## Feature Overview
Comprehensive user activity monitoring system tracking DAU/WAU/MAU, session analytics, feature usage, and engagement patterns to understand user behavior.

## Technical Requirements
- Real-time activity tracking
- Session management and analytics
- Feature usage heatmaps
- User journey mapping
- Retention and churn analysis
- Privacy-compliant tracking

## Implementation Details

### Data Structure
```typescript
interface UserActivityData {
  userId: string;
  workspaceId: string;
  timeframe: TimeFrame;
  
  // Activity Metrics
  activityMetrics: {
    // Active Users
    dau: number;
    wau: number;
    mau: number;
    
    // Growth Metrics
    newUsers: number;
    returningUsers: number;
    reactivatedUsers: number;
    churnedUsers: number;
    
    // Engagement Metrics
    avgSessionsPerUser: number;
    avgSessionDuration: number; // seconds
    bounceRate: number; // percentage
    engagementScore: number; // 0-100
    
    // Activity Distribution
    activityByHour: number[]; // 24 hours
    activityByDayOfWeek: number[]; // 7 days
    activityByDate: Array<{
      date: string;
      activeUsers: number;
      sessions: number;
      events: number;
    }>;
  };
  
  // Session Analytics
  sessionAnalytics: {
    totalSessions: number;
    avgSessionLength: number;
    medianSessionLength: number;
    
    // Session Distribution
    sessionLengthDistribution: {
      '0-30s': number;
      '30s-2m': number;
      '2m-5m': number;
      '5m-15m': number;
      '15m-30m': number;
      '30m+': number;
    };
    
    // Device & Platform
    deviceBreakdown: {
      desktop: number;
      mobile: number;
      tablet: number;
    };
    
    browserBreakdown: {
      [browser: string]: number;
    };
    
    // Geographic Distribution
    locationBreakdown: {
      [country: string]: {
        users: number;
        sessions: number;
      };
    };
  };
  
  // Feature Usage
  featureUsage: {
    // Core Features
    features: Array<{
      featureName: string;
      category: string;
      usageCount: number;
      uniqueUsers: number;
      avgTimeSpent: number;
      adoptionRate: number;
      retentionRate: number;
    }>;
    
    // Feature Adoption Funnel
    adoptionFunnel: Array<{
      stage: string;
      users: number;
      dropoffRate: number;
    }>;
    
    // Most Used Features
    topFeatures: Array<{
      feature: string;
      usage: number;
      trend: 'increasing' | 'stable' | 'decreasing';
    }>;
    
    // Unused Features
    unusedFeatures: Array<{
      feature: string;
      lastUsed: string | null;
    }>;
  };
  
  // User Journey
  userJourney: {
    // Common Paths
    commonPaths: Array<{
      path: string[];
      frequency: number;
      avgCompletion: number;
      dropoffPoints: Array<{
        step: string;
        dropoffRate: number;
      }>;
    }>;
    
    // Entry Points
    entryPoints: Array<{
      page: string;
      count: number;
      bounceRate: number;
    }>;
    
    // Exit Points
    exitPoints: Array<{
      page: string;
      count: number;
      avgTimeBeforeExit: number;
    }>;
    
    // Conversion Paths
    conversionPaths: Array<{
      goal: string;
      paths: Array<{
        steps: string[];
        conversions: number;
        conversionRate: number;
      }>;
    }>;
  };
  
  // Retention & Cohorts
  retention: {
    // Retention Curve
    retentionCurve: Array<{
      day: number;
      retentionRate: number;
      activeUsers: number;
    }>;
    
    // Cohort Analysis
    cohorts: Array<{
      cohortDate: string;
      cohortSize: number;
      retention: {
        day1: number;
        day7: number;
        day14: number;
        day30: number;
        day60: number;
        day90: number;
      };
    }>;
    
    // Churn Analysis
    churnAnalysis: {
      churnRate: number;
      avgLifetime: number; // days
      riskSegments: Array<{
        segment: string;
        users: number;
        churnProbability: number;
        characteristics: string[];
      }>;
    };
  };
  
  // User Segments
  segments: Array<{
    segmentName: string;
    segmentType: 'behavioral' | 'demographic' | 'technographic';
    userCount: number;
    characteristics: string[];
    avgEngagement: number;
    avgRevenue: number;
  }>;
}
```

### Frontend Components

#### User Activity Dashboard
```typescript
// frontend/src/app/users/page.tsx
'use client';

import { useState } from 'react';
import { useUserActivity } from '@/hooks/api/useUserActivity';
import { ActiveUsersChart } from '@/components/users/ActiveUsersChart';
import { SessionAnalytics } from '@/components/users/SessionAnalytics';
import { FeatureUsageHeatmap } from '@/components/users/FeatureUsageHeatmap';
import { UserJourneyFlow } from '@/components/users/UserJourneyFlow';
import { RetentionCurve } from '@/components/users/RetentionCurve';
import { CohortAnalysis } from '@/components/users/CohortAnalysis';
import { UserSegments } from '@/components/users/UserSegments';
import { EngagementScore } from '@/components/users/EngagementScore';

export default function UserActivityDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('30d');
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const { workspaceId } = useAuth();
  
  const { data, isLoading, error } = useUserActivity(workspaceId, timeframe, selectedSegment);
  
  if (isLoading) return <UserActivitySkeleton />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="py-6">
          <h1 className="text-2xl font-bold text-gray-900">User Activity Analytics</h1>
          <p className="mt-1 text-sm text-gray-500">
            Track user engagement, behavior patterns, and feature adoption
          </p>
        </div>
        
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <MetricCard 
            title="Daily Active Users"
            value={data.activityMetrics.dau}
            change={data.activityMetrics.dauChange}
            format="number"
          />
          <MetricCard 
            title="Weekly Active Users"
            value={data.activityMetrics.wau}
            change={data.activityMetrics.wauChange}
            format="number"
          />
          <MetricCard 
            title="Monthly Active Users"
            value={data.activityMetrics.mau}
            change={data.activityMetrics.mauChange}
            format="number"
          />
          <EngagementScore 
            score={data.activityMetrics.engagementScore}
            trend={data.activityMetrics.engagementTrend}
          />
        </div>
        
        {/* Active Users Trend */}
        <ActiveUsersChart 
          data={data.activityMetrics.activityByDate}
          timeframe={timeframe}
        />
        
        {/* Session Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <SessionAnalytics data={data.sessionAnalytics} />
          <FeatureUsageHeatmap features={data.featureUsage.features} />
        </div>
        
        {/* User Journey */}
        <UserJourneyFlow 
          journeys={data.userJourney}
          onPathClick={(path) => analyzePathDetails(path)}
        />
        
        {/* Retention & Cohorts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <RetentionCurve data={data.retention.retentionCurve} />
          <CohortAnalysis cohorts={data.retention.cohorts} />
        </div>
        
        {/* User Segments */}
        <UserSegments 
          segments={data.segments}
          selectedSegment={selectedSegment}
          onSegmentSelect={setSelectedSegment}
        />
      </div>
    </div>
  );
}
```

#### Feature Usage Heatmap
```typescript
// frontend/src/components/users/FeatureUsageHeatmap.tsx
import { useMemo } from 'react';
import { Tooltip } from '@/components/ui/Tooltip';

interface FeatureUsageHeatmapProps {
  features: Array<{
    featureName: string;
    category: string;
    usageCount: number;
    uniqueUsers: number;
    adoptionRate: number;
  }>;
}

export function FeatureUsageHeatmap({ features }: FeatureUsageHeatmapProps) {
  const heatmapData = useMemo(() => {
    // Group features by category
    const grouped = features.reduce((acc, feature) => {
      if (!acc[feature.category]) {
        acc[feature.category] = [];
      }
      acc[feature.category].push(feature);
      return acc;
    }, {} as Record<string, typeof features>);
    
    return grouped;
  }, [features]);
  
  const getIntensity = (adoptionRate: number) => {
    if (adoptionRate > 75) return 'bg-green-600';
    if (adoptionRate > 50) return 'bg-green-500';
    if (adoptionRate > 25) return 'bg-yellow-500';
    if (adoptionRate > 10) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Feature Usage Heatmap</h3>
      
      <div className="space-y-4">
        {Object.entries(heatmapData).map(([category, categoryFeatures]) => (
          <div key={category}>
            <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
            <div className="grid grid-cols-4 gap-2">
              {categoryFeatures.map((feature) => (
                <Tooltip
                  key={feature.featureName}
                  content={
                    <div>
                      <p className="font-medium">{feature.featureName}</p>
                      <p className="text-xs">Usage: {feature.usageCount.toLocaleString()}</p>
                      <p className="text-xs">Users: {feature.uniqueUsers}</p>
                      <p className="text-xs">Adoption: {feature.adoptionRate}%</p>
                    </div>
                  }
                >
                  <div
                    className={`${getIntensity(feature.adoptionRate)} 
                      text-white text-xs p-2 rounded cursor-pointer 
                      hover:opacity-90 transition-opacity`}
                  >
                    <div className="truncate">{feature.featureName}</div>
                    <div className="mt-1 font-semibold">{feature.adoptionRate}%</div>
                  </div>
                </Tooltip>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div className="mt-6 flex items-center justify-between text-xs">
        <span className="text-gray-500">Low Usage</span>
        <div className="flex gap-1">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <div className="w-4 h-4 bg-orange-500 rounded"></div>
          <div className="w-4 h-4 bg-yellow-500 rounded"></div>
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <div className="w-4 h-4 bg-green-600 rounded"></div>
        </div>
        <span className="text-gray-500">High Usage</span>
      </div>
    </div>
  );
}
```

### Backend Implementation

#### User Activity Service
```python
# backend/src/services/analytics/user_activity.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

class UserActivityService:
    def __init__(self, db, cache_service):
        self.db = db
        self.cache = cache_service
    
    async def get_user_activity(
        self,
        workspace_id: str,
        timeframe: str,
        segment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive user activity analytics"""
        
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(timeframe)
        
        # Get user IDs for segment if specified
        user_filter = None
        if segment_id:
            user_filter = await self._get_segment_users(segment_id)
        
        # Parallel fetch all metrics
        results = await asyncio.gather(
            self._get_activity_metrics(workspace_id, start_date, end_date, user_filter),
            self._get_session_analytics(workspace_id, start_date, end_date, user_filter),
            self._get_feature_usage(workspace_id, start_date, end_date, user_filter),
            self._get_user_journeys(workspace_id, start_date, end_date, user_filter),
            self._get_retention_data(workspace_id, start_date, end_date, user_filter),
            self._get_user_segments(workspace_id)
        )
        
        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "activityMetrics": results[0],
            "sessionAnalytics": results[1],
            "featureUsage": results[2],
            "userJourney": results[3],
            "retention": results[4],
            "segments": results[5]
        }
    
    async def _get_activity_metrics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate DAU/WAU/MAU and engagement metrics"""
        
        # Base query for active users
        base_query = """
            WITH user_activity AS (
                SELECT DISTINCT
                    user_id,
                    DATE(created_at) as activity_date
                FROM analytics.user_activity
                WHERE workspace_id = $1
                    AND created_at BETWEEN $2 AND $3
                    {user_filter}
            ),
            daily_metrics AS (
                SELECT
                    activity_date,
                    COUNT(DISTINCT user_id) as daily_users
                FROM user_activity
                GROUP BY activity_date
            )
            SELECT
                -- DAU (today)
                (SELECT daily_users FROM daily_metrics 
                 WHERE activity_date = CURRENT_DATE) as dau,
                
                -- WAU (last 7 days)
                (SELECT COUNT(DISTINCT user_id) FROM user_activity 
                 WHERE activity_date >= CURRENT_DATE - INTERVAL '7 days') as wau,
                
                -- MAU (last 30 days)
                (SELECT COUNT(DISTINCT user_id) FROM user_activity 
                 WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days') as mau,
                
                -- New users
                (SELECT COUNT(DISTINCT user_id) 
                 FROM public.users 
                 WHERE workspace_id = $1 
                    AND created_at BETWEEN $2 AND $3
                    {user_filter}) as new_users,
                
                -- Returning users
                (SELECT COUNT(DISTINCT ua.user_id)
                 FROM user_activity ua
                 JOIN user_activity ua_prev 
                    ON ua.user_id = ua_prev.user_id
                    AND ua_prev.activity_date < ua.activity_date - INTERVAL '1 day'
                ) as returning_users
        """
        
        # Format query with user filter
        if user_filter:
            user_filter_sql = f"AND user_id IN ({','.join(['%s'] * len(user_filter))})"
            query = base_query.replace('{user_filter}', user_filter_sql)
            params = [workspace_id, start_date, end_date] + user_filter
        else:
            query = base_query.replace('{user_filter}', '')
            params = [workspace_id, start_date, end_date]
        
        result = await self.db.fetch_one(query, *params)
        
        # Calculate engagement score
        engagement_score = await self._calculate_engagement_score(
            workspace_id, start_date, end_date
        )
        
        # Get activity distribution
        activity_dist = await self._get_activity_distribution(
            workspace_id, start_date, end_date
        )
        
        return {
            "dau": result['dau'] or 0,
            "wau": result['wau'] or 0,
            "mau": result['mau'] or 0,
            "newUsers": result['new_users'] or 0,
            "returningUsers": result['returning_users'] or 0,
            "engagementScore": engagement_score,
            **activity_dist
        }
    
    async def _get_feature_usage(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze feature usage patterns"""
        
        query = """
            SELECT 
                event_name as feature_name,
                metadata->>'category' as category,
                COUNT(*) as usage_count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(CAST(metadata->>'duration' AS FLOAT)) as avg_time_spent
            FROM analytics.user_activity
            WHERE workspace_id = $1
                AND created_at BETWEEN $2 AND $3
                AND event_type = 'feature_use'
                {user_filter}
            GROUP BY feature_name, category
            ORDER BY usage_count DESC
        """
        
        features = await self.db.fetch_all(query, workspace_id, start_date, end_date)
        
        # Calculate adoption rates
        total_users = await self._get_total_users(workspace_id)
        
        feature_list = []
        for feature in features:
            adoption_rate = (feature['unique_users'] / total_users * 100) if total_users > 0 else 0
            
            feature_list.append({
                "featureName": feature['feature_name'],
                "category": feature['category'] or 'Uncategorized',
                "usageCount": feature['usage_count'],
                "uniqueUsers": feature['unique_users'],
                "avgTimeSpent": round(feature['avg_time_spent'] or 0, 2),
                "adoptionRate": round(adoption_rate, 2)
            })
        
        # Get top features
        top_features = feature_list[:10]
        
        # Identify unused features
        all_features = await self._get_all_features()
        used_features = {f['featureName'] for f in feature_list}
        unused_features = [
            {"feature": f, "lastUsed": None}
            for f in all_features if f not in used_features
        ]
        
        return {
            "features": feature_list,
            "topFeatures": top_features,
            "unusedFeatures": unused_features
        }
    
    async def _get_user_journeys(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze user navigation patterns"""
        
        # Get page sequences
        journey_query = """
            SELECT 
                user_id,
                session_id,
                ARRAY_AGG(page_path ORDER BY created_at) as path,
                COUNT(*) as steps,
                MAX(created_at) - MIN(created_at) as duration
            FROM analytics.user_activity
            WHERE workspace_id = $1
                AND created_at BETWEEN $2 AND $3
                AND event_type = 'page_view'
                {user_filter}
            GROUP BY user_id, session_id
            HAVING COUNT(*) > 1
        """
        
        journeys = await self.db.fetch_all(journey_query, workspace_id, start_date, end_date)
        
        # Analyze common paths
        path_frequency = defaultdict(int)
        for journey in journeys:
            path_key = '->'.join(journey['path'][:5])  # First 5 steps
            path_frequency[path_key] += 1
        
        common_paths = [
            {
                "path": path.split('->'),
                "frequency": count,
                "avgCompletion": 100.0  # Calculate actual completion
            }
            for path, count in sorted(
                path_frequency.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        ]
        
        return {
            "commonPaths": common_paths,
            "entryPoints": await self._get_entry_points(workspace_id, start_date, end_date),
            "exitPoints": await self._get_exit_points(workspace_id, start_date, end_date)
        }
```

#### Retention Analysis Service
```python
# backend/src/services/analytics/retention_analysis.py
class RetentionAnalysisService:
    async def calculate_retention_curve(
        self,
        workspace_id: str,
        cohort_date: datetime,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Calculate retention curve for a cohort"""
        
        query = """
            WITH cohort AS (
                SELECT DISTINCT user_id
                FROM analytics.user_activity
                WHERE workspace_id = $1
                    AND DATE(created_at) = $2
            ),
            retention_data AS (
                SELECT 
                    DATE(ua.created_at) - $2 as days_since_signup,
                    COUNT(DISTINCT ua.user_id) as retained_users
                FROM analytics.user_activity ua
                INNER JOIN cohort c ON ua.user_id = c.user_id
                WHERE ua.workspace_id = $1
                    AND ua.created_at >= $2
                    AND ua.created_at < $2 + INTERVAL '%s days'
                GROUP BY days_since_signup
            )
            SELECT 
                days_since_signup as day,
                retained_users,
                retained_users::FLOAT / (SELECT COUNT(*) FROM cohort) * 100 as retention_rate
            FROM retention_data
            ORDER BY day
        """ % days
        
        results = await self.db.fetch_all(query, workspace_id, cohort_date)
        
        return [
            {
                "day": r['day'],
                "retentionRate": round(r['retention_rate'], 2),
                "activeUsers": r['retained_users']
            }
            for r in results
        ]
```

### Database Schema
```sql
-- User activity event table
CREATE TABLE analytics.user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    workspace_id UUID REFERENCES public.workspaces(id),
    session_id UUID,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    event_name VARCHAR(100),
    page_path VARCHAR(255),
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    device_type VARCHAR(20),
    browser VARCHAR(50),
    os VARCHAR(50),
    country_code VARCHAR(2),
    
    -- Event data
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'page_view', 'feature_use', 'api_call', 
            'login', 'logout', 'error', 'custom'
        )
    )
);

-- Indexes
CREATE INDEX idx_user_activity_user_workspace_time 
    ON analytics.user_activity(user_id, workspace_id, created_at DESC);

CREATE INDEX idx_user_activity_session 
    ON analytics.user_activity(session_id, created_at);

CREATE INDEX idx_user_activity_event 
    ON analytics.user_activity(event_type, event_name, created_at DESC);

-- User segments table
CREATE TABLE analytics.user_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    segment_name VARCHAR(100) NOT NULL,
    segment_type VARCHAR(50),
    
    -- Segment definition
    criteria JSONB NOT NULL,
    
    -- Cached metrics
    user_count INTEGER DEFAULT 0,
    avg_engagement NUMERIC(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Testing Requirements
- Unit tests for DAU/WAU/MAU calculations
- Integration tests for session tracking
- Performance tests for large datasets
- Privacy compliance tests
- Accuracy tests for retention calculations

## Performance Targets
- Activity metrics query: <500ms
- Feature usage heatmap: <1 second
- User journey analysis: <2 seconds
- Retention curve calculation: <1 second

## Security Considerations
- PII anonymization in analytics
- GDPR/CCPA compliance
- User consent tracking
- Data retention policies
- IP address hashing