/**
 * UserActivityChart Component
 * Area chart showing user activity over time
 */

import React from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { TimeSeriesData, Timeframe } from '@/types/executive'

interface UserActivityChartProps {
  data: TimeSeriesData[]
  timeframe: Timeframe
}

export function UserActivityChart({ data, timeframe }: UserActivityChartProps) {
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
      <h3 className="text-lg font-semibold mb-4">User Activity</h3>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
            </linearGradient>
          </defs>
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
          <Area
            type="monotone"
            dataKey="value"
            stroke="#8b5cf6"
            fillOpacity={1}
            fill="url(#colorUsers)"
            name="Active Users"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
