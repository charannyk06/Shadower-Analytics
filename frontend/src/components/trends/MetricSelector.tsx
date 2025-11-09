/**
 * Metric Selector Component
 */

'use client';

import { MetricType } from '@/hooks/api/useTrendAnalysis';

interface MetricSelectorProps {
  value: MetricType;
  onChange: (metric: MetricType) => void;
}

const METRICS: { value: MetricType; label: string }[] = [
  { value: 'executions', label: 'Executions' },
  { value: 'users', label: 'Users' },
  { value: 'credits', label: 'Credits' },
  { value: 'success_rate', label: 'Success Rate' },
  { value: 'revenue', label: 'Revenue' },
  { value: 'errors', label: 'Errors' },
];

export function MetricSelector({ value, onChange }: MetricSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as MetricType)}
      className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 font-medium hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    >
      {METRICS.map((metric) => (
        <option key={metric.value} value={metric.value}>
          {metric.label}
        </option>
      ))}
    </select>
  );
}
