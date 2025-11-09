/**
 * Execution Metrics Dashboard
 * Comprehensive real-time and historical execution metrics tracking
 */

'use client'

import { useState, useEffect } from 'react'
import { useExecutionMetrics } from '@/hooks/api/useExecutionMetrics'
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
  const [wsError, setWsError] = useState<string | null>(null)

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
        setWsError('Failed to parse real-time updates')
      }
    },
    onError: () => {
      setWsError('Real-time updates disconnected')
    },
    onClose: () => {
      setWsError('Real-time updates disconnected')
    },
    onOpen: () => {
      setWsError(null)
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
      {/* WebSocket Error Alert */}
      {wsError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-sm text-yellow-800">{wsError}</span>
          </div>
          <button
            onClick={() => setWsError(null)}
            className="text-yellow-600 hover:text-yellow-800"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}

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
