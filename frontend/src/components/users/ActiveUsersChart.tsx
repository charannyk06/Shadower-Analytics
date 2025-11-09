/**
 * ActiveUsersChart Component
 * Line chart showing DAU/WAU/MAU trends over time
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
import type { ActivityByDate, TimeFrame } from '@/types/user-activity'

interface ActiveUsersChartProps {
  data: ActivityByDate[]
  timeframe: TimeFrame
}

export function ActiveUsersChart({ data, timeframe }: ActiveUsersChartProps) {
  const formatXAxis = (date: string) => {
    const dateObj = new Date(date)

    switch (timeframe) {
      case '7d':
        return format(dateObj, 'EEE')
      case '30d':
        return format(dateObj, 'MMM d')
      case '90d':
      case '1y':
        return format(dateObj, 'MMM d')
      default:
        return format(dateObj, 'MMM d')
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h3 className="text-lg font-semibold mb-4">Active Users Trend</h3>

      {data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No activity data available for the selected period
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tickFormatter={formatXAxis}
              style={{ fontSize: 12 }}
            />
            <YAxis style={{ fontSize: 12 }} />
            <Tooltip
              labelFormatter={(value) => format(new Date(value as string), 'PPP')}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="activeUsers"
              stroke="#8b5cf6"
              strokeWidth={2}
              name="Active Users"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="sessions"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Sessions"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="events"
              stroke="#10b981"
              strokeWidth={2}
              name="Events"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
