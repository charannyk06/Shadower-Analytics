'use client';

import React, { useState } from 'react';
import { usePeriodComparison } from '@/hooks/api/useComparisons';
import { PeriodComparison } from '@/types/comparison-views';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/solid';

export default function PeriodComparisonView() {
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [includeTimeSeries, setIncludeTimeSeries] = useState<boolean>(true);

  const { data, isLoading, error, refetch } = usePeriodComparison(
    startDate,
    endDate,
    includeTimeSeries
  );

  const handleCompare = () => {
    refetch();
  };

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Period Selection</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Start Date</label>
            <input
              type="date"
              className="w-full px-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">End Date</label>
            <input
              type="date"
              className="w-full px-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={includeTimeSeries}
                onChange={(e) => setIncludeTimeSeries(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Include time series</span>
            </label>
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={isLoading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Comparing...' : 'Compare Periods'}
        </button>
      </div>

      {/* Results */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">Error: {error.message}</p>
        </div>
      )}

      {data?.data?.periodComparison && (
        <PeriodComparisonResults comparison={data.data.periodComparison} />
      )}
    </div>
  );
}

interface PeriodComparisonResultsProps {
  comparison: PeriodComparison;
}

function PeriodComparisonResults({ comparison }: PeriodComparisonResultsProps) {
  const { current, previous, change } = comparison;

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <ArrowUpIcon className="w-4 h-4" />;
      case 'down':
        return <ArrowDownIcon className="w-4 h-4" />;
      default:
        return <MinusIcon className="w-4 h-4" />;
    }
  };

  const getChangeColor = (direction: string) => {
    switch (direction) {
      case 'positive':
        return 'text-green-600 dark:text-green-400';
      case 'negative':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const metrics = [
    { key: 'totalRuns', label: 'Total Runs', format: (v: number) => v.toLocaleString() },
    { key: 'successRate', label: 'Success Rate', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'averageRuntime', label: 'Avg Runtime', format: (v: number) => `${v.toFixed(0)}ms` },
    { key: 'totalCost', label: 'Total Cost', format: (v: number) => `$${v.toFixed(2)}` },
    { key: 'errorCount', label: 'Error Count', format: (v: number) => v.toLocaleString() },
    { key: 'activeAgents', label: 'Active Agents', format: (v: number) => v.toLocaleString() },
    { key: 'activeUsers', label: 'Active Users', format: (v: number) => v.toLocaleString() },
    { key: 'throughput', label: 'Throughput', format: (v: number) => `${v.toFixed(1)}/min` },
    { key: 'p95Runtime', label: 'P95 Runtime', format: (v: number) => `${v.toFixed(0)}ms` },
    { key: 'creditConsumption', label: 'Credits', format: (v: number) => v.toLocaleString() },
  ];

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Summary</h3>
        <p className="text-gray-700 dark:text-gray-300">{comparison.summary}</p>
      </div>

      {/* Improvements and Regressions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Improvements */}
        {comparison.improvements.length > 0 && (
          <div className="bg-green-50 dark:bg-green-900/20 p-6 rounded-lg border border-green-200 dark:border-green-800">
            <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-4">
              Improvements
            </h3>
            <ul className="space-y-2">
              {comparison.improvements.map((improvement, idx) => (
                <li
                  key={idx}
                  className="flex items-start text-green-800 dark:text-green-200"
                >
                  <ArrowUpIcon className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                  <span>{improvement}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Regressions */}
        {comparison.regressions.length > 0 && (
          <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-lg border border-red-200 dark:border-red-800">
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-4">
              Regressions
            </h3>
            <ul className="space-y-2">
              {comparison.regressions.map((regression, idx) => (
                <li
                  key={idx}
                  className="flex items-start text-red-800 dark:text-red-200"
                >
                  <ArrowDownIcon className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                  <span>{regression}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Detailed Metrics Comparison */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Detailed Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {metrics.map((metric) => {
            const currentValue = current[metric.key as keyof typeof current] as number;
            const previousValue = previous[metric.key as keyof typeof previous] as number;
            const changeData = change[metric.key as keyof typeof change] as any;

            return (
              <div
                key={metric.key}
                className="border dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {metric.label}
                  </span>
                  <div
                    className={`flex items-center space-x-1 ${getChangeColor(
                      changeData.direction
                    )}`}
                  >
                    {getTrendIcon(changeData.trend)}
                    <span className="text-sm font-medium">
                      {changeData.percent >= 0 ? '+' : ''}
                      {changeData.percent.toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Current:
                    </span>
                    <span className="ml-2 font-semibold">
                      {metric.format(currentValue)}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Previous:
                    </span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {metric.format(previousValue)}
                    </span>
                  </div>
                </div>

                {changeData.significant && (
                  <div className="mt-2 pt-2 border-t dark:border-gray-700">
                    <span className="text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100 px-2 py-1 rounded">
                      Significant
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
