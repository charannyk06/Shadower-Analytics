/**
 * MetricsGrid Component
 * Displays a grid of metric cards with key business metrics
 */

import React from 'react'
import { MetricCard } from './MetricCard'
import { ExecutiveDashboardData } from '@/types/executive'

interface MetricsGridProps {
  data: ExecutiveDashboardData
  loading?: boolean
}

export function MetricsGrid({ data, loading = false }: MetricsGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {[...Array(8)].map((_, i) => (
          <MetricCard
            key={i}
            title="Loading..."
            value={0}
            loading={true}
          />
        ))}
      </div>
    )
  }

  const { userMetrics, executionMetrics, businessMetrics } = data

  return (
    <div className="mb-8">
      {/* Top Row - Key Business Metrics */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <MetricCard
          title="Monthly Recurring Revenue"
          value={businessMetrics.mrr}
          change={businessMetrics.mrrChange}
          format="currency"
          description="Total MRR across all active subscriptions"
        />

        <MetricCard
          title="Daily Active Users"
          value={userMetrics.dau}
          change={userMetrics.dauChange}
          format="number"
          description="Unique users active in the last 24 hours"
        />

        <MetricCard
          title="Monthly Active Users"
          value={userMetrics.mau}
          change={userMetrics.mauChange}
          format="number"
          description="Unique users active in the last 30 days"
        />

        <MetricCard
          title="Total Executions"
          value={executionMetrics.totalRuns}
          change={executionMetrics.totalRunsChange}
          format="number"
          description="Total agent executions in selected period"
        />
      </div>

      {/* Second Row - Performance & Financial Metrics */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Success Rate"
          value={executionMetrics.successRate}
          change={executionMetrics.successRateChange}
          format="percentage"
          description="Percentage of successful agent executions"
        />

        <MetricCard
          title="Credits Used"
          value={executionMetrics.totalCreditsUsed}
          change={executionMetrics.creditsChange}
          format="number"
          description="Total credits consumed across all executions"
        />

        <MetricCard
          title="Active Workspaces"
          value={businessMetrics.activeWorkspaces}
          format="number"
          description="Total active workspaces across all plans"
        />

        <MetricCard
          title="Churn Rate"
          value={businessMetrics.churnRate}
          format="percentage"
          description="Customer churn rate (lower is better)"
          trend={businessMetrics.churnRate > 5 ? 'down' : 'neutral'}
        />
      </div>
    </div>
  )
}
