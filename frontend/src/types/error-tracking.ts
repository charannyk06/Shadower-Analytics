/**
 * Error Tracking Type Definitions
 */

export type TimeFrame = '24h' | '7d' | '30d' | '90d';
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';
export type ErrorStatus = 'new' | 'acknowledged' | 'investigating' | 'resolved' | 'ignored';
export type SystemImpact = 'low' | 'medium' | 'high' | 'critical';
export type ErrorTrend = 'increasing' | 'stable' | 'decreasing';
export type ErrorCategory = 'api' | 'timeout' | 'validation' | 'auth' | 'system' | 'unknown';

export interface ErrorOverview {
  totalErrors: number;
  uniqueErrors: number;
  affectedUsers: number;
  affectedAgents: number;
  errorRate: number;
  errorRateChange: number;
  criticalErrorRate: number;
  userImpact: number;
  systemImpact: SystemImpact;
  estimatedRevenueLoss: number;
  avgRecoveryTime: number;
  autoRecoveryRate: number;
  manualInterventions: number;
}

export interface ErrorSample {
  errorId: string;
  message: string;
  stackTrace: string;
  occurredAt: string;
}

export interface ErrorTypeDetail {
  type: string;
  category: ErrorCategory;
  count: number;
  percentage: number;
  trend: ErrorTrend;
  severity: ErrorSeverity;
  samples: ErrorSample[];
}

export interface ErrorCategories {
  byType: ErrorTypeDetail[];
  bySeverity: Record<ErrorSeverity, number>;
  bySource: {
    agent: number;
    api: number;
    database: number;
    integration: number;
    system: number;
  };
}

export interface TimeSeriesPoint {
  timestamp: string;
  count: number;
  criticalCount: number;
  uniqueErrors: number;
}

export interface ErrorSpike {
  startTime: string;
  endTime: string | null;
  peakErrors: number;
  totalErrors: number;
  primaryCause: string;
  resolved: boolean;
}

export interface ErrorPattern {
  pattern: string;
  frequency: number;
  lastOccurrence: string;
  correlation: string;
}

export interface ErrorTimeline {
  errorsByTime: TimeSeriesPoint[];
  spikes: ErrorSpike[];
  patterns: ErrorPattern[];
}

export interface ErrorImpact {
  usersAffected: number;
  executionsAffected: number;
  creditsLost: number;
  cascadingFailures: number;
}

export interface ErrorResolution {
  resolvedAt: string;
  resolvedBy: string | null;
  resolution: string;
  rootCause: string;
  preventiveMeasures: string[];
}

export interface ErrorDetail {
  errorId: string;
  fingerprint: string;
  type: string;
  message: string;
  severity: ErrorSeverity;
  status: ErrorStatus;
  firstSeen: string;
  lastSeen: string;
  occurrences: number;
  affectedUsers: string[];
  affectedAgents: string[];
  stackTrace: string;
  context: Record<string, any>;
  impact: ErrorImpact;
  resolution?: ErrorResolution;
}

export interface TopError {
  errorId: string;
  type: string;
  count: number;
  lastSeen: string;
}

export interface TopErrorByImpact {
  errorId: string;
  type: string;
  usersAffected: number;
  creditsLost: number;
}

export interface UnresolvedError {
  errorId: string;
  type: string;
  age: number;
  priority: number;
}

export interface TopErrors {
  byOccurrence: TopError[];
  byImpact: TopErrorByImpact[];
  unresolved: UnresolvedError[];
}

export interface AgentCorrelation {
  agentId: string;
  agentName: string;
  errorTypes: string[];
  errorRate: number;
  commonCause: string;
}

export interface UserCorrelation {
  userId: string;
  errorTypes: string[];
  frequency: number;
  possibleCause: string;
}

export interface ErrorChain {
  rootError: string;
  cascadingErrors: string[];
  totalImpact: number;
  preventable: boolean;
}

export interface ErrorCorrelations {
  agentCorrelation: AgentCorrelation[];
  userCorrelation: UserCorrelation[];
  errorChains: ErrorChain[];
}

export interface RecoveryTimeMetrics {
  avg: number;
  median: number;
  p95: number;
}

export interface RecoveryMethod {
  method: string;
  successRate: number;
  avgTime: number;
  usageCount: number;
}

export interface FailedRecovery {
  errorId: string;
  attemptedMethods: string[];
  failureReason: string;
}

export interface RecoveryAnalysis {
  recoveryTimes: {
    automatic: RecoveryTimeMetrics;
    manual: RecoveryTimeMetrics;
  };
  recoveryMethods: RecoveryMethod[];
  failedRecoveries: FailedRecovery[];
}

export interface ErrorTracking {
  workspaceId: string;
  timeframe: TimeFrame;
  overview: ErrorOverview;
  categories: ErrorCategories;
  timeline: ErrorTimeline;
  errors: ErrorDetail[];
  topErrors: TopErrors;
  correlations: ErrorCorrelations;
  recovery: RecoveryAnalysis;
}

export interface TrackErrorRequest {
  type: string;
  message: string;
  severity?: ErrorSeverity;
  stackTrace?: string;
  context?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface ResolveErrorRequest {
  resolvedBy: string;
  resolution: string;
  rootCause?: string;
  preventiveMeasures?: string[];
}
