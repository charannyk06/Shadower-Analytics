/**
 * Real-time Executions Component
 * Displays currently running executions with progress indicators
 */

'use client'

import { ExecutionInProgress } from '@/types/execution'
import { formatDistanceToNow } from 'date-fns'

interface RealtimeExecutionsProps {
  executions: ExecutionInProgress[]
}

export function RealtimeExecutions({ executions }: RealtimeExecutionsProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">
        Live Executions ({executions.length})
      </h3>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {executions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="mt-2">No executions running</p>
          </div>
        ) : (
          executions.map((exec) => (
            <div
              key={exec.runId}
              className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="font-medium text-sm text-gray-900">{exec.agentName}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Started{' '}
                    {formatDistanceToNow(new Date(exec.startedAt), { addSuffix: true })}
                  </p>
                </div>

                <div className="text-right ml-4">
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-medium text-gray-700">
                      {Math.floor(exec.elapsedTime)}s
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Est. {exec.estimatedCompletion}s
                  </p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-blue-600 h-1.5 rounded-full transition-all duration-1000"
                  style={{
                    width: `${Math.min(
                      (() => {
                        const est = parseFloat(exec.estimatedCompletion)
                        if (isNaN(est) || est <= 0) return 0
                        return (exec.elapsedTime / est) * 100
                      })(),
                      100
                    )}%`,
                  }}
                />
              </div>

              {/* User info */}
              <div className="mt-2 flex items-center text-xs text-gray-500">
                <svg
                  className="h-3 w-3 mr-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                    clipRule="evenodd"
                  />
                </svg>
                {exec.userId}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
