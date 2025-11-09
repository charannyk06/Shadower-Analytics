# User Feature Adoption Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track which features users actually use versus what they ignore. No complex analytics - just simple feature adoption tracking to know what's valuable.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Feature usage tracking
interface FeatureUsage {
  userId: string;
  feature: FeatureInfo;
  usage: UsageMetrics;
  adoption: AdoptionStatus;
}

interface FeatureInfo {
  id: string;
  name: string;
  category: 'core' | 'advanced' | 'experimental' | 'premium';
  releaseDate: Date;
  complexity: 'simple' | 'moderate' | 'complex';
}

interface UsageMetrics {
  firstUsed?: Date;
  lastUsed?: Date;
  useCount: number;
  dailyUse: boolean;
  weeklyUse: boolean;
  abandoned: boolean;
}

interface AdoptionStatus {
  stage: 'unaware' | 'aware' | 'tried' | 'regular' | 'power' | 'abandoned';
  timeToAdoption?: number; // Days from release to first use
  stickiness: number; // Percentage of days used after first use
}

// Feature discovery
interface FeatureDiscovery {
  userId: string;
  featureId: string;
  discoveryMethod: 'tutorial' | 'exploration' | 'recommendation' | 'documentation';
  timestamp: Date;
  converted: boolean;
}
```

#### 1.2 SQL Schema

```sql
-- Dead simple feature tracking
CREATE TABLE feature_usage (
    user_id UUID NOT NULL,
    feature_id VARCHAR(100) NOT NULL,
    feature_name VARCHAR(255),
    first_used DATE,
    last_used DATE,
    use_count INTEGER DEFAULT 0,
    abandoned BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, feature_id)
);

-- Daily feature usage snapshots
CREATE TABLE daily_feature_usage (
    date DATE NOT NULL,
    feature_id VARCHAR(100) NOT NULL,
    unique_users INTEGER DEFAULT 0,
    total_uses INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,
    PRIMARY KEY (date, feature_id)
);

-- Feature discovery tracking
CREATE TABLE feature_discoveries (
    user_id UUID NOT NULL,
    feature_id VARCHAR(100) NOT NULL,
    discovery_method VARCHAR(50),
    discovered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    first_used_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, feature_id)
);

-- Simple indexes
CREATE INDEX idx_feature_usage_user ON feature_usage(user_id);
CREATE INDEX idx_feature_usage_last ON feature_usage(last_used DESC);
CREATE INDEX idx_daily_feature_date ON daily_feature_usage(date DESC);
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta

@dataclass
class FeatureAdoptionAnalyzer:
    """Track what features people actually use"""
    
    def get_user_features(self, user_id: str) -> List[Dict]:
        """What features does this user use?"""
        return self.db.query(
            """
            SELECT 
                feature_id,
                feature_name,
                use_count,
                first_used,
                last_used,
                abandoned
            FROM feature_usage
            WHERE user_id = ?
            ORDER BY use_count DESC
            """,
            (user_id,)
        )
    
    def get_popular_features(self) -> List[Dict]:
        """Most used features this week"""
        return self.db.query(
            """
            SELECT 
                feature_id,
                SUM(unique_users) as users,
                SUM(total_uses) as uses
            FROM daily_feature_usage
            WHERE date > CURRENT_DATE - INTERVAL '7 days'
            GROUP BY feature_id
            ORDER BY users DESC
            LIMIT 10
            """
        )
    
    def get_ignored_features(self) -> List[Dict]:
        """Features nobody uses"""
        return self.db.query(
            """
            SELECT 
                feature_id,
                MAX(date) as last_seen,
                MAX(unique_users) as peak_users
            FROM daily_feature_usage
            GROUP BY feature_id
            HAVING MAX(unique_users) < 10
            OR MAX(date) < CURRENT_DATE - INTERVAL '30 days'
            """
        )
    
    def calculate_adoption_funnel(self, feature_id: str) -> Dict:
        """How many users adopt a feature?"""
        stats = self.db.query_one(
            """
            SELECT 
                COUNT(DISTINCT user_id) as discovered,
                COUNT(DISTINCT CASE WHEN first_used_at IS NOT NULL 
                      THEN user_id END) as tried,
                COUNT(DISTINCT CASE WHEN use_count > 5 
                      THEN user_id END) as regular_users
            FROM feature_discoveries
            LEFT JOIN feature_usage USING (user_id, feature_id)
            WHERE feature_id = ?
            """,
            (feature_id,)
        )
        
        return {
            'discovered': stats['discovered'],
            'tried': stats['tried'],
            'regular': stats['regular_users'],
            'conversion_rate': stats['tried'] / stats['discovered'] if stats['discovered'] > 0 else 0,
            'retention_rate': stats['regular_users'] / stats['tried'] if stats['tried'] > 0 else 0
        }
```

### 2. API Endpoints

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/features")

@router.post("/track")
async def track_feature_use(
    user_id: str,
    feature_id: str
):
    """Track feature usage"""
    pass

@router.get("/user/{user_id}")
async def get_user_features(user_id: str):
    """Get user's feature usage"""
    pass

@router.get("/popular")
async def get_popular_features():
    """Most used features"""
    pass

@router.get("/ignored")
async def get_ignored_features():
    """Unused features"""
    pass

@router.get("/{feature_id}/adoption")
async def get_feature_adoption(feature_id: str):
    """Feature adoption funnel"""
    pass
```

### 3. Dashboard Components

```typescript
export const FeatureTracker: React.FC = () => {
  // Auto-track feature usage
  const trackFeature = (featureId: string) => {
    api.post('/features/track', {
      userId: getCurrentUser().id,
      featureId
    });
  };
  
  // Track on feature component mount
  useEffect(() => {
    trackFeature(props.featureId);
  }, []);
  
  return null;
};

export const MyFeatures: React.FC = () => {
  const [features, setFeatures] = useState([]);
  
  return (
    <div>
      <h3>Your Features</h3>
      <div className="grid grid-cols-3 gap-2">
        {features.map(f => (
          <div key={f.featureId} className={`p-2 rounded ${f.abandoned ? 'opacity-50' : ''}`}>
            <div>{f.featureName}</div>
            <div className="text-xs">Used {f.useCount} times</div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## What This Tells Us

- Which features are actually valuable
- What to improve vs what to remove
- User learning curves
- Feature discovery methods that work

## Cost Optimization

- Track feature use, not every click
- Daily aggregations
- 30-day retention only
- No complex attribution