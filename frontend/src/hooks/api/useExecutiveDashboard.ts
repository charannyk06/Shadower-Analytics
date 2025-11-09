/**
 * Executive dashboard hooks with caching support
 */

import { useQuery, UseQueryResult, useQueryClient } from '@tanstack/react-query'
import apiClient, { buildQueryParams } from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'
import { queryKeys, cacheTime } from '@/lib/react-query'
import { ExecutiveDashboardData, Timeframe } from '@/types/executive'

interface ExecutiveOverviewParams {
  workspaceId: string
  timeframe: '24h' | '7d' | '30d' | '90d'
}

interface ExecutiveOverviewData {
  workspace_id: string
  timeframe: string
  period: {
    start: string
    end: string
  }
  mrr: number
  churn_rate: number
  ltv: number
  dau: number
  wau: number
  mau: number
  total_executions: number
  success_rate: number
  _meta?: {
    cached: boolean
    timestamp: string
  }
}

interface UseExecutiveDashboardOptions {
  workspaceId?: string
  timeframe?: Timeframe
  enabled?: boolean
  refetchInterval?: number
}

/**
 * Hook to fetch comprehensive executive dashboard with all metrics, trends, and KPIs
 */
export function useExecutiveDashboard(
  options: UseExecutiveDashboardOptions = {}
): UseQueryResult<ExecutiveDashboardData, Error> {
  const {
    workspaceId,
    timeframe = '7d',
    enabled = true,
    refetchInterval,
  } = options

  return useQuery({
    queryKey: ['executive-dashboard', workspaceId, timeframe],
    queryFn: async () => {
      const params = new URLSearchParams()

      if (workspaceId) {
        params.append('workspace_id', workspaceId)
      }

      params.append('timeframe', timeframe)

      const url = `${endpoints.executiveDashboard}?${params.toString()}`
      const response = await apiClient.get<ExecutiveDashboardData>(url)

      return response.data
    },
    enabled,
    refetchInterval,
    staleTime: 60000, // Consider data fresh for 1 minute
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

/**
 * Hook to fetch executive dashboard overview with caching
 */
export function useExecutiveOverview(
  params: ExecutiveOverviewParams,
  options?: {
    skipCache?: boolean
    refetchInterval?: number
    enabled?: boolean
  }
) {
  return useQuery({
    queryKey: queryKeys.executive(params.workspaceId, params.timeframe),

    queryFn: async () => {
      const queryString = buildQueryParams(
        {
          workspace_id: params.workspaceId,
          timeframe: params.timeframe,
        },
        { skipCache: options?.skipCache }
      )

      const response = await apiClient.get<ExecutiveOverviewData>(
        `${endpoints.executiveOverview}?${queryString}`
      )

      return response.data
    },

    // Use shorter stale time if cache is skipped
    staleTime: options?.skipCache ? 0 : cacheTime.LONG,

    // Optional refetch interval for real-time updates
    refetchInterval: options?.refetchInterval,

    // Cache for 30 minutes
    gcTime: cacheTime.LONG,

    // Can be disabled via options
    enabled: options?.enabled !== false,
  })
}

interface RevenueMetricsParams {
  workspaceId: string
  timeframe: '7d' | '30d' | '90d' | '1y'
}

interface RevenueMetricsData {
  workspace_id: string
  timeframe: string
  total_revenue: number
  mrr: number
  arr: number
  trend: Array<{ date: string; value: number }>
  growth_rate: number
}

/**
 * Hook to fetch revenue metrics with caching
 */
export function useRevenueMetrics(
  params: RevenueMetricsParams,
  options?: {
    skipCache?: boolean
    enabled?: boolean
  }
) {
  return useQuery({
    queryKey: queryKeys.revenue(params.workspaceId, params.timeframe),

    queryFn: async () => {
      const queryString = buildQueryParams(
        {
          workspace_id: params.workspaceId,
          timeframe: params.timeframe,
        },
        { skipCache: options?.skipCache }
      )

      const response = await apiClient.get<RevenueMetricsData>(
        `${endpoints.revenue}?${queryString}`
      )

      return response.data
    },

    staleTime: options?.skipCache ? 0 : cacheTime.LONG,
    gcTime: cacheTime.LONG,
    enabled: options?.enabled !== false,
  })
}

interface KPIsData {
  workspace_id: string
  total_users: number
  active_agents: number
  total_executions: number
  success_rate: number
  avg_execution_time: number
  total_credits_used: number
}

/**
 * Hook to fetch key performance indicators with caching
 */
export function useKPIs(
  workspaceId: string,
  options?: {
    skipCache?: boolean
    refetchInterval?: number
    enabled?: boolean
  }
) {
  return useQuery({
    queryKey: queryKeys.kpis(workspaceId),

    queryFn: async () => {
      const queryString = buildQueryParams(
        {
          workspace_id: workspaceId,
        },
        { skipCache: options?.skipCache }
      )

      const response = await apiClient.get<KPIsData>(`${endpoints.kpis}?${queryString}`)

      return response.data
    },

    // Shorter stale time for KPIs (5 minutes)
    staleTime: options?.skipCache ? 0 : cacheTime.MEDIUM,

    // Optional refetch for real-time KPIs
    refetchInterval: options?.refetchInterval,

    gcTime: cacheTime.MEDIUM,
    enabled: options?.enabled !== false,
  })
}

/**
 * Hook for refreshing dashboard data
 */
export function useRefreshDashboard() {
  const queryClient = useQueryClient()

  return () => {
    queryClient.invalidateQueries({ queryKey: ['executive-dashboard'] })
  }
}
