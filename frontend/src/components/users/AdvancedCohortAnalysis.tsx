/**
 * AdvancedCohortAnalysis Component
 * Displays comprehensive cohort analysis with LTV, segments, and comparison
 */

import React, { useState } from 'react'
import type { CohortAdvanced, CohortComparison, CohortSegment } from '@/types/user-activity'

interface AdvancedCohortAnalysisProps {
  cohorts: CohortAdvanced[]
  comparison: CohortComparison
}

export function AdvancedCohortAnalysis({ cohorts, comparison }: AdvancedCohortAnalysisProps) {
  const [selectedCohort, setSelectedCohort] = useState<CohortAdvanced | null>(null)
  const [expandedView, setExpandedView] = useState<'retention' | 'metrics' | 'segments'>('retention')

  const getRetentionColor = (rate: number): string => {
    if (rate >= 70) return 'bg-green-600 text-white'
    if (rate >= 50) return 'bg-green-500 text-white'
    if (rate >= 30) return 'bg-yellow-500 text-white'
    if (rate >= 15) return 'bg-orange-500 text-white'
    if (rate > 0) return 'bg-red-500 text-white'
    return 'bg-gray-200 text-gray-500'
  }

  const getTrendIcon = (trend: string): string => {
    if (trend === 'improving') return '📈'
    if (trend === 'declining') return '📉'
    return '➡️'
  }

  const getTrendColor = (trend: string): string => {
    if (trend === 'improving') return 'text-green-600'
    if (trend === 'declining') return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className="space-y-6">
      {/* Comparison Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Cohort Comparison</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Best Performing</p>
            <p className="text-lg font-bold text-green-700">
              {comparison.bestPerforming || 'N/A'}
            </p>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Needs Attention</p>
            <p className="text-lg font-bold text-red-700">
              {comparison.worstPerforming || 'N/A'}
            </p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Average Retention (D30)</p>
            <div className="flex items-center gap-2">
              <p className="text-lg font-bold text-blue-700">
                {comparison.avgRetention.toFixed(1)}%
              </p>
              <span className={`text-2xl ${getTrendColor(comparison.trend)}`}>
                {getTrendIcon(comparison.trend)}
              </span>
            </div>
            <p className={`text-xs mt-1 ${getTrendColor(comparison.trend)}`}>
              Trend: {comparison.trend}
            </p>
          </div>
        </div>
      </div>

      {/* Main Cohort Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Cohort Details</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setExpandedView('retention')}
              className={`px-3 py-1 rounded text-sm font-medium ${
                expandedView === 'retention'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Retention
            </button>
            <button
              onClick={() => setExpandedView('metrics')}
              className={`px-3 py-1 rounded text-sm font-medium ${
                expandedView === 'metrics'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Metrics
            </button>
            <button
              onClick={() => setExpandedView('segments')}
              className={`px-3 py-1 rounded text-sm font-medium ${
                expandedView === 'segments'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Segments
            </button>
          </div>
        </div>

        {cohorts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No cohort data available
          </div>
        ) : (
          <div className="overflow-x-auto">
            {expandedView === 'retention' && (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-medium text-gray-700">Cohort</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">Size</th>
                    <th className="text-center py-2 px-2 font-medium text-gray-700">D0</th>
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
                    <tr
                      key={cohort.cohortId}
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedCohort(cohort)}
                    >
                      <td className="py-2 px-3 font-medium text-gray-900">
                        {new Date(cohort.cohortDate).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="text-center py-2 px-3 text-gray-600">
                        {cohort.cohortSize}
                      </td>
                      {['day0', 'day1', 'day7', 'day14', 'day30', 'day60', 'day90'].map((day) => (
                        <td key={day} className="text-center py-2 px-2">
                          <span
                            className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                              cohort.retention[day as keyof typeof cohort.retention]
                            )}`}
                          >
                            {cohort.retention[day as keyof typeof cohort.retention].toFixed(0)}%
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {expandedView === 'metrics' && (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-medium text-gray-700">Cohort</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">Size</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">Avg Revenue</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">LTV</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">Churn Rate</th>
                    <th className="text-center py-2 px-3 font-medium text-gray-700">Engagement</th>
                  </tr>
                </thead>
                <tbody>
                  {cohorts.map((cohort) => (
                    <tr
                      key={cohort.cohortId}
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedCohort(cohort)}
                    >
                      <td className="py-2 px-3 font-medium text-gray-900">
                        {new Date(cohort.cohortDate).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="text-center py-2 px-3 text-gray-600">
                        {cohort.cohortSize}
                      </td>
                      <td className="text-center py-2 px-3 text-gray-900 font-medium">
                        {cohort.metrics.avgRevenue.toFixed(0)} credits
                      </td>
                      <td className="text-center py-2 px-3 text-gray-900 font-medium">
                        {cohort.metrics.ltv.toFixed(0)} credits
                      </td>
                      <td className="text-center py-2 px-3">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                            cohort.metrics.churnRate < 20
                              ? 'bg-green-100 text-green-800'
                              : cohort.metrics.churnRate < 40
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {cohort.metrics.churnRate.toFixed(1)}%
                        </span>
                      </td>
                      <td className="text-center py-2 px-3">
                        <div className="flex items-center justify-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-purple-600 h-2 rounded-full"
                              style={{ width: `${cohort.metrics.engagementScore}%` }}
                            ></div>
                          </div>
                          <span className="ml-2 text-xs text-gray-600">
                            {cohort.metrics.engagementScore.toFixed(0)}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {expandedView === 'segments' && selectedCohort && (
              <div>
                <div className="mb-4 p-4 bg-purple-50 rounded-lg">
                  <p className="text-sm text-gray-600">
                    Selected Cohort:{' '}
                    <span className="font-semibold text-gray-900">
                      {new Date(selectedCohort.cohortDate).toLocaleDateString('en-US', {
                        month: 'long',
                        year: 'numeric',
                      })}
                    </span>
                  </p>
                </div>
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-3 font-medium text-gray-700">Segment</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-700">Users</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-700">Retention</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-700">Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedCohort.segments.map((segment, idx) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium text-gray-900">{segment.segment}</td>
                        <td className="text-center py-2 px-3 text-gray-600">{segment.count}</td>
                        <td className="text-center py-2 px-3">
                          <span
                            className={`inline-block px-2 py-1 rounded text-xs font-medium ${getRetentionColor(
                              segment.retention
                            )}`}
                          >
                            {segment.retention.toFixed(1)}%
                          </span>
                        </td>
                        <td className="text-center py-2 px-3">
                          <div className="flex items-center justify-center">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{
                                  width: `${(segment.count / selectedCohort.cohortSize) * 100}%`,
                                }}
                              ></div>
                            </div>
                            <span className="ml-2 text-xs text-gray-600">
                              {((segment.count / selectedCohort.cohortSize) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {expandedView === 'segments' && !selectedCohort && (
              <div className="text-center py-12 text-gray-500">
                Click on a cohort to view segment breakdown
              </div>
            )}
          </div>
        )}

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
    </div>
  )
}
