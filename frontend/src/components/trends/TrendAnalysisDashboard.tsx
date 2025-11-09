/**
 * Trend Analysis Dashboard Component
 */

'use client';

import { useState } from 'react';
import {
  useTrendAnalysis,
  MetricType,
  TimeFrame,
} from '@/hooks/api/useTrendAnalysis';
import { TrendOverviewCard } from './TrendOverviewCard';
import { TrendChart } from './TrendChart';
import { SeasonalityChart } from './SeasonalityChart';
import { ForecastChart } from './ForecastChart';
import { TrendInsights } from './TrendInsights';
import { MetricSelector } from './MetricSelector';
import { TimeframeSelector } from './TimeframeSelector';
import { LoadingState } from './LoadingState';
import { ErrorState } from './ErrorState';

interface TrendAnalysisDashboardProps {
  workspaceId: string;
  initialMetric?: MetricType;
  initialTimeframe?: TimeFrame;
}

export function TrendAnalysisDashboard({
  workspaceId,
  initialMetric = 'executions',
  initialTimeframe = '30d',
}: TrendAnalysisDashboardProps) {
  const [metric, setMetric] = useState<MetricType>(initialMetric);
  const [timeframe, setTimeframe] = useState<TimeFrame>(initialTimeframe);
  const [showDecomposition, setShowDecomposition] = useState(false);

  const { data, isLoading, error, refetch } = useTrendAnalysis({
    workspaceId,
    metric,
    timeframe,
  });

  if (isLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={refetch} />;
  }

  if (!data || data.error) {
    return (
      <div className="p-8 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h3 className="text-lg font-semibold text-yellow-900 mb-2">
          Insufficient Data
        </h3>
        <p className="text-yellow-700">
          {data?.message || 'Not enough data points for comprehensive analysis. Please check back later.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-1">
              Trend Analysis
            </h2>
            <p className="text-sm text-gray-600">
              Comprehensive time-series analysis and forecasting
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <MetricSelector value={metric} onChange={setMetric} />
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />

            <button
              onClick={() => setShowDecomposition(!showDecomposition)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                showDecomposition
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {showDecomposition ? 'Hide' : 'Show'} Decomposition
            </button>
          </div>
        </div>
      </div>

      {/* Overview Card */}
      <TrendOverviewCard overview={data.overview} metric={metric} />

      {/* Main Trend Chart */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Time Series Analysis
        </h3>
        <TrendChart
          timeSeries={data.timeSeries}
          decomposition={showDecomposition ? data.decomposition : undefined}
          metric={metric}
        />
      </div>

      {/* Pattern Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Seasonality */}
        {data.patterns.seasonality.detected && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Seasonality Analysis
            </h3>
            <SeasonalityChart patterns={data.patterns} />
          </div>
        )}

        {/* Growth Pattern */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Growth Pattern
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-600">Type:</span>
              <span className="text-sm font-semibold text-gray-900 capitalize">
                {data.patterns.growth.type}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-600">Rate:</span>
              <span className="text-sm font-semibold text-gray-900">
                {data.patterns.growth.rate.toFixed(2)} / day
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-600">
                30-day Projection:
              </span>
              <span className="text-sm font-semibold text-gray-900">
                {data.patterns.growth.projectedGrowth > 0 ? '+' : ''}
                {data.patterns.growth.projectedGrowth.toFixed(0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Forecast */}
      {data.forecast.shortTerm.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            7-Day Forecast
          </h3>
          <ForecastChart
            forecast={data.forecast}
            historical={data.timeSeries.data.slice(-14)}
          />
        </div>
      )}

      {/* Insights */}
      {data.insights.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Key Insights & Recommendations
          </h3>
          <TrendInsights insights={data.insights} />
        </div>
      )}

      {/* Statistics */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Statistical Summary
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">Mean</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.timeSeries.statistics.mean.toFixed(2)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">Median</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.timeSeries.statistics.median.toFixed(2)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">Std Dev</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.timeSeries.statistics.stdDev.toFixed(2)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">Autocorr</div>
            <div className="text-lg font-semibold text-gray-900">
              {data.timeSeries.statistics.autocorrelation.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
