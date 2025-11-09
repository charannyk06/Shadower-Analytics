'use client'

import { useState } from 'react'
import { useExecutiveDashboard } from '@/hooks/api/useExecutiveDashboard'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { MetricsGrid } from '@/components/dashboard/MetricsGrid'
import { ChartsSection } from '@/components/dashboard/ChartsSection'
import { TablesSection } from '@/components/dashboard/TablesSection'
import { LiveActivityFeed } from '@/components/dashboard/LiveActivityFeed'
import { DashboardSkeleton } from '@/components/dashboard/DashboardSkeleton'
import { Timeframe } from '@/types/executive'

export default function ExecutiveDashboard() {
  const [timeframe, setTimeframe] = useState<Timeframe>('7d')

  const {
    data,
    isLoading,
    error,
    refetch
  } = useExecutiveDashboard({
    timeframe,
  })

  const handleExport = async (format: 'pdf' | 'csv') => {
    // TODO: Implement export functionality
    console.log(`Exporting dashboard as ${format}`)
    alert(`Export as ${format.toUpperCase()} will be implemented`)
  }

  if (isLoading) {
    return <DashboardSkeleton />
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <div className="flex items-center justify-center mb-4">
            <svg
              className="h-12 w-12 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 text-center mb-2">
            Error Loading Dashboard
          </h2>
          <p className="text-gray-600 text-center mb-6">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => refetch()}
            className="w-full bg-blue-600 text-white rounded-md py-2 px-4 hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!data) {
    return <DashboardSkeleton />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader
        timeframe={timeframe}
        onTimeframeChange={setTimeframe}
        onRefresh={() => refetch()}
        onExport={handleExport}
        loading={isLoading}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Key Metrics */}
        <MetricsGrid data={data} loading={isLoading} />

        {/* Charts */}
        <ChartsSection
          trends={data.trends}
          timeframe={timeframe}
        />

        {/* Tables and Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <TablesSection data={data} />
          </div>
          <div>
            <LiveActivityFeed />
          </div>
        </div>
      </div>
    </div>
  )
}
