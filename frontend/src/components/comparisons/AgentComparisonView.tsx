'use client';

import React, { useState } from 'react';
import { useAgentComparison } from '@/hooks/api/useComparisons';
import { AgentComparison } from '@/types/comparison-views';

export default function AgentComparisonView() {
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data, isLoading, error, refetch } = useAgentComparison(
    selectedAgents,
    startDate,
    endDate
  );

  const handleCompare = () => {
    if (selectedAgents.length >= 2) {
      refetch();
    }
  };

  return (
    <div className="space-y-6">
      {/* Agent Selection */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Select Agents to Compare</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Agent IDs (comma-separated)
            </label>
            <input
              type="text"
              placeholder="agent-1, agent-2, agent-3"
              className="w-full px-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
              onChange={(e) =>
                setSelectedAgents(
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
          disabled={selectedAgents.length < 2 || isLoading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Comparing...' : 'Compare Agents'}
        </button>
      </div>

      {/* Results */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Error: {error.message}
          </p>
        </div>
      )}

      {data?.data?.agentComparison && (
        <AgentComparisonResults comparison={data.data.agentComparison} />
      )}
    </div>
  );
}

interface AgentComparisonResultsProps {
  comparison: AgentComparison;
}

function AgentComparisonResults({ comparison }: AgentComparisonResultsProps) {
  return (
    <div className="space-y-6">
      {/* Winner Card */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 p-6 rounded-lg border border-green-200 dark:border-green-800">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-green-900 dark:text-green-100">
              Best Performer
            </h3>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
              {comparison.agents.find((a) => a.id === comparison.winner)?.name || comparison.winner}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-green-700 dark:text-green-300">
              Overall Score
            </p>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              {comparison.winnerScore.toFixed(1)}
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Comparison Table */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow overflow-x-auto">
        <h3 className="text-lg font-semibold mb-4">Metrics Comparison</h3>
        <table className="w-full">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-3 px-4">Agent</th>
              <th className="text-right py-3 px-4">Success Rate</th>
              <th className="text-right py-3 px-4">Avg Runtime</th>
              <th className="text-right py-3 px-4">Cost/Run</th>
              <th className="text-right py-3 px-4">Throughput</th>
              <th className="text-right py-3 px-4">Error Rate</th>
            </tr>
          </thead>
          <tbody>
            {comparison.agents.map((agent) => (
              <tr
                key={agent.id}
                className={`border-b dark:border-gray-700 ${
                  agent.id === comparison.winner
                    ? 'bg-green-50 dark:bg-green-900/10'
                    : ''
                }`}
              >
                <td className="py-3 px-4 font-medium">
                  {agent.name}
                  {agent.id === comparison.winner && (
                    <span className="ml-2 text-xs bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 px-2 py-1 rounded">
                      Winner
                    </span>
                  )}
                </td>
                <td className="text-right py-3 px-4">
                  {agent.metrics.successRate.toFixed(1)}%
                </td>
                <td className="text-right py-3 px-4">
                  {agent.metrics.averageRuntime.toFixed(0)}ms
                </td>
                <td className="text-right py-3 px-4">
                  ${agent.metrics.costPerRun.toFixed(3)}
                </td>
                <td className="text-right py-3 px-4">
                  {agent.metrics.throughput.toFixed(1)}/min
                </td>
                <td className="text-right py-3 px-4">
                  {agent.metrics.errorRate.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Key Differences */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(comparison.differences).map(([metric, diff]) => (
          <div
            key={metric}
            className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow"
          >
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              {metric.replace(/([A-Z])/g, ' $1').trim()}
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-green-600 dark:text-green-400">
                  Best
                </span>
                <span className="font-semibold">{diff.best}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-red-600 dark:text-red-400">
                  Worst
                </span>
                <span className="font-semibold">{diff.worst}</span>
              </div>
              <div className="pt-2 border-t dark:border-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Difference: {diff.deltaPercent.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {comparison.recommendations.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
          <div className="space-y-3">
            {comparison.recommendations.map((rec, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  rec.priority === 'critical'
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : rec.priority === 'high'
                    ? 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800'
                    : rec.priority === 'medium'
                    ? 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                    : 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold">{rec.title}</h4>
                    <p className="text-sm mt-1 text-gray-700 dark:text-gray-300">
                      {rec.description}
                    </p>
                    {rec.affectedAgents.length > 0 && (
                      <p className="text-xs mt-2 text-gray-600 dark:text-gray-400">
                        Affected: {rec.affectedAgents.join(', ')}
                      </p>
                    )}
                  </div>
                  <span
                    className={`ml-4 px-3 py-1 text-xs font-medium rounded-full ${
                      rec.priority === 'critical'
                        ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                        : rec.priority === 'high'
                        ? 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100'
                        : rec.priority === 'medium'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                    }`}
                  >
                    {rec.priority}
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
