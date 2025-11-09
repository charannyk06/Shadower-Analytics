/**
 * Execution Metrics Dashboard
 * Comprehensive real-time and historical execution metrics tracking
 */

'use client'

import { useState, useEffect } from 'react'
import { useExecutionMetrics, useExecutionRealtime } from '@/hooks/api/useExecutionMetrics'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ExecutionTimeframe, RealtimeMetrics } from '@/types/execution'
import { RealtimeExecutions } from './RealtimeExecutions'
import { QueueDepthIndicator } from './QueueDepthIndicator'
import { SystemLoadMonitor } from './SystemLoadMonitor'
import { ThroughputChart } from './ThroughputChart'
import { LatencyDistribution } from './LatencyDistribution'
import { ExecutionTimeline } from './ExecutionTimeline'
import { PerformanceByAgent } from './PerformanceByAgent'
import { MetricCard } from '../dashboard/MetricCard'
import { DashboardSkeleton } from '../dashboard/DashboardSkeleton'

interface ExecutionMetricsDashboardProps {
  workspaceId: string
}

export function ExecutionMetricsDashboard({ workspaceId }: ExecutionMetricsDashboardProps) {
  const [timeframe, setTimeframe] = useState<ExecutionTimeframe>('1h')
  const { data, isLoading, error, refetch } = useExecutionMetrics({
    workspaceId,
    timeframe,
  })
  const [realtimeData, setRealtimeData] = useState<RealtimeMetrics | undefined>(data?.realtime)

  // Update realtime data when full data changes
  useEffect(() => {
    if (data?.realtime) {
      setRealtimeData(data.realtime)
    }
  }, [data])

  // WebSocket connection for real-time updates
  const { connected } = useWebSocket({
    workspaceId,
    onMessage: (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.event === 'execution_update') {
          setRealtimeData(message.data)
        } else if (message.event === 'execution_started' || message.event === 'execution_completed') {
          // Refetch full metrics on execution changes
          refetch()
        }
      } catch (err) {
        console.error('WebSocket message parse error:', err)
      }
    },
  })

  if (isLoading) return <DashboardSkeleton />
  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <h3 className="text-red-800 font-semibold">Error loading execution metrics</h3>
        <p className="text-red-600 text-sm mt-2">
          {error instanceof Error ? error.message : 'Unknown error occurred'}
        </p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6 p-6">
      {/* Header with timeframe selector */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Execution Metrics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time and historical execution performance tracking
            {connected && (
              <span className="ml-2 inline-flex items-center">
                <span className="h-2 w-2 bg-green-500 rounded-full animate-pulse mr-1"></span>
                Live
              </span>
            )}
          </p>
        </div>

        {/* Timeframe Selector */}
        <div className="flex space-x-2">
          {(['1h', '6h', '24h', '7d', '30d'] as ExecutionTimeframe[]).map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                timeframe === tf
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Real-time Status Bar */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <MetricCard
            title="Running Now"
            value={realtimeData?.currentlyRunning || 0}
            format="number"
            className="!shadow-none !p-4"
          />

          <QueueDepthIndicator
            depth={realtimeData?.queueDepth || 0}
            waitTime={realtimeData?.avgQueueWaitTime || 0}
          />

          <MetricCard
            title="Per Minute"
            value={data.throughput.executionsPerMinute}
            format="number"
            description="Current throughput"
            className="!shadow-none !p-4"
          />

          <MetricCard
            title="Success Rate"
            value={data.performance.successRate}
            format="percentage"
            className="!shadow-none !p-4"
          />

          <MetricCard
            title="Median Latency"
            value={data.latency.executionLatency.median}
            format="duration"
            className="!shadow-none !p-4"
          />
        </div>
      </div>

      {/* Live Executions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RealtimeExecutions executions={realtimeData?.executionsInProgress || []} />
        <SystemLoadMonitor load={realtimeData?.systemLoad} />
      </div>

      {/* Throughput and Latency Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ThroughputChart data={data.throughput} />
        <LatencyDistribution data={data.latency} />
      </div>

      {/* Execution Timeline */}
      <ExecutionTimeline
        timeline={data.patterns.timeline}
        anomalies={data.patterns.anomalies}
      />

      {/* Performance Breakdown */}
      <PerformanceByAgent agents={data.performance.byAgent} />
    </div>
  )
}
