/**
 * Agent Lifecycle Analytics API Hooks
 *
 * Provides React Query hooks for fetching agent lifecycle data including:
 * - Comprehensive lifecycle analytics
 * - State transitions
 * - Current lifecycle status
 * - Version comparisons
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import {
  AgentLifecycleAnalytics,
  LifecycleAnalyticsQuery,
  LifecycleStatusResponse,
  TransitionsResponse,
  VersionComparisonResponse,
  VersionComparisonRequest,
  LifecycleTimeframe,
  LifecycleEvent,
  LifecycleEventResponse,
} from '@/types/agent-lifecycle';

// ============================================================================
// Query Options Interfaces
// ============================================================================

export interface UseAgentLifecycleOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: LifecycleTimeframe;
  includePredictions?: boolean;
  includeVersions?: boolean;
  includeDeployments?: boolean;
  includeHealth?: boolean;
  enabled?: boolean;
}

export interface UseLifecycleStatusOptions {
  agentId: string;
  workspaceId: string;
  enabled?: boolean;
  refetchInterval?: number; // Poll interval in ms
}

export interface UseLifecycleTransitionsOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: LifecycleTimeframe;
  enabled?: boolean;
}

export interface UseVersionComparisonOptions {
  agentId: string;
  workspaceId: string;
  versionA: string;
  versionB: string;
  enabled?: boolean;
}

// ============================================================================
// Main Lifecycle Analytics Hook
// ============================================================================

/**
 * Hook to fetch comprehensive agent lifecycle analytics
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useAgentLifecycle({
 *   agentId: 'agent-123',
 *   workspaceId: 'ws-456',
 *   timeframe: '30d',
 * });
 * ```
 */
