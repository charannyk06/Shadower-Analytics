# Specification: Cohort Analysis

## Feature Overview
User cohort tracking and retention analysis to understand user behavior patterns over time.

## Technical Requirements
- Cohort creation and segmentation
- Retention calculation
- Cohort comparison
- Behavioral analysis
- LTV calculation

## Implementation Details

### Data Structure
```typescript
interface CohortAnalysis {
  cohortType: 'signup' | 'activation' | 'feature_adoption' | 'custom';
  cohortPeriod: 'daily' | 'weekly' | 'monthly';
  
  cohorts: Array<{
    cohortId: string;
    cohortDate: string;
    cohortSize: number;
    
    retention: {
      day0: number;   // 100%
      day1: number;
      day7: number;
      day14: number;
      day30: number;
      day60: number;
      day90: number;
    };
    
    metrics: {
      avgRevenue: number;
      ltv: number;
      churnRate: number;
      engagementScore: number;
    };
    
    segments: Array<{
      segment: string;
      count: number;
      retention: number;
    }>;
  }>;
  
  comparison: {
    bestPerforming: string;
    worstPerforming: string;
    avgRetention: number;
    trend: 'improving' | 'declining' | 'stable';
  };
}
```

### Backend Implementation
```python
# backend/src/services/analytics/cohort_analysis.py
class CohortAnalysisService:
    async def calculate_cohorts(
        self,
        workspace_id: str,
        cohort_type: str,
        period: str
    ):
        query = """
            WITH cohort_users AS (
                SELECT 
                    user_id,
                    DATE_TRUNC($2, created_at) as cohort_date
                FROM public.users
                WHERE workspace_id = $1
                GROUP BY user_id, DATE_TRUNC($2, created_at)
            ),
            retention_data AS (
                SELECT 
                    cu.cohort_date,
                    cu.user_id,
                    DATE(ua.created_at) as activity_date,
                    DATE(ua.created_at) - cu.cohort_date as days_since_signup
                FROM cohort_users cu
                LEFT JOIN analytics.user_activity ua 
                    ON cu.user_id = ua.user_id
            )
            SELECT 
                cohort_date,
                COUNT(DISTINCT user_id) as cohort_size,
                COUNT(DISTINCT CASE WHEN days_since_signup = 0 THEN user_id END) as day_0,
                COUNT(DISTINCT CASE WHEN days_since_signup = 1 THEN user_id END) as day_1,
                COUNT(DISTINCT CASE WHEN days_since_signup = 7 THEN user_id END) as day_7,
                COUNT(DISTINCT CASE WHEN days_since_signup = 30 THEN user_id END) as day_30
            FROM retention_data
            GROUP BY cohort_date
            ORDER BY cohort_date DESC
        """
        
        return await self.db.fetch_all(query, workspace_id, period)
```

## Testing Requirements
- Retention calculation accuracy
- Cohort segmentation tests
- LTV calculation validation

## Performance Targets
- Cohort calculation: <3 seconds
- Retention matrix: <2 seconds

## Security Considerations
- User data privacy
- Cohort anonymization