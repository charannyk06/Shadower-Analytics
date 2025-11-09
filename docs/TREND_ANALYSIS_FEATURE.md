# Trend Analysis Feature Documentation

## Overview

The Trend Analysis feature provides comprehensive time-series analysis, pattern detection, and forecasting capabilities for workspace metrics. It leverages advanced statistical methods and machine learning to generate actionable insights.

## Features

### 1. **Time-Series Decomposition**
- Breaks down metrics into trend, seasonal, and residual components
- Uses statsmodels seasonal decomposition
- Identifies underlying patterns and noise levels

### 2. **Seasonality Detection**
- Detects daily, weekly, monthly, quarterly, and yearly patterns
- Uses autocorrelation function (ACF) analysis
- Identifies peak and low periods
- Provides seasonality strength metrics (0-100%)

### 3. **Growth Pattern Analysis**
- Identifies linear vs exponential growth patterns
- Calculates growth rate and acceleration
- Projects 30-day growth trends
- Compares model fits (R-squared)

### 4. **Anomaly Detection**
- Identifies outliers using statistical methods
- Uses confidence intervals (±2 standard deviations)
- Highlights anomalous data points in visualizations

### 5. **Forecasting**
- Short-term forecasts (7 days) using Facebook Prophet
- Long-term forecasts (3 months, monthly aggregates)
- Confidence intervals (95% confidence level)
- Model accuracy metrics (MAPE, RMSE, R²)

### 6. **Pattern Recognition**
- Cycle detection using FFT (Fast Fourier Transform)
- Identifies recurring patterns beyond seasonality
- Measures cycle period, amplitude, and significance

### 7. **Period Comparisons**
- Period-over-period analysis
- Year-over-year comparisons (when sufficient data)
- Change percentage calculations

### 8. **Actionable Insights**
- AI-generated insights with impact levels (high/medium/low)
- Confidence scores for each insight
- Specific recommendations based on detected patterns

## Architecture

### Backend

#### Service Layer
- **File**: `backend/src/services/analytics/trend_analysis.py`
- **Class**: `TrendAnalysisService`
- **Key Dependencies**:
  - pandas: Data manipulation
  - numpy: Numerical computations
  - scipy: Statistical functions
  - statsmodels: Time-series analysis
  - scikit-learn: Linear regression
  - prophet: Forecasting (Facebook Prophet)

#### API Routes
- **File**: `backend/src/api/routes/trends.py`
- **Endpoints**:
  - `GET /api/v1/trends/{workspace_id}/{metric}` - Full trend analysis
  - `GET /api/v1/trends/{workspace_id}/overview` - All metrics overview
  - `GET /api/v1/trends/{workspace_id}/{metric}/forecast` - Forecast only
  - `GET /api/v1/trends/{workspace_id}/{metric}/patterns` - Pattern analysis
  - `GET /api/v1/trends/{workspace_id}/{metric}/insights` - Insights only
  - `DELETE /api/v1/trends/{workspace_id}/cache` - Clear cache

#### Database
- **Schema**: `analytics.trend_analysis_cache`
- **Purpose**: Cache computationally expensive analyses
- **Columns**:
  - `workspace_id`: Workspace identifier
  - `user_id`: User identifier (for security scoping)
  - `metric`: Metric name
  - `timeframe`: Analysis time window
  - `analysis_data`: JSONB containing full analysis
  - `expires_at`: Cache expiration timestamp
- **Cache Duration**:
  - 7d timeframe: 1 hour
  - 30d timeframe: 6 hours
  - 90d timeframe: 24 hours
  - 1y timeframe: 48 hours

### Frontend

#### Components
- **Location**: `frontend/src/components/trends/`
- **Main Component**: `TrendAnalysisDashboard.tsx`
- **Sub-components**:
  - `TrendOverviewCard.tsx` - Summary metrics and trend indicators
  - `TrendChart.tsx` - Main time-series visualization with anomaly detection
  - `SeasonalityChart.tsx` - Seasonal pattern visualization
  - `ForecastChart.tsx` - Forecast visualization with confidence intervals
  - `ComparisonChart.tsx` - Period comparison visualization
  - `TrendInsights.tsx` - Insight cards with recommendations
  - `MetricSelector.tsx` - Metric selection dropdown
  - `TimeframeSelector.tsx` - Timeframe selection dropdown

#### Hooks
- **File**: `frontend/src/hooks/api/useTrendAnalysis.ts`
- **Hooks**:
  - `useTrendAnalysis()` - Main trend analysis hook
  - `useTrendsOverview()` - All metrics overview
  - `useMetricForecast()` - Forecast only
  - `useMetricPatterns()` - Pattern analysis
  - `useMetricInsights()` - Insights only
  - `useClearTrendCache()` - Cache clearing mutation
  - `usePrefetchTrendAnalysis()` - Prefetch for performance

#### Page
- **Location**: `frontend/src/app/workspaces/[id]/trends/page.tsx`
- **Route**: `/workspaces/{id}/trends`

## Usage

### Backend Usage

```python
from services.analytics.trend_analysis import TrendAnalysisService
from core.database import get_db

async def analyze_workspace_trends():
    async with get_db() as db:
        service = TrendAnalysisService(db)

        analysis = await service.analyze_trend(
            workspace_id="workspace-uuid",
            metric="executions",
            timeframe="30d",
            user_id="user-uuid"
        )

        print(f"Trend: {analysis['overview']['trend']}")
        print(f"Change: {analysis['overview']['changePercentage']:.1f}%")
        print(f"Insights: {len(analysis['insights'])} generated")
```

### Frontend Usage

