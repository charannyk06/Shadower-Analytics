'use client'

/**
 * Cohort Analysis Dashboard
 * Advanced cohort tracking with LTV, retention, and segmentation
 */

import { useState } from 'react'
import { useAdvancedCohortAnalysis } from '@/hooks/api/useUserActivity'
import { AdvancedCohortAnalysis } from '@/components/users/AdvancedCohortAnalysis'
import type { CohortType, CohortPeriod } from '@/types/user-activity'

export default function CohortAnalysisDashboard() {
  const [cohortType, setCohortType] = useState<CohortType>('signup')
  const [cohortPeriod, setCohortPeriod] = useState<CohortPeriod>('monthly')
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  })

  // For demo purposes, using a mock workspace ID
  // In production, this would come from auth context
  const workspaceId = 'demo-workspace-id'

  const { data, isLoading, error, refetch } = useAdvancedCohortAnalysis({
    workspaceId,
    cohortType,
    cohortPeriod,
    startDate: dateRange.start,
    endDate: dateRange.end,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading cohort analysis...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-2">⚠️</div>
          <p className="text-gray-900 font-semibold">Error loading data</p>
          <p className="text-gray-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'An error occurred'}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Cohort Analysis</h1>
          <p className="text-gray-600">
            Track user retention, LTV, and behavior patterns across cohorts
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Cohort Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cohort Type
              </label>
              <select
                value={cohortType}
                onChange={(e) => setCohortType(e.target.value as CohortType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="signup">Signup Date</option>
                <option value="activation">Activation Date</option>
                <option value="feature_adoption">Feature Adoption</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            {/* Cohort Period */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Period
              </label>
              <select
                value={cohortPeriod}
                onChange={(e) => setCohortPeriod(e.target.value as CohortPeriod)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            {/* Start Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Start Date
              </label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date
              </label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            >
              Apply Filters
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        {data && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600 mb-1">Total Cohorts</p>
              <p className="text-2xl font-bold text-gray-900">{data.cohorts.length}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600 mb-1">Total Users</p>
              <p className="text-2xl font-bold text-gray-900">
                {data.cohorts.reduce((sum, c) => sum + c.cohortSize, 0).toLocaleString()}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600 mb-1">Avg LTV</p>
              <p className="text-2xl font-bold text-gray-900">
                {data.cohorts.length > 0
                  ? (
                      data.cohorts.reduce((sum, c) => sum + c.metrics.ltv, 0) /
                      data.cohorts.length
                    ).toFixed(0)
                  : '0'}{' '}
                credits
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600 mb-1">Avg Churn Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {data.cohorts.length > 0
                  ? (
                      data.cohorts.reduce((sum, c) => sum + c.metrics.churnRate, 0) /
                      data.cohorts.length
                    ).toFixed(1)
                  : '0.0'}
                %
              </p>
            </div>
          </div>
        )}

        {/* Main Content */}
        {data && (
          <AdvancedCohortAnalysis cohorts={data.cohorts} comparison={data.comparison} />
        )}

        {/* Help Text */}
        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-2">
            📊 Understanding Cohort Analysis
          </h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>
              • <strong>Retention:</strong> Percentage of users still active after specific time
              periods
            </li>
            <li>
              • <strong>LTV (Lifetime Value):</strong> Estimated total value generated by users in
              the cohort
            </li>
            <li>
              • <strong>Churn Rate:</strong> Percentage of users who became inactive in the last 30
              days
            </li>
            <li>
              • <strong>Engagement Score:</strong> Overall activity level of the cohort (0-100)
            </li>
            <li>
              • <strong>Segments:</strong> Breakdown of cohort by device type or other attributes
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
