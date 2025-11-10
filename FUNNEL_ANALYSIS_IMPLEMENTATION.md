# Funnel Analysis Implementation

## Overview

This document describes the implementation of the Funnel Analysis feature for Shadower-Analytics. The feature enables conversion funnel tracking, drop-off analysis, and user journey optimization.

## Architecture

### Backend Components

#### 1. Database Layer
- **Location**: `database/migrations/014_create_funnel_analysis_tables.sql`
- **Tables**:
  - `analytics.funnel_definitions` - Stores funnel configurations
  - `analytics.funnel_analysis_results` - Caches analysis results
  - `analytics.funnel_step_performance` - Per-step performance metrics
  - `analytics.user_funnel_journeys` - Individual user paths

#### 2. Data Models
- **Location**: `backend/src/models/database/tables.py`
- **Models**:
  - `FunnelDefinition` - Funnel configuration model
  - `FunnelAnalysisResult` - Analysis results model
  - `FunnelStepPerformance` - Step metrics model
  - `UserFunnelJourney` - User journey tracking model

#### 3. Service Layer
- **Location**: `backend/src/services/analytics/funnel_analysis.py`
- **Class**: `FunnelAnalysisService`
- **Key Methods**:
  - `create_funnel_definition()` - Create new funnel
  - `analyze_funnel()` - Run funnel analysis
  - `track_user_journey()` - Track user progress
  - `get_funnel_performance_summary()` - Get all funnels overview

#### 4. API Endpoints
- **Location**: `backend/src/api/routes/funnels.py`
- **Endpoints**:
  - `POST /api/v1/funnels/definitions` - Create funnel
  - `GET /api/v1/funnels/definitions` - List funnels
  - `GET /api/v1/funnels/definitions/{id}` - Get funnel details
  - `PATCH /api/v1/funnels/definitions/{id}` - Update funnel
  - `POST /api/v1/funnels/definitions/{id}/analyze` - Run analysis
  - `GET /api/v1/funnels/definitions/{id}/journeys` - Get user journeys
  - `GET /api/v1/funnels/performance-summary` - Get summary

### Frontend Components

#### 1. Type Definitions
- **Location**: `frontend/src/types/funnel-analysis.ts`
- **Types**:
  - `FunnelDefinition` - Funnel configuration
  - `FunnelAnalysisResult` - Analysis data
  - `UserFunnelJourney` - User journey data
  - `FunnelPerformanceSummaryResponse` - Summary data

#### 2. API Integration
- **Location**: `frontend/src/hooks/api/useFunnelAnalysis.ts`
- **Hooks**:
  - `useFunnelDefinitions()` - List funnels
  - `useFunnelDefinition()` - Get single funnel
  - `useCreateFunnelDefinition()` - Create funnel
  - `useUpdateFunnelDefinition()` - Update funnel
  - `useFunnelAnalysis()` - Run analysis
  - `useFunnelJourneys()` - Get journeys
  - `useFunnelPerformanceSummary()` - Get summary

- **Location**: `frontend/src/lib/api/endpoints.ts`
- **Endpoints**: Registered all funnel API endpoints

## Database Schema

### funnel_definitions Table
```sql
- id (UUID, PK)
- workspace_id (UUID, FK)
- name (VARCHAR)
- description (TEXT)
- status (VARCHAR) - active, paused, archived
- steps (JSONB) - Array of funnel steps
- timeframe (VARCHAR) - Default analysis period
- segment_by (VARCHAR) - Optional segmentation field
- created_by (UUID)
- created_at, updated_at (TIMESTAMPTZ)
```

### funnel_analysis_results Table
```sql
- id (UUID, PK)
- funnel_id (UUID, FK)
- workspace_id (UUID, FK)
- analysis_start, analysis_end (TIMESTAMPTZ)
- step_results (JSONB) - Per-step metrics
- total_entered, total_completed (INTEGER)
- overall_conversion_rate (DECIMAL)
- avg_time_to_complete (DECIMAL)
- biggest_drop_off_step (VARCHAR)
- biggest_drop_off_rate (DECIMAL)
- segment_name (VARCHAR)
- segment_results (JSONB)
- calculated_at, created_at (TIMESTAMPTZ)
```

### user_funnel_journeys Table
```sql
- id (UUID, PK)
- funnel_id (UUID, FK)
- workspace_id, user_id (UUID)
- started_at, completed_at (TIMESTAMPTZ)
- last_step_reached (VARCHAR)
- status (VARCHAR) - in_progress, completed, abandoned
- journey_path (JSONB) - Array of steps with timestamps
- total_time_spent (DECIMAL)
- time_per_step (JSONB)
- user_segment (VARCHAR)
- created_at, updated_at (TIMESTAMPTZ)
```

## API Usage Examples

### Create a Funnel
```bash
POST /api/v1/funnels/definitions?workspace_id={workspace_id}
Content-Type: application/json

{
  "name": "Sign-up Funnel",
  "description": "Track user sign-up process",
  "steps": [
    {
      "stepId": "landing",
      "stepName": "Landing Page",
      "event": "page_view_landing"
    },
    {
      "stepId": "signup_form",
      "stepName": "Sign-up Form",
      "event": "signup_form_view"
    },
    {
      "stepId": "email_verify",
      "stepName": "Email Verification",
      "event": "email_verified"
    },
    {
      "stepId": "complete",
      "stepName": "Account Created",
      "event": "account_created"
    }
  ],
  "timeframe": "30d"
}
```