```typescript
import { TrendAnalysisDashboard } from '@/components/trends';

export default function TrendsPage() {
  return (
    <TrendAnalysisDashboard
      workspaceId="workspace-uuid"
      initialMetric="executions"
      initialTimeframe="30d"
    />
  );
}
```

### Using Individual Hooks

```typescript
import { useTrendAnalysis, useMetricForecast } from '@/hooks/api/useTrendAnalysis';

function MyComponent() {
  const { data, isLoading } = useTrendAnalysis({
    workspaceId: 'workspace-uuid',
    metric: 'executions',
    timeframe: '30d',
  });

  const { data: forecast } = useMetricForecast(
    'workspace-uuid',
    'executions',
    7 // 7-day forecast
  );

  // Use data...
}
```

## Supported Metrics

- `executions` - Agent execution count
- `users` - Unique user count
- `credits` - Credit consumption
- `errors` - Error count
- `success_rate` - Execution success rate percentage
- `revenue` - Revenue (if applicable)

## Supported Timeframes

- `7d` - 7 days
- `30d` - 30 days
- `90d` - 90 days
- `1y` - 1 year

## Security

### Authentication & Authorization
- All endpoints require authentication
- Workspace access validation using `WorkspaceAccess.validate_workspace_access()`
- User can only access workspaces they have permissions for

### Cache Security
- Cache entries are scoped by `user_id`
- Prevents information leakage between users in shared workspaces
- Cache invalidation on user logout (handled by frontend)

### Rate Limiting
- 10 requests per minute per user
- 100 requests per hour per user
- Protects against DoS attacks on expensive computations

### Request Timeouts
- Trend analysis: 30 seconds maximum
- Prophet forecasting: 30 seconds maximum
- FFT cycle detection: 10 seconds maximum
- Decomposition: 15 seconds maximum

## Performance

### Backend Performance Targets
- Trend calculation: <2 seconds
- Decomposition: <1 second
- Forecast generation: <3 seconds
- Pattern detection: <1 second
- Full analysis: <5 seconds

### Optimization Strategies
1. **Caching**: Results cached in database
2. **Async Operations**: Parallel execution of analysis steps using `asyncio.gather()`
3. **Timeouts**: Prevent long-running operations from blocking
4. **Error Handling**: Graceful degradation if individual analysis steps fail
5. **Data Sampling**: Limit data points for very large datasets

### Frontend Performance
- Query caching with React Query
- Stale-while-revalidate strategy
- Prefetching for improved UX
- Optimistic updates for cache clearing

## Error Handling

### Insufficient Data
- Minimum 14 data points required for analysis
- Returns friendly message: "Not enough data points for trend analysis"
- Graceful degradation with empty analysis structure

### Analysis Failures
- Individual analysis steps can fail without breaking entire analysis
- Fallback to empty results for failed steps
- Comprehensive error logging

### Prophet Unavailable
- Falls back to simple linear forecasting
- Ensures forecasting always works even if Prophet fails to install

## Testing

### Backend Tests
- **Location**: `backend/tests/integration/test_trend_analysis_routes.py`
- **Coverage**:
  - Authentication requirements
  - Input validation (metrics, timeframes)
  - Rate limiting
  - Cache operations

### Running Tests
```bash
# Backend tests
cd backend
pytest tests/integration/test_trend_analysis_routes.py -v

# All tests
pytest tests/ -v
```

## Monitoring & Logging

### Logged Events
- Analysis requests (workspace_id, metric, timeframe)
- Analysis failures with stack traces
- Cache hits/misses
- Timeout events
- Rate limit violations

### Metrics to Monitor
- Analysis request rate
- Average analysis duration
- Cache hit rate
- Timeout frequency
- Error rate by analysis step

## Future Enhancements

### Planned Features
1. **Multi-metric Correlation**
   - Cross-metric correlation analysis
   - Identify leading/lagging indicators
   - Correlation strength and significance

2. **External Benchmarks**
   - Industry average comparisons
   - Percentile rankings
   - Competitive analysis

3. **Custom Alerts**
   - Threshold-based alerts
   - Anomaly alerts
   - Trend change notifications

4. **Advanced Forecasting**
   - ARIMA models
   - LSTM neural networks
   - Ensemble methods

5. **What-If Analysis**
   - Scenario modeling
   - Impact simulation
   - Goal tracking

## Troubleshooting

### Common Issues

**Issue**: "Prophet not available" warning
- **Solution**: Install prophet: `pip install prophet`
- **Fallback**: System uses simple linear forecasting

**Issue**: Timeout errors
- **Solution**: Reduce timeframe or try again later
- **Root Cause**: Dataset too large or system under load

**Issue**: Empty forecasts
- **Solution**: Ensure at least 14 days of data
- **Root Cause**: Insufficient historical data

**Issue**: Cache not updating
- **Solution**: Use cache clear endpoint or wait for expiration
- **Troubleshooting**: Check `expires_at` in database

## Contributing

### Adding New Metrics
1. Add metric to `ALLOWED_METRICS` in `trend_analysis_constants.py`
2. Add SQL query to `_build_metric_query()` in trend_analysis.py
3. Update TypeScript types in `useTrendAnalysis.ts`
4. Update MetricSelector component options

### Adding New Analysis Methods
1. Add method to `TrendAnalysisService` class
2. Call method in `analyze_trend()` using `asyncio.gather()`
3. Add fallback in `_get_fallback_result()`
4. Update response types

## API Reference

See [API Documentation](./API.md) for detailed endpoint specifications.

## Support

For issues or questions:
- GitHub Issues: [Link to repo issues]
- Documentation: This file and inline code comments
- Contact: [Support contact]
