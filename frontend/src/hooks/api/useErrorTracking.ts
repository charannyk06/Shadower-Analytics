/**
 * Error Tracking API Hooks
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { ErrorTracking, TimeFrame, TrackErrorRequest, ResolveErrorRequest } from '@/types/error-tracking';
import { apiClient } from '@/lib/api/client';

export interface UseErrorTrackingOptions {
  workspaceId: string;
  timeframe?: TimeFrame;
  severityFilter?: string;
  enabled?: boolean;
}

/**
 * Hook to fetch error tracking data
 */
export function useErrorTracking(
  options: UseErrorTrackingOptions
): UseQueryResult<ErrorTracking, Error> {
  const {
    workspaceId,
    timeframe = '7d',
    severityFilter = 'all',
    enabled = true,
  } = options;

  return useQuery<ErrorTracking, Error>({
    queryKey: ['errorTracking', workspaceId, timeframe, severityFilter],
    queryFn: async () => {
      const response = await apiClient.get<ErrorTracking>(
        `/api/v1/errors/${workspaceId}`,
        {
          params: {
            timeframe,
            severity_filter: severityFilter !== 'all' ? severityFilter : undefined,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

/**
 * Hook to track a new error
 */
export function useTrackError(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (errorData: TrackErrorRequest) => {
      const response = await apiClient.post(
        `/api/v1/errors/${workspaceId}/track`,
        errorData
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate error tracking queries
      queryClient.invalidateQueries({ queryKey: ['errorTracking', workspaceId] });
    },
  });
}

/**
 * Hook to resolve an error
 */
export function useResolveError() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      errorId,
      resolutionData,
    }: {
      errorId: string;
      resolutionData: ResolveErrorRequest;
    }) => {
      const response = await apiClient.post(
        `/api/v1/errors/${errorId}/resolve`,
        resolutionData
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all error tracking queries
      queryClient.invalidateQueries({ queryKey: ['errorTracking'] });
    },
  });
}

/**
 * Hook to ignore an error
 */
export function useIgnoreError() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (errorId: string) => {
      const response = await apiClient.post(`/api/v1/errors/${errorId}/ignore`);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all error tracking queries
      queryClient.invalidateQueries({ queryKey: ['errorTracking'] });
    },
  });
}

/**
 * Hook to prefetch error tracking data
 */
export function usePrefetchErrorTracking() {
  const queryClient = useQueryClient();

  return (workspaceId: string, timeframe: TimeFrame = '7d') => {
    return queryClient.prefetchQuery({
      queryKey: ['errorTracking', workspaceId, timeframe, 'all'],
      queryFn: async () => {
        const response = await apiClient.get<ErrorTracking>(
          `/api/v1/errors/${workspaceId}`,
          {
            params: {
              timeframe,
            },
          }
        );
        return response.data;
      },
      staleTime: 30 * 1000,
    });
  };
}
