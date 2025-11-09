/**
 * React Query configuration and cache key factory
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

/**
 * Centralized cache key factory for consistent query key management
 */
export const queryKeys = {
  /**
   * Executive dashboard metrics
   */
  executive: (workspaceId: string, timeframe: string) => [
    'executive',
    workspaceId,
    timeframe,
  ] as const,

  /**
   * Revenue metrics
   */
  revenue: (workspaceId: string, timeframe: string) => [
    'revenue',
    workspaceId,
    timeframe,
  ] as const,

  /**
   * Key performance indicators
   */
  kpis: (workspaceId: string) => ['kpis', workspaceId] as const,

  /**
   * All agents in a workspace
   */
  agents: (workspaceId: string) => ['agents', workspaceId] as const,

  /**
   * Specific agent detail with analytics
   */
  agentDetail: (agentId: string, timeframe: string) => [
    'agent',
    agentId,
    timeframe,
  ] as const,

  /**
   * Top performing agents
   */
  topAgents: (workspaceId: string, timeframe: string, limit: number) => [
    'agents',
    'top',
    workspaceId,
    timeframe,
    limit,
  ] as const,

  /**
   * User list with filters
   */
  users: (workspaceId: string, filters: Record<string, any>) => [
    'users',
    workspaceId,
    filters,
  ] as const,

  /**
   * User activity
   */
  userActivity: (userId: string, date: string) => [
    'user',
    'activity',
    userId,
    date,
  ] as const,

  /**
   * Metrics by type
   */
  metrics: (type: string, params: Record<string, any>) => [
    'metrics',
    type,
    params,
  ] as const,

  /**
   * Real-time metrics (short cache time)
   */
  realtime: (workspaceId: string) => ['realtime', workspaceId] as const,

  /**
   * Reports
   */
  report: (reportId: string, format: string) => [
    'report',
    reportId,
    format,
  ] as const,

  /**
   * Workspace overview
   */
  workspace: (workspaceId: string) => ['workspace', workspaceId] as const,
};

/**
 * Cache time presets matching backend TTLs
 */
export const cacheTime = {
  SHORT: 1000 * 60 * 1, // 1 minute
  MEDIUM: 1000 * 60 * 5, // 5 minutes
  LONG: 1000 * 60 * 30, // 30 minutes
  HOUR: 1000 * 60 * 60, // 1 hour
  DAY: 1000 * 60 * 60 * 24, // 24 hours
};
