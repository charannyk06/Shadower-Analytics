/**
 * Runtime Distribution Component
 * Visualizes runtime percentiles and distribution
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { RuntimeMetrics } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

interface RuntimeDistributionProps {
  runtime: RuntimeMetrics;
}

export function RuntimeDistribution({ runtime }: RuntimeDistributionProps) {
  const data = [
    { label: 'Min', value: runtime.min, fill: '#10b981' },
    { label: 'P50', value: runtime.p50, fill: '#3b82f6' },
    { label: 'P75', value: runtime.p75, fill: '#6366f1' },
    { label: 'P90', value: runtime.p90, fill: '#f59e0b' },
    { label: 'P95', value: runtime.p95, fill: '#f97316' },
    { label: 'P99', value: runtime.p99, fill: '#ef4444' },
    { label: 'Max', value: runtime.max, fill: '#dc2626' },
  ];

  return (
    <Card
      title="Runtime Distribution"
      subtitle="Execution time percentiles (seconds)"
    >
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="label"
              tick={{ fill: '#6b7280', fontSize: 12 }}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 12 }}
              label={{
                value: 'Seconds',
                angle: -90,
                position: 'insideLeft',
                style: { textAnchor: 'middle', fill: '#6b7280' },
              }}
            />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(2)}s`, 'Runtime']}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                padding: '8px 12px',
              }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4 pt-6 border-t border-gray-200">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Average</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">
            {runtime.average.toFixed(2)}s
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Median</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">
            {runtime.median.toFixed(2)}s
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Std Dev</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">
            {runtime.standardDeviation.toFixed(2)}s
          </div>
        </div>
      </div>
    </Card>
  );
}
