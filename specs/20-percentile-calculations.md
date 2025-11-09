# Specification: Percentile Calculations

## Feature Overview
Statistical percentile calculations for performance metrics to understand distribution and outliers.

## Technical Requirements
- P50, P75, P90, P95, P99 calculations
- Distribution analysis
- Outlier detection
- Percentile trends

## Implementation Details

### Backend Implementation
```python
# backend/src/services/analytics/percentiles.py
import numpy as np
from typing import List, Dict

class PercentileCalculator:
    @staticmethod
    async def calculate_percentiles(
        values: List[float],
        percentiles: List[int] = [50, 75, 90, 95, 99]
    ) -> Dict[str, float]:
        """Calculate percentiles for given values"""
        if not values:
            return {f"p{p}": 0 for p in percentiles}
        
        results = {}
        for p in percentiles:
            results[f"p{p}"] = float(np.percentile(values, p))
        
        # Add distribution metrics
        results['mean'] = float(np.mean(values))
        results['median'] = float(np.median(values))
        results['std_dev'] = float(np.std(values))
        results['min'] = float(np.min(values))
        results['max'] = float(np.max(values))
        
        return results
    
    async def calculate_runtime_percentiles(
        self,
        workspace_id: str,
        timeframe: str
    ):
        query = """
            SELECT 
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99,
                AVG(runtime_seconds) as mean,
                STDDEV(runtime_seconds) as std_dev
            FROM public.agent_runs
            WHERE workspace_id = $1
                AND started_at >= NOW() - INTERVAL $2
        """
        
        return await self.db.fetch_one(query, workspace_id, timeframe)
```

## Testing Requirements
- Percentile accuracy tests
- Edge case handling
- Performance with large datasets

## Performance Targets
- Calculation time: <500ms for 100k values
- Database percentiles: <200ms

## Security Considerations
- Data access restrictions