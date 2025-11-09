# Specification: Trend Analysis

## Feature Overview
Advanced time-series analysis and trend detection for metrics, identifying patterns, seasonality, and providing insights for decision-making.

## Technical Requirements
- Time-series decomposition
- Seasonality detection
- Growth rate calculations
- Anomaly detection in trends
- Comparative period analysis
- Predictive trend forecasting

## Implementation Details

### Data Structure
```typescript
interface TrendAnalysis {
  workspaceId: string;
  metric: string;
  timeframe: TimeFrame;
  
  // Trend Overview
  overview: {
    currentValue: number;
    previousValue: number;
    change: number;
    changePercentage: number;
    trend: 'increasing' | 'decreasing' | 'stable' | 'volatile';
    trendStrength: number; // 0-100
    confidence: number; // statistical confidence
  };
  
  // Time Series Data
  timeSeries: {
    data: Array<{
      timestamp: string;
      value: number;
      movingAverage: number;
      upperBound: number; // confidence interval
      lowerBound: number;
      isAnomaly: boolean;
    }>;
    
    // Statistical Measures
    statistics: {
      mean: number;
      median: number;
      stdDev: number;
      variance: number;
      skewness: number;
      kurtosis: number;
      autocorrelation: number;
    };
  };
  
  // Decomposition
  decomposition: {
    trend: Array<{
      timestamp: string;
      value: number;
    }>;
    
    seasonal: Array<{
      timestamp: string;
      value: number;
      period: string; // 'daily', 'weekly', 'monthly'
    }>;
    
    residual: Array<{
      timestamp: string;
      value: number;
    }>;
    
    noise: number; // noise level percentage
  };
  
  // Patterns
  patterns: {
    // Seasonality
    seasonality: {
      detected: boolean;
      type: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
      strength: number; // 0-100
      peakPeriods: string[];
      lowPeriods: string[];
    };
    
    // Cycles
    cycles: Array<{
      period: number; // days
      amplitude: number;
      phase: number;
      significance: number;
    }>;
    
    // Growth Pattern
    growth: {
      type: 'linear' | 'exponential' | 'logarithmic' | 'polynomial';
      rate: number;
      acceleration: number;
      projectedGrowth: number;
    };
  };
  
  // Comparisons
  comparisons: {
    // Period over Period
    periodComparison: {
      currentPeriod: {
        start: string;
        end: string;
        value: number;
        avg: number;
      };
      previousPeriod: {
        start: string;
        end: string;
        value: number;
        avg: number;
      };
      change: number;
      changePercentage: number;
    };
    
    // Year over Year
    yearOverYear: {
      currentYear: number;
      previousYear: number;
      change: number;
      changePercentage: number;
      monthlyComparison: Array<{
        month: string;
        current: number;
        previous: number;
        change: number;
      }>;
    };
    
    // Benchmarks
    benchmarks: {
      industryAverage: number;
      topPerformers: number;
      position: 'above' | 'below' | 'at';
      percentile: number;
    };
  };
  
  // Correlations
  correlations: Array<{
    metric: string;
    correlation: number; // -1 to 1
    lag: number; // time lag in periods
    significance: number;
    relationship: 'positive' | 'negative' | 'none';
  }>;
  
  // Forecasting
  forecast: {
    // Short-term Forecast
    shortTerm: Array<{
      timestamp: string;
      predicted: number;
      upper: number; // confidence interval
      lower: number;
      confidence: number;
    }>;
    
    // Long-term Forecast
    longTerm: Array<{
      period: string;
      predicted: number;
      range: {
        optimistic: number;
        realistic: number;
        pessimistic: number;
      };
    }>;
    
    // Model Accuracy
    accuracy: {
      mape: number; // Mean Absolute Percentage Error
      rmse: number; // Root Mean Square Error
      r2: number; // R-squared
    };
  };
  
  // Insights
  insights: Array<{
    type: 'trend' | 'anomaly' | 'pattern' | 'correlation' | 'forecast';
    title: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    confidence: number;
    recommendation: string;
  }>;
}
```

### Frontend Components

