# Agent Analytics Feature - Implementation Documentation

## Overview

Comprehensive analytics dashboard for individual AI agents, providing deep insights into performance, costs, errors, user satisfaction, and optimization opportunities.

## Features Implemented

### 1. **Performance Metrics**
- ✅ Total runs, success rate, availability tracking
- ✅ Runtime statistics (min, max, avg, median, percentiles)
- ✅ Throughput metrics (runs per hour/day, concurrency)
- ✅ Execution breakdown (successful, failed, cancelled)

### 2. **Runtime Distribution**
- ✅ Percentile visualization (P50, P75, P90, P95, P99)
- ✅ Interactive bar charts with Recharts
- ✅ Statistical summary (average, median, std deviation)

### 3. **Error Analysis**
- ✅ Error rate tracking and categorization
- ✅ Error patterns with suggested fixes
- ✅ Recovery metrics (MTTR, auto-recovery rate)
- ✅ Top error types with severity levels
- ✅ Error impact analysis

### 4. **User Satisfaction**
- ✅ User ratings and feedback display
- ✅ Rating distribution visualization
- ✅ Top users by activity
- ✅ Usage patterns (by hour, by day of week)
- ✅ Average interactions per user

### 5. **Cost Analysis**
- ✅ Total cost and cost per run
- ✅ Token usage tracking
- ✅ Model usage breakdown with pie charts
- ✅ Detailed cost breakdown table
- ✅ Cost efficiency metrics

### 6. **Comparative Analysis**
- ✅ Comparison vs workspace average
- ✅ Overall ranking and percentile
- ✅ Previous period comparison
- ✅ Trend indicators and insights

### 7. **Optimization Suggestions**
- ✅ AI-generated recommendations
- ✅ Categorized by type (performance, cost, reliability)
- ✅ Effort estimation (low, medium, high)
- ✅ Impact estimation
- ✅ Suggested fixes for common issues

## Technical Implementation

### Backend (Python/FastAPI)

#### Database Schema
```sql
-- Key tables created:
- analytics.agent_runs              # Individual execution records
- analytics.agent_errors            # Detailed error tracking
- analytics.agent_performance_hourly # Hourly aggregations
- analytics.agent_optimization_suggestions
- analytics.agent_user_feedback
- analytics.agent_model_usage
- analytics.agent_analytics_summary (materialized view)
```

#### Services
- `AgentAnalyticsService` - Main analytics aggregation service
  - Performance metrics calculation
  - Error pattern analysis
  - User metrics aggregation
  - Comparison calculations
  - Optimization suggestion generation
  - Time series data generation

#### API Endpoints
```
GET /api/v1/agents/{agent_id}/analytics
  Query params:
    - workspace_id: string (required)
    - timeframe: '24h' | '7d' | '30d' | '90d' | 'all'
    - skip_cache: boolean
```

### Frontend (Next.js/React)

#### Type Definitions
- `AgentAnalytics` - Complete analytics response
- `PerformanceMetrics`, `RuntimeMetrics`, `ThroughputMetrics`
- `ResourceUsage`, `ErrorAnalysis`, `UserMetrics`
- `ComparisonMetrics`, `OptimizationSuggestion`
- `TrendData`, `TimeSeriesDataPoint`

#### Components Created
```
/frontend/src/components/agents/
  ├── AgentHeader.tsx              # Header with export/share actions
  ├── PerformanceMetrics.tsx       # Performance overview cards
  ├── RuntimeDistribution.tsx      # Runtime percentile chart
  ├── ErrorAnalysis.tsx            # Error patterns and analysis
  ├── UserSatisfaction.tsx         # User ratings and feedback
  ├── CostAnalysis.tsx             # Cost breakdown and charts
  ├── AgentComparison.tsx          # Comparative metrics
  └── OptimizationSuggestions.tsx  # AI recommendations

/frontend/src/components/common/
  └── TimeframeSelector.tsx        # Time range selector

/frontend/src/app/agents/[id]/
  └── page.tsx                     # Main dashboard page
```

#### Custom Hooks
- `useAgentAnalytics` - Fetch analytics with React Query
- `useAgent` - Simplified analytics fetch
- `usePrefetchAgentAnalytics` - Performance optimization

## File Structure

```
Shadower-Analytics/
├── backend/
│   ├── src/
│   │   ├── api/routes/
│   │   │   └── agents.py                          # API routes
│   │   ├── models/schemas/
│   │   │   └── agent_analytics.py                 # Pydantic schemas
│   │   └── services/analytics/
│   │       └── agent_analytics_service.py         # Business logic
│   └── database/
│       └── migrations/
│           └── 009_create_agent_analytics_tables.sql
│
└── frontend/
    └── src/
        ├── types/
        │   └── agent-analytics.ts                 # TypeScript types
        ├── hooks/api/
        │   └── useAgentAnalytics.ts               # Data fetching hooks
        ├── components/
        │   ├── agents/                            # Agent-specific components
        │   └── common/                            # Shared components
        └── app/agents/[id]/
            └── page.tsx                           # Main dashboard page
```

