/**
 * API endpoint definitions
 */

const API_VERSION = '/api/v1';

export const endpoints = {
  // Executive dashboard
  executiveOverview: `${API_VERSION}/executive/overview`,
  executiveDashboard: `${API_VERSION}/executive/dashboard`,
  revenue: `${API_VERSION}/executive/revenue`,
  kpis: `${API_VERSION}/executive/kpis`,

  // Agents
  agents: `${API_VERSION}/agents`,
  agentDetail: (id: string) => `${API_VERSION}/agents/${id}`,
  agentAnalytics: (id: string) => `${API_VERSION}/agents/${id}/analytics`,
  topAgents: `${API_VERSION}/agents/top`,

  // Users
  users: `${API_VERSION}/users`,
  userDetail: (id: string) => `${API_VERSION}/users/${id}`,
  userActivity: (id: string) => `${API_VERSION}/users/${id}/activity`,

  // Metrics
  metricsSummary: `${API_VERSION}/metrics/summary`,
  realtimeMetrics: `${API_VERSION}/metrics/realtime`,
  customMetrics: `${API_VERSION}/metrics/custom`,

  // Reports
  reports: `${API_VERSION}/reports`,
  reportDetail: (id: string) => `${API_VERSION}/reports/${id}`,
  generateReport: `${API_VERSION}/reports/generate`,

  // Workspaces
  workspaces: `${API_VERSION}/workspaces`,
  workspaceDetail: (id: string) => `${API_VERSION}/workspaces/${id}`,

  // Cache management (admin only)
  cacheStats: `${API_VERSION}/cache/stats`,
  cacheInvalidate: `${API_VERSION}/cache/invalidate`,
  cacheWarm: `${API_VERSION}/cache/warm`,
} as const;
