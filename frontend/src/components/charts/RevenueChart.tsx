/**
 * RevenueChart Component
 * Bar/Area chart showing revenue trends
 */

import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { TimeSeriesData, Timeframe } from '@/types/executive'

interface RevenueChartProps {
  data: TimeSeriesData[]
  timeframe: Timeframe
}

export function RevenueChart({ data, timeframe }: RevenueChartProps) {
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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Revenue Trends</h3>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatXAxis}
            style={{ fontSize: 12 }}
          />
          <YAxis
            tickFormatter={formatCurrency}
            style={{ fontSize: 12 }}
          />
          <Tooltip
            labelFormatter={(value) => format(new Date(value), 'PPpp')}
            formatter={(value: number) => formatCurrency(value)}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Bar
            dataKey="value"
            fill="#10b981"
            radius={[4, 4, 0, 0]}
            name="Revenue"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
