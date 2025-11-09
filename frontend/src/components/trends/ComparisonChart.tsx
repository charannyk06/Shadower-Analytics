/**
 * Comparison Chart Component
 *
 * Displays period-over-period and year-over-year comparisons
 */

import React from 'react';
import type { Comparisons } from '@/types/trend-analysis';

interface ComparisonChartProps {
  comparisons: Comparisons;
  className?: string;
}

export function ComparisonChart({ comparisons, className = '' }: ComparisonChartProps) {
  const { periodComparison, yearOverYear } = comparisons;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Comparisons</h3>

      {/* Period Comparison */}
      {periodComparison && periodComparison.currentPeriod && (
        <div className="mb-6">
          <h4 className="font-medium text-gray-700 mb-3">Period Comparison</h4>

          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* Current Period */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-gray-600 mb-1">Current Period</div>
              <div className="text-sm text-gray-500">
                {formatDate(periodComparison.currentPeriod.start)} -{' '}
                {formatDate(periodComparison.currentPeriod.end)}
              </div>
              <div className="text-2xl font-bold text-blue-700 mt-2">
                {periodComparison.currentPeriod.value.toLocaleString()}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                Avg: {periodComparison.currentPeriod.avg.toFixed(2)}
              </div>
            </div>

            {/* Previous Period */}
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="text-xs text-gray-600 mb-1">Previous Period</div>
              <div className="text-sm text-gray-500">
                {formatDate(periodComparison.previousPeriod.start)} -{' '}
                {formatDate(periodComparison.previousPeriod.end)}
              </div>
              <div className="text-2xl font-bold text-gray-700 mt-2">
                {periodComparison.previousPeriod.value.toLocaleString()}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                Avg: {periodComparison.previousPeriod.avg.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Change Summary */}
          <div className={`p-4 rounded-lg ${
            periodComparison.change >= 0
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-700">Period Change</div>
                <div className={`text-2xl font-bold ${
                  periodComparison.change >= 0 ? 'text-green-700' : 'text-red-700'
                }`}>
                  {periodComparison.change >= 0 ? '+' : ''}
                  {periodComparison.change.toLocaleString()}
                </div>
              </div>
              <div className={`text-3xl font-bold ${
                periodComparison.changePercentage >= 0 ? 'text-green-700' : 'text-red-700'
              }`}>
                {periodComparison.changePercentage >= 0 ? '+' : ''}
                {periodComparison.changePercentage.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Year over Year */}
      {yearOverYear && yearOverYear.currentYear !== null && (
        <div>
          <h4 className="font-medium text-gray-700 mb-3">Year over Year</h4>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500">Current Year</div>
              <div className="text-xl font-bold">
                {yearOverYear.currentYear.toLocaleString()}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500">Previous Year</div>
              <div className="text-xl font-bold">
                {yearOverYear.previousYear?.toLocaleString() || 'N/A'}
              </div>
            </div>
          </div>

          {yearOverYear.changePercentage !== null && (
            <div className={`mt-3 p-3 rounded-lg ${
              yearOverYear.changePercentage >= 0
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}>
              <div className="text-sm font-medium">
                YoY Change: {yearOverYear.changePercentage >= 0 ? '+' : ''}
                {yearOverYear.changePercentage.toFixed(1)}%
              </div>
            </div>
          )}
        </div>
      )}

      {!periodComparison?.currentPeriod && !yearOverYear?.currentYear && (
        <div className="text-center text-gray-500 py-8">
          No comparison data available
        </div>
      )}
    </div>
  );
}