#### Trend Analysis Dashboard
```typescript
// frontend/src/components/trends/TrendAnalysisDashboard.tsx
'use client';

import { useState } from 'react';
import { useTrendAnalysis } from '@/hooks/api/useTrendAnalysis';
import { TrendChart } from './TrendChart';
import { SeasonalityChart } from './SeasonalityChart';
import { ComparisonChart } from './ComparisonChart';
import { ForecastChart } from './ForecastChart';
import { TrendInsights } from './TrendInsights';
import { MetricSelector } from './MetricSelector';

interface TrendAnalysisDashboardProps {
  workspaceId: string;
  initialMetric?: string;
}

export function TrendAnalysisDashboard({ 
  workspaceId, 
  initialMetric = 'executions' 
}: TrendAnalysisDashboardProps) {
  const [metric, setMetric] = useState(initialMetric);
  const [timeframe, setTimeframe] = useState<TimeFrame>('90d');
  const [showDecomposition, setShowDecomposition] = useState(false);
  
  const { data, isLoading, error } = useTrendAnalysis(workspaceId, metric, timeframe);
  
  if (isLoading) return <TrendSkeleton />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center">
          <MetricSelector 
            value={metric} 
            onChange={setMetric}
            availableMetrics={[
              'executions', 'users', 'credits', 'errors', 
              'success_rate', 'revenue'
            ]}
          />
          
          <div className="flex gap-4">
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
            <button
              onClick={() => setShowDecomposition(!showDecomposition)}
              className={`px-4 py-2 rounded-lg ${
                showDecomposition 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              Decomposition
            </button>
          </div>
        </div>
      </div>
      
      {/* Trend Overview */}
      <TrendOverview overview={data.overview} />
      
      {/* Main Trend Chart */}
      <TrendChart 
        timeSeries={data.timeSeries}
        showDecomposition={showDecomposition}
        decomposition={data.decomposition}
      />
      
      {/* Pattern Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeasonalityChart patterns={data.patterns} />
        <ComparisonChart comparisons={data.comparisons} />
      </div>
      
      {/* Forecast */}
      <ForecastChart forecast={data.forecast} />
      
      {/* Correlations */}
      <CorrelationMatrix correlations={data.correlations} />
      
      {/* Insights */}
      <TrendInsights insights={data.insights} />
    </div>
  );
}
```

### Backend Implementation

#### Trend Analysis Service
```python
# backend/src/services/analytics/trend_analysis.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats, signal
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf
from sklearn.linear_model import LinearRegression
from prophet import Prophet

