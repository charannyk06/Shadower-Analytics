/**
 * Trend Analysis React Hook
 *
 * Custom hook for fetching and managing trend analysis data
 */

import { useQuery, useQueryClient, useQueries, UseQueryOptions } from '@tanstack/react-query';
import apiClient from '@/lib/api/client';
import type {
  TrendAnalysis,
  TrendAnalysisParams,
  TimeFrame,
  AvailableMetric
} from '@/types/trend-analysis';

/**
 * API endpoint for trend analysis
 */
const TREND_ANALYSIS_ENDPOINT = '/api/v1/metrics/trends/analysis';

/**
 * Fetch trend analysis data from the API
 */
async function fetchTrendAnalysis(
  params: TrendAnalysisParams
): Promise<TrendAnalysis> {
  const response = await apiClient.get<TrendAnalysis>(TREND_ANALYSIS_ENDPOINT, {
    params: {
      workspace_id: params.workspaceId,
      metric: params.metric,
      timeframe: params.timeframe
    }
  });

  return response.data;
}

/**
 * Hook for fetching trend analysis data
 *
 * @param workspaceId - Workspace to analyze
 * @param metric - Metric to analyze (executions, users, credits, etc.)
 * @param timeframe - Time window (7d, 30d, 90d, 1y)
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useTrendAnalysis(
 *   'workspace-123',
 *   'executions',
 *   '30d'
 * );
 * ```
 */
export function useTrendAnalysis(
  workspaceId: string,
  metric: AvailableMetric,
  timeframe: TimeFrame = '30d',
  options?: Omit<UseQueryOptions<TrendAnalysis>, 'queryKey' | 'queryFn'>
) {
  return useQuery<TrendAnalysis>({
    queryKey: ['trend-analysis', workspaceId, metric, timeframe],
    queryFn: () => fetchTrendAnalysis({ workspaceId, metric, timeframe }),
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    cacheTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    retry: 2,
    enabled: !!workspaceId && !!metric,
    ...options
  });
}

/**
 * Hook for prefetching trend analysis data
 *
 * Useful for preloading data before user interaction
 *
 * @example
 * ```tsx
 * const prefetchTrendAnalysis = usePrefetchTrendAnalysis();
 *
 * // Prefetch on hover
 * <button
 *   onMouseEnter={() => prefetchTrendAnalysis('workspace-123', 'executions', '30d')}
 * >
 *   View Trends
 * </button>
 * ```
 */
export function usePrefetchTrendAnalysis() {
  const queryClient = useQueryClient();

  return (
    workspaceId: string,
    metric: AvailableMetric,
    timeframe: TimeFrame = '30d'
  ) => {
    queryClient.prefetchQuery({
      queryKey: ['trend-analysis', workspaceId, metric, timeframe],
      queryFn: () => fetchTrendAnalysis({ workspaceId, metric, timeframe }),
      staleTime: 5 * 60 * 1000
    });
  };
}

/**
 * Hook for invalidating trend analysis cache
 *
 * Useful when data is updated and cache needs to be refreshed
 *
 * @example
 * ```tsx
 * const invalidateTrends = useInvalidateTrendAnalysis();
 *
 * // Invalidate after data update
 * const handleUpdate = async () => {
 *   await updateData();
 *   invalidateTrends('workspace-123');
 * };
 * ```
 */
export function useInvalidateTrendAnalysis() {
  const queryClient = useQueryClient();

  return (workspaceId?: string, metric?: AvailableMetric, timeframe?: TimeFrame) => {
    const queryKey = ['trend-analysis'];

    if (workspaceId) queryKey.push(workspaceId);
    if (metric) queryKey.push(metric);
    if (timeframe) queryKey.push(timeframe);

    return queryClient.invalidateQueries({ queryKey });
  };
}

/**
 * Hook for fetching multiple trend analyses in parallel
 *
 * Useful for comparing different metrics or timeframes
 *
 * @example
 * ```tsx
 * const analyses = useMultipleTrendAnalyses([
 *   { workspaceId: 'ws-123', metric: 'executions', timeframe: '30d' },
 *   { workspaceId: 'ws-123', metric: 'users', timeframe: '30d' },
 * ]);
 * ```
 */
export function useMultipleTrendAnalyses(
  params: TrendAnalysisParams[]
) {
  return useQueries({
    queries: params.map(param => ({
      queryKey: ['trend-analysis', param.workspaceId, param.metric, param.timeframe],
      queryFn: () => fetchTrendAnalysis(param),
      staleTime: 5 * 60 * 1000,
      cacheTime: 30 * 60 * 1000,
      retry: 2,
      enabled: !!param.workspaceId && !!param.metric
    }))
  });
}

// Re-export types for convenience
export type {
  TrendAnalysis,
  TrendAnalysisParams,
  TimeFrame,
  AvailableMetric
} from '@/types/trend-analysis';
