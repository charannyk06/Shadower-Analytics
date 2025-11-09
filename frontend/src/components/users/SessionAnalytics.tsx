/**
 * SessionAnalytics Component
 * Displays session metrics and distributions
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
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import type { SessionAnalytics as SessionAnalyticsType } from '@/types/user-activity'

interface SessionAnalyticsProps {
  data: SessionAnalyticsType
}

const DEVICE_COLORS = {
  desktop: '#8b5cf6',
  mobile: '#3b82f6',
  tablet: '#10b981',
}

export function SessionAnalytics({ data }: SessionAnalyticsProps) {
  const sessionLengthData = [
    { name: '0-30s', value: data.sessionLengthDistribution['0-30s'] },
    { name: '30s-2m', value: data.sessionLengthDistribution['30s-2m'] },
    { name: '2m-5m', value: data.sessionLengthDistribution['2m-5m'] },
    { name: '5m-15m', value: data.sessionLengthDistribution['5m-15m'] },
    { name: '15m-30m', value: data.sessionLengthDistribution['15m-30m'] },
    { name: '30m+', value: data.sessionLengthDistribution['30m+'] },
  ]

  const deviceData = [
    { name: 'Desktop', value: data.deviceBreakdown.desktop },
    { name: 'Mobile', value: data.deviceBreakdown.mobile },
    { name: 'Tablet', value: data.deviceBreakdown.tablet },
  ]

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Session Analytics</h3>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">
            {data.totalSessions.toLocaleString()}
          </p>
          <p className="text-sm text-gray-500">Total Sessions</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">
            {formatDuration(data.avgSessionLength)}
          </p>
          <p className="text-sm text-gray-500">Avg Session</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">
            {formatDuration(data.medianSessionLength)}
          </p>
          <p className="text-sm text-gray-500">Median Session</p>
        </div>
      </div>

      {/* Session Length Distribution */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Session Length Distribution</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={sessionLengthData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" style={{ fontSize: 11 }} />
            <YAxis style={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Device Breakdown */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Device Breakdown</h4>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={deviceData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {deviceData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={Object.values(DEVICE_COLORS)[index]}
                />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
