/**
 * Trend Analysis API Hooks
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export type TimeFrame = '7d' | '30d' | '90d' | '1y';
export type MetricType = 'executions' | 'users' | 'credits' | 'errors' | 'success_rate' | 'revenue';

export interface TrendOverview {
  currentValue: number;
  previousValue: number;
  change: number;
  changePercentage: number;
  trend: 'increasing' | 'decreasing' | 'stable' | 'volatile';
  trendStrength: number;
  confidence: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  movingAverage: number;
  upperBound: number;
  lowerBound: number;
  isAnomaly: boolean;
}

export interface TimeSeriesStatistics {
  mean: number;
  median: number;
  stdDev: number;
  variance: number;
  skewness: number;
  kurtosis: number;
  autocorrelation: number;
}

export interface DecompositionPoint {
  timestamp: string;
  value: number | null;
  period?: string;
}

export interface Decomposition {
  trend: DecompositionPoint[];
  seasonal: DecompositionPoint[];
  residual: DecompositionPoint[];
  noise: number;
}

export interface Seasonality {
  detected: boolean;
  type: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | null;
  strength: number;
  peakPeriods: string[];
  lowPeriods: string[];
}

export interface GrowthPattern {
  type: 'linear' | 'exponential' | 'logarithmic' | 'polynomial';
  rate: number;
  acceleration: number;
  projectedGrowth: number;
}

export interface Cycle {
  period: number;
  amplitude: number;
  phase: number;
  significance: number;
}

export interface Patterns {
  seasonality: Seasonality;
  growth: GrowthPattern;
  cycles: Cycle[];
}

export interface PeriodData {
  start: string;
  end: string;
  value: number;
  avg: number;
}

export interface PeriodComparison {
  currentPeriod: PeriodData;
  previousPeriod: PeriodData;
  change: number;
  changePercentage: number;
}

export interface YearOverYear {
  currentYear: number;
  previousYear: number;
  change: number;
  changePercentage: number;
  monthlyComparison: Array<{
    month: string;
    current: number;
    previous: number;
    change: number;
  }>;
}

export interface Benchmarks {
  industryAverage: number;
  topPerformers: number;
  position: 'above' | 'below' | 'at';
  percentile: number;
}

export interface Comparisons {
  periodComparison: PeriodComparison;
  yearOverYear: YearOverYear;
  benchmarks: Benchmarks;
}

export interface Correlation {
  metric: string;
  correlation: number;
  lag: number;
  significance: number;
  relationship: 'positive' | 'negative' | 'none';
}

export interface ForecastPoint {
  timestamp: string;
  predicted: number;
  upper: number;
  lower: number;
  confidence: number;
}

export interface LongTermForecast {
  period: string;
  predicted: number;
  range: {
    optimistic: number;
    realistic: number;
    pessimistic: number;
  };
}

export interface ForecastAccuracy {
  mape: number;
  rmse: number;
  r2: number;
}

export interface Forecast {
  shortTerm: ForecastPoint[];
  longTerm: LongTermForecast[];
  accuracy: ForecastAccuracy;
}

export interface Insight {
  type: 'trend' | 'anomaly' | 'pattern' | 'correlation' | 'forecast';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  confidence: number;
  recommendation: string;
}

export interface TrendAnalysis {
  workspaceId: string;
  metric: string;
  timeframe: string;
  overview: TrendOverview;
  timeSeries: {
    data: TimeSeriesPoint[];
    statistics: TimeSeriesStatistics;
  };
  decomposition: Decomposition;
  patterns: Patterns;
  comparisons: Comparisons;
  correlations: Correlation[];
  forecast: Forecast;
  insights: Insight[];
  error?: string;
  message?: string;
}

export interface UseTrendAnalysisOptions {
  workspaceId: string;
  metric: MetricType;
  timeframe?: TimeFrame;
  enabled?: boolean;
}

/**
 * Hook to fetch comprehensive trend analysis
 */
