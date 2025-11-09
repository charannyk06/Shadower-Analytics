/**
 * Timeframe Selector Component
 * Allows users to select different time ranges for analytics
 */

import React from 'react';
import { TimeFrame } from '@/types/agent-analytics';

interface TimeframeSelectorProps {
  value: TimeFrame;
  onChange: (timeframe: TimeFrame) => void;
  className?: string;
}

const timeframeOptions: { value: TimeFrame; label: string }[] = [
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
  { value: 'all', label: 'All Time' },
];

export function TimeframeSelector({
  value,
  onChange,
  className = '',
}: TimeframeSelectorProps) {
  return (
    <div className={`inline-flex rounded-lg border border-gray-200 bg-white p-1 ${className}`}>
      {timeframeOptions.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`
            px-4 py-2 text-sm font-medium rounded-md transition-colors
            ${
              value === option.value
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }
          `}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
