/**
 * Comparison Views API Hooks
 * React hooks for fetching comparison data
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import {
  ComparisonResponse,
  ComparisonType,
  ComparisonFilters,
  ComparisonOptions,
} from '@/types/comparison-views';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// API Client Functions
// ============================================================================

async function fetchComparison(
  type: ComparisonType,
  filters: ComparisonFilters,
  options?: ComparisonOptions
): Promise<ComparisonResponse> {
  const response = await fetch(`${API_BASE}/api/v1/comparisons/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type,
      filters,
      options,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch comparison');
  }

  return response.json();
}

async function fetchAgentComparison(
  agentIds: string[],
  startDate?: string,
  endDate?: string,
  includeRecommendations = true,
  includeVisualDiff = true
): Promise<ComparisonResponse> {
  const params = new URLSearchParams();
  agentIds.forEach((id) => params.append('agent_ids', id));
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('include_recommendations', includeRecommendations.toString());
  params.append('include_visual_diff', includeVisualDiff.toString());

  const response = await fetch(
    `${API_BASE}/api/v1/comparisons/agents?${params}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch agent comparison');
  }

  return response.json();
}

async function fetchPeriodComparison(
  startDate?: string,
  endDate?: string,
  includeTimeSeries = true,
  workspaceIds?: string[],
  agentIds?: string[]
): Promise<ComparisonResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('include_time_series', includeTimeSeries.toString());
  if (workspaceIds) {
    workspaceIds.forEach((id) => params.append('workspace_ids', id));
  }
  if (agentIds) {
    agentIds.forEach((id) => params.append('agent_ids', id));
  }

  const response = await fetch(
    `${API_BASE}/api/v1/comparisons/periods?${params}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch period comparison');
  }

  return response.json();
}

async function fetchWorkspaceComparison(
  workspaceIds: string[],
  startDate?: string,
  endDate?: string,
  includeStatistics = true
): Promise<ComparisonResponse> {
  const params = new URLSearchParams();
  workspaceIds.forEach((id) => params.append('workspace_ids', id));
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('include_statistics', includeStatistics.toString());

  const response = await fetch(
    `${API_BASE}/api/v1/comparisons/workspaces?${params}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch workspace comparison');
  }

  return response.json();
}

async function fetchMetricComparison(
  metricName: string,
  startDate?: string,
  endDate?: string,
  includeCorrelations = false,
  includeStatistics = true,
  workspaceIds?: string[],
  agentIds?: string[]
): Promise<ComparisonResponse> {
  const params = new URLSearchParams();
  params.append('metric_name', metricName);
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('include_correlations', includeCorrelations.toString());
  params.append('include_statistics', includeStatistics.toString());
  if (workspaceIds) {
    workspaceIds.forEach((id) => params.append('workspace_ids', id));
  }
  if (agentIds) {
    agentIds.forEach((id) => params.append('agent_ids', id));
  }

  const response = await fetch(
    `${API_BASE}/api/v1/comparisons/metrics?${params}`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch metric comparison');
  }

  return response.json();
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Generic comparison hook
 */
export function useComparison(
  type: ComparisonType,
  filters: ComparisonFilters,
  options?: ComparisonOptions,
  enabled = true
): UseQueryResult<ComparisonResponse, Error> {
  return useQuery({
    queryKey: ['comparison', type, filters, options],
    queryFn: () => fetchComparison(type, filters, options),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Agent comparison hook
 */
export function useAgentComparison(
  agentIds: string[],
  startDate?: string,
  endDate?: string,
  includeRecommendations = true,
  includeVisualDiff = true
): UseQueryResult<ComparisonResponse, Error> {
  return useQuery({
    queryKey: [
      'comparison',
      'agents',
      agentIds,
      startDate,
      endDate,
      includeRecommendations,
      includeVisualDiff,
    ],
    queryFn: () =>
      fetchAgentComparison(
        agentIds,
        startDate,
        endDate,
        includeRecommendations,
        includeVisualDiff
      ),
    enabled: agentIds.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Period comparison hook
 */
export function usePeriodComparison(
  startDate?: string,
  endDate?: string,
  includeTimeSeries = true,
  workspaceIds?: string[],
  agentIds?: string[]
): UseQueryResult<ComparisonResponse, Error> {
  return useQuery({
    queryKey: [
      'comparison',
      'periods',
      startDate,
      endDate,
      includeTimeSeries,
      workspaceIds,
      agentIds,
    ],
    queryFn: () =>
      fetchPeriodComparison(
        startDate,
        endDate,
        includeTimeSeries,
        workspaceIds,
        agentIds
      ),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Workspace comparison hook
 */
export function useWorkspaceComparison(
  workspaceIds: string[],
  startDate?: string,
  endDate?: string,
  includeStatistics = true
): UseQueryResult<ComparisonResponse, Error> {
  return useQuery({
    queryKey: [
      'comparison',
      'workspaces',
      workspaceIds,
      startDate,
      endDate,
      includeStatistics,
    ],
    queryFn: () =>
      fetchWorkspaceComparison(workspaceIds, startDate, endDate, includeStatistics),
    enabled: workspaceIds.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Metric comparison hook
 */
export function useMetricComparison(
  metricName: string,
  startDate?: string,
  endDate?: string,
  includeCorrelations = false,
  includeStatistics = true,
  workspaceIds?: string[],
  agentIds?: string[]
): UseQueryResult<ComparisonResponse, Error> {
  return useQuery({
    queryKey: [
      'comparison',
      'metrics',
      metricName,
      startDate,
      endDate,
      includeCorrelations,
      includeStatistics,
      workspaceIds,
      agentIds,
    ],
    queryFn: () =>
      fetchMetricComparison(
        metricName,
        startDate,
        endDate,
        includeCorrelations,
        includeStatistics,
        workspaceIds,
        agentIds
      ),
    enabled: !!metricName,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Health check hook for comparison service
 */
export function useComparisonHealth(): UseQueryResult<
  { status: string; service: string; timestamp: string },
  Error
> {
  return useQuery({
    queryKey: ['comparison', 'health'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/v1/comparisons/health`);
      if (!response.ok) {
        throw new Error('Health check failed');
      }
      return response.json();
    },
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}
