/**
 * Agent Execution Analytics Types
 */

export interface TokensUsed {
  prompt: number
  completion: number
  total: number
}

export interface ExecutionStep {
  stepIndex: number
  stepName: string
  stepType?: string
  startTime?: string
  endTime?: string
  durationMs?: number
  status?: string
  input?: Record<string, any>
  output?: Record<string, any>
  error?: Record<string, any>
  tokensUsed?: number
}

export interface ExecutionDetail {
  executionId: string
  agentId: string
  workspaceId: string
  userId: string

  // Execution details
  triggerType?: string
  triggerSource?: Record<string, any>
  inputData?: Record<string, any>
  outputData?: Record<string, any>

  // Performance metrics
  startTime: string
  endTime?: string
  durationMs?: number
  status: string
  errorMessage?: string
  errorType?: string

  // Resource usage
  creditsConsumed: number
  tokensUsed?: TokensUsed
  apiCallsCount: number
  memoryUsageMb?: number

  // Execution path
  stepsTotal?: number
  stepsCompleted?: number
  executionGraph?: Record<string, any>

  // Context
  environment?: string
  runtimeMode?: string
  version?: string

  createdAt: string
  updatedAt: string
}

export interface ExecutionSummary {
  totalExecutions: number
  successfulExecutions: number
  failedExecutions: number
  timeoutExecutions: number
  successRate: number
  avgDurationMs: number
  medianDurationMs: number
  p95DurationMs: number
  p99DurationMs: number
  totalCreditsConsumed: number
  avgCreditsPerExecution: number
}

export interface ExecutionTrendPoint {
  timestamp: string
  executionCount: number
  successRate: number
  avgDuration: number
  failureCount: number
  creditsUsed: number
}

export interface FailureDetail {
  errorType: string
  count: number
  percentage: number
  avgDurationBeforeFailure: number
  lastOccurred?: string
  exampleMessage?: string
}

export interface FailureAnalysis {
  totalFailures: number
  failureRate: number
  failuresByType: FailureDetail[]
  commonPatterns: string[]
}

export interface PerformanceMetrics {
  avgDurationMs: number
  medianDurationMs: number
  minDurationMs: number
  maxDurationMs: number
  p50DurationMs: number
  p75DurationMs: number
  p90DurationMs: number
  p95DurationMs: number
  p99DurationMs: number
  stdDeviation: number
}

export interface HourlyPattern {
  hour: number
  executionCount: number
  avgDurationMs: number
  successRate: number
}

export interface ExecutionPathPattern {
  executionPath: string
  frequency: number
  avgDurationMs: number
  avgCredits: number
  successRate: number
}

export interface BottleneckDetail {
  stepName: string
  avgDurationMs: number
  durationVariance: number
  executionCount: number
  p95DurationMs?: number
  p99DurationMs?: number
  impactScore?: number
  optimizationPriority?: string
}

export interface ExecutionPatternAnalysis {
  hourlyPatterns: HourlyPattern[]
  executionPaths: ExecutionPathPattern[]
  bottlenecks: BottleneckDetail[]
  optimizationSuggestions: string[]
}

export interface ExecutionAnalyticsResponse {
  agentId: string
  workspaceId: string
  timeframe: string
  generatedAt: string

  summary: ExecutionSummary
  trends: ExecutionTrendPoint[]
  performance: PerformanceMetrics
  failureAnalysis: FailureAnalysis
  patterns?: ExecutionPatternAnalysis
  recentExecutions: ExecutionDetail[]
}

export interface LiveExecution {
  executionId: string
  agentId: string
  status: string
  startTime: string
  currentStep?: string
  stepsCompleted: number
  stepsTotal?: number
  progressPercent: number
}

export interface LiveExecutionUpdate {
  type: string
  execution: LiveExecution
  timestamp: string
}

export interface ExecutionStepsResponse {
  executionId: string
  steps: ExecutionStep[]
  totalSteps: number
  completedSteps: number
}

export interface WorkspaceExecutionAnalytics {
  workspaceId: string
  timeframe: string
  totalExecutions: number
  successRate: number
  avgDurationMs: number
  totalCredits: number
  activeAgents: number
  trends: ExecutionTrendPoint[]
  topAgents: Array<{
    agentId: string
    executionCount: number
    successRate: number
    avgDurationMs: number
  }>
}

export interface ExecutionComparison {
  currentPeriod: ExecutionSummary
  previousPeriod: ExecutionSummary
  executionsChange: number
  successRateChange: number
  durationChange: number
  creditsChange: number
}

// Request types
export interface ExecutionAnalyticsRequest {
  agentId: string
  workspaceId: string
  timeframe?: string
  skipCache?: boolean
}

export interface BatchExecutionAnalysisRequest {
  agentIds: string[]
  workspaceId: string
  timeframe?: string
}

// WebSocket event types
export interface ExecutionProgressEvent {
  type: 'execution_progress'
  event: 'execution.progress'
  data: {
    execution_id: string
    agent_id: string
    current_step: string
    steps_completed: number
    steps_total: number
    progress_percent: number
  }
  timestamp: string
}

export interface ExecutionFailedEvent {
  type: 'execution_failed'
  event: 'execution.failed'
  data: {
    execution_id: string
    agent_id: string
    error_type: string
    error_message: string
    duration_ms: number
    failed_at: string
  }
  timestamp: string
}

export interface PerformanceAlertEvent {
  type: 'performance_alert'
  event: 'performance.alert'
  data: {
    agent_id: string
    alert_type: string
    metric_name: string
    current_value: number
    threshold: number
    severity: string
  }
  timestamp: string
}

export interface BottleneckDetectedEvent {
  type: 'bottleneck_detected'
  event: 'performance.bottleneck_detected'
  data: {
    agent_id: string
    step_name: string
    avg_duration_ms: number
    impact_score: number
    priority: string
  }
  timestamp: string
}

export type ExecutionWebSocketEvent =
  | ExecutionProgressEvent
  | ExecutionFailedEvent
  | PerformanceAlertEvent
  | BottleneckDetectedEvent
