/**
 * React Query hooks for execution metrics
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import {
  ExecutionMetricsData,
  ExecutionTimeframe,
  RealtimeMetrics,
  ThroughputMetrics,
  LatencyMetrics,
} from '@/types/execution'

// Cache and polling configuration constants
const METRICS_STALE_TIME_MS = 30000 // 30 seconds - how long data is considered fresh
const REALTIME_POLL_INTERVAL_MS = 5000 // 5 seconds - polling frequency for realtime data
const REALTIME_STALE_TIME_MS = 1000 // 1 second - realtime data becomes stale quickly
const THROUGHPUT_LATENCY_STALE_TIME_MS = 60000 // 1 minute - longer cache for historical data

interface ExecutionMetricsParams {
  workspaceId: string
  timeframe?: ExecutionTimeframe
}

/**
 * Fetch comprehensive execution metrics
 */
export function useExecutionMetrics(
  params: ExecutionMetricsParams,
  options?: Omit<UseQueryOptions<ExecutionMetricsData>, 'queryKey' | 'queryFn'>
) {
  const { workspaceId, timeframe = '1h' } = params

  return useQuery<ExecutionMetricsData>({
    queryKey: ['execution-metrics', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/metrics/execution', {
        params: { workspace_id: workspaceId, timeframe },
      })
      return response.data
    },
    staleTime: METRICS_STALE_TIME_MS,
    ...options,
  })
}

/**
 * Fetch real-time execution status (lightweight, for frequent polling)
 */
export function useExecutionRealtime(
  workspaceId: string,
  options?: Omit<UseQueryOptions<{ workspaceId: string; realtime: RealtimeMetrics }>, 'queryKey' | 'queryFn'>
) {
  return useQuery<{ workspaceId: string; realtime: RealtimeMetrics }>({
    queryKey: ['execution-realtime', workspaceId],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/metrics/execution/realtime', {
        params: { workspace_id: workspaceId },
      })
      return response.data
    },
    refetchInterval: REALTIME_POLL_INTERVAL_MS,
    staleTime: REALTIME_STALE_TIME_MS,
    ...options,
  })
}

/**
 * Fetch throughput metrics
 */
export function useExecutionThroughput(
  params: ExecutionMetricsParams,
  options?: Omit<UseQueryOptions<{ workspaceId: string; timeframe: string; throughput: ThroughputMetrics }>, 'queryKey' | 'queryFn'>
) {
  const { workspaceId, timeframe = '24h' } = params

  return useQuery<{ workspaceId: string; timeframe: string; throughput: ThroughputMetrics }>({
    queryKey: ['execution-throughput', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/metrics/execution/throughput', {
        params: { workspace_id: workspaceId, timeframe },
      })
      return response.data
    },
    staleTime: THROUGHPUT_LATENCY_STALE_TIME_MS,
    ...options,
  })
}

/**
 * Fetch latency metrics
 */
export function useExecutionLatency(
  params: ExecutionMetricsParams,
  options?: Omit<UseQueryOptions<{ workspaceId: string; timeframe: string; latency: LatencyMetrics }>, 'queryKey' | 'queryFn'>
) {
  const { workspaceId, timeframe = '24h' } = params

  return useQuery<{ workspaceId: string; timeframe: string; latency: LatencyMetrics }>({
    queryKey: ['execution-latency', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/metrics/execution/latency', {
        params: { workspace_id: workspaceId, timeframe },
      })
      return response.data
    },
    staleTime: THROUGHPUT_LATENCY_STALE_TIME_MS,
    ...options,
  })
}
