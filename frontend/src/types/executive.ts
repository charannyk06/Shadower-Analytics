/**
 * Executive Dashboard Types
 * Comprehensive type definitions for executive dashboard data structures
 */

export type Timeframe = '24h' | '7d' | '30d' | '90d' | 'all'

export interface TimeSeriesData {
  timestamp: string
  value: number
  label?: string
  total?: number
  successful?: number
  failed?: number
}

export interface UserMetrics {
  dau: number
  dauChange: number
  wau: number
  wauChange: number
  mau: number
  mauChange: number
  newUsers: number
  churnedUsers: number
  activeRate: number
}

export interface ExecutionMetrics {
  totalRuns: number
  totalRunsChange: number
  successfulRuns: number
  failedRuns: number
  successRate: number
  successRateChange: number
  avgRuntime: number
  p95Runtime: number
  totalCreditsUsed: number
  creditsChange: number
}

export interface BusinessMetrics {
  mrr: number
  mrrChange: number
  arr: number
  ltv: number
  cac: number
  ltvCacRatio: number
  activeWorkspaces: number
  paidWorkspaces: number
  trialWorkspaces: number
  churnRate: number
}

export interface TopAgent {
  id: string
  name: string
  runs: number
  successRate: number
  avgRuntime: number
}

export interface AgentMetrics {
  totalAgents: number
  activeAgents: number
  topAgents: TopAgent[]
}

export interface TopUser {
  id: string
  name: string
  email: string
  totalRuns: number
  creditsUsed: number
  lastActive: string
}

export interface Alert {
  id: string
  type: string
  message: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  triggeredAt: string
}

export interface TrendData {
  execution: TimeSeriesData[]
  users: TimeSeriesData[]
  revenue: TimeSeriesData[]
  errors: TimeSeriesData[]
}

export interface Period {
  start: string
  end: string
}

export interface ExecutiveDashboardData {
  timeframe: Timeframe
  period: Period
  userMetrics: UserMetrics
  executionMetrics: ExecutionMetrics
  businessMetrics: BusinessMetrics
  agentMetrics: AgentMetrics
  trends: TrendData
  activeAlerts: Alert[]
  topUsers?: TopUser[]
}

export type MetricFormat = 'number' | 'currency' | 'percentage' | 'duration'

export interface MetricCardData {
  title: string
  value: number | string
  change?: number
  format?: MetricFormat
  description?: string
  trend?: 'up' | 'down' | 'neutral'
}
