/**
 * Trend Overview Card Component
 */

'use client';

import { TrendOverview, MetricType } from '@/hooks/api/useTrendAnalysis';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/solid';

interface TrendOverviewCardProps {
  overview: TrendOverview;
  metric: MetricType;
}

export function TrendOverviewCard({ overview, metric }: TrendOverviewCardProps) {
  const getTrendIcon = () => {
    switch (overview.trend) {
      case 'increasing':
        return <ArrowUpIcon className="w-6 h-6 text-green-600" />;
      case 'decreasing':
        return <ArrowDownIcon className="w-6 h-6 text-red-600" />;
      case 'stable':
        return <MinusIcon className="w-6 h-6 text-blue-600" />;
      case 'volatile':
        return <span className="text-orange-600 text-xl">~</span>;
      default:
        return null;
    }
  };

  const getTrendColor = () => {
    switch (overview.trend) {
      case 'increasing':
        return 'text-green-600 bg-green-50';
      case 'decreasing':
        return 'text-red-600 bg-red-50';
      case 'stable':
        return 'text-blue-600 bg-blue-50';
      case 'volatile':
        return 'text-orange-600 bg-orange-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const formatMetricName = (m: string) => {
    return m.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Current Value */}
        <div>
          <h4 className="text-sm font-medium text-gray-600 mb-2">
            Current {formatMetricName(metric)}
          </h4>
          <p className="text-3xl font-bold text-gray-900">
            {overview.currentValue.toLocaleString()}
          </p>
        </div>

        {/* Change */}
        <div>
          <h4 className="text-sm font-medium text-gray-600 mb-2">Change</h4>
          <p
            className={`text-3xl font-bold ${
              overview.change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {overview.change >= 0 ? '+' : ''}
            {overview.change.toFixed(0)}
          </p>
          <p
            className={`text-sm font-medium ${
              overview.changePercentage >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {overview.changePercentage >= 0 ? '+' : ''}
            {overview.changePercentage.toFixed(1)}%
          </p>
        </div>

        {/* Trend Direction */}
        <div>
          <h4 className="text-sm font-medium text-gray-600 mb-2">Trend</h4>
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${getTrendColor()}`}>
              {getTrendIcon()}
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-900 capitalize">
                {overview.trend}
              </p>
              <p className="text-xs text-gray-600">
                Strength: {overview.trendStrength.toFixed(0)}%
              </p>
            </div>
          </div>
        </div>

        {/* Confidence */}
        <div>
          <h4 className="text-sm font-medium text-gray-600 mb-2">Confidence</h4>
          <p className="text-3xl font-bold text-gray-900">
            {overview.confidence.toFixed(0)}%
          </p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${overview.confidence}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
