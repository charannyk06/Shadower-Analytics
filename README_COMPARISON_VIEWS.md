# Comparison Views Feature

## Overview

The Comparison Views feature provides comprehensive side-by-side analysis capabilities for agents, time periods, workspaces, and metrics. This enables users to identify differences, improvements, and optimization opportunities across different dimensions of their analytics data.

## Features

### 1. Agent Comparison
- **Multi-Agent Analysis**: Compare 2-10 agents simultaneously
- **Performance Metrics**: Success rate, runtime, throughput, error rate
- **Cost Analysis**: Cost per run, total cost, credit efficiency
- **Winner Determination**: Composite scoring to identify best performer
- **Recommendations**: AI-generated optimization suggestions
- **Visual Differences**: Highlighted performance gaps

### 2. Period Comparison
- **Period-over-Period**: Compare current vs. previous time periods
- **Change Tracking**: Automatic detection of improvements and regressions
- **Time Series**: Visual comparison of trends over time
- **Statistical Significance**: Identify meaningful changes
- **Summary Insights**: Natural language summary of changes

### 3. Workspace Comparison
- **Multi-Workspace**: Compare 2-20 workspaces
- **Benchmarking**: Compare against average performance
- **Rankings**: Automated ranking based on composite score
- **Strengths/Weaknesses**: Identify areas of excellence and improvement
- **Insights**: Anomaly detection and optimization opportunities

### 4. Metric Comparison
- **Deep Dive**: Analyze single metrics across entities
- **Statistical Analysis**: Mean, median, std dev, percentiles
- **Distribution**: Histogram and normality testing
- **Outlier Detection**: Z-score based outlier identification
- **Correlations**: Relationship analysis between metrics

## API Endpoints

### Agent Comparison
```
POST /api/v1/comparisons/agents
Query Parameters:
  - agent_ids: string[] (required, 2-10 agents)
  - start_date: datetime (optional)
  - end_date: datetime (optional)
  - include_recommendations: boolean (default: true)
  - include_visual_diff: boolean (default: true)
```

### Period Comparison
```
POST /api/v1/comparisons/periods
Query Parameters:
  - start_date: datetime (optional, defaults to 7 days ago)
  - end_date: datetime (optional, defaults to now)
  - include_time_series: boolean (default: true)
  - workspace_ids: string[] (optional)
  - agent_ids: string[] (optional)
```

### Workspace Comparison
```
POST /api/v1/comparisons/workspaces
Query Parameters:
  - workspace_ids: string[] (required, 2-20 workspaces)
  - start_date: datetime (optional)
  - end_date: datetime (optional)
  - include_statistics: boolean (default: true)
```

### Metric Comparison
```
POST /api/v1/comparisons/metrics
Query Parameters:
  - metric_name: string (required)
  - workspace_ids: string[] (optional)
  - agent_ids: string[] (optional)
  - start_date: datetime (optional)
  - end_date: datetime (optional)
  - include_correlations: boolean (default: false)
  - include_statistics: boolean (default: true)
```

### Health Check
```
GET /api/v1/comparisons/health
```

## Frontend Components

### ComparisonDashboard
Main dashboard with tab navigation for all comparison types.

```tsx
import { ComparisonDashboard } from '@/components/comparisons';

<ComparisonDashboard defaultType="agents" />
```

### Individual Comparison Views
- `AgentComparisonView`: Agent performance comparison
- `PeriodComparisonView`: Period-over-period analysis
- `WorkspaceComparisonView`: Workspace benchmarking
- `MetricComparisonView`: Metric deep dive

### API Hooks
```tsx
import {
  useAgentComparison,
  usePeriodComparison,
  useWorkspaceComparison,
  useMetricComparison,
} from '@/hooks/api/useComparisons';

// Example: Agent Comparison
const { data, isLoading, error } = useAgentComparison(
  ['agent-1', 'agent-2'],
  '2024-01-01',
  '2024-01-31'
);
```

## TypeScript Types

All types are defined in `/frontend/src/types/comparison-views.ts`:
- `ComparisonViews`: Main container type
- `AgentComparison`: Agent comparison results
- `PeriodComparison`: Period comparison results
- `WorkspaceComparison`: Workspace comparison results
- `MetricComparison`: Metric comparison results
- `ComparisonFilters`: Filter options
- `ComparisonOptions`: Display options

