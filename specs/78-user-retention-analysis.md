# User Retention Analysis Specification

## Overview
Simple user retention tracking without complex cohort analysis or predictive modeling. Track who comes back and when.

## TypeScript Interfaces

```typescript
// User retention event
interface RetentionEvent {
  user_id: string;
  date: string;
  is_new_user: boolean;
  days_since_signup: number;
  session_count: number;
  activity_score: number;
}

// Daily retention summary
interface DailyRetention {
  date: string;
  total_users: number;
  returning_users: number;
  new_users: number;
  churned_count: number;
  retention_rate: number;
}

// User retention status
interface UserRetentionStatus {
  user_id: string;
  first_seen: Date;
  last_seen: Date;
  total_days_active: number;
  current_streak: number;
  status: 'active' | 'at_risk' | 'churned';
}

// Weekly retention cohort
interface WeeklyRetention {
  week_start: Date;
  week_number: number;
  users_started: number;
  week_1_retained: number;
  week_2_retained: number;
  week_3_retained: number;
  week_4_retained: number;
}
```

## SQL Schema

```sql
-- Simple retention tracking table
CREATE TABLE user_retention (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    is_new_user BOOLEAN DEFAULT false,
    days_since_signup INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 1,
    activity_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Daily retention aggregates
CREATE TABLE daily_retention (
    date DATE PRIMARY KEY,
    total_users INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    churned_count INTEGER DEFAULT 0,
    retention_rate DECIMAL(5,2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User retention status
CREATE TABLE user_retention_status (
    user_id VARCHAR(255) PRIMARY KEY,
    first_seen DATE NOT NULL,
    last_seen DATE NOT NULL,
    total_days_active INTEGER DEFAULT 1,
    current_streak INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weekly cohorts (simplified)
CREATE TABLE weekly_retention_cohorts (
    week_start DATE PRIMARY KEY,
    week_number INTEGER NOT NULL,
    users_started INTEGER DEFAULT 0,
    week_1_retained INTEGER DEFAULT 0,
    week_2_retained INTEGER DEFAULT 0,
    week_3_retained INTEGER DEFAULT 0,
    week_4_retained INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes only
CREATE INDEX idx_retention_user_date ON user_retention(user_id, date DESC);
CREATE INDEX idx_retention_status ON user_retention_status(status);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class RetentionStatus(Enum):
    ACTIVE = "active"
    AT_RISK = "at_risk"
    CHURNED = "churned"

@dataclass
class RetentionMetrics:
    """Simple retention metrics"""
    user_id: str
    days_active: int
    last_seen_days_ago: int
    retention_score: float
    status: RetentionStatus
    
    def calculate_score(self) -> float:
        """Simple retention score based on activity"""
        if self.last_seen_days_ago == 0:
            return 100.0
        elif self.last_seen_days_ago <= 3:
            return 80.0
        elif self.last_seen_days_ago <= 7:
            return 60.0
        elif self.last_seen_days_ago <= 14:
            return 40.0
        elif self.last_seen_days_ago <= 30:
            return 20.0
        else:
            return 0.0

class RetentionAnalyzer:
    """Simple retention analysis without ML"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def track_daily_activity(self, user_id: str) -> None:
        """Track user activity for retention"""
        query = """
        INSERT INTO user_retention (user_id, date, is_new_user, days_since_signup)
        VALUES (%s, CURRENT_DATE, %s, %s)
        ON CONFLICT (user_id, date) 
        DO UPDATE SET 
            session_count = user_retention.session_count + 1,
            activity_score = user_retention.activity_score + 10
        """
        
        # Check if new user
        is_new = self.is_new_user(user_id)
        days_since = self.get_days_since_signup(user_id)
        
        self.db.execute(query, (user_id, is_new, days_since))
        self.update_user_status(user_id)
    
    def is_new_user(self, user_id: str) -> bool:
        """Check if user is new (first day)"""
        query = """
        SELECT COUNT(*) = 0 as is_new
        FROM user_retention
        WHERE user_id = %s
        """
        result = self.db.fetchone(query, (user_id,))
        return result['is_new'] if result else True
    
    def get_days_since_signup(self, user_id: str) -> int:
        """Get days since user first appeared"""
        query = """
        SELECT EXTRACT(DAY FROM CURRENT_DATE - MIN(date))::INTEGER as days
        FROM user_retention
        WHERE user_id = %s
        """
        result = self.db.fetchone(query, (user_id,))
        return result['days'] if result and result['days'] else 0
    
    def update_user_status(self, user_id: str) -> None:
        """Update user retention status"""
        query = """
        INSERT INTO user_retention_status (user_id, first_seen, last_seen, total_days_active)
        VALUES (%s, CURRENT_DATE, CURRENT_DATE, 1)
        ON CONFLICT (user_id)
        DO UPDATE SET
            last_seen = CURRENT_DATE,
            total_days_active = user_retention_status.total_days_active + 1,
            current_streak = CASE
                WHEN user_retention_status.last_seen = CURRENT_DATE - INTERVAL '1 day'
                THEN user_retention_status.current_streak + 1
                ELSE 1
            END,
            status = CASE
                WHEN CURRENT_DATE - user_retention_status.last_seen <= INTERVAL '7 days' THEN 'active'
                WHEN CURRENT_DATE - user_retention_status.last_seen <= INTERVAL '14 days' THEN 'at_risk'
                ELSE 'churned'
            END,
            updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(query, (user_id,))
    
    def calculate_daily_retention(self, date: Optional[datetime] = None) -> Dict:
        """Calculate retention for a specific day"""
        target_date = date or datetime.now().date()
        
        query = """
        WITH daily_stats AS (
            SELECT
                COUNT(DISTINCT user_id) as total_users,
                COUNT(DISTINCT CASE WHEN is_new_user THEN user_id END) as new_users,
                COUNT(DISTINCT CASE WHEN NOT is_new_user THEN user_id END) as returning_users
            FROM user_retention
            WHERE date = %s
        ),
        churned_stats AS (
            SELECT COUNT(*) as churned_count
            FROM user_retention_status
            WHERE status = 'churned'
            AND DATE(updated_at) = %s
        )
        SELECT 
            ds.total_users,
            ds.new_users,
            ds.returning_users,
            cs.churned_count,
            CASE 
                WHEN ds.total_users > 0 
                THEN (ds.returning_users::FLOAT / ds.total_users * 100)
                ELSE 0 
            END as retention_rate
        FROM daily_stats ds, churned_stats cs
        """
        
        result = self.db.fetchone(query, (target_date, target_date))
        
        # Store in daily aggregates
        self.store_daily_retention(target_date, result)
        
        return result
    
    def store_daily_retention(self, date: datetime, metrics: Dict) -> None:
        """Store daily retention metrics"""
        query = """
        INSERT INTO daily_retention 
        (date, total_users, returning_users, new_users, churned_count, retention_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (date)
        DO UPDATE SET
            total_users = EXCLUDED.total_users,
            returning_users = EXCLUDED.returning_users,
            new_users = EXCLUDED.new_users,
            churned_count = EXCLUDED.churned_count,
            retention_rate = EXCLUDED.retention_rate,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (
            date,
            metrics['total_users'],
            metrics['returning_users'],
            metrics['new_users'],
            metrics['churned_count'],
            metrics['retention_rate']
        ))
    
    def get_retention_trend(self, days: int = 30) -> List[Dict]:
        """Get retention trend for past N days"""
        query = """
        SELECT 
            date,
            total_users,
            returning_users,
            new_users,
            retention_rate
        FROM daily_retention
        WHERE date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date DESC
        """
        return self.db.fetchall(query, (days,))
    
    def get_at_risk_users(self) -> List[Dict]:
        """Get users at risk of churning"""
        query = """
        SELECT 
            user_id,
            last_seen,
            total_days_active,
            current_streak,
            EXTRACT(DAY FROM CURRENT_DATE - last_seen)::INTEGER as days_inactive
        FROM user_retention_status
        WHERE status = 'at_risk'
        ORDER BY last_seen DESC
        LIMIT 100
        """
        return self.db.fetchall(query)
    
    def get_simple_cohort_retention(self, weeks_back: int = 4) -> List[Dict]:
        """Get simple weekly cohort retention"""
        query = """
        WITH weekly_cohorts AS (
            SELECT 
                DATE_TRUNC('week', first_seen) as week_start,
                user_id,
                first_seen
            FROM user_retention_status
            WHERE first_seen >= CURRENT_DATE - INTERVAL '%s weeks'
        )
        SELECT 
            week_start,
            COUNT(DISTINCT user_id) as users_started,
            COUNT(DISTINCT CASE 
                WHEN last_seen >= first_seen + INTERVAL '1 week' 
                THEN user_id 
            END) as week_1_retained,
            COUNT(DISTINCT CASE 
                WHEN last_seen >= first_seen + INTERVAL '2 weeks' 
                THEN user_id 
            END) as week_2_retained,
            COUNT(DISTINCT CASE 
                WHEN last_seen >= first_seen + INTERVAL '3 weeks' 
                THEN user_id 
            END) as week_3_retained,
            COUNT(DISTINCT CASE 
                WHEN last_seen >= first_seen + INTERVAL '4 weeks' 
                THEN user_id 
            END) as week_4_retained
        FROM weekly_cohorts wc
        LEFT JOIN user_retention_status urs ON wc.user_id = urs.user_id
        GROUP BY week_start
        ORDER BY week_start DESC
        """
        return self.db.fetchall(query, (weeks_back,))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, date
from typing import List, Optional

router = APIRouter(prefix="/api/retention", tags=["retention"])

@router.post("/track/{user_id}")
async def track_user_activity(user_id: str):
    """Track user activity for retention analysis"""
    try:
        analyzer = RetentionAnalyzer(db)
        analyzer.track_daily_activity(user_id)
        return {"status": "tracked", "user_id": user_id}
    except Exception as e:
        return {"error": str(e)}

@router.get("/daily")
async def get_daily_retention(
    date: Optional[date] = Query(None, description="Specific date")
):
    """Get daily retention metrics"""
    analyzer = RetentionAnalyzer(db)
    metrics = analyzer.calculate_daily_retention(date)
    return metrics

@router.get("/trend")
async def get_retention_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days")
):
    """Get retention trend over time"""
    analyzer = RetentionAnalyzer(db)
    trend = analyzer.get_retention_trend(days)
    return {"trend": trend, "days": days}

@router.get("/at-risk")
async def get_at_risk_users():
    """Get users at risk of churning"""
    analyzer = RetentionAnalyzer(db)
    users = analyzer.get_at_risk_users()
    return {"at_risk_users": users, "count": len(users)}

@router.get("/cohorts")
async def get_cohort_retention(
    weeks: int = Query(4, ge=1, le=12, description="Weeks to analyze")
):
    """Get simple weekly cohort retention"""
    analyzer = RetentionAnalyzer(db)
    cohorts = analyzer.get_simple_cohort_retention(weeks)
    return {"cohorts": cohorts}

@router.get("/user/{user_id}/status")
async def get_user_retention_status(user_id: str):
    """Get retention status for specific user"""
    query = """
    SELECT 
        user_id,
        first_seen,
        last_seen,
        total_days_active,
        current_streak,
        status,
        EXTRACT(DAY FROM CURRENT_DATE - last_seen)::INTEGER as days_inactive
    FROM user_retention_status
    WHERE user_id = %s
    """
    result = db.fetchone(query, (user_id,))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.get("/summary")
async def get_retention_summary():
    """Get overall retention summary"""
    query = """
    SELECT 
        COUNT(DISTINCT CASE WHEN status = 'active' THEN user_id END) as active_users,
        COUNT(DISTINCT CASE WHEN status = 'at_risk' THEN user_id END) as at_risk_users,
        COUNT(DISTINCT CASE WHEN status = 'churned' THEN user_id END) as churned_users,
        AVG(current_streak) as avg_streak,
        AVG(total_days_active) as avg_days_active
    FROM user_retention_status
    """
    result = db.fetchone(query)
    return result
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Line, Bar } from 'recharts';

interface RetentionMetrics {
  date: string;
  totalUsers: number;
  returningUsers: number;
  newUsers: number;
  retentionRate: number;
}

interface AtRiskUser {
  userId: string;
  lastSeen: string;
  daysInactive: number;
  totalDaysActive: number;
  currentStreak: number;
}

export const RetentionDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<RetentionMetrics[]>([]);
  const [atRiskUsers, setAtRiskUsers] = useState<AtRiskUser[]>([]);
  const [summary, setSummary] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRetentionData();
  }, []);

  const fetchRetentionData = async () => {
    try {
      const [trendRes, atRiskRes, summaryRes] = await Promise.all([
        fetch('/api/retention/trend?days=30'),
        fetch('/api/retention/at-risk'),
        fetch('/api/retention/summary')
      ]);

      const trend = await trendRes.json();
      const atRisk = await atRiskRes.json();
      const sum = await summaryRes.json();

      setMetrics(trend.trend);
      setAtRiskUsers(atRisk.at_risk_users);
      setSummary(sum);
    } catch (error) {
      console.error('Error fetching retention data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'at_risk': return 'text-yellow-600';
      case 'churned': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const formatDaysAgo = (days: number) => {
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    return `${days} days ago`;
  };

  if (loading) return <div>Loading retention data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">User Retention Analysis</h2>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Active Users</div>
          <div className="text-2xl font-bold text-green-600">
            {summary.active_users || 0}
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">At Risk</div>
          <div className="text-2xl font-bold text-yellow-600">
            {summary.at_risk_users || 0}
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Churned</div>
          <div className="text-2xl font-bold text-red-600">
            {summary.churned_users || 0}
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Avg Streak</div>
          <div className="text-2xl font-bold">
            {Math.round(summary.avg_streak || 0)} days
          </div>
        </div>
      </div>

      {/* Retention Trend Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">30-Day Retention Trend</h3>
        <div className="h-64">
          <Line
            data={metrics}
            xKey="date"
            yKey="retentionRate"
            stroke="#10b981"
            strokeWidth={2}
          />
        </div>
      </div>

      {/* User Activity Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Daily User Activity</h3>
        <div className="h-64">
          <Bar data={metrics}>
            <Bar dataKey="newUsers" fill="#3b82f6" name="New Users" />
            <Bar dataKey="returningUsers" fill="#10b981" name="Returning Users" />
          </Bar>
        </div>
      </div>

      {/* At Risk Users Table */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">At Risk Users</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  User ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Last Seen
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Days Inactive
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Total Active Days
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Current Streak
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {atRiskUsers.slice(0, 10).map((user) => (
                <tr key={user.userId} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm">{user.userId}</td>
                  <td className="px-4 py-2 text-sm">
                    {formatDaysAgo(user.daysInactive)}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <span className="text-yellow-600">{user.daysInactive}</span>
                  </td>
                  <td className="px-4 py-2 text-sm">{user.totalDaysActive}</td>
                  <td className="px-4 py-2 text-sm">{user.currentStreak}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Simple Cohort Retention */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Weekly Cohort Retention</h3>
        <div className="text-sm text-gray-600 mb-2">
          Shows % of users retained each week after signup
        </div>
        <SimpleRetentionCohorts />
      </div>
    </div>
  );
};

const SimpleRetentionCohorts: React.FC = () => {
  const [cohorts, setCohorts] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/retention/cohorts?weeks=4')
      .then(res => res.json())
      .then(data => setCohorts(data.cohorts))
      .catch(console.error);
  }, []);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
              Week
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">
              Users
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">
              Week 1
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">
              Week 2
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">
              Week 3
            </th>
            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">
              Week 4
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {cohorts.map((cohort) => (
            <tr key={cohort.week_start}>
              <td className="px-4 py-2 text-sm">
                {new Date(cohort.week_start).toLocaleDateString()}
              </td>
              <td className="px-4 py-2 text-sm text-center">
                {cohort.users_started}
              </td>
              <td className="px-4 py-2 text-sm text-center">
                {cohort.users_started > 0 
                  ? `${Math.round(cohort.week_1_retained / cohort.users_started * 100)}%`
                  : '-'}
              </td>
              <td className="px-4 py-2 text-sm text-center">
                {cohort.users_started > 0 
                  ? `${Math.round(cohort.week_2_retained / cohort.users_started * 100)}%`
                  : '-'}
              </td>
              <td className="px-4 py-2 text-sm text-center">
                {cohort.users_started > 0 
                  ? `${Math.round(cohort.week_3_retained / cohort.users_started * 100)}%`
                  : '-'}
              </td>
              <td className="px-4 py-2 text-sm text-center">
                {cohort.users_started > 0 
                  ? `${Math.round(cohort.week_4_retained / cohort.users_started * 100)}%`
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic retention tracking (user activity, daily metrics)
- **Phase 2**: At-risk user identification
- **Phase 3**: Simple cohort analysis
- **Phase 4**: Retention alerts and notifications

## Performance Considerations
- Daily batch processing for retention calculations
- Minimal real-time processing
- Simple SQL queries without complex joins
- Limited historical data retention (90 days)

## Security Considerations
- User ID hashing for privacy
- No PII in retention tables
- Rate limiting on tracking endpoints
- Aggregate data only in dashboards

## Monitoring and Alerts
- Alert when retention rate drops below 60%
- Daily report of at-risk users
- Weekly cohort performance summary
- Monthly retention trend analysis

## Dependencies
- PostgreSQL for data storage
- FastAPI for REST endpoints
- React with Recharts for visualization
- Daily cron job for batch processing