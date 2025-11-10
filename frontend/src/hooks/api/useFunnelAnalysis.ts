/**
 * Funnel Analysis API Hooks
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import {
  FunnelDefinition,
  FunnelDefinitionCreate,
  FunnelDefinitionUpdate,
  FunnelDefinitionListResponse,
  FunnelAnalysisResult,
  FunnelPerformanceSummaryResponse,
  UserFunnelJourneysResponse,
  FunnelTimeframe,
  JourneyStatus,
} from '@/types/funnel-analysis';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';

// ===================================================================
// FUNNEL DEFINITIONS
// ===================================================================

export interface UseFunnelDefinitionsOptions {
  workspaceId: string;
  status?: string;
  enabled?: boolean;
}

/**
 * Hook to fetch all funnel definitions for a workspace
 */
export function useFunnelDefinitions(
  options: UseFunnelDefinitionsOptions
): UseQueryResult<FunnelDefinitionListResponse, Error> {
  const { workspaceId, status, enabled = true } = options;

  return useQuery<FunnelDefinitionListResponse, Error>({
    queryKey: ['funnelDefinitions', workspaceId, status],
    queryFn: async () => {
      const response = await apiClient.get<FunnelDefinitionListResponse>(
        endpoints.funnelDefinitions,
        {
          params: {
            workspace_id: workspaceId,
            status,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch a specific funnel definition
 */
export function useFunnelDefinition(
  funnelId: string,
  workspaceId: string,
  enabled: boolean = true
): UseQueryResult<FunnelDefinition, Error> {
  return useQuery<FunnelDefinition, Error>({
    queryKey: ['funnelDefinition', funnelId, workspaceId],
    queryFn: async () => {
      const response = await apiClient.get<FunnelDefinition>(
        endpoints.funnelDefinition(funnelId),
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!funnelId && !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
}

/**
 * Hook to create a new funnel definition
 */
export function useCreateFunnelDefinition() {
  const queryClient = useQueryClient();

  return useMutation<
    FunnelDefinition,
    Error,
    { workspaceId: string; data: FunnelDefinitionCreate }
  >({
    mutationFn: async ({ workspaceId, data }) => {
      const response = await apiClient.post<FunnelDefinition>(
        endpoints.funnelDefinitions,
        data,
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate funnel definitions list
      queryClient.invalidateQueries({
        queryKey: ['funnelDefinitions', variables.workspaceId],
      });
    },
  });
}

/**
 * Hook to update a funnel definition
 */
export function useUpdateFunnelDefinition() {
  const queryClient = useQueryClient();

  return useMutation<
    FunnelDefinition,
    Error,
    { funnelId: string; workspaceId: string; updates: FunnelDefinitionUpdate }
  >({
    mutationFn: async ({ funnelId, workspaceId, updates }) => {
      const response = await apiClient.patch<FunnelDefinition>(
        endpoints.funnelDefinition(funnelId),
        updates,
        {
          params: {
            workspace_id: workspaceId,
          },
        }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate specific funnel definition
      queryClient.invalidateQueries({
        queryKey: ['funnelDefinition', variables.funnelId],
      });
      // Invalidate funnel definitions list
      queryClient.invalidateQueries({
        queryKey: ['funnelDefinitions', variables.workspaceId],
      });
    },
  });
}

// ===================================================================
// FUNNEL ANALYSIS
// ===================================================================

export interface UseFunnelAnalysisOptions {
  funnelId: string;
  workspaceId: string;
  startDate?: string;
  endDate?: string;
  segmentName?: string;
  enabled?: boolean;
}

/**
 * Hook to analyze a funnel
 */
export function useFunnelAnalysis(
  options: UseFunnelAnalysisOptions
): UseQueryResult<FunnelAnalysisResult, Error> {
  const {
    funnelId,
    workspaceId,
    startDate,
    endDate,
    segmentName,
    enabled = true,
  } = options;

  return useQuery<FunnelAnalysisResult, Error>({
    queryKey: ['funnelAnalysis', funnelId, workspaceId, startDate, endDate, segmentName],
    queryFn: async () => {
      const response = await apiClient.post<FunnelAnalysisResult>(
        endpoints.funnelAnalyze(funnelId),
        null,
        {
          params: {
            workspace_id: workspaceId,
            start_date: startDate,
            end_date: endDate,
            segment_name: segmentName,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!funnelId && !!workspaceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

/**
 * Hook to trigger funnel analysis (mutation)
 */
export function useAnalyzeFunnel() {
  const queryClient = useQueryClient();

  return useMutation<
    FunnelAnalysisResult,
    Error,
    {
      funnelId: string;
      workspaceId: string;
      startDate?: string;
      endDate?: string;
      segmentName?: string;
    }
  >({
    mutationFn: async ({ funnelId, workspaceId, startDate, endDate, segmentName }) => {
      const response = await apiClient.post<FunnelAnalysisResult>(
        endpoints.funnelAnalyze(funnelId),
        null,
        {
          params: {
            workspace_id: workspaceId,
            start_date: startDate,
            end_date: endDate,
            segment_name: segmentName,
          },
        }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate funnel analysis cache
      queryClient.invalidateQueries({
        queryKey: ['funnelAnalysis', variables.funnelId],
      });
      // Invalidate performance summary
      queryClient.invalidateQueries({
        queryKey: ['funnelPerformanceSummary', variables.workspaceId],
      });
    },
  });
}

// ===================================================================
// USER JOURNEYS
// ===================================================================

export interface UseFunnelJourneysOptions {
  funnelId: string;
  workspaceId: string;
  status?: JourneyStatus;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

/**
 * Hook to fetch user journeys through a funnel
 */
export function useFunnelJourneys(
  options: UseFunnelJourneysOptions
): UseQueryResult<UserFunnelJourneysResponse, Error> {
  const {
    funnelId,
    workspaceId,
    status,
    limit = 100,
    offset = 0,
    enabled = true,
  } = options;

  return useQuery<UserFunnelJourneysResponse, Error>({
    queryKey: ['funnelJourneys', funnelId, workspaceId, status, limit, offset],
    queryFn: async () => {
      const response = await apiClient.get<UserFunnelJourneysResponse>(
        endpoints.funnelJourneys(funnelId),
        {
          params: {
            workspace_id: workspaceId,
            status,
            limit,
            offset,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!funnelId && !!workspaceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// ===================================================================
// PERFORMANCE SUMMARY
// ===================================================================

export interface UseFunnelPerformanceSummaryOptions {
  workspaceId: string;
  timeframe?: FunnelTimeframe;
  enabled?: boolean;
}

/**
 * Hook to fetch funnel performance summary
 */
export function useFunnelPerformanceSummary(
  options: UseFunnelPerformanceSummaryOptions
): UseQueryResult<FunnelPerformanceSummaryResponse, Error> {
  const { workspaceId, timeframe = '30d', enabled = true } = options;

  return useQuery<FunnelPerformanceSummaryResponse, Error>({
    queryKey: ['funnelPerformanceSummary', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<FunnelPerformanceSummaryResponse>(
        endpoints.funnelPerformanceSummary,
        {
          params: {
            workspace_id: workspaceId,
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
}