class TrendAnalysisService:
    def __init__(self, db, cache_service):
        self.db = db
        self.cache = cache_service
    
    async def analyze_trend(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Perform comprehensive trend analysis"""
        
        # Get time series data
        time_series = await self._get_time_series(workspace_id, metric, timeframe)
        
        if len(time_series) < 14:  # Need minimum data points
            return self._insufficient_data_response()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(time_series)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Parallel analysis
        results = await asyncio.gather(
            self._calculate_overview(df),
            self._perform_decomposition(df),
            self._detect_patterns(df),
            self._generate_comparisons(df),
            self._find_correlations(workspace_id, metric, df),
            self._generate_forecast(df),
            self._generate_insights(df)
        )
        
        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "overview": results[0],
            "timeSeries": self._prepare_time_series(df),
            "decomposition": results[1],
            "patterns": results[2],
            "comparisons": results[3],
            "correlations": results[4],
            "forecast": results[5],
            "insights": results[6]
        }
    
    async def _perform_decomposition(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual"""
        
        # Determine period for decomposition
        period = self._detect_period(df)
        
        # Perform decomposition
        decomposition = seasonal_decompose(
            df['value'], 
            model='additive', 
            period=period
        )
        
        return {
            "trend": [
                {
                    "timestamp": ts.isoformat(),
                    "value": float(val) if not pd.isna(val) else None
                }
                for ts, val in decomposition.trend.items()
            ],
            "seasonal": [
                {
                    "timestamp": ts.isoformat(),
                    "value": float(val) if not pd.isna(val) else None,
                    "period": self._get_period_name(period)
                }
                for ts, val in decomposition.seasonal.items()
            ],
            "residual": [
                {
                    "timestamp": ts.isoformat(),
                    "value": float(val) if not pd.isna(val) else None
                }
                for ts, val in decomposition.resid.items()
            ],
            "noise": float(np.std(decomposition.resid.dropna()) / np.std(df['value']) * 100)
        }
    
    async def _detect_patterns(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Detect patterns in time series"""
        
        # Seasonality detection
        seasonality = self._detect_seasonality(df)
        
        # Growth pattern detection
        growth = self._detect_growth_pattern(df)
        
        # Cycle detection
        cycles = self._detect_cycles(df)
        
        return {
            "seasonality": seasonality,
            "growth": growth,
            "cycles": cycles
        }
    
    def _detect_seasonality(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Detect seasonality in data"""
        
        # Use autocorrelation to detect seasonality
        acf_values = acf(df['value'], nlags=min(40, len(df)//2))
        
        # Find peaks in ACF
        peaks, properties = signal.find_peaks(acf_values[1:], height=0.3)
        
        if len(peaks) > 0:
            # Strongest seasonal period
            strongest_peak = peaks[np.argmax(properties['peak_heights'])]
            period = strongest_peak + 1
            
            # Determine seasonality type
            if period <= 1:
                season_type = 'daily'
            elif period <= 7:
                season_type = 'weekly'
            elif period <= 31:
                season_type = 'monthly'
            elif period <= 92:
                season_type = 'quarterly'
            else:
                season_type = 'yearly'
            
            # Find peak and low periods
            seasonal_avg = df.groupby(df.index.dayofweek)['value'].mean()
            peak_periods = seasonal_avg.nlargest(2).index.tolist()
            low_periods = seasonal_avg.nsmallest(2).index.tolist()
            
            return {
                "detected": True,
                "type": season_type,
                "strength": float(properties['peak_heights'][np.argmax(properties['peak_heights'])] * 100),
                "peakPeriods": [self._day_name(d) for d in peak_periods],
                "lowPeriods": [self._day_name(d) for d in low_periods]
            }
        
        return {
            "detected": False,
            "type": None,
            "strength": 0,
            "peakPeriods": [],
            "lowPeriods": []
        }
    
    async def _generate_forecast(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate time series forecast"""
        
        # Prepare data for Prophet
        prophet_df = df.reset_index()
        prophet_df.columns = ['ds', 'y']
        
        # Initialize and fit model
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False
        )
        model.fit(prophet_df)
        
        # Generate forecast
        future = model.make_future_dataframe(periods=30, freq='D')
        forecast = model.predict(future)
        
        # Extract short-term forecast (next 7 days)
        short_term = forecast[forecast['ds'] > prophet_df['ds'].max()].head(7)
        
        # Extract long-term forecast (next 3 months)
        long_term_monthly = forecast[forecast['ds'] > prophet_df['ds'].max()].resample('M', on='ds').agg({
            'yhat': 'mean',
            'yhat_lower': 'mean',
            'yhat_upper': 'mean'
        })
        
        # Calculate accuracy metrics on historical data
        historical_forecast = forecast[forecast['ds'] <= prophet_df['ds'].max()]
        actual = prophet_df['y'].values
        predicted = historical_forecast['yhat'].values[:len(actual)]
        
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        r2 = 1 - (np.sum((actual - predicted) ** 2) / np.sum((actual - np.mean(actual)) ** 2))
        
        return {
            "shortTerm": [
                {
                    "timestamp": row['ds'].isoformat(),
                    "predicted": float(row['yhat']),
                    "upper": float(row['yhat_upper']),
                    "lower": float(row['yhat_lower']),
                    "confidence": 0.95
                }
                for _, row in short_term.iterrows()
            ],
            "longTerm": [
                {
                    "period": period.strftime('%Y-%m'),
                    "predicted": float(row['yhat']),
                    "range": {
                        "optimistic": float(row['yhat_upper']),
                        "realistic": float(row['yhat']),
                        "pessimistic": float(row['yhat_lower'])
                    }
                }
                for period, row in long_term_monthly.iterrows()
            ],
            "accuracy": {
                "mape": float(mape),
                "rmse": float(rmse),
                "r2": float(r2)
            }
        }
```

### Database Schema
```sql
-- Trend analysis cache table
CREATE TABLE analytics.trend_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    metric VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    
    -- Analysis results
    analysis_data JSONB NOT NULL,
    
    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_trend_analysis UNIQUE(workspace_id, metric, timeframe)
);

-- Indexes
CREATE INDEX idx_trend_analysis_workspace 
    ON analytics.trend_analysis_cache(workspace_id, metric);
```

## Testing Requirements
- Time series decomposition accuracy tests
- Seasonality detection tests
- Forecast accuracy validation
- Pattern detection tests
- Performance tests with large datasets

## Performance Targets
- Trend calculation: <2 seconds
- Decomposition: <1 second
- Forecast generation: <3 seconds
- Pattern detection: <1 second
- Full analysis: <5 seconds

## Security Considerations
- Data aggregation privacy
- Forecast access restrictions
- Cache invalidation on data updates