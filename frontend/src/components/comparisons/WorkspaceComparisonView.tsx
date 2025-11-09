'use client';

import React, { useState } from 'react';
import { useWorkspaceComparison } from '@/hooks/api/useComparisons';
import { WorkspaceComparison } from '@/types/comparison-views';

export default function WorkspaceComparisonView() {
  const [selectedWorkspaces, setSelectedWorkspaces] = useState<string[]>([]);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data, isLoading, error, refetch } = useWorkspaceComparison(
    selectedWorkspaces,
    startDate,
    endDate
  );

  const handleCompare = () => {
    if (selectedWorkspaces.length >= 2) {
      refetch();
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Selection */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Select Workspaces</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Workspace IDs (comma-separated)
            </label>
            <input
              type="text"
              placeholder="ws-1, ws-2, ws-3"
              className="w-full px-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
              onChange={(e) =>
                setSelectedWorkspaces(
                  e.target.value.split(',').map((id) => id.trim()).filter(Boolean)
                )
              }
            />
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
        </div>

        <button
          onClick={handleCompare}
          disabled={selectedWorkspaces.length < 2 || isLoading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Comparing...' : 'Compare Workspaces'}
        </button>
      </div>

      {/* Results */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">Error: {error.message}</p>
        </div>
      )}

      {data?.data?.workspaceComparison && (
        <WorkspaceComparisonResults comparison={data.data.workspaceComparison} />
      )}
    </div>
  );
}

interface WorkspaceComparisonResultsProps {
  comparison: WorkspaceComparison;
}

function WorkspaceComparisonResults({ comparison }: WorkspaceComparisonResultsProps) {
  const { workspaces, benchmarks, rankings, insights } = comparison;

  return (
    <div className="space-y-6">
      {/* Top Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 p-6 rounded-lg border border-green-200 dark:border-green-800">
          <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-2">
            Top Performer
          </h3>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">
            {benchmarks.topPerformer.workspaceName}
          </p>
          <p className="text-sm text-green-700 dark:text-green-300 mt-1">
            Score: {benchmarks.topPerformer.score.toFixed(1)}
          </p>
        </div>

        <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 p-6 rounded-lg border border-orange-200 dark:border-orange-800">
          <h3 className="text-lg font-semibold text-orange-900 dark:text-orange-100 mb-2">
            Needs Improvement
          </h3>
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {benchmarks.bottomPerformer.workspaceName}
          </p>
          <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
            Score: {benchmarks.bottomPerformer.score.toFixed(1)}
          </p>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow overflow-x-auto">
        <h3 className="text-lg font-semibold mb-4">Workspace Rankings</h3>
        <table className="w-full">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-3 px-4">Rank</th>
              <th className="text-left py-3 px-4">Workspace</th>
              <th className="text-right py-3 px-4">Score</th>
              <th className="text-right py-3 px-4">Percentile</th>
              <th className="text-left py-3 px-4">Strengths</th>
              <th className="text-left py-3 px-4">Weaknesses</th>
            </tr>
          </thead>
          <tbody>
            {rankings.rankings.map((ranking) => (
              <tr
                key={ranking.workspaceId}
                className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <td className="py-3 px-4">
                  <span
                    className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-semibold ${
                      ranking.rank === 1
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                        : ranking.rank === 2
                        ? 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-100'
                        : ranking.rank === 3
                        ? 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100'
                        : 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    #{ranking.rank}
                  </span>
                </td>
                <td className="py-3 px-4 font-medium">{ranking.workspaceName}</td>
                <td className="text-right py-3 px-4">{ranking.score.toFixed(1)}</td>
                <td className="text-right py-3 px-4">
                  {ranking.percentile.toFixed(0)}th
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {ranking.strengths.slice(0, 2).map((strength, idx) => (
                      <span
                        key={idx}
                        className="text-xs bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 px-2 py-1 rounded"
                      >
                        {strength}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {ranking.weaknesses.slice(0, 2).map((weakness, idx) => (
                      <span
                        key={idx}
                        className="text-xs bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100 px-2 py-1 rounded"
                      >
                        {weakness}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Benchmarks */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Benchmarks</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Avg Success Rate</p>
            <p className="text-2xl font-bold">{benchmarks.averageSuccessRate.toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Avg Runtime</p>
            <p className="text-2xl font-bold">{benchmarks.averageRuntime.toFixed(0)}ms</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Avg Cost</p>
            <p className="text-2xl font-bold">${benchmarks.averageCost.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Avg Throughput</p>
            <p className="text-2xl font-bold">{benchmarks.averageThroughput.toFixed(1)}/min</p>
          </div>
        </div>
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Insights</h3>
          <div className="space-y-3">
            {insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  insight.severity === 'critical'
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : insight.severity === 'high'
                    ? 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800'
                    : insight.severity === 'medium'
                    ? 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                    : 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold">{insight.title}</h4>
                    <p className="text-sm mt-1">{insight.description}</p>
                  </div>
                  <span
                    className={`ml-4 px-3 py-1 text-xs font-medium rounded-full ${
                      insight.type === 'warning'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                        : insight.type === 'anomaly'
                        ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                        : insight.type === 'opportunity'
                        ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                    }`}
                  >
                    {insight.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
