/**
 * Execution Metrics Types
 * Comprehensive type definitions for execution metrics tracking
 */

export type ExecutionTimeframe = '1h' | '6h' | '24h' | '7d' | '30d' | '90d'

export interface ExecutionInProgress {
  runId: string
  agentId: string
  agentName: string
  userId: string
  startedAt: string
  elapsedTime: number
  estimatedCompletion: string
}

export interface QueuedExecution {
  queueId: string
  agentId: string
  priority: number
  queuedAt: string
  estimatedStartTime: string | null
}

export interface SystemLoad {
  cpu: number
  memory: number
  workers: {
    total: number
    busy: number
    idle: number
  }
}

export interface RealtimeMetrics {
  currentlyRunning: number
  queueDepth: number
  avgQueueWaitTime: number
  executionsInProgress: ExecutionInProgress[]
  queuedExecutions: QueuedExecution[]
  systemLoad: SystemLoad
}

export interface ThroughputTrend {
  timestamp: string
  value: number
}

export interface PeakThroughput {
  value: number
  timestamp: string
}

export interface ThroughputMetrics {
  executionsPerMinute: number
  executionsPerHour: number
  executionsPerDay: number
  throughputTrend: ThroughputTrend[]
  peakThroughput: PeakThroughput
  capacityUtilization: number
  maxCapacity: number
}

export interface LatencyPercentiles {
  avg: number
  p50: number
  p75: number
  p90: number
  p95: number
  p99: number
}

export interface LatencyDistributionBucket {
  bucket: string
  count: number
  percentage: number
}

export interface LatencyMetrics {
  queueLatency: LatencyPercentiles
  executionLatency: LatencyPercentiles
  endToEndLatency: LatencyPercentiles
  latencyDistribution: LatencyDistributionBucket[]
}

export interface AgentPerformance {
  agentId: string
  agentName: string
  executions: number
  successRate: number
  avgRuntime: number
  errorRate: number
}

export interface HourlyPerformance {
  hour: number
  executions: number
  successRate: number
  avgLatency: number
}

export interface PeriodComparison {
  executionsChange: number
  successRateChange: number
  latencyChange: number
}

export interface PerformanceMetrics {
  totalExecutions: number
  successfulExecutions: number
  failedExecutions: number
  cancelledExecutions: number
  successRate: number
  failureRate: number
  cancellationRate: number
  byAgent: AgentPerformance[]
  byHour: HourlyPerformance[]
  vsLastPeriod: PeriodComparison
}

export interface ExecutionTimelinePoint {
  timestamp: string
  executions: number
  successRate: number
  avgDuration: number
}

export interface ExecutionBurst {
  startTime: string
  endTime: string | null
  peakExecutions: number
  totalExecutions: number
  impact: 'low' | 'medium' | 'high'
}

export interface ExecutionPatternAnalysis {
  peakHours: number[]
  quietHours: number[]
  averageDaily: number
  weekdayAverage: number
  weekendAverage: number
}

export interface ExecutionAnomaly {
  timestamp: string
  type: 'spike' | 'drop' | 'failure_surge' | 'burst' | 'anomaly'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
}

export interface ExecutionPatterns {
  timeline: ExecutionTimelinePoint[]
  bursts: ExecutionBurst[]
  patterns: ExecutionPatternAnalysis
  anomalies: ExecutionAnomaly[]
}

export interface ComputeUsagePoint {
  timestamp: string
  value: number
}

export interface ComputeMetrics {
  cpuUsage: ComputeUsagePoint[]
  memoryUsage: ComputeUsagePoint[]
  gpuUsage?: ComputeUsagePoint[]
}

export interface ModelUsage {
  [modelName: string]: {
    calls: number
    tokens: number
    avgLatency: number
    cost: number
  }
}

export interface DatabaseLoad {
  connections: number
  queryRate: number
  avgQueryTime: number
}

export interface ResourceUtilization {
  compute: ComputeMetrics
  modelUsage: ModelUsage
  databaseLoad: DatabaseLoad
}

export interface ExecutionMetricsData {
  timeframe: ExecutionTimeframe
  workspaceId: string
  realtime: RealtimeMetrics
  throughput: ThroughputMetrics
  latency: LatencyMetrics
  performance: PerformanceMetrics
  patterns: ExecutionPatterns
  resources: ResourceUtilization
}

// WebSocket event types
export interface ExecutionUpdateEvent {
  event: 'execution_update'
  data: RealtimeMetrics
}

export interface ExecutionStartedEvent {
  event: 'execution_started'
  data: ExecutionInProgress
}

export interface ExecutionCompletedEvent {
  event: 'execution_completed'
  data: {
    runId: string
    status: 'success' | 'failure' | 'cancelled'
    duration: number
  }
}

export type ExecutionWebSocketEvent =
  | ExecutionUpdateEvent
  | ExecutionStartedEvent
  | ExecutionCompletedEvent
