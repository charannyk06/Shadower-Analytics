/**
 * Agent Analytics API Hooks
 */

import { useQuery, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { AgentAnalytics, TimeFrame } from '@/types/agent-analytics';
import { apiClient } from '@/lib/api/client';

export interface UseAgentAnalyticsOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: TimeFrame;
  skipCache?: boolean;
  enabled?: boolean;
}

/**
 * Hook to fetch comprehensive agent analytics
 */
export function useAgentAnalytics(
  options: UseAgentAnalyticsOptions
): UseQueryResult<AgentAnalytics, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    skipCache = false,
    enabled = true,
  } = options;

  return useQuery<AgentAnalytics, Error>({
    queryKey: ['agentAnalytics', agentId, workspaceId, timeframe, skipCache],
    queryFn: async () => {
      const response = await apiClient.get<AgentAnalytics>(
        `/api/v1/agents/${agentId}/analytics`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            skip_cache: skipCache,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

/**
 * Hook to fetch agent analytics with simplified interface
 */
export function useAgent(
  agentId: string,
  workspaceId: string,
  timeframe: TimeFrame = '7d'
): UseQueryResult<AgentAnalytics, Error> {
  return useAgentAnalytics({ agentId, workspaceId, timeframe });
}

/**
 * Hook to prefetch agent analytics for performance
 */
export function usePrefetchAgentAnalytics() {
  const queryClient = useQueryClient();

  return (agentId: string, workspaceId: string, timeframe: TimeFrame = '7d') => {
    return queryClient.prefetchQuery({
      queryKey: ['agentAnalytics', agentId, workspaceId, timeframe, false],
      queryFn: async () => {
        const response = await apiClient.get<AgentAnalytics>(
          `/api/v1/agents/${agentId}/analytics`,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
              skip_cache: false,
            },
          }
        );
        return response.data;
      },
      staleTime: 60 * 1000,
    });
  };
}
