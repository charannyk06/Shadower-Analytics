/**
 * RetentionCurve Component
 * Line chart showing user retention over time
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
  Area,
  AreaChart,
} from 'recharts'
import type { RetentionCurvePoint } from '@/types/user-activity'

interface RetentionCurveProps {
  data: RetentionCurvePoint[]
}

export function RetentionCurve({ data }: RetentionCurveProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Retention Curve</h3>

      {data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No retention data available
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorRetention" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="day"
                label={{ value: 'Days Since Signup', position: 'insideBottom', offset: -5 }}
                style={{ fontSize: 12 }}
              />
              <YAxis
                label={{ value: 'Retention %', angle: -90, position: 'insideLeft' }}
                style={{ fontSize: 12 }}
              />
              <Tooltip
                formatter={(value: number) => `${value.toFixed(2)}%`}
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Area
                type="monotone"
                dataKey="retentionRate"
                stroke="#8b5cf6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorRetention)"
                name="Retention Rate"
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4 mt-4">
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">
                {data[0]?.retentionRate.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">Day 0</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">
                {data[7]?.retentionRate.toFixed(1) || 'N/A'}%
              </p>
              <p className="text-xs text-gray-500">Day 7</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">
                {data[30]?.retentionRate.toFixed(1) || 'N/A'}%
              </p>
              <p className="text-xs text-gray-500">Day 30</p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
