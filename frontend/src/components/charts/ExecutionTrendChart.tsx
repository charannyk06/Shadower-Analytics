/**
 * ExecutionTrendChart Component
 * Line chart showing execution trends over time
 */

import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { TimeSeriesData, Timeframe } from '@/types/executive'

interface ExecutionTrendChartProps {
  data: TimeSeriesData[]
  timeframe: Timeframe
  showSuccess?: boolean
}

export function ExecutionTrendChart({
  data,
  timeframe,
  showSuccess = true,
}: ExecutionTrendChartProps) {
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
      <h3 className="text-lg font-semibold mb-4">Execution Trends</h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatXAxis}
            style={{ fontSize: 12 }}
          />
          <YAxis style={{ fontSize: 12 }} />
          <Tooltip
            labelFormatter={(value) => format(new Date(value), 'PPpp')}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Legend />

          <Line
            type="monotone"
            dataKey="total"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name="Total Executions"
          />

          {showSuccess && (
            <>
              <Line
                type="monotone"
                dataKey="successful"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Successful"
              />
              <Line
                type="monotone"
                dataKey="failed"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                name="Failed"
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
