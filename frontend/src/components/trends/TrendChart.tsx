/**
 * Trend Chart Component
 * Displays time series data with optional decomposition
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
  Scatter,
} from 'recharts';
import { TimeSeriesPoint, Decomposition, MetricType } from '@/hooks/api/useTrendAnalysis';

interface TrendChartProps {
  timeSeries: {
    data: TimeSeriesPoint[];
    statistics: any;
  };
  decomposition?: Decomposition;
  metric: MetricType;
}

export function TrendChart({ timeSeries, decomposition, metric }: TrendChartProps) {
  const chartData = useMemo(() => {
    return timeSeries.data.map((point, index) => {
      const date = new Date(point.timestamp);
      const formattedDate = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });

      const result: any = {
        timestamp: formattedDate,
        value: point.value,
        movingAverage: point.movingAverage,
        upperBound: point.upperBound,
        lowerBound: point.lowerBound,
      };

      // Add anomaly marker
      if (point.isAnomaly) {
        result.anomaly = point.value;
      }

      // Add decomposition data if available
      if (decomposition) {
        if (decomposition.trend[index]?.value !== null) {
          result.trendComponent = decomposition.trend[index]?.value;
        }
        if (decomposition.seasonal[index]?.value !== null) {
          result.seasonalComponent = decomposition.seasonal[index]?.value;
        }
      }

      return result;
    });
  }, [timeSeries.data, decomposition]);

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Legend />

          {/* Confidence interval */}
          <Line
            type="monotone"
            dataKey="upperBound"
            stroke="#e5e7eb"
            strokeDasharray="3 3"
            dot={false}
            name="Upper Bound"
            strokeWidth={1}
          />
          <Line
            type="monotone"
            dataKey="lowerBound"
            stroke="#e5e7eb"
            strokeDasharray="3 3"
            dot={false}
            name="Lower Bound"
            strokeWidth={1}
          />

          {/* Moving average */}
          <Line
            type="monotone"
            dataKey="movingAverage"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name="Moving Average"
          />

          {/* Actual values */}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#1f2937"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Actual Value"
          />

          {/* Anomalies */}
          <Scatter
            dataKey="anomaly"
            fill="#ef4444"
            shape="circle"
            name="Anomaly"
          />

          {/* Decomposition components (if enabled) */}
          {decomposition && (
            <>
              <Line
                type="monotone"
                dataKey="trendComponent"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Trend Component"
              />
              <Line
                type="monotone"
                dataKey="seasonalComponent"
                stroke="#f59e0b"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                name="Seasonal Component"
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
