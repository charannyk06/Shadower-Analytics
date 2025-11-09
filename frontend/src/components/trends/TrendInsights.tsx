/**
 * Trend Insights Component
 *
 * Displays actionable insights from trend analysis
 */

import React from 'react';
import type { Insight } from '@/types/trend-analysis';

interface TrendInsightsProps {
  insights: Insight[];
  className?: string;
}

export function TrendInsights({ insights, className = '' }: TrendInsightsProps) {
  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'trend':
        return '📈';
      case 'anomaly':
        return '⚠️';
      case 'pattern':
        return '🔄';
      case 'correlation':
        return '🔗';
      case 'forecast':
        return '🔮';
      default:
        return '💡';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'border-red-500 bg-red-50';
      case 'medium':
        return 'border-yellow-500 bg-yellow-50';
      case 'low':
        return 'border-blue-500 bg-blue-50';
      default:
        return 'border-gray-500 bg-gray-50';
    }
  };

  const getImpactBadgeColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!insights || insights.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">Insights</h3>
        <p className="text-gray-500 text-center py-8">
          No insights available yet. More data may be needed for analysis.
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Insights & Recommendations</h3>

      <div className="space-y-4">
        {insights.map((insight, index) => (
          <div
            key={index}
            className={`border-l-4 rounded-lg p-4 ${getImpactColor(insight.impact)}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getInsightIcon(insight.type)}</span>
                <h4 className="font-semibold text-gray-900">{insight.title}</h4>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getImpactBadgeColor(insight.impact)}`}>
                  {insight.impact.toUpperCase()}
                </span>
                <span className="text-xs text-gray-600">
                  {(insight.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
            </div>

            <p className="text-gray-700 mb-3">{insight.description}</p>

            <div className="bg-white bg-opacity-60 rounded p-3 border border-gray-200">
              <div className="text-xs font-semibold text-gray-600 mb-1">
                Recommendation:
              </div>
              <div className="text-sm text-gray-800">
                {insight.recommendation}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
