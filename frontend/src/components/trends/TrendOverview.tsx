/**
 * Trend Overview Component
 *
 * Displays high-level trend metrics and direction
 */

import React from 'react';
import type { TrendOverview as TrendOverviewType } from '@/types/trend-analysis';

interface TrendOverviewProps {
  overview: TrendOverviewType;
  className?: string;
}

export function TrendOverview({ overview, className = '' }: TrendOverviewProps) {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return '↗';
      case 'decreasing':
        return '↘';
      case 'stable':
        return '→';
      case 'volatile':
        return '⚡';
      default:
        return '—';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return 'text-green-600';
      case 'decreasing':
        return 'text-red-600';
      case 'stable':
        return 'text-blue-600';
      case 'volatile':
        return 'text-orange-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatChange = (change: number) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}`;
  };

  const formatPercentage = (percentage: number) => {
    const sign = percentage >= 0 ? '+' : '';
    return `${sign}${percentage.toFixed(1)}%`;
  };

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Current Value */}
        <div className="flex flex-col">
          <div className="text-sm text-gray-500 mb-1">Current Value</div>
          <div className="text-2xl font-bold text-gray-900">
            {overview.currentValue.toLocaleString()}
          </div>
        </div>

        {/* Change */}
        <div className="flex flex-col">
          <div className="text-sm text-gray-500 mb-1">Change</div>
          <div className={`text-2xl font-bold ${
            overview.change >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatChange(overview.change)}
          </div>
          <div className={`text-sm ${
            overview.changePercentage >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatPercentage(overview.changePercentage)}
          </div>
        </div>

        {/* Trend */}
        <div className="flex flex-col">
          <div className="text-sm text-gray-500 mb-1">Trend</div>
          <div className={`text-2xl font-bold ${getTrendColor(overview.trend)}`}>
            <span className="mr-2">{getTrendIcon(overview.trend)}</span>
            {overview.trend.charAt(0).toUpperCase() + overview.trend.slice(1)}
          </div>
          <div className="text-sm text-gray-600">
            Strength: {overview.trendStrength.toFixed(0)}%
          </div>
        </div>

        {/* Confidence */}
        <div className="flex flex-col">
          <div className="text-sm text-gray-500 mb-1">Confidence</div>
          <div className="text-2xl font-bold text-gray-900">
            {(overview.confidence * 100).toFixed(0)}%
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${overview.confidence * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
