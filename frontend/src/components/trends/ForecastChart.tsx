/**
 * Forecast Chart Component
 */

'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import { Forecast, TimeSeriesPoint } from '@/hooks/api/useTrendAnalysis';

interface ForecastChartProps {
  forecast: Forecast;
  historical: TimeSeriesPoint[];
}

export function ForecastChart({ forecast, historical }: ForecastChartProps) {
  const chartData = useMemo(() => {
    // Combine historical and forecast data
    const historicalData = historical.map((point) => ({
      timestamp: new Date(point.timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      actual: point.value,
      type: 'historical',
    }));

    const forecastData = forecast.shortTerm.map((point) => ({
      timestamp: new Date(point.timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      predicted: point.predicted,
      upper: point.upper,
      lower: point.lower,
      type: 'forecast',
    }));

    return [...historicalData, ...forecastData];
  }, [historical, forecast.shortTerm]);

  return (
    <div className="space-y-4">
      {/* Accuracy Metrics */}
      {forecast.accuracy && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">MAPE</div>
            <div className="text-sm font-semibold text-gray-900">
              {forecast.accuracy.mape.toFixed(2)}%
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">RMSE</div>
            <div className="text-sm font-semibold text-gray-900">
              {forecast.accuracy.rmse.toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-xs font-medium text-gray-600 mb-1">R²</div>
            <div className="text-sm font-semibold text-gray-900">
              {forecast.accuracy.r2.toFixed(3)}
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} stroke="#6b7280" />
            <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Legend />

            {/* Confidence interval area */}
            <Area
              type="monotone"
              dataKey="upper"
              fill="#93c5fd"
              stroke="none"
              fillOpacity={0.3}
              name="Upper Bound"
            />
            <Area
              type="monotone"
              dataKey="lower"
              fill="#93c5fd"
              stroke="none"
              fillOpacity={0.3}
              name="Lower Bound"
            />

            {/* Historical actual values */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#1f2937"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Historical"
            />

            {/* Forecast */}
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 4, fill: '#3b82f6' }}
              name="Forecast"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
