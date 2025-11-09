/**
 * Timeframe Selector Component
 */

'use client';

import { TimeFrame } from '@/hooks/api/useTrendAnalysis';

interface TimeframeSelectorProps {
  value: TimeFrame;
  onChange: (timeframe: TimeFrame) => void;
}

const TIMEFRAMES: { value: TimeFrame; label: string }[] = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '1y', label: '1 Year' },
];

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as TimeFrame)}
      className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 font-medium hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    >
      {TIMEFRAMES.map((timeframe) => (
        <option key={timeframe.value} value={timeframe.value}>
          {timeframe.label}
        </option>
      ))}
    </select>
  );
}
