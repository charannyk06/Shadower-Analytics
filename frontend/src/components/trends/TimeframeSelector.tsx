/**
 * Timeframe Selector Component
 *
 * Button group for selecting analysis time window
 */

import React from 'react';
import type { TimeFrame } from '@/types/trend-analysis';

interface TimeframeOption {
  value: TimeFrame;
  label: string;
}

const TIMEFRAME_OPTIONS: TimeframeOption[] = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '1y', label: '1 Year' }
];

interface TimeframeSelectorProps {
  value: TimeFrame;
  onChange: (timeframe: TimeFrame) => void;
  className?: string;
}

export function TimeframeSelector({
  value,
  onChange,
  className = ''
}: TimeframeSelectorProps) {
  return (
    <div className={`flex gap-2 ${className}`}>
      {TIMEFRAME_OPTIONS.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            value === option.value
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
