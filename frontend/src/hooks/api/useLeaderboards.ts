/**
 * Leaderboards API Hooks
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import {
  AgentLeaderboardResponse,
  UserLeaderboardResponse,
  WorkspaceLeaderboardResponse,
  MyAgentRankResponse,
  TimeFrame,
  AgentCriteria,
  UserCriteria,
  WorkspaceCriteria,
} from '@/types/leaderboards';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';

// ===================================================================
// AGENT LEADERBOARD
// ===================================================================

export interface UseAgentLeaderboardOptions {
  workspaceId: string;
  timeframe?: TimeFrame;
  criteria?: AgentCriteria;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

/**
 * Hook to fetch agent leaderboard
 */
export function useAgentLeaderboard(
  options: UseAgentLeaderboardOptions
): UseQueryResult<AgentLeaderboardResponse, Error> {
  const {
    workspaceId,
    timeframe = '7d',
    criteria = 'success_rate',
    limit = 100,
    offset = 0,
    enabled = true,
  } = options;

  return useQuery<AgentLeaderboardResponse, Error>({
    queryKey: ['agentLeaderboard', workspaceId, timeframe, criteria, limit, offset],
    queryFn: async () => {
      const response = await apiClient.get<AgentLeaderboardResponse>(
        endpoints.agentLeaderboard,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            criteria,
            limit,
            offset,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch my agent's rank
 */
export function useMyAgentRank(
  agentId: string,
  workspaceId: string,
  timeframe: TimeFrame = '7d',
  criteria: AgentCriteria = 'success_rate'
): UseQueryResult<MyAgentRankResponse, Error> {
  return useQuery<MyAgentRankResponse, Error>({
    queryKey: ['myAgentRank', agentId, workspaceId, timeframe, criteria],
    queryFn: async () => {
      const response = await apiClient.get<MyAgentRankResponse>(
        endpoints.myAgentRank(agentId),
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            criteria,
          },
        }
      );
      return response.data;
    },
    enabled: !!agentId && !!workspaceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// ===================================================================
// USER LEADERBOARD
// ===================================================================

export interface UseUserLeaderboardOptions {
  workspaceId: string;
  timeframe?: TimeFrame;
  criteria?: UserCriteria;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

/**
 * Hook to fetch user leaderboard
 */
export function useUserLeaderboard(
  options: UseUserLeaderboardOptions
): UseQueryResult<UserLeaderboardResponse, Error> {
  const {
    workspaceId,
    timeframe = '7d',
    criteria = 'activity',
    limit = 100,
    offset = 0,
    enabled = true,
  } = options;

  return useQuery<UserLeaderboardResponse, Error>({
    queryKey: ['userLeaderboard', workspaceId, timeframe, criteria, limit, offset],
    queryFn: async () => {
      const response = await apiClient.get<UserLeaderboardResponse>(
        endpoints.userLeaderboard,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            criteria,
            limit,
            offset,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// ===================================================================
// WORKSPACE LEADERBOARD
// ===================================================================

export interface UseWorkspaceLeaderboardOptions {
  timeframe?: TimeFrame;
  criteria?: WorkspaceCriteria;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

/**
 * Hook to fetch workspace leaderboard
 */
export function useWorkspaceLeaderboard(
  options: UseWorkspaceLeaderboardOptions = {}
): UseQueryResult<WorkspaceLeaderboardResponse, Error> {
  const {
    timeframe = '7d',
    criteria = 'activity',
    limit = 100,
    offset = 0,
    enabled = true,
  } = options;

  return useQuery<WorkspaceLeaderboardResponse, Error>({
    queryKey: ['workspaceLeaderboard', timeframe, criteria, limit, offset],
    queryFn: async () => {
      const response = await apiClient.get<WorkspaceLeaderboardResponse>(
        endpoints.workspaceLeaderboard,
        {
          params: {
            timeframe,
            criteria,
            limit,
            offset,
          },
        }
      );
      return response.data;
    },
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// ===================================================================
// MUTATIONS
// ===================================================================

/**
 * Hook to refresh leaderboards
 */
export function useRefreshLeaderboards() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (workspaceId: string) => {
      const response = await apiClient.post(
        endpoints.refreshLeaderboards(workspaceId)
      );
      return response.data;
    },
    onSuccess: (_, workspaceId) => {
      // Invalidate all leaderboard queries for this workspace
      queryClient.invalidateQueries({ queryKey: ['agentLeaderboard', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['userLeaderboard', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['workspaceLeaderboard'] });
    },
  });
}

// ===================================================================
// PREFETCH UTILITIES
// ===================================================================

/**
 * Hook to prefetch agent leaderboard for performance
 */
export function usePrefetchAgentLeaderboard() {
  const queryClient = useQueryClient();

  return (
    workspaceId: string,
    timeframe: TimeFrame = '7d',
    criteria: AgentCriteria = 'success_rate'
  ) => {
    return queryClient.prefetchQuery({
      queryKey: ['agentLeaderboard', workspaceId, timeframe, criteria, 100, 0],
      queryFn: async () => {
        const response = await apiClient.get<AgentLeaderboardResponse>(
          endpoints.agentLeaderboard,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
              criteria,
              limit: 100,
              offset: 0,
            },
          }
        );
        return response.data;
      },
      staleTime: 2 * 60 * 1000,
    });
  };
}

/**
 * Hook to prefetch user leaderboard for performance
 */
export function usePrefetchUserLeaderboard() {
  const queryClient = useQueryClient();

  return (
    workspaceId: string,
    timeframe: TimeFrame = '7d',
    criteria: UserCriteria = 'activity'
  ) => {
    return queryClient.prefetchQuery({
      queryKey: ['userLeaderboard', workspaceId, timeframe, criteria, 100, 0],
      queryFn: async () => {
        const response = await apiClient.get<UserLeaderboardResponse>(
          endpoints.userLeaderboard,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
              criteria,
              limit: 100,
              offset: 0,
            },
          }
        );
        return response.data;
      },
      staleTime: 2 * 60 * 1000,
    });
  };
}
