/**
 * Trend Insights Component
 */

'use client';

import { Insight } from '@/hooks/api/useTrendAnalysis';
import {
  LightBulbIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

interface TrendInsightsProps {
  insights: Insight[];
}

export function TrendInsights({ insights }: TrendInsightsProps) {
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'border-red-200 bg-red-50';
      case 'medium':
        return 'border-yellow-200 bg-yellow-50';
      case 'low':
        return 'border-blue-200 bg-blue-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const getImpactIcon = (impact: string) => {
    switch (impact) {
      case 'high':
        return <ExclamationTriangleIcon className="w-5 h-5 text-red-600" />;
      case 'medium':
        return <InformationCircleIcon className="w-5 h-5 text-yellow-600" />;
      case 'low':
        return <LightBulbIcon className="w-5 h-5 text-blue-600" />;
      default:
        return null;
    }
  };

  if (insights.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No insights available at this time
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {insights.map((insight, index) => (
        <div
          key={index}
          className={`border rounded-lg p-4 ${getImpactColor(insight.impact)}`}
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {getImpactIcon(insight.impact)}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900">{insight.title}</h4>
                <span className="text-xs font-medium text-gray-600 bg-white px-2 py-1 rounded">
                  {insight.confidence.toFixed(0)}% confidence
                </span>
              </div>
              <p className="text-sm text-gray-700 mb-3">{insight.description}</p>
              <div className="bg-white bg-opacity-60 rounded p-3">
                <div className="text-xs font-medium text-gray-600 mb-1">
                  Recommendation:
                </div>
                <p className="text-sm text-gray-800">{insight.recommendation}</p>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
