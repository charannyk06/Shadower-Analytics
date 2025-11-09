/**
 * CohortAnalysis Component
 * Displays cohort retention heatmap
 */

import React from 'react'
import type { Cohort } from '@/types/user-activity'

interface CohortAnalysisProps {
  cohorts: Cohort[]
}

export function CohortAnalysis({ cohorts }: CohortAnalysisProps) {
  const getRetentionColor = (rate: number): string => {
    if (rate >= 70) return 'bg-green-600 text-white'
    if (rate >= 50) return 'bg-green-500 text-white'
    if (rate >= 30) return 'bg-yellow-500 text-white'
    if (rate >= 15) return 'bg-orange-500 text-white'
    if (rate > 0) return 'bg-red-500 text-white'
    return 'bg-gray-200 text-gray-500'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Cohort Analysis</h3>

      {cohorts.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No cohort data available
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-medium text-gray-700">Cohort</th>
                <th className="text-center py-2 px-3 font-medium text-gray-700">Size</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D1</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D7</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D14</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D30</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D60</th>
                <th className="text-center py-2 px-2 font-medium text-gray-700">D90</th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((cohort) => (
                <tr key={cohort.cohortDate} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium text-gray-900">
                    {new Date(cohort.cohortDate).toLocaleDateString('en-US', {
                      month: 'short',
                      year: 'numeric',
                    })}
                  </td>
                  <td className="text-center py-2 px-3 text-gray-600">
                    {cohort.cohortSize}
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day1
                      )}`}
                    >
                      {cohort.retention.day1.toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day7
                      )}`}
                    >
                      {cohort.retention.day7.toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day14
                      )}`}
                    >
                      {cohort.retention.day14.toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day30
                      )}`}
                    >
                      {cohort.retention.day30.toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day60
                      )}`}
                    >
                      {cohort.retention.day60.toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-2">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                        cohort.retention.day90
                      )}`}
                    >
                      {cohort.retention.day90.toFixed(0)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div className="mt-4 flex items-center justify-end gap-2 text-xs">
            <span className="text-gray-500">Retention:</span>
            <span className="inline-block px-2 py-1 rounded bg-red-500 text-white">0-15%</span>
            <span className="inline-block px-2 py-1 rounded bg-orange-500 text-white">15-30%</span>
            <span className="inline-block px-2 py-1 rounded bg-yellow-500 text-white">30-50%</span>
            <span className="inline-block px-2 py-1 rounded bg-green-500 text-white">50-70%</span>
            <span className="inline-block px-2 py-1 rounded bg-green-600 text-white">70%+</span>
          </div>
        </div>
      )}
    </div>
  )
}