export function useAgentLifecycle(
  options: UseAgentLifecycleOptions
): UseQueryResult<AgentLifecycleAnalytics, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = 'all',
    includePredictions = false,
    includeVersions = true,
    includeDeployments = true,
    includeHealth = true,
    enabled = true,
  } = options;

  return useQuery<AgentLifecycleAnalytics, Error>({
    queryKey: [
      'agentLifecycle',
      agentId,
      workspaceId,
      timeframe,
      includePredictions,
      includeVersions,
      includeDeployments,
      includeHealth,
    ],
    queryFn: async () => {
      const response = await apiClient.get<AgentLifecycleAnalytics>(
        `/api/v1/agents/${agentId}/lifecycle`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            include_predictions: includePredictions,
            include_versions: includeVersions,
            include_deployments: includeDeployments,
            include_health: includeHealth,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// ============================================================================
// Lifecycle Status Hook (Lightweight, for Polling)
// ============================================================================

/**
 * Hook to fetch current lifecycle status only (lightweight)
 *
 * Useful for frequent polling to check current state without
 * fetching full historical data.
 *
 * @example
 * ```tsx
 * const { data } = useLifecycleStatus({
 *   agentId: 'agent-123',
 *   workspaceId: 'ws-456',
 *   refetchInterval: 30000, // Poll every 30 seconds
 * });
 * ```
 */
export function useLifecycleStatus(
  options: UseLifecycleStatusOptions
): UseQueryResult<LifecycleStatusResponse, Error> {
  const {
    agentId,
    workspaceId,
    enabled = true,
    refetchInterval = 0, // No auto-refetch by default
  } = options;

  return useQuery<LifecycleStatusResponse, Error>({
    queryKey: ['lifecycleStatus', agentId, workspaceId],
    queryFn: async () => {
      const response = await apiClient.get<LifecycleStatusResponse>(
        `/api/v1/agents/${agentId}/lifecycle/status`,
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 60 * 1000, // 1 minute
    refetchInterval, // Auto-refetch at specified interval
    retry: 2,
  });
}

// ============================================================================
// State Transitions Hook
// ============================================================================

/**
 * Hook to fetch detailed state transition history
 *
 * @example
 * ```tsx
 * const { data } = useLifecycleTransitions({
 *   agentId: 'agent-123',
 *   workspaceId: 'ws-456',
 *   timeframe: '7d',
 * });
 * ```
 */
export function useLifecycleTransitions(
  options: UseLifecycleTransitionsOptions
): UseQueryResult<TransitionsResponse, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '30d',
    enabled = true,
  } = options;

  return useQuery<TransitionsResponse, Error>({
    queryKey: ['lifecycleTransitions', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<TransitionsResponse>(
        `/api/v1/agents/${agentId}/lifecycle/transitions`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
}

// ============================================================================
// Version Comparison Hook
// ============================================================================

/**
 * Hook to compare performance between two agent versions
 *
 * @example
 * ```tsx
 * const { data } = useVersionComparison({
 *   agentId: 'agent-123',
 *   workspaceId: 'ws-456',
 *   versionA: '1.0.0',
 *   versionB: '1.1.0',
 * });
 * ```
 */
export function useVersionComparison(
  options: UseVersionComparisonOptions
): UseQueryResult<VersionComparisonResponse, Error> {
  const {
    agentId,
    workspaceId,
    versionA,
    versionB,
    enabled = true,
  } = options;

  return useQuery<VersionComparisonResponse, Error>({
    queryKey: ['versionComparison', agentId, workspaceId, versionA, versionB],
    queryFn: async () => {
      const response = await apiClient.get<VersionComparisonResponse>(
        `/api/v1/agents/${agentId}/versions/compare`,
        {
          params: {
            workspace_id: workspaceId,
            version_a: versionA,
            version_b: versionB,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId && !!versionA && !!versionB,
    staleTime: 5 * 60 * 1000, // 5 minutes (version comparisons change less frequently)
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
}

// ============================================================================
// Lifecycle Event Recording Mutation
// ============================================================================

export interface RecordLifecycleEventParams {
  agentId: string;
  workspaceId: string;
  eventType: string;
  previousState?: string;
  newState?: string;
  triggeredBy?: string;
  metadata?: Record<string, any>;
}

/**
 * Hook to record a lifecycle event (mutation)
 *
 * @example
 * ```tsx
 * const recordEvent = useRecordLifecycleEvent();
 *
 * recordEvent.mutate({
 *   agentId: 'agent-123',
 *   workspaceId: 'ws-456',
 *   eventType: 'state_change',
 *   previousState: 'testing',
 *   newState: 'production',
 *   triggeredBy: 'user@example.com',
 * });
 * ```
 */
export function useRecordLifecycleEvent() {
  const queryClient = useQueryClient();

  return useMutation<LifecycleEventResponse, Error, RecordLifecycleEventParams>({
    mutationFn: async (params) => {
      const { agentId, ...eventData } = params;
      const response = await apiClient.post<LifecycleEventResponse>(
        `/api/v1/agents/${agentId}/lifecycle/events`,
        eventData
      );
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate related queries to trigger refetch
      queryClient.invalidateQueries({
        queryKey: ['agentLifecycle', variables.agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['lifecycleStatus', variables.agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['lifecycleTransitions', variables.agentId],
      });
    },
  });
}

// ============================================================================
// Prefetch Hooks for Performance
// ============================================================================

/**
 * Hook to prefetch agent lifecycle analytics
 *
 * @example
 * ```tsx
 * const prefetchLifecycle = usePrefetchAgentLifecycle();
 *
 * // Prefetch on hover or navigation
 * onMouseEnter={() => prefetchLifecycle('agent-123', 'ws-456')}
 * ```
 */
export function usePrefetchAgentLifecycle() {
  const queryClient = useQueryClient();

  return (
    agentId: string,
    workspaceId: string,
    timeframe: LifecycleTimeframe = 'all'
  ) => {
    return queryClient.prefetchQuery({
      queryKey: ['agentLifecycle', agentId, workspaceId, timeframe, false, true, true, true],
      queryFn: async () => {
        const response = await apiClient.get<AgentLifecycleAnalytics>(
          `/api/v1/agents/${agentId}/lifecycle`,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
            },
          }
        );
        return response.data;
      },
      staleTime: 60 * 1000,
    });
  };
}

/**
 * Hook to prefetch lifecycle status
 */
export function usePrefetchLifecycleStatus() {
  const queryClient = useQueryClient();

  return (agentId: string, workspaceId: string) => {
    return queryClient.prefetchQuery({
      queryKey: ['lifecycleStatus', agentId, workspaceId],
      queryFn: async () => {
        const response = await apiClient.get<LifecycleStatusResponse>(
          `/api/v1/agents/${agentId}/lifecycle/status`,
          {
            params: {
              workspace_id: workspaceId,
            },
          }
        );
        return response.data;
      },
      staleTime: 30 * 1000,
    });
  };
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to invalidate lifecycle-related queries
 *
 * Useful for manually triggering data refresh
 */
export function useInvalidateLifecycleQueries() {
  const queryClient = useQueryClient();

  return (agentId: string) => {
    queryClient.invalidateQueries({
      queryKey: ['agentLifecycle', agentId],
    });
    queryClient.invalidateQueries({
      queryKey: ['lifecycleStatus', agentId],
    });
    queryClient.invalidateQueries({
      queryKey: ['lifecycleTransitions', agentId],
    });
  };
}

/**
 * Simplified hook for common use case
 */
export function useAgentLifecycleSimple(
  agentId: string,
  workspaceId: string,
  timeframe: LifecycleTimeframe = '30d'
) {
  return useAgentLifecycle({
    agentId,
    workspaceId,
    timeframe,
    includeVersions: true,
    includeDeployments: true,
    includeHealth: true,
  });
}
