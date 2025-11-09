/**
 * ErrorRateChart Component
 * Line chart showing error rate trends
 */

import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { format } from 'date-fns'
import { TimeSeriesData, Timeframe } from '@/types/executive'

interface ErrorRateChartProps {
  data: TimeSeriesData[]
  timeframe: Timeframe
  threshold?: number
}

export function ErrorRateChart({
  data,
  timeframe,
  threshold = 5.0,
}: ErrorRateChartProps) {
  const formatXAxis = (timestamp: string) => {
    const date = new Date(timestamp)

    switch (timeframe) {
      case '24h':
        return format(date, 'HH:mm')
      case '7d':
        return format(date, 'EEE')
      case '30d':
      case '90d':
        return format(date, 'MMM d')
      default:
        return format(date, 'MMM d')
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Error Rate</h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatXAxis}
            style={{ fontSize: 12 }}
          />
          <YAxis
            label={{ value: 'Error Rate (%)', angle: -90, position: 'insideLeft' }}
            style={{ fontSize: 12 }}
          />
          <Tooltip
            labelFormatter={(value) => format(new Date(value), 'PPpp')}
            formatter={(value: number) => `${value.toFixed(2)}%`}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <ReferenceLine
            y={threshold}
            stroke="#ef4444"
            strokeDasharray="3 3"
            label={{ value: `Threshold: ${threshold}%`, position: 'right' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            name="Error Rate"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
