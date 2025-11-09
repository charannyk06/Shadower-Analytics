/**
 * UserJourneyFlow Component
 * Displays common user paths and entry/exit points
 */

import React from 'react'
import type { UserJourney } from '@/types/user-activity'

interface UserJourneyFlowProps {
  journeys: UserJourney
  onPathClick?: (path: string[]) => void
}

export function UserJourneyFlow({ journeys, onPathClick }: UserJourneyFlowProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h3 className="text-lg font-semibold mb-4">User Journey Analysis</h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Common Paths */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Most Common Paths</h4>
          {journeys.commonPaths.length === 0 ? (
            <p className="text-sm text-gray-500">No path data available</p>
          ) : (
            <div className="space-y-3">
              {journeys.commonPaths.slice(0, 5).map((path, idx) => (
                <div
                  key={idx}
                  onClick={() => onPathClick?.(path.path)}
                  className="border border-gray-200 rounded-lg p-3 hover:border-purple-300 hover:bg-purple-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-600">
                      {path.frequency} users
                    </span>
                    <span className="text-xs text-green-600">
                      {path.avgCompletion.toFixed(0)}% completion
                    </span>
                  </div>
                  <div className="flex items-center gap-2 overflow-x-auto">
                    {path.path.map((step, stepIdx) => (
                      <React.Fragment key={stepIdx}>
                        <div className="text-xs bg-gray-100 px-2 py-1 rounded whitespace-nowrap">
                          {step}
                        </div>
                        {stepIdx < path.path.length - 1 && (
                          <svg
                            className="w-4 h-4 text-gray-400 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Entry & Exit Points */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Entry Points</h4>
          {journeys.entryPoints.length === 0 ? (
            <p className="text-sm text-gray-500 mb-6">No entry point data</p>
          ) : (
            <div className="space-y-2 mb-6">
              {journeys.entryPoints.slice(0, 5).map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded"
                >
                  <span className="text-sm text-gray-900 truncate flex-1">
                    {entry.page}
                  </span>
                  <div className="flex items-center gap-3 ml-2">
                    <span className="text-xs text-gray-600">
                      {entry.count} visits
                    </span>
                    {entry.bounceRate > 0 && (
                      <span
                        className={`text-xs ${
                          entry.bounceRate > 50 ? 'text-red-600' : 'text-green-600'
                        }`}
                      >
                        {entry.bounceRate.toFixed(0)}% bounce
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <h4 className="text-sm font-medium text-gray-700 mb-3">Exit Points</h4>
          {journeys.exitPoints.length === 0 ? (
            <p className="text-sm text-gray-500">No exit point data</p>
          ) : (
            <div className="space-y-2">
              {journeys.exitPoints.slice(0, 5).map((exit, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded"
                >
                  <span className="text-sm text-gray-900 truncate flex-1">
                    {exit.page}
                  </span>
                  <div className="flex items-center gap-3 ml-2">
                    <span className="text-xs text-gray-600">
                      {exit.count} exits
                    </span>
                    {exit.avgTimeBeforeExit > 0 && (
                      <span className="text-xs text-gray-500">
                        {Math.round(exit.avgTimeBeforeExit / 60)}m avg
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
