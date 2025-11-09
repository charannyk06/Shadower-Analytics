/**
 * Performance By Agent Component
 * Displays performance breakdown by agent
 */

'use client'

import { AgentPerformance } from '@/types/execution'

interface PerformanceByAgentProps {
  agents: AgentPerformance[]
}

export function PerformanceByAgent({ agents }: PerformanceByAgentProps) {
  if (agents.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Performance by Agent</h3>
        <p className="text-gray-500 text-sm">No agent data available</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Performance by Agent</h3>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Executions
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Success Rate
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Avg Runtime
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Error Rate
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {agents.map((agent) => (
              <tr key={agent.agentId} className="hover:bg-gray-50">
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{agent.agentName}</div>
                  <div className="text-xs text-gray-500">{agent.agentId}</div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {agent.executions.toLocaleString()}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right">
                  <span
                    className={`text-sm font-semibold ${
                      agent.successRate >= 95
                        ? 'text-green-600'
                        : agent.successRate >= 80
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {agent.successRate.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {agent.avgRuntime.toFixed(2)}s
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right">
                  <span
                    className={`text-sm ${
                      agent.errorRate < 5
                        ? 'text-green-600'
                        : agent.errorRate < 10
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {agent.errorRate.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
