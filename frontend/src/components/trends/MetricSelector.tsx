/**
 * Metric Selector Component
 *
 * Dropdown selector for choosing which metric to analyze
 */

import React from 'react';
import type { AvailableMetric } from '@/types/trend-analysis';

interface MetricConfig {
  value: AvailableMetric;
  label: string;
  description: string;
}

const METRIC_OPTIONS: MetricConfig[] = [
  {
    value: 'executions',
    label: 'Executions',
    description: 'Total agent execution count'
  },
  {
    value: 'users',
    label: 'Active Users',
    description: 'Unique active users'
  },
  {
    value: 'credits',
    label: 'Credits',
    description: 'Credits consumed'
  },
  {
    value: 'errors',
    label: 'Errors',
    description: 'Failed executions'
  },
  {
    value: 'success_rate',
    label: 'Success Rate',
    description: 'Execution success percentage'
  },
  {
    value: 'revenue',
    label: 'Revenue',
    description: 'Total revenue generated'
  }
];

interface MetricSelectorProps {
  value: AvailableMetric;
  onChange: (metric: AvailableMetric) => void;
  availableMetrics?: AvailableMetric[];
  className?: string;
}

export function MetricSelector({
  value,
  onChange,
  availableMetrics,
  className = ''
}: MetricSelectorProps) {
  const options = availableMetrics
    ? METRIC_OPTIONS.filter(opt => availableMetrics.includes(opt.value))
    : METRIC_OPTIONS;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-sm font-medium text-gray-700">
        Metric
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as AvailableMetric)}
        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
