'use client';

import React, { useState } from 'react';
import { useMetricComparison } from '@/hooks/api/useComparisons';
import { MetricComparison } from '@/types/comparison-views';

export default function MetricComparisonView() {
  const [metricName, setMetricName] = useState<string>('success_rate');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [includeCorrelations, setIncludeCorrelations] = useState<boolean>(false);

  const { data, isLoading, error, refetch } = useMetricComparison(
    metricName,
    startDate,
    endDate,
    includeCorrelations
  );

  const handleCompare = () => {
    refetch();
  };

  return (
    <div className="space-y-6">
      {/* Metric Selection */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Select Metric</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Metric Name</label>
            <select
              className="w-full px-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
              value={metricName}
              onChange={(e) => setMetricName(e.target.value)}
            >
              <option value="success_rate">Success Rate</option>
              <option value="average_runtime">Average Runtime</option>
              <option value="error_rate">Error Rate</option>
              <option value="cost_per_run">Cost Per Run</option>
              <option value="throughput">Throughput</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
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
          </div>

          <div className="flex items-end">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={includeCorrelations}
                onChange={(e) => setIncludeCorrelations(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Include correlations</span>
            </label>
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={isLoading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Analyzing...' : 'Analyze Metric'}
        </button>
      </div>

      {/* Results */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">Error: {error.message}</p>
        </div>
      )}

      {data?.data?.metricComparison && (
        <MetricComparisonResults comparison={data.data.metricComparison} />
      )}
    </div>
  );
}

interface MetricComparisonResultsProps {
  comparison: MetricComparison;
}

function MetricComparisonResults({ comparison }: MetricComparisonResultsProps) {
  const { entities, statistics, distribution, outliers, correlations } = comparison;

  return (
    <div className="space-y-6">
      {/* Statistics Overview */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Statistical Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Mean</p>
            <p className="text-xl font-bold">{statistics.mean.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Median</p>
            <p className="text-xl font-bold">{statistics.median.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Std Dev</p>
            <p className="text-xl font-bold">{statistics.standardDeviation.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Min</p>
            <p className="text-xl font-bold">{statistics.min.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Max</p>
            <p className="text-xl font-bold">{statistics.max.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">P95</p>
            <p className="text-xl font-bold">{statistics.p95.toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* Distribution */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Distribution</h3>
        <div className="space-y-2">
          {distribution.buckets.map((bucket, idx) => (
            <div key={idx} className="flex items-center space-x-4">
              <div className="w-32 text-sm text-gray-600 dark:text-gray-400">
                {bucket.label}
              </div>
              <div className="flex-1">
                <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full flex items-center justify-end px-2"
                    style={{ width: `${bucket.percentage}%` }}
                  >
                    {bucket.percentage > 10 && (
                      <span className="text-xs text-white font-medium">
                        {bucket.count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="w-16 text-sm text-right">
                {bucket.percentage.toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t dark:border-gray-700 grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600 dark:text-gray-400">Skewness:</span>
            <span className="ml-2 font-medium">{distribution.skewness.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Kurtosis:</span>
            <span className="ml-2 font-medium">{distribution.kurtosis.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Normal:</span>
            <span
              className={`ml-2 font-medium ${
                distribution.isNormal
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-orange-600 dark:text-orange-400'
              }`}
            >
              {distribution.isNormal ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>

      {/* Top/Bottom Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 text-green-600 dark:text-green-400">
            Top Performers
          </h3>
          <div className="space-y-3">
            {entities
              .sort((a, b) => b.value - a.value)
              .slice(0, 5)
              .map((entity) => (
                <div
                  key={entity.id}
                  className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"
                >
                  <div>
                    <p className="font-medium">{entity.name}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {entity.percentile.toFixed(0)}th percentile
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-green-600 dark:text-green-400">
                      {entity.value.toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 text-orange-600 dark:text-orange-400">
            Bottom Performers
          </h3>
          <div className="space-y-3">
            {entities
              .sort((a, b) => a.value - b.value)
              .slice(0, 5)
              .map((entity) => (
                <div
                  key={entity.id}
                  className="flex items-center justify-between p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg"
                >
                  <div>
                    <p className="font-medium">{entity.name}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {entity.percentile.toFixed(0)}th percentile
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-orange-600 dark:text-orange-400">
                      {entity.value.toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Outliers */}
      {outliers.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Outliers</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {outliers.map((outlier) => (
              <div
                key={outlier.entityId}
                className={`p-4 rounded-lg border ${
                  outlier.severity === 'extreme'
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : outlier.severity === 'moderate'
                    ? 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800'
                    : 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{outlier.entityName}</p>
                    <p className="text-sm mt-1">
                      Value: <span className="font-semibold">{outlier.value.toFixed(2)}</span>
                    </p>
                    <p className="text-sm">
                      Z-Score: <span className="font-semibold">{outlier.zScore.toFixed(2)}</span>
                    </p>
                  </div>
                  <div className="flex flex-col items-end space-y-1">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        outlier.type === 'high'
                          ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                          : 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                      }`}
                    >
                      {outlier.type}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        outlier.severity === 'extreme'
                          ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                          : outlier.severity === 'moderate'
                          ? 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100'
                          : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                      }`}
                    >
                      {outlier.severity}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Correlations */}
      {correlations && correlations.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Correlations</h3>
          <div className="space-y-3">
            {correlations.map((corr, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
              >
                <div className="flex-1">
                  <p className="font-medium">
                    {corr.metric1} vs {corr.metric2}
                  </p>
                  <div className="flex items-center space-x-4 mt-1 text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        corr.strength === 'strong'
                          ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                          : corr.strength === 'moderate'
                          ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-100'
                      }`}
                    >
                      {corr.strength}
                    </span>
                    <span
                      className={`px-2 py-1 rounded ${
                        corr.direction === 'positive'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                          : 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100'
                      }`}
                    >
                      {corr.direction}
                    </span>
                    {corr.significant && (
                      <span className="px-2 py-1 rounded bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100">
                        significant
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">{corr.coefficient.toFixed(3)}</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    p-value: {corr.pValue.toFixed(4)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
