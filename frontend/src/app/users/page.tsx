'use client'

/**
 * User Activity Dashboard
 * Comprehensive analytics for user behavior and engagement
 */

import { useState } from 'react'
import { useUserActivity } from '@/hooks/api/useUserActivity'
import { ActiveUsersChart } from '@/components/users/ActiveUsersChart'
import { SessionAnalytics } from '@/components/users/SessionAnalytics'
import { FeatureUsageHeatmap } from '@/components/users/FeatureUsageHeatmap'
import { UserJourneyFlow } from '@/components/users/UserJourneyFlow'
import { RetentionCurve } from '@/components/users/RetentionCurve'
import { CohortAnalysis } from '@/components/users/CohortAnalysis'
import { UserSegments } from '@/components/users/UserSegments'
import { EngagementScore } from '@/components/users/EngagementScore'
import type { TimeFrame } from '@/types/user-activity'

// Metric Card Component
interface MetricCardProps {
  title: string
  value: number | string
  change?: number
  format?: 'number' | 'percentage' | 'duration'
}

function MetricCard({ title, value, change, format = 'number' }: MetricCardProps) {
  const formatValue = (val: number | string): string => {
    if (typeof val === 'string') return val

    switch (format) {
      case 'percentage':
        return `${val.toFixed(1)}%`
      case 'duration':
        if (val < 60) return `${Math.round(val)}s`
        if (val < 3600) return `${Math.round(val / 60)}m`
        return `${Math.round(val / 3600)}h`
      default:
        return val.toLocaleString()
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
      <div className="flex items-baseline justify-between">
        <p className="text-2xl font-bold text-gray-900">{formatValue(value)}</p>
        {change !== undefined && (
          <span
            className={`text-sm font-medium ${
              change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {change >= 0 ? '+' : ''}
            {change.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  )
}

export default function UserActivityDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('30d')
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null)

  // For demo purposes, using a mock workspace ID
  // In production, this would come from auth context
  const workspaceId = 'demo-workspace-id'

  const { data, isLoading, error } = useUserActivity({
    workspaceId,
    timeframe,
    segmentId: selectedSegment || undefined,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading user activity data...</p>
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
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">No data available</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                User Activity Analytics
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Track user engagement, behavior patterns, and feature adoption
              </p>
            </div>

            {/* Timeframe Selector */}
            <div className="flex gap-2">
              {(['7d', '30d', '90d', '1y'] as TimeFrame[]).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    timeframe === tf
                      ? 'bg-purple-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {tf === '1y' ? '1 Year' : tf.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Daily Active Users"
            value={data.activityMetrics.dau}
            format="number"
          />
          <MetricCard
            title="Weekly Active Users"
            value={data.activityMetrics.wau}
            format="number"
          />
          <MetricCard
            title="Monthly Active Users"
            value={data.activityMetrics.mau}
            format="number"
          />
          <EngagementScore score={data.activityMetrics.engagementScore} />
        </div>

        {/* Active Users Trend */}
        <ActiveUsersChart
          data={data.activityMetrics.activityByDate}
          timeframe={timeframe}
        />

        {/* Session Analytics & Feature Usage */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <SessionAnalytics data={data.sessionAnalytics} />
          <FeatureUsageHeatmap features={data.featureUsage.features} />
        </div>

        {/* User Journey */}
        <UserJourneyFlow
          journeys={data.userJourney}
          onPathClick={(path) => console.log('Path clicked:', path)}
        />

        {/* Retention & Cohorts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <RetentionCurve data={data.retention.retentionCurve} />
          <CohortAnalysis cohorts={data.retention.cohorts} />
        </div>

        {/* User Segments */}
        <UserSegments
          segments={data.segments}
          selectedSegment={selectedSegment}
          onSegmentSelect={setSelectedSegment}
        />
      </div>
    </div>
  )
}