export function useTrendAnalysis(
  options: UseTrendAnalysisOptions
): UseQueryResult<TrendAnalysis, Error> {
  const {
    workspaceId,
    metric,
    timeframe = '30d',
    enabled = true,
  } = options;

  return useQuery<TrendAnalysis, Error>({
    queryKey: ['trendAnalysis', workspaceId, metric, timeframe],
    queryFn: async () => {
      const response = await apiClient.get<TrendAnalysis>(
        `/api/v1/trends/${workspaceId}/${metric}`,
        {
          params: {
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId && !!metric,
    staleTime: 60 * 1000, // 1 minute (trend analysis is cached on backend)
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

/**
 * Hook to fetch trends overview for all metrics
 */
export function useTrendsOverview(
  workspaceId: string,
  timeframe: TimeFrame = '30d',
  enabled = true
): UseQueryResult<{ metrics: Record<MetricType, TrendOverview> }, Error> {
  return useQuery({
    queryKey: ['trendsOverview', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/trends/${workspaceId}/overview`,
        {
          params: {
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch metric forecast
 */
export function useMetricForecast(
  workspaceId: string,
  metric: MetricType,
  periods = 7,
  enabled = true
): UseQueryResult<{ forecast: ForecastPoint[]; accuracy: ForecastAccuracy }, Error> {
  return useQuery({
    queryKey: ['metricForecast', workspaceId, metric, periods],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/trends/${workspaceId}/${metric}/forecast`,
        {
          params: {
            periods,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId && !!metric,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch pattern analysis
 */
export function useMetricPatterns(
  workspaceId: string,
  metric: MetricType,
  timeframe: TimeFrame = '90d',
  enabled = true
): UseQueryResult<{ patterns: Patterns; insights: Insight[] }, Error> {
  return useQuery({
    queryKey: ['metricPatterns', workspaceId, metric, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/trends/${workspaceId}/${metric}/patterns`,
        {
          params: {
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId && !!metric,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch metric insights
 */
export function useMetricInsights(
  workspaceId: string,
  metric: MetricType,
  timeframe: TimeFrame = '30d',
  enabled = true
): UseQueryResult<{ insights: Insight[]; overview: TrendOverview }, Error> {
  return useQuery({
    queryKey: ['metricInsights', workspaceId, metric, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/trends/${workspaceId}/${metric}/insights`,
        {
          params: {
            timeframe,
          },
        }
      );
      return response.data;
    },
    enabled: enabled && !!workspaceId && !!metric,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to clear trend cache
 */
export function useClearTrendCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workspaceId,
      metric,
    }: {
      workspaceId: string;
      metric?: MetricType;
    }) => {
      const response = await apiClient.delete(
        `/api/v1/trends/${workspaceId}/cache`,
        {
          params: metric ? { metric } : undefined,
        }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate all trend queries for this workspace
      queryClient.invalidateQueries({
        queryKey: ['trendAnalysis', variables.workspaceId]
      });
      queryClient.invalidateQueries({
        queryKey: ['trendsOverview', variables.workspaceId]
      });
      queryClient.invalidateQueries({
        queryKey: ['metricForecast', variables.workspaceId]
      });
      queryClient.invalidateQueries({
        queryKey: ['metricPatterns', variables.workspaceId]
      });
      queryClient.invalidateQueries({
        queryKey: ['metricInsights', variables.workspaceId]
      });
    },
  });
}

/**
 * Hook to prefetch trend analysis data
 */
export function usePrefetchTrendAnalysis() {
  const queryClient = useQueryClient();

  return (
    workspaceId: string,
    metric: MetricType,
    timeframe: TimeFrame = '30d'
  ) => {
    return queryClient.prefetchQuery({
      queryKey: ['trendAnalysis', workspaceId, metric, timeframe],
      queryFn: async () => {
        const response = await apiClient.get<TrendAnalysis>(
          `/api/v1/trends/${workspaceId}/${metric}`,
          {
            params: {
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