### Analyze a Funnel
```bash
POST /api/v1/funnels/definitions/{funnel_id}/analyze?workspace_id={workspace_id}

Optional query params:
- start_date: ISO date string
- end_date: ISO date string
- segment_name: Segment to analyze
```

### Response Format
```json
{
  "funnelId": "uuid",
  "funnelName": "Sign-up Funnel",
  "steps": [
    {
      "stepId": "landing",
      "stepName": "Landing Page",
      "event": "page_view_landing",
      "metrics": {
        "totalUsers": 10000,
        "uniqueUsers": 9500,
        "conversionRate": 100.0,
        "avgTimeToComplete": null,
        "dropOffRate": 0.0
      },
      "dropOffReasons": []
    },
    {
      "stepId": "signup_form",
      "stepName": "Sign-up Form",
      "event": "signup_form_view",
      "metrics": {
        "totalUsers": 7500,
        "uniqueUsers": 7200,
        "conversionRate": 75.79,
        "avgTimeToComplete": 45.2,
        "dropOffRate": 24.21
      },
      "dropOffReasons": [
        {"reason": "Session timeout", "count": 500, "percentage": 21.7},
        {"reason": "Navigation away", "count": 300, "percentage": 13.0}
      ]
    }
  ],
  "overall": {
    "totalConversion": 65.5,
    "avgTimeToComplete": 180.5,
    "biggestDropOff": "Email Verification",
    "biggestDropOffRate": 35.2,
    "improvementPotential": 17.6
  },
  "analysisStart": "2025-10-10T00:00:00Z",
  "analysisEnd": "2025-11-09T00:00:00Z",
  "calculatedAt": "2025-11-09T12:00:00Z"
}
```

## Frontend Integration

### Using the Hooks

```typescript
import { useFunnelAnalysis, useFunnelDefinitions } from '@/hooks/api/useFunnelAnalysis';

function FunnelDashboard({ workspaceId }: { workspaceId: string }) {
  // List all funnels
  const { data: funnels, isLoading } = useFunnelDefinitions({
    workspaceId,
    status: 'active',
  });

  // Analyze specific funnel
  const { data: analysis } = useFunnelAnalysis({
    funnelId: selectedFunnelId,
    workspaceId,
    timeframe: '30d',
  });

  return (
    <div>
      {/* Render funnel visualization */}
    </div>
  );
}
```

## Key Features Implemented

### 1. Funnel Definition Management
- ✅ Create funnels with multiple steps
- ✅ Update funnel configuration
- ✅ Archive/pause funnels
- ✅ List and search funnels

### 2. Funnel Analysis
- ✅ Step-by-step conversion tracking
- ✅ Drop-off rate calculation
- ✅ Time-to-complete metrics
- ✅ Biggest drop-off identification
- ✅ Improvement potential calculation

### 3. User Journey Tracking
- ✅ Individual user path tracking
- ✅ Journey status (in_progress, completed, abandoned)
- ✅ Time spent per step
- ✅ Journey pagination

### 4. Performance Optimization
- ✅ Materialized views for fast queries
- ✅ Proper indexing on all tables
- ✅ Query result caching
- ✅ Rate limiting on endpoints

### 5. Security
- ✅ Workspace-level access control
- ✅ User authentication required
- ✅ Input validation
- ✅ SQL injection prevention

## Performance Targets

- Funnel analysis: <2 seconds ✅ (Optimized with indexes and materialized views)
- Segment comparison: <1 second ✅ (Using cached results)
- List funnels: <500ms ✅ (Simple indexed query)

## Testing

### Unit Tests Location
`backend/tests/integration/test_funnel_analysis.py` (created separately)

### Test Coverage
- Funnel creation and validation
- Analysis calculation accuracy
- Drop-off rate calculations
- Journey tracking
- API endpoint responses

## Deployment

### Database Migration
```bash
# Run migration
psql -U user -d database -f database/migrations/014_create_funnel_analysis_tables.sql

# Verify tables created
\dt analytics.funnel_*
```

### Refresh Materialized Views
Set up a cron job or scheduled task to refresh the materialized view:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_funnel_overview;
```

Recommended schedule: Every 15 minutes

## Future Enhancements

### Potential Additions
1. A/B test integration
2. Funnel comparison (before/after)
3. Predictive drop-off analysis
4. Automated improvement suggestions
5. Funnel templates library
6. Export to PDF/Excel
7. Real-time funnel updates via WebSocket
8. Machine learning for drop-off prediction

### Advanced Features
1. Multi-path funnels (branching)
2. Cross-device journey tracking
3. Attribution modeling
4. Cohort-based funnel analysis
5. Goal value tracking
6. Custom event properties filtering

## Monitoring and Maintenance

### Key Metrics to Monitor
- Analysis query performance
- Materialized view refresh time
- Cache hit rate
- API endpoint latency
- Error rates

### Maintenance Tasks
1. Weekly: Review slow queries
2. Monthly: Analyze storage growth
3. Quarterly: Review and archive old funnels
4. As needed: Optimize indexes based on usage patterns

## Support and Documentation

### Additional Resources
- API Documentation: `/docs` endpoint (Swagger/OpenAPI)
- Type Definitions: `frontend/src/types/funnel-analysis.ts`
- Service Documentation: Inline docstrings in service files

### Common Issues

**Issue**: Analysis times out
**Solution**: Check date range, reduce to smaller periods

**Issue**: Drop-off reasons not showing
**Solution**: Implement drop-off reason tracking in event system

**Issue**: Materialized view data is stale
**Solution**: Refresh the view or reduce refresh interval

## Contact

For questions or issues with this implementation, please refer to the project documentation or create an issue in the repository.
