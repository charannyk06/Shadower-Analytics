# Specification: Moving Averages

## Feature Overview
Moving average calculations for smoothing trends and identifying patterns in time-series data.

## Technical Requirements
- Simple moving average (SMA)
- Exponential moving average (EMA)
- Weighted moving average (WMA)
- Trend identification

## Implementation Details

### Backend Implementation
```python
# backend/src/services/analytics/moving_averages.py
import pandas as pd
import numpy as np

class MovingAverageService:
    @staticmethod
    def calculate_sma(data: pd.Series, window: int) -> pd.Series:
        """Calculate simple moving average"""
        return data.rolling(window=window).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, span: int) -> pd.Series:
        """Calculate exponential moving average"""
        return data.ewm(span=span, adjust=False).mean()
    
    @staticmethod
    def calculate_wma(data: pd.Series, weights: List[float]) -> pd.Series:
        """Calculate weighted moving average"""
        def weighted_avg(values):
            return np.average(values, weights=weights[-len(values):])
        
        return data.rolling(window=len(weights)).apply(weighted_avg)
    
    async def get_metric_with_ma(
        self,
        workspace_id: str,
        metric: str,
        ma_type: str = 'sma',
        window: int = 7
    ):
        """Get metric with moving average"""
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as value
            FROM analytics.user_activity
            WHERE workspace_id = $1
                AND created_at >= NOW() - INTERVAL '90 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        
        data = await self.db.fetch_all(query, workspace_id)
        df = pd.DataFrame(data)
        
        if ma_type == 'sma':
            df['moving_average'] = self.calculate_sma(df['value'], window)
        elif ma_type == 'ema':
            df['moving_average'] = self.calculate_ema(df['value'], window)
        
        return df.to_dict('records')
```

## Testing Requirements
- Calculation accuracy tests
- Edge case handling
- Performance tests

## Performance Targets
- MA calculation: <100ms for 1000 points

## Security Considerations
- Data access control