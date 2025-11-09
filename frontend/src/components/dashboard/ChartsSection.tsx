/**
 * ChartsSection Component
 * Container for all dashboard charts
 */

import React from 'react'
import { ExecutionTrendChart } from '@/components/charts/ExecutionTrendChart'
import { UserActivityChart } from '@/components/charts/UserActivityChart'
import { RevenueChart } from '@/components/charts/RevenueChart'
import { ErrorRateChart } from '@/components/charts/ErrorRateChart'
import { TrendData, Timeframe } from '@/types/executive'

interface ChartsSectionProps {
  trends: TrendData
  timeframe: Timeframe
}

export function ChartsSection({ trends, timeframe }: ChartsSectionProps) {
  return (
    <div className="space-y-6 mb-8">
      {/* Top Row - Execution and User Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ExecutionTrendChart
          data={trends.execution}
          timeframe={timeframe}
          showSuccess={true}
        />
        <UserActivityChart data={trends.users} timeframe={timeframe} />
      </div>

      {/* Bottom Row - Revenue and Error Rate */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RevenueChart data={trends.revenue} timeframe={timeframe} />
        <ErrorRateChart data={trends.errors} timeframe={timeframe} />
      </div>
    </div>
  )
}
