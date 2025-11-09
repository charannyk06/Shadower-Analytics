/**
 * Seasonality Chart Component
 */

'use client';

import { Patterns } from '@/hooks/api/useTrendAnalysis';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface SeasonalityChartProps {
  patterns: Patterns;
}

export function SeasonalityChart({ patterns }: SeasonalityChartProps) {
  const { seasonality } = patterns;

  if (!seasonality.detected) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No significant seasonality detected
      </div>
    );
  }

  // Create chart data for peak and low periods
  const chartData = [
    ...seasonality.peakPeriods.map((period) => ({
      period,
      type: 'Peak',
      value: seasonality.strength * 0.8, // Approximate relative value
    })),
    ...seasonality.lowPeriods.map((period) => ({
      period,
      type: 'Low',
      value: seasonality.strength * 0.3, // Approximate relative value
    })),
  ];

  return (
    <div className="space-y-4">
      {/* Seasonality Info */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-3 rounded-lg">
          <div className="text-xs font-medium text-blue-600 mb-1">Type</div>
          <div className="text-sm font-semibold text-blue-900 capitalize">
            {seasonality.type}
          </div>
        </div>
        <div className="bg-blue-50 p-3 rounded-lg">
          <div className="text-xs font-medium text-blue-600 mb-1">Strength</div>
          <div className="text-sm font-semibold text-blue-900">
            {seasonality.strength.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Peak and Low Periods */}
      <div className="space-y-2">
        <div>
          <div className="text-xs font-medium text-gray-600 mb-1">Peak Periods:</div>
          <div className="flex flex-wrap gap-2">
            {seasonality.peakPeriods.map((period) => (
              <span
                key={period}
                className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded"
              >
                {period}
              </span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-600 mb-1">Low Periods:</div>
          <div className="flex flex-wrap gap-2">
            {seasonality.lowPeriods.map((period) => (
              <span
                key={period}
                className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded"
              >
                {period}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Simple visualization */}
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar
              dataKey="value"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
