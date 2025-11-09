'use client'

/**
 * Cohort Analysis Dashboard
 * Advanced cohort tracking with LTV, retention, and segmentation
 */

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useAdvancedCohortAnalysis } from '@/hooks/api/useUserActivity'
import { AdvancedCohortAnalysis } from '@/components/users/AdvancedCohortAnalysis'
import type { CohortType, CohortPeriod } from '@/types/user-activity'

export default function CohortAnalysisDashboard() {
  const { user } = useAuth()
  const [cohortType, setCohortType] = useState<CohortType>('signup')
  const [cohortPeriod, setCohortPeriod] = useState<CohortPeriod>('monthly')
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  })

  // Get workspace ID from authenticated user
  const workspaceId = user?.workspaceId

  // Early return if user not loaded yet or missing workspace
  if (!workspaceId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading workspace...</p>
        </div>
      </div>
    )
  }

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
    const errorMessage = error instanceof Error ? error.message : 'An error occurred'
    const isNetworkError = errorMessage.includes('network') || errorMessage.includes('fetch')
    const isAuthError = errorMessage.includes('401') || errorMessage.includes('unauthorized')
    const isAccessError = errorMessage.includes('403') || errorMessage.includes('forbidden')

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md mx-auto px-4">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="text-center">
              <div className="text-red-600 text-4xl mb-4">⚠️</div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Unable to Load Cohort Data
              </h2>
              <p className="text-gray-600 text-sm mb-4">{errorMessage}</p>
            </div>

            <div className="mt-4 bg-blue-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">
                Troubleshooting Steps:
              </h3>
              <ul className="text-sm text-blue-800 space-y-1">
                {isNetworkError && (
                  <>
                    <li>• Check your internet connection</li>
                    <li>• Verify the API server is running</li>
                    <li>• Try refreshing the page</li>
                  </>
                )}
                {isAuthError && (
                  <>
                    <li>• Please log in again</li>
                    <li>• Your session may have expired</li>
                  </>
                )}
                {isAccessError && (
                  <>
                    <li>• Verify you have access to this workspace</li>
                    <li>• Contact your workspace administrator</li>
                  </>
                )}
                {!isNetworkError && !isAuthError && !isAccessError && (
                  <>
                    <li>• Try adjusting the date range</li>
                    <li>• Ensure the workspace has activity data</li>
                    <li>• Contact support if the issue persists</li>
                  </>
                )}
              </ul>
            </div>

            <button
              onClick={() => refetch()}
              aria-label="Retry loading cohort data"
              className="mt-4 w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-colors"
            >
              Try Again
            </button>
          </div>
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
              <label htmlFor="cohort-type" className="block text-sm font-medium text-gray-700 mb-2">
                Cohort Type
              </label>
              <select
                id="cohort-type"
                aria-label="Select cohort type"
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
              <label htmlFor="cohort-period" className="block text-sm font-medium text-gray-700 mb-2">
                Period
              </label>
              <select
                id="cohort-period"
                aria-label="Select cohort period"
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
              <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 mb-2">
                Start Date
              </label>
              <input
                id="start-date"
                type="date"
                aria-label="Select start date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* End Date */}
            <div>
              <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 mb-2">
                End Date
              </label>
              <input
                id="end-date"
                type="date"
                aria-label="Select end date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => refetch()}
              aria-label="Apply cohort analysis filters"
              disabled={isLoading}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading && (
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
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
                {(
                  data.cohorts.reduce((sum, c) => sum + c.metrics.ltv, 0) /
                  data.cohorts.length
                ).toFixed(0)}{' '}
                credits
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600 mb-1">Avg Churn Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {(
                  data.cohorts.reduce((sum, c) => sum + c.metrics.churnRate, 0) /
                  data.cohorts.length
                ).toFixed(1)}
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
