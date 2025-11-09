/**
 * Trend Chart Component
 *
 * Displays time series data with moving average and anomalies
 * Note: This is a simplified version. In production, integrate with a charting library like Recharts or Chart.js
 */

import React from 'react';
import type { TimeSeries, Decomposition } from '@/types/trend-analysis';

interface TrendChartProps {
  timeSeries: TimeSeries;
  showDecomposition?: boolean;
  decomposition?: Decomposition;
  className?: string;
}

export function TrendChart({
  timeSeries,
  showDecomposition = false,
  decomposition,
  className = ''
}: TrendChartProps) {
  const { data, statistics } = timeSeries;

  if (!data || data.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">Time Series Trend</h3>
        <p className="text-gray-500 text-center py-8">No data available</p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Time Series Trend</h3>

      {/* Statistics Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs text-gray-500">Mean</div>
          <div className="text-sm font-semibold">{statistics.mean.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Median</div>
          <div className="text-sm font-semibold">{statistics.median.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Std Dev</div>
          <div className="text-sm font-semibold">{statistics.stdDev.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Autocorrelation</div>
          <div className="text-sm font-semibold">{statistics.autocorrelation.toFixed(3)}</div>
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
        <div className="text-center text-gray-500 py-8">
          <div className="text-lg font-semibold mb-2">📊 Chart Visualization</div>
          <p className="text-sm">
            Time series chart showing {data.length} data points
            {showDecomposition && ' with decomposition'}
          </p>
          <p className="text-xs mt-2">
            Integrate with Recharts, Chart.js, or similar library for full visualization
          </p>
        </div>

        {/* Data Summary */}
        <div className="mt-4 text-sm">
          <div className="flex justify-between mb-2">
            <span className="text-gray-600">Data Points:</span>
            <span className="font-semibold">{data.length}</span>
          </div>
          <div className="flex justify-between mb-2">
            <span className="text-gray-600">Anomalies Detected:</span>
            <span className="font-semibold text-red-600">
              {data.filter(d => d.isAnomaly).length}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Date Range:</span>
            <span className="font-semibold">
              {new Date(data[0].timestamp).toLocaleDateString()} -{' '}
              {new Date(data[data.length - 1].timestamp).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      {/* Decomposition Section */}
      {showDecomposition && decomposition && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h4 className="font-semibold mb-2">Decomposition Components</h4>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-gray-600">Trend</div>
              <div className="font-semibold">{decomposition.trend.length} points</div>
            </div>
            <div>
              <div className="text-gray-600">Seasonal</div>
              <div className="font-semibold">{decomposition.seasonal.length} points</div>
            </div>
            <div>
              <div className="text-gray-600">Noise Level</div>
              <div className="font-semibold">{decomposition.noise.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
