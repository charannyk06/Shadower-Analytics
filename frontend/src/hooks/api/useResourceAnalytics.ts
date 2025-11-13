/**
 * Resource Analytics API Hooks
 * Hooks for fetching resource utilization, cost optimization, and efficiency metrics
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import {
  ResourceUsage,
  ResourceAnalytics,
  TokenAnalysisResponse,
  CostOptimization,
  WasteSummary,
  ForecastResponse,
  WorkspaceCostAnalysis,
  EfficiencyLeaderboard,
  TimeFrame,
  OptimizationRecommendation,
} from '@/types/resource-analytics';
import { apiClient } from '@/lib/api/client';

// ============================================================================
// Resource Usage Hooks
// ============================================================================
export interface UseResourceUsageOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: TimeFrame;
  granularity?: 'hourly' | 'daily' | 'weekly';
  resourceTypes?: string[];
  enabled?: boolean;
}

/**
 * Hook to fetch comprehensive resource usage metrics for an agent
 */
export function useResourceUsage(
  options: UseResourceUsageOptions
): UseQueryResult<ResourceUsage, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    granularity = 'daily',
    resourceTypes,
    enabled = true,
  } = options;

  return useQuery<ResourceUsage, Error>({
    queryKey: ['resourceUsage', agentId, workspaceId, timeframe, granularity, resourceTypes],
    queryFn: async () => {
      const response = await apiClient.get<ResourceUsage>(
        `/api/v1/resources/agents/${agentId}/usage`,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
            granularity,
            resource_types: resourceTypes,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// ============================================================================
// Comprehensive Analytics Hooks
// ============================================================================
export interface UseResourceAnalyticsOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: TimeFrame;
  enabled?: boolean;
}

/**
 * Hook to fetch comprehensive resource analytics including optimization and forecasting
 */
export function useResourceAnalytics(
  options: UseResourceAnalyticsOptions
): UseQueryResult<ResourceAnalytics, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    enabled = true,
  } = options;

  return useQuery<ResourceAnalytics, Error>({
    queryKey: ['resourceAnalytics', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<ResourceAnalytics>(
        `/api/v1/resources/agents/${agentId}/analytics`,
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
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
}

// ============================================================================
// Token Analysis Hooks
// ============================================================================
export interface UseTokenAnalysisOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: TimeFrame;
  enabled?: boolean;
}

/**
 * Hook to fetch detailed token usage analysis
 */
export function useTokenAnalysis(
  options: UseTokenAnalysisOptions
): UseQueryResult<TokenAnalysisResponse, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    enabled = true,
  } = options;

  return useQuery<TokenAnalysisResponse, Error>({
    queryKey: ['tokenAnalysis', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<TokenAnalysisResponse>(
        `/api/v1/resources/agents/${agentId}/token-analysis`,
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
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 2,
  });
}

// ============================================================================
// Cost Optimization Hooks
// ============================================================================
export interface UseCostOptimizationOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: '7d' | '30d' | '90d';
  enabled?: boolean;
}

/**
 * Hook to fetch cost optimization recommendations
 */
export function useCostOptimization(
  options: UseCostOptimizationOptions
): UseQueryResult<CostOptimization, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '30d',
    enabled = true,
  } = options;

  return useQuery<CostOptimization, Error>({
    queryKey: ['costOptimization', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<CostOptimization>(
        `/api/v1/resources/agents/${agentId}/cost-optimization`,
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
    staleTime: 10 * 60 * 1000, // 10 minutes (changes less frequently)
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
  });
}

// ============================================================================
// Waste Detection Hooks
// ============================================================================
export interface UseWasteDetectionOptions {
  agentId: string;
  workspaceId: string;
  timeframe?: TimeFrame;
  enabled?: boolean;
}

/**
 * Hook to fetch resource waste detection
 */
export function useWasteDetection(
  options: UseWasteDetectionOptions
): UseQueryResult<WasteSummary, Error> {
  const {
    agentId,
    workspaceId,
    timeframe = '7d',
    enabled = true,
  } = options;

  return useQuery<WasteSummary, Error>({
    queryKey: ['wasteDetection', agentId, workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<WasteSummary>(
        `/api/v1/resources/agents/${agentId}/waste-detection`,
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
    staleTime: 5 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    retry: 2,
  });
}

// ============================================================================
// Forecasting Hooks
// ============================================================================
export interface UseForecastOptions {
  agentId: string;
  workspaceId: string;
  horizonDays?: number;
  includeCostProjection?: boolean;
  enabled?: boolean;
}

/**
 * Hook to fetch resource usage forecasts
 */
export function useResourceForecast(
  options: UseForecastOptions
): UseQueryResult<ForecastResponse, Error> {
  const {
    agentId,
    workspaceId,
    horizonDays = 30,
    includeCostProjection = true,
    enabled = true,
  } = options;

  return useQuery<ForecastResponse, Error>({
    queryKey: ['resourceForecast', agentId, workspaceId, horizonDays, includeCostProjection],
    queryFn: async () => {
      const response = await apiClient.get<ForecastResponse>(
        `/api/v1/resources/agents/${agentId}/forecast`,
        {
          params: {
            workspace_id: workspaceId,
            horizon_days: horizonDays,
            include_cost_projection: includeCostProjection,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!agentId && !!workspaceId,
    staleTime: 60 * 60 * 1000, // 1 hour (forecasts change less frequently)
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    retry: 2,
  });
}

// ============================================================================
// Workspace-Level Hooks
// ============================================================================
export interface UseWorkspaceCostAnalysisOptions {
  workspaceId: string;
  period?: 'day' | 'week' | 'month' | 'quarter';
  breakdownBy?: 'agent' | 'category' | 'model';
  enabled?: boolean;
}

/**
 * Hook to fetch workspace-wide cost analysis
 */
export function useWorkspaceCostAnalysis(
  options: UseWorkspaceCostAnalysisOptions
): UseQueryResult<WorkspaceCostAnalysis, Error> {
  const {
    workspaceId,
    period = 'month',
    breakdownBy = 'agent',
    enabled = true,
  } = options;

  return useQuery<WorkspaceCostAnalysis, Error>({
    queryKey: ['workspaceCostAnalysis', workspaceId, period, breakdownBy],
    queryFn: async () => {
      const response = await apiClient.get<WorkspaceCostAnalysis>(
        `/api/v1/resources/workspace/${workspaceId}/cost-analysis`,
        {
          params: {
            period,
            breakdown_by: breakdownBy,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
  });
}

// ============================================================================
// Efficiency Leaderboard Hooks
// ============================================================================
export interface UseEfficiencyLeaderboardOptions {
  workspaceId: string;
  metric?: 'overall' | 'cost' | 'tokens' | 'performance';
  limit?: number;
  enabled?: boolean;
}

/**
 * Hook to fetch efficiency leaderboard
 */
export function useEfficiencyLeaderboard(
  options: UseEfficiencyLeaderboardOptions
): UseQueryResult<EfficiencyLeaderboard, Error> {
  const {
    workspaceId,
    metric = 'overall',
    limit = 10,
    enabled = true,
  } = options;

  return useQuery<EfficiencyLeaderboard, Error>({
    queryKey: ['efficiencyLeaderboard', workspaceId, metric, limit],
    queryFn: async () => {
      const response = await apiClient.get<EfficiencyLeaderboard>(
        `/api/v1/resources/workspace/${workspaceId}/efficiency-leaderboard`,
        {
          params: {
            metric,
            limit,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
  });
}

// ============================================================================
// Optimization Mutation Hooks
// ============================================================================
export interface OptimizeResourcesRequest {
  agentId: string;
  workspaceId: string;
  optimizationGoals?: string[];
  constraints?: Record<string, any>;
}

export interface OptimizeResourcesResponse {
  agentId: string;
  optimizationGoals: string[];
  recommendations: OptimizationRecommendation[];
  expectedSavings: number;
  status: string;
}

/**
 * Hook to trigger resource optimization
 */
export function useOptimizeResources() {
  const queryClient = useQueryClient();

  return useMutation<OptimizeResourcesResponse, Error, OptimizeResourcesRequest>({
    mutationFn: async (request) => {
      const response = await apiClient.post<OptimizeResourcesResponse>(
        `/api/v1/resources/agents/${request.agentId}/optimize`,
        request.constraints || {},
        {
          params: {
            workspace_id: request.workspaceId,
            optimization_goals: request.optimizationGoals || ['cost', 'performance'],
          },
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: ['costOptimization', data.agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['resourceAnalytics', data.agentId],
      });
    },
  });
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to prefetch resource usage for performance
 */
export function usePrefetchResourceUsage() {
  const queryClient = useQueryClient();

  return (agentId: string, workspaceId: string, timeframe: TimeFrame = '7d') => {
    return queryClient.prefetchQuery({
      queryKey: ['resourceUsage', agentId, workspaceId, timeframe, 'daily', undefined],
      queryFn: async () => {
        const response = await apiClient.get<ResourceUsage>(
          `/api/v1/resources/agents/${agentId}/usage`,
          {
            params: {
              workspace_id: workspaceId,
              timeframe,
              granularity: 'daily',
            },
          }
        );
        return response.data;
      },
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Hook to invalidate all resource analytics queries
 */
export function useInvalidateResourceAnalytics() {
  const queryClient = useQueryClient();

  return (agentId?: string, workspaceId?: string) => {
    if (agentId) {
      queryClient.invalidateQueries({
        queryKey: ['resourceUsage', agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['resourceAnalytics', agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['tokenAnalysis', agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['costOptimization', agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['wasteDetection', agentId],
      });
      queryClient.invalidateQueries({
        queryKey: ['resourceForecast', agentId],
      });
    }

    if (workspaceId) {
      queryClient.invalidateQueries({
        queryKey: ['workspaceCostAnalysis', workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: ['efficiencyLeaderboard', workspaceId],
      });
    }
  };
}