## Usage

### Accessing the Dashboard

1. **Via URL:**
   ```
   http://localhost:3000/agents/{agent-id}?workspace_id={workspace-id}
   ```

2. **Timeframe Selection:**
   - Last 24 Hours
   - Last 7 Days (default)
   - Last 30 Days
   - Last 90 Days
   - All Time

3. **Actions Available:**
   - Export analytics data (JSON)
   - Share dashboard link
   - Refresh data
   - View optimization suggestions

### Example API Usage

```bash
# Get agent analytics
curl -X GET "http://localhost:8000/api/v1/agents/{agent_id}/analytics?workspace_id={workspace_id}&timeframe=7d" \
  -H "Authorization: Bearer {token}"
```

### Example Response Structure

```json
{
  "agentId": "550e8400-e29b-41d4-a716-446655440000",
  "workspaceId": "660e8400-e29b-41d4-a716-446655440000",
  "timeframe": "7d",
  "generatedAt": "2025-11-09T10:00:00Z",
  "performance": {
    "totalRuns": 1250,
    "successRate": 94.4,
    "runtime": { ... },
    "throughput": { ... }
  },
  "resources": { ... },
  "errors": { ... },
  "userMetrics": { ... },
  "comparison": { ... },
  "optimizations": [ ... ],
  "trends": { ... }
}
```

## Database Setup

### Run Migration

```bash
# Apply the migration
psql -U postgres -d shadower_analytics -f database/migrations/009_create_agent_analytics_tables.sql

# Generate sample data (for testing)
SELECT analytics.generate_sample_agent_runs(
  '550e8400-e29b-41d4-a716-446655440000'::uuid,  -- agent_id
  '660e8400-e29b-41d4-a716-446655440000'::uuid,  -- workspace_id
  30,  -- days_back
  50   -- runs_per_day
);

# Refresh materialized view
SELECT analytics.refresh_agent_analytics_summary();
```

## Performance Considerations

### Backend Optimizations
1. **Materialized Views**: Pre-aggregated daily summaries
2. **Indexes**: BRIN indexes for time-series data
3. **Parallel Queries**: Uses `asyncio.gather` for concurrent fetching
4. **Caching**: 1-minute stale time in React Query

### Frontend Optimizations
1. **Code Splitting**: Next.js automatic route-based splitting
2. **Lazy Loading**: Charts loaded on demand
3. **Memoization**: React Query caches API responses
4. **Skeleton Loading**: Smooth loading experience

## Security

1. **Authentication**: JWT token validation (commented out in current implementation)
2. **Workspace Access Control**: Validates user has access to workspace
3. **PII Filtering**: Error messages truncated to 200 characters
4. **Rate Limiting**: Can be added via FastAPI middleware

## Testing

### Unit Tests Needed
- [ ] Performance metrics calculation
- [ ] Percentile calculations accuracy
- [ ] Error pattern analysis
- [ ] Optimization suggestion generation

### Integration Tests Needed
- [ ] API endpoint responses
- [ ] Database queries performance
- [ ] Frontend component rendering
- [ ] End-to-end user flows

### Load Tests Needed
- [ ] Large dataset queries (>10M records)
- [ ] Concurrent user access
- [ ] Materialized view refresh performance

## Future Enhancements

### Planned Features
1. **Real-time Updates**: WebSocket integration for live metrics
2. **Custom Dashboards**: User-configurable widget layouts
3. **Alerts**: Threshold-based notifications
4. **Export Options**: CSV, PDF reports
5. **Comparison Mode**: Side-by-side agent comparison
6. **Historical Analysis**: Long-term trend analysis
7. **ML Predictions**: Predictive analytics for performance
8. **Cost Forecasting**: Budget and cost predictions

### Technical Improvements
1. **Query Optimization**: Additional indexes and query tuning
2. **Caching Strategy**: Redis integration for faster responses
3. **Data Archival**: Automated old data archiving
4. **Monitoring**: Performance metrics and error tracking

## Troubleshooting

### Common Issues

**1. No data appearing in dashboard**
- Check if agent_runs table has data
- Verify workspace_id matches
- Refresh materialized view

**2. Slow query performance**
- Run ANALYZE on tables
- Check if indexes are being used
- Consider refreshing materialized views

**3. Frontend build errors**
- Verify all dependencies installed: `npm install`
- Check TypeScript types match API responses
- Clear Next.js cache: `rm -rf .next`

**4. API 500 errors**
- Check database connection
- Verify migration applied
- Review backend logs for stack traces

## Dependencies

### Backend
- FastAPI 0.104+
- SQLAlchemy 2.0+
- asyncpg
- pydantic

### Frontend
- Next.js 14+
- React 18+
- React Query 5+
- Recharts 2.10+
- Tailwind CSS 3.4+

## Contributing

When adding new metrics or features:
1. Update database schema with migration
2. Add Pydantic schemas for validation
3. Implement service layer logic
4. Create/update API endpoints
5. Add TypeScript types
6. Build UI components
7. Update this documentation

## License

Part of Shadower Analytics Platform
