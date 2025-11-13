/**
 * React Query hooks for Predictive Analytics API
 *
 * Author: Claude Code
 * Date: 2025-11-12
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Types
export interface Prediction {
  date: string;
  predicted_value: number;
  confidence_lower: number;
  confidence_upper: number;
  confidence_level?: number;
}

export interface CreditConsumptionPrediction {
  workspace_id: string;
  prediction_type: string;
  granularity: string;
  days_ahead: number;
  predictions: Prediction[];
  insights: {
    summary: {
      historical_daily_avg: number;
      predicted_daily_avg: number;
      trend_percentage: number;
      trend_direction: string;
      total_predicted_consumption: number;
    };
    peak_usage: {
      date: string;
      predicted_credits: number;
    };
    recommendations: string[];
  };
  model_version: string;
  generated_at: string;
}

export interface ChurnPrediction {
  workspace_id: string;
  total_users: number;
  high_risk_users: number;
  predictions: Array<{
    user_id: string;
    churn_probability: number;
    risk_score: number;
    risk_level: string;
    risk_factors: Array<{
      factor: string;
      severity: string;
      description: string;
      impact: number;
    }>;
    recommended_actions: string[];
    days_until_churn: number;
  }>;
  risk_analysis: {
    risk_distribution: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
    statistics: {
      average_churn_probability: number;
      median_churn_probability: number;
      at_risk_percentage: number;
    };
  };
}

export interface GrowthPrediction {
  workspace_id: string;
  metric: string;
  horizon_days: number;
  base_predictions: Prediction[];
  scenarios: {
    optimistic: Prediction[];
    base: Prediction[];
    pessimistic: Prediction[];
  };
  milestones: Array<{
    target_value: number;
    growth_percentage: number;
    expected_date: string;
    confidence: string;
  }>;
  insights: {
    current_value: number;
    predicted_avg: number;
    growth_rate: number;
    trend: string;
    trend_description: string;
    recommendations: string[];
  };
}

export interface PeakUsagePrediction {
  workspace_id: string;
  granularity: string;
  days_ahead: number;
  predictions: Array<{
    timestamp: string;
    predicted_executions: number;
    confidence_lower: number;
    confidence_upper: number;
    hour?: number;
    day_of_week: number;
  }>;
  peak_times: {
    peak_timestamp: string;
    peak_executions: number;
    peak_hours?: number[];
    peak_days: string[];
  };
  capacity_recommendations: {
    current_peak_capacity: number;
    predicted_peak_usage: number;
    recommended_capacity: number;
    capacity_increase_needed: number;
    scaling_recommendation: string;
  };
}

export interface ErrorRatePrediction {
  workspace_id: string;
  days_ahead: number;
  predictions: Array<{
    date: string;
    predicted_error_rate: number;
    confidence_lower: number;
    confidence_upper: number;
    severity: string;
  }>;
  anomalies: Array<{
    date?: string;
    predicted_error_rate?: number;
    baseline?: number;
    severity?: string;
    type?: string;
    description?: string;
  }>;
  alerts: Array<{
    type: string;
    severity: string;
    message: string;
    action_required: boolean;
  }>;
  patterns: {
    day_of_week_patterns: Record<string, number>;
    worst_day: string;
    trends: {
      '7_day_avg': number;
      '30_day_avg': number;
      trend_direction: string;
    };
  };
  recommendations: string[];
}

/**
 * Hook to fetch credit consumption predictions
 */
export function useCreditConsumptionPrediction(
  workspaceId: string,
  daysAhead: number = 30,
  granularity: 'daily' | 'weekly' = 'daily'
) {
  return useQuery<CreditConsumptionPrediction>({
    queryKey: ['predictions', 'consumption', workspaceId, daysAhead, granularity],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/consumption/${workspaceId}`,
        {
          params: { days_ahead: daysAhead, granularity },
        }
      );
      return response.data;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    enabled: !!workspaceId,
  });
}

/**
 * Hook to fetch user churn predictions
 */
export function useChurnPrediction(
  workspaceId: string,
  riskThreshold: number = 0.7,
  limit: number = 100
) {
  return useQuery<ChurnPrediction>({
    queryKey: ['predictions', 'churn', workspaceId, riskThreshold, limit],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/churn/${workspaceId}`,
        {
          params: { risk_threshold: riskThreshold, limit },
        }
      );
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes (churn data changes frequently)
    gcTime: 30 * 60 * 1000, // 30 minutes
    enabled: !!workspaceId,
  });
}

/**
 * Hook to fetch growth metric predictions
 */
export function useGrowthPrediction(
  workspaceId: string,
  metric: 'dau' | 'wau' | 'mau' | 'mrr' | 'active_users' = 'dau',
  horizonDays: number = 90
) {
  return useQuery<GrowthPrediction>({
    queryKey: ['predictions', 'growth', workspaceId, metric, horizonDays],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/growth/${workspaceId}`,
        {
          params: { metric, horizon_days: horizonDays },
        }
      );
      return response.data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    enabled: !!workspaceId,
  });
}

/**
 * Hook to fetch peak usage predictions
 */
export function usePeakUsagePrediction(
  workspaceId: string,
  granularity: 'hourly' | 'daily' = 'hourly',
  daysAhead: number = 7
) {
  return useQuery<PeakUsagePrediction>({
    queryKey: ['predictions', 'peak-usage', workspaceId, granularity, daysAhead],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/peak-usage/${workspaceId}`,
        {
          params: { granularity, days_ahead: daysAhead },
        }
      );
      return response.data;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    enabled: !!workspaceId,
  });
}

/**
 * Hook to fetch error rate predictions
 */
export function useErrorRatePrediction(
  workspaceId: string,
  agentId?: string,
  daysAhead: number = 14
) {
  return useQuery<ErrorRatePrediction>({
    queryKey: ['predictions', 'error-rates', workspaceId, agentId, daysAhead],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/error-rates/${workspaceId}`,
        {
          params: { agent_id: agentId, days_ahead: daysAhead },
        }
      );
      return response.data;
    },
    staleTime: 20 * 60 * 1000, // 20 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    enabled: !!workspaceId,
  });
}

/**
 * Hook to generate custom prediction
 */
export function useGeneratePrediction(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      prediction_type: string;
      target_metric: string;
      horizon: number;
      parameters?: Record<string, any>;
    }) => {
      const response = await apiClient.post(
        `/api/v1/predictions/generate/${workspaceId}`,
        params
      );
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({
        queryKey: ['predictions', variables.prediction_type, workspaceId],
      });
    },
  });
}

/**
 * Hook to fetch prediction history
 */
export function usePredictionHistory(
  workspaceId: string,
  predictionType?: string,
  daysBack: number = 30
) {
  return useQuery({
    queryKey: ['predictions', 'history', workspaceId, predictionType, daysBack],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/history/${workspaceId}`,
        {
          params: {
            prediction_type: predictionType,
            days_back: daysBack,
          },
        }
      );
      return response.data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    enabled: !!workspaceId,
  });
}

/**
 * Hook to fetch prediction accuracy metrics
 */
export function usePredictionAccuracy(
  workspaceId: string,
  predictionType: string,
  daysBack: number = 30
) {
  return useQuery({
    queryKey: ['predictions', 'accuracy', workspaceId, predictionType, daysBack],
    queryFn: async () => {
      const response = await apiClient.get(
        `/api/v1/predictions/accuracy/${workspaceId}`,
        {
          params: {
            prediction_type: predictionType,
            days_back: daysBack,
          },
        }
      );
      return response.data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    enabled: !!workspaceId && !!predictionType,
  });
}
