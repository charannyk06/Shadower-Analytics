/**
 * Workspace analytics hooks with caching support
 */

import { useQuery, UseQueryResult, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'
import { cacheTime } from '@/lib/react-query'
import {
  WorkspaceAnalytics,
  TimeFrame,
  WorkspaceAnalyticsParams,
} from '@/types/workspace'

interface UseWorkspaceAnalyticsOptions {
  workspaceId: string
  timeframe?: TimeFrame
  includeComparison?: boolean
  enabled?: boolean
  refetchInterval?: number
  skipCache?: boolean
}

/**
 * Hook to fetch comprehensive workspace analytics
 *
 * Fetches detailed workspace analytics including:
 * - Overview metrics (members, activity, health score)
 * - Member analytics (roles, activity distribution, top contributors)
 * - Agent usage (performance, efficiency)
 * - Resource utilization (credits, storage, API)
 * - Billing information
 * - Workspace comparison (admin only, when includeComparison=true)
 *
 * @param options Configuration options for the hook
 * @returns React Query result with workspace analytics data
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useWorkspaceAnalytics({
 *   workspaceId: 'workspace-123',
 *   timeframe: '30d',
 *   includeComparison: true,
 * })
 * ```
 */
export function useWorkspaceAnalytics(
  options: UseWorkspaceAnalyticsOptions
): UseQueryResult<WorkspaceAnalytics, Error> {
  const {
    workspaceId,
    timeframe = '30d',
    includeComparison = false,
    enabled = true,
    refetchInterval,
    skipCache = false,
  } = options

  return useQuery({
    queryKey: ['workspace-analytics', workspaceId, timeframe, includeComparison],

    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('timeframe', timeframe)

      if (includeComparison) {
        params.append('include_comparison', 'true')
      }

      if (skipCache) {
        params.append('skip_cache', 'true')
      }

      const url = `${endpoints.workspaceAnalytics(workspaceId)}?${params.toString()}`
      const response = await apiClient.get<WorkspaceAnalytics>(url)

      return response.data
    },

    enabled: enabled && !!workspaceId,
    refetchInterval,
    staleTime: skipCache ? 0 : cacheTime.LONG, // Consider data fresh for 30 minutes
    gcTime: cacheTime.LONG, // Cache for 30 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

/**
 * Hook for refreshing workspace analytics data
 *
 * @param workspaceId Optional workspace ID to invalidate specific workspace data
 * @returns Function to trigger refresh
 *
 * @example
 * ```tsx
 * const refresh = useRefreshWorkspaceAnalytics('workspace-123')
 *
 * // Later...
 * refresh() // Invalidates and refetches data
 * ```
 */
export function useRefreshWorkspaceAnalytics(workspaceId?: string) {
  const queryClient = useQueryClient()

  return () => {
    if (workspaceId) {
      queryClient.invalidateQueries({
        queryKey: ['workspace-analytics', workspaceId]
      })
    } else {
      queryClient.invalidateQueries({
        queryKey: ['workspace-analytics']
      })
    }
  }
}

/**
 * Hook to prefetch workspace analytics data
 *
 * Useful for optimistic loading when user is likely to visit workspace analytics page
 *
 * @param params Workspace analytics parameters
 *
 * @example
 * ```tsx
 * const prefetch = usePrefetchWorkspaceAnalytics()
 *
 * // Prefetch on hover
 * <Link
 *   onMouseEnter={() => prefetch({ workspaceId: 'workspace-123', timeframe: '30d' })}
 * >
 *   View Analytics
 * </Link>
 * ```
 */
export function usePrefetchWorkspaceAnalytics() {
  const queryClient = useQueryClient()

  return (params: WorkspaceAnalyticsParams) => {
    const { workspaceId, timeframe = '30d', includeComparison = false } = params

    queryClient.prefetchQuery({
      queryKey: ['workspace-analytics', workspaceId, timeframe, includeComparison],
      queryFn: async () => {
        const queryParams = new URLSearchParams()
        queryParams.append('timeframe', timeframe)

        if (includeComparison) {
          queryParams.append('include_comparison', 'true')
        }

        const url = `${endpoints.workspaceAnalytics(workspaceId)}?${queryParams.toString()}`
        const response = await apiClient.get<WorkspaceAnalytics>(url)

        return response.data
      },
      staleTime: cacheTime.LONG,
    })
  }
}