## Backend Models

Pydantic models in `/backend/src/models/comparison_views.py`:
- Mirror TypeScript types for API contracts
- Validation and serialization
- Database schema compatibility

## Service Layer

`ComparisonService` in `/backend/src/services/comparison_service.py`:
- Business logic for all comparison types
- Statistical calculations (NumPy, SciPy)
- Recommendation generation
- Performance optimization

## Performance Targets

- **Comparison Load**: < 1.5 seconds
- **Diff Calculation**: < 500ms
- **API Response**: < 1 second for typical requests

## Security

- **Cross-Workspace Access Control**: Enforced at API level
- **Data Privacy**: Workspace isolation
- **Rate Limiting**: Applied to expensive operations
- **Input Validation**: Pydantic models with strict validation

## Testing

### Backend Tests
- **Unit Tests**: `/backend/tests/unit/test_comparison_service.py`
  - Service logic validation
  - Statistical calculation verification
  - Edge case handling

- **Integration Tests**: `/backend/tests/integration/test_comparison_routes.py`
  - API endpoint validation
  - Request/response validation
  - Performance benchmarking

### Running Tests
```bash
# Backend tests
cd backend
pytest tests/unit/test_comparison_service.py -v
pytest tests/integration/test_comparison_routes.py -v

# All comparison tests
pytest tests/ -k "comparison" -v
```

## Usage Examples

### Example 1: Compare Three Agents
```typescript
const { data } = useAgentComparison(
  ['agent-alpha', 'agent-beta', 'agent-gamma'],
  '2024-01-01',
  '2024-01-31',
  true, // include recommendations
  true  // include visual diff
);

if (data?.data?.agentComparison) {
  console.log('Winner:', data.data.agentComparison.winner);
  console.log('Score:', data.data.agentComparison.winnerScore);
  console.log('Recommendations:', data.data.agentComparison.recommendations);
}
```

### Example 2: Period-over-Period Analysis
```typescript
const { data } = usePeriodComparison(
  '2024-01-01',
  '2024-01-31',
  true // include time series
);

if (data?.data?.periodComparison) {
  console.log('Improvements:', data.data.periodComparison.improvements);
  console.log('Regressions:', data.data.periodComparison.regressions);
}
```

### Example 3: Workspace Benchmarking
```typescript
const { data } = useWorkspaceComparison(
  ['ws-prod', 'ws-staging', 'ws-dev']
);

if (data?.data?.workspaceComparison) {
  const rankings = data.data.workspaceComparison.rankings.rankings;
  rankings.forEach((rank) => {
    console.log(`${rank.rank}. ${rank.workspaceName} - Score: ${rank.score}`);
  });
}
```

## Future Enhancements

1. **Export Functionality**: PDF and CSV report generation
2. **Scheduled Comparisons**: Automated periodic comparisons
3. **Alerts**: Threshold-based notifications for significant changes
4. **Custom Metrics**: User-defined comparison metrics
5. **Historical Tracking**: Trend analysis over multiple periods
6. **Advanced Visualizations**: Interactive charts and graphs
7. **Sharing**: Shareable comparison reports

## File Structure

```
frontend/
├── src/
│   ├── types/
│   │   └── comparison-views.ts
│   ├── components/
│   │   └── comparisons/
│   │       ├── ComparisonDashboard.tsx
│   │       ├── AgentComparisonView.tsx
│   │       ├── PeriodComparisonView.tsx
│   │       ├── WorkspaceComparisonView.tsx
│   │       ├── MetricComparisonView.tsx
│   │       └── index.ts
│   ├── hooks/
│   │   └── api/
│   │       └── useComparisons.ts
│   └── app/
│       └── comparisons/
│           └── page.tsx

backend/
├── src/
│   ├── models/
│   │   └── comparison_views.py
│   ├── services/
│   │   └── comparison_service.py
│   └── api/
│       └── routes/
│           └── comparisons.py
└── tests/
    ├── unit/
    │   └── test_comparison_service.py
    └── integration/
        └── test_comparison_routes.py
```

## Support

For issues or questions:
1. Check the API health endpoint: `GET /api/v1/comparisons/health`
2. Review logs for error details
3. Consult the test files for usage examples
4. Contact the development team

## License

Copyright © 2024 Shadower Analytics. All rights reserved.
