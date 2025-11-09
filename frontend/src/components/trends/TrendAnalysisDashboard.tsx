/**
 * Trend Analysis Dashboard Component
 *
 * Main dashboard for comprehensive trend analysis with decomposition, patterns, and forecasting
 */

'use client';

import React, { useState } from 'react';
import { useTrendAnalysis } from '@/hooks/api/useTrendAnalysis';
import { MetricSelector } from './MetricSelector';
import { TimeframeSelector } from './TimeframeSelector';
import { TrendOverview } from './TrendOverview';
import { TrendChart } from './TrendChart';
import { SeasonalityChart } from './SeasonalityChart';
import { ComparisonChart } from './ComparisonChart';
import { ForecastChart } from './ForecastChart';
import { TrendInsights } from './TrendInsights';
import type { TimeFrame, AvailableMetric } from '@/types/trend-analysis';

interface TrendAnalysisDashboardProps {
  workspaceId: string;
  initialMetric?: AvailableMetric;
  initialTimeframe?: TimeFrame;
  className?: string;
}

export function TrendAnalysisDashboard({
  workspaceId,
  initialMetric = 'executions',
  initialTimeframe = '30d',
  className = ''
}: TrendAnalysisDashboardProps) {
  const [metric, setMetric] = useState<AvailableMetric>(initialMetric);
  const [timeframe, setTimeframe] = useState<TimeFrame>(initialTimeframe);
  const [showDecomposition, setShowDecomposition] = useState(false);

  const { data, isLoading, error, isError } = useTrendAnalysis(
    workspaceId,
    metric,
    timeframe
  );

  // Loading State
  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (isError || error) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="text-2xl">⚠️</div>
            <div>
              <div className="font-semibold text-red-800">Error Loading Trend Analysis</div>
              <div className="text-sm text-red-600 mt-1">
                {error?.message || 'Failed to load trend analysis data'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Insufficient Data State
  if (data?.error === 'insufficient_data') {
    return (
      <div className={`space-y-6 ${className}`}>
        {/* Controls */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <MetricSelector value={metric} onChange={setMetric} />
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
          </div>
        </div>

        {/* Insufficient Data Message */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="text-2xl">📊</div>
            <div>
              <div className="font-semibold text-yellow-800">Insufficient Data</div>
              <div className="text-sm text-yellow-600 mt-1">
                {data?.message || 'Not enough data points for comprehensive trend analysis. At least 14 data points are required.'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success State with Data
  if (!data) {
    return null;
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex flex-col md:flex-row gap-4 flex-1">
            <MetricSelector
              value={metric}
              onChange={setMetric}
              availableMetrics={[
                'executions',
                'users',
                'credits',
                'errors',
                'success_rate'
              ]}
            />
          </div>

          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
            <button
              onClick={() => setShowDecomposition(!showDecomposition)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                showDecomposition
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
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

      {/* Insights */}
      <TrendInsights insights={data.insights} />
    </div>
  );
}
