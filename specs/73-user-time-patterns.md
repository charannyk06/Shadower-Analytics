# User Time Patterns Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

When do users actually use the system? Track activity patterns by time of day, day of week. Simple time-based analytics to understand user habits.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Time patterns
interface UserTimePattern {
  userId: string;
  patterns: TimePattern;
  peak: PeakUsage;
  consistency: UsageConsistency;
}

interface TimePattern {
  hourlyDistribution: number[]; // 24 hours
  dailyDistribution: number[]; // 7 days
  monthlyDistribution: number[]; // 30 days
  timezone: string;
}

interface PeakUsage {
  peakHour: number;
  peakDay: string;
  peakDuration: number;
  offHours: number[];
}

interface UsageConsistency {
  isRegular: boolean;
  avgSessionsPerDay: number;
  activeDays: number;
  streakDays: number;
}
```

#### 1.2 SQL Schema

```sql
-- Hourly activity tracking
CREATE TABLE hourly_activity (
    user_id UUID NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour < 24),
    activity_count INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date, hour)
);

-- User time patterns
CREATE TABLE user_time_patterns (
    user_id UUID PRIMARY KEY,
    peak_hour INTEGER,
    peak_day VARCHAR(10),
    timezone VARCHAR(50),
    is_morning_user BOOLEAN,
    is_evening_user BOOLEAN,
    is_weekend_user BOOLEAN,
    avg_sessions_per_day DECIMAL(5,2),
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Simple activity log
CREATE TABLE activity_log (
    user_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    activity_type VARCHAR(50),
    PRIMARY KEY (user_id, timestamp)
);

CREATE INDEX idx_hourly_activity_user ON hourly_activity(user_id, date DESC);
CREATE INDEX idx_activity_log_time ON activity_log(timestamp DESC);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class TimePatternAnalyzer:
    """When are users active?"""
    
    def get_user_peak_hours(self, user_id: str) -> Dict:
        """When is user most active?"""
        hourly = self.db.query(
            """
            SELECT 
                hour,
                SUM(activity_count) as total
            FROM hourly_activity
            WHERE user_id = ? AND date > CURRENT_DATE - INTERVAL '30 days'
            GROUP BY hour
            ORDER BY total DESC
            """,
            (user_id,)
        )
        
        if not hourly:
            return {}
            
        peak_hour = hourly[0]['hour']
        
        return {
            'peak_hour': peak_hour,
            'peak_period': 'morning' if peak_hour < 12 else 'afternoon' if peak_hour < 17 else 'evening',
            'distribution': {h['hour']: h['total'] for h in hourly}
        }
    
    def identify_user_type(self, user_id: str) -> str:
        """Morning person or night owl?"""
        pattern = self.get_user_peak_hours(user_id)
        
        if not pattern:
            return 'unknown'
            
        peak = pattern['peak_hour']
        
        if peak >= 5 and peak < 9:
            return 'early_bird'
        elif peak >= 9 and peak < 17:
            return 'business_hours'
        elif peak >= 17 and peak < 22:
            return 'evening_user'
        else:
            return 'night_owl'
    
    def calculate_streak(self, user_id: str) -> int:
        """How many days in a row?"""
        days = self.db.query(
            """
            SELECT DISTINCT date
            FROM hourly_activity
            WHERE user_id = ?
            ORDER BY date DESC
            """,
            (user_id,)
        )
        
        if not days:
            return 0
            
        streak = 1
        last_date = days[0]['date']
        
        for day in days[1:]:
            if (last_date - day['date']).days == 1:
                streak += 1
                last_date = day['date']
            else:
                break
                
        return streak
```

### 2. API Endpoints

```python
@router.post("/activity")
async def log_activity(
    user_id: str,
    activity_type: str
):
    """Log user activity"""
    pass

@router.get("/patterns/{user_id}")
async def get_time_patterns(user_id: str):
    """Get user's time patterns"""
    pass

@router.get("/peak-hours")
async def get_peak_hours():
    """System-wide peak hours"""
    pass

@router.get("/streak/{user_id}")
async def get_user_streak(user_id: str):
    """User's activity streak"""
    pass
```

### 3. Dashboard Components

```typescript
export const ActivityTracker: React.FC = () => {
  // Log activity every minute while active
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        api.post('/time-patterns/activity', {
          userId: getCurrentUser().id,
          activityType: 'active'
        });
      }
    }, 60000);
    
    return () => clearInterval(interval);
  }, []);
  
  return null;
};

export const UserTimePattern: React.FC = () => {
  const [pattern, setPattern] = useState(null);
  
  return (
    <div>
      <h3>Your Activity Pattern</h3>
      <div className="text-2xl">
        {pattern?.userType === 'early_bird' ? '🌅 Early Bird' :
         pattern?.userType === 'night_owl' ? '🦉 Night Owl' :
         '📊 Regular Hours'}
      </div>
      <div className="text-sm">
        Peak: {pattern?.peakHour}:00
      </div>
      <div className="text-sm">
        🔥 {pattern?.streak} day streak
      </div>
    </div>
  );
};
```

## What This Tells Us

- When to schedule maintenance
- When users need support
- User consistency patterns
- Best times for notifications

## Cost Optimization

- Hourly aggregation only
- No minute-level tracking
- 30-day retention
- Batch activity logs