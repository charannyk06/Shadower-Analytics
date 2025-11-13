/**
 * Execution Analytics API Hooks
 */

import { useQuery, useQueryClient, UseQueryResult } from '@tanstack/react-query'
import {
  ExecutionAnalyticsResponse,
  ExecutionSummary,
  WorkspaceExecutionAnalytics,
  ExecutionDetail,
  ExecutionStepsResponse,
  ExecutionAnalyticsRequest,
} from '@/types/execution-analytics'
import { apiClient } from '@/lib/api/client'

export type TimeFrame = '24h' | '7d' | '30d' | '90d' | 'all'

export interface UseExecutionAnalyticsOptions {
  agentId: string
  workspaceId: string
  timeframe?: TimeFrame
  skipCache?: boolean
  enabled?: boolean
}

/**
 * Hook to fetch comprehensive execution analytics for an agent
 */
export function useExecutionAnalytics(
  options: UseExecutionAnalyticsOptions
): UseQueryResult<ExecutionAnalyticsResponse, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    skipCache = false,
    enabled = true,
  } = options

  return useQuery<ExecutionAnalyticsResponse, Error>({
    queryKey: ['executionAnalytics', agentId, workspaceId, timeframe, skipCache],
    queryFn: async () => {
      const response = await apiClient.get<ExecutionAnalyticsResponse>(
        `/api/v1/agent-executions/${agentId}/analytics`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            skip_cache: skipCache,
          },
        }
      )
      return response.data
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

/**
 * Hook to fetch execution summary
 */
export function useExecutionSummary(
  workspaceId: string,
  agentId?: string,
  timeframe: TimeFrame = '7d'
): UseQueryResult<ExecutionSummary, Error> {
  return useQuery<ExecutionSummary, Error>({
    queryKey: ['executionSummary', workspaceId, agentId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<ExecutionSummary>(
        '/api/v1/agent-executions/summary',
        {
          params: {
            workspace_id: workspaceId,
            agent_id: agentId,
            timeframe,
          },
        }
      )
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to fetch performance metrics for an agent
 */
export function useExecutionPerformance(
  agentId: string,
  workspaceId: string,
  timeframe: TimeFrame = '7d'
): UseQueryResult<{ agentId: string; workspaceId: string; timeframe: string; performance: any; trends: any[] }, Error> {
  return useQuery({
    queryKey: ['executionPerformance', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/agent-executions/${agentId}/performance`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
          },
        }
      )
      return response.data
    },
    enabled: !!agentId && !!workspaceId,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to fetch failure analysis for an agent
 */
export function useExecutionFailures(
  agentId: string,
  workspaceId: string,
  timeframe: TimeFrame = '7d'
): UseQueryResult<{ agentId: string; workspaceId: string; timeframe: string; failureAnalysis: any }, Error> {
  return useQuery({
    queryKey: ['executionFailures', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/agent-executions/${agentId}/failures`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
          },
        }
      )
      return response.data
    },
    enabled: !!agentId && !!workspaceId,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to fetch execution patterns
 */
export function useExecutionPatterns(
  agentId: string,
  workspaceId: string,
  lookbackDays: number = 30
): UseQueryResult<any, Error> {
  return useQuery({
    queryKey: ['executionPatterns', agentId, workspaceId, lookbackDays],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/agent-executions/${agentId}/patterns`,
        {
          params: {
            workspace_id: workspaceId,
            lookback_days: lookbackDays,
          },
        }
      )
      return response.data
    },
    enabled: !!agentId && !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes for pattern analysis
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  })
}

/**
 * Hook to fetch workspace execution analytics
 */
export function useWorkspaceExecutionAnalytics(
  workspaceId: string,
  timeframe: TimeFrame = '7d'
): UseQueryResult<WorkspaceExecutionAnalytics, Error> {
  return useQuery<WorkspaceExecutionAnalytics, Error>({
    queryKey: ['workspaceExecutionAnalytics', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<WorkspaceExecutionAnalytics>(
        `/api/v1/agent-executions/workspace/${workspaceId}/trends`,
        {
          params: {
            timeframe,
          },
        }
      )
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to fetch specific execution detail
 */
export function useExecutionDetail(
  agentId: string,
  executionId: string,
  workspaceId: string,
  enabled: boolean = true
): UseQueryResult<ExecutionDetail, Error> {
  return useQuery<ExecutionDetail, Error>({
    queryKey: ['executionDetail', agentId, executionId, workspaceId],
    queryFn: async () => {
      const response = await apiClient.get<ExecutionDetail>(
        `/api/v1/agent-executions/${agentId}/executions/${executionId}`,
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      )
      return response.data
    },
    enabled: enabled && !!agentId && !!executionId && !!workspaceId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to fetch execution steps
 */
export function useExecutionSteps(
  agentId: string,
  executionId: string,
  workspaceId: string,
  enabled: boolean = true
): UseQueryResult<ExecutionStepsResponse, Error> {
  return useQuery<ExecutionStepsResponse, Error>({
    queryKey: ['executionSteps', agentId, executionId, workspaceId],
    queryFn: async () => {
      const response = await apiClient.get<ExecutionStepsResponse>(
        `/api/v1/agent-executions/${agentId}/executions/${executionId}/steps`,
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      )
      return response.data
    },
    enabled: enabled && !!agentId && !!executionId && !!workspaceId,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 3,
  })
}

/**
 * Hook to prefetch execution analytics for performance
 */
export function usePrefetchExecutionAnalytics() {
  const queryClient = useQueryClient()

  return (agentId: string, workspaceId: string, timeframe: TimeFrame = '7d') => {
    return queryClient.prefetchQuery({
      queryKey: ['executionAnalytics', agentId, workspaceId, timeframe, false],
      queryFn: async () => {
        const response = await apiClient.get<ExecutionAnalyticsResponse>(
          `/api/v1/agent-executions/${agentId}/analytics`,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
              skip_cache: false,
            },
          }
        )
        return response.data
      },
      staleTime: 60 * 1000,
    })
  }
}

/**
 * Hook to invalidate execution analytics cache
 */
export function useInvalidateExecutionAnalytics() {
  const queryClient = useQueryClient()

  return (agentId?: string) => {
    if (agentId) {
      // Invalidate specific agent's execution analytics
      queryClient.invalidateQueries({
        queryKey: ['executionAnalytics', agentId],
      })
      queryClient.invalidateQueries({
        queryKey: ['executionPerformance', agentId],
      })
      queryClient.invalidateQueries({
        queryKey: ['executionFailures', agentId],
      })
    } else {
      // Invalidate all execution analytics
      queryClient.invalidateQueries({
        queryKey: ['executionAnalytics'],
      })
      queryClient.invalidateQueries({
        queryKey: ['executionSummary'],
      })
      queryClient.invalidateQueries({
        queryKey: ['workspaceExecutionAnalytics'],
      })
    }
  }
}
