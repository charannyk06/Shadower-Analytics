/**
 * Comparison Views Types
 * Side-by-side comparison views for agents, periods, workspaces, and metrics
 */

// ============================================================================
// Core Comparison Types
// ============================================================================

export type ComparisonType = 'agents' | 'periods' | 'workspaces' | 'metrics';

export interface ComparisonViews {
  type: ComparisonType;
  timestamp: string;
  agentComparison?: AgentComparison;
  periodComparison?: PeriodComparison;
  workspaceComparison?: WorkspaceComparison;
  metricComparison?: MetricComparison;
}

// ============================================================================
// Agent Comparison
// ============================================================================

export interface AgentMetrics {
  successRate: number;
  averageRuntime: number;
  totalRuns: number;
  errorRate: number;
  costPerRun: number;
  totalCost: number;
  p50Runtime: number;
  p95Runtime: number;
  p99Runtime: number;
  throughput: number;
  userSatisfaction?: number;
  creditsPerRun: number;
}

export interface AgentComparisonItem {
  id: string;
  name: string;
  version?: string;
  metrics: AgentMetrics;
  tags?: string[];
  lastRunAt?: string;
}

export interface MetricDifference {
  best: string;
  worst: string;
  delta: number;
  deltaPercent: number;
  values: Record<string, number>;
}

export interface AgentComparison {
  agents: AgentComparisonItem[];
  differences: {
    successRate: MetricDifference;
    runtime: MetricDifference;
    cost: MetricDifference;
    throughput: MetricDifference;
    errorRate: MetricDifference;
  };
  winner: string;
  winnerScore: number;
  recommendations: Recommendation[];
  exportUrl?: string;
}

export interface Recommendation {
  type: 'performance' | 'cost' | 'reliability' | 'user_experience';
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affectedAgents: string[];
  potentialImpact?: {
    metric: string;
    estimatedImprovement: number;
  };
}

// ============================================================================
// Period Comparison
// ============================================================================

export interface PeriodMetrics {
  period: string;
  startDate: string;
  endDate: string;
  totalRuns: number;
  successRate: number;
  averageRuntime: number;
  totalCost: number;
  errorCount: number;
  activeAgents: number;
  activeUsers: number;
  throughput: number;
  p95Runtime: number;
  creditConsumption: number;
}

export interface ChangeMetrics {
  totalRuns: ChangeDetail;
  successRate: ChangeDetail;
  averageRuntime: ChangeDetail;
  totalCost: ChangeDetail;
  errorCount: ChangeDetail;
  activeAgents: ChangeDetail;
  activeUsers: ChangeDetail;
  throughput: ChangeDetail;
  p95Runtime: ChangeDetail;
  creditConsumption: ChangeDetail;
}

export interface ChangeDetail {
  absolute: number;
  percent: number;
  trend: 'up' | 'down' | 'stable';
  significant: boolean;
  direction: 'positive' | 'negative' | 'neutral';
}

export interface PeriodComparison {
  current: PeriodMetrics;
  previous: PeriodMetrics;
  change: ChangeMetrics;
  improvements: string[];
  regressions: string[];
  summary: string;
  timeSeriesComparison?: TimeSeriesComparison;
  exportUrl?: string;
}

export interface TimeSeriesComparison {
  currentPeriodData: TimeSeriesPoint[];
  previousPeriodData: TimeSeriesPoint[];
  metric: string;
  unit: string;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  label?: string;
}

// ============================================================================
// Workspace Comparison
// ============================================================================

export interface WorkspaceMetrics {
  workspaceId: string;
  workspaceName: string;
  totalRuns: number;
  successRate: number;
  averageRuntime: number;
  totalCost: number;
  activeAgents: number;
  activeUsers: number;
  creditUsage: number;
  errorRate: number;
  throughput: number;
  userSatisfaction?: number;
  tags?: string[];
}

export interface BenchmarkMetrics {
  averageSuccessRate: number;
  averageRuntime: number;
  averageCost: number;
  averageThroughput: number;
  topPerformer: {
    workspaceId: string;
    workspaceName: string;
    score: number;
  };
  bottomPerformer: {
    workspaceId: string;
    workspaceName: string;
    score: number;
  };
}

export interface RankingMetrics {
  rankings: WorkspaceRanking[];
  scoreMethod: 'weighted' | 'composite' | 'custom';
  weights?: {
    successRate: number;
    runtime: number;
    cost: number;
    throughput: number;
  };
}

export interface WorkspaceRanking {
  rank: number;
  workspaceId: string;
  workspaceName: string;
  score: number;
  percentile: number;
  strengths: string[];
  weaknesses: string[];
}

export interface WorkspaceComparison {
  workspaces: WorkspaceMetrics[];
  benchmarks: BenchmarkMetrics;
  rankings: RankingMetrics;
  insights: ComparisonInsight[];
  exportUrl?: string;
}

export interface ComparisonInsight {
  type: 'trend' | 'anomaly' | 'opportunity' | 'warning';
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  affectedWorkspaces: string[];
  dataPoints?: Record<string, number>;
}

// ============================================================================
// Metric Comparison
// ============================================================================

export interface MetricComparison {
  metricName: string;
  metricType: 'performance' | 'cost' | 'reliability' | 'usage';
  entities: MetricEntity[];
  statistics: MetricStatistics;
  distribution: MetricDistribution;
  outliers: MetricOutlier[];
  correlations?: MetricCorrelation[];
  exportUrl?: string;
}

export interface MetricEntity {
  id: string;
  name: string;
  value: number;
  percentile: number;
  deviationFromMean: number;
  trend?: 'increasing' | 'decreasing' | 'stable';
  sparklineData?: number[];
}

export interface MetricStatistics {
  mean: number;
  median: number;
  standardDeviation: number;
  min: number;
  max: number;
  p25: number;
  p75: number;
  p90: number;
  p95: number;
  p99: number;
  variance: number;
  coefficientOfVariation: number;
}

export interface MetricDistribution {
  buckets: DistributionBucket[];
  skewness: number;
  kurtosis: number;
  isNormal: boolean;
}

export interface DistributionBucket {
  min: number;
  max: number;
  count: number;
  percentage: number;
  label: string;
}

export interface MetricOutlier {
  entityId: string;
  entityName: string;
  value: number;
  zScore: number;
  type: 'high' | 'low';
  severity: 'mild' | 'moderate' | 'extreme';
}

export interface MetricCorrelation {
  metric1: string;
  metric2: string;
  coefficient: number;
  strength: 'weak' | 'moderate' | 'strong';
  direction: 'positive' | 'negative';
  pValue: number;
  significant: boolean;
}

// ============================================================================
// Comparison Filters and Options
// ============================================================================

export interface ComparisonFilters {
  startDate?: string;
  endDate?: string;
  agentIds?: string[];
  workspaceIds?: string[];
  metricNames?: string[];
  tags?: string[];
  minSuccessRate?: number;
  maxCost?: number;
}

export interface ComparisonOptions {
  includeTimeSeries?: boolean;
  includeRecommendations?: boolean;
  includeVisualDiff?: boolean;
  includeStatistics?: boolean;
  includeCorrelations?: boolean;
  exportFormat?: 'json' | 'csv' | 'pdf';
  groupBy?: 'day' | 'week' | 'month';
}

// ============================================================================
// Visual Diff Types
// ============================================================================

export interface VisualDiff {
  metric: string;
  items: VisualDiffItem[];
  highlightThreshold?: number;
}

export interface VisualDiffItem {
  id: string;
  name: string;
  value: number;
  baseline: number;
  difference: number;
  percentDifference: number;
  highlight: boolean;
  color: 'red' | 'yellow' | 'green' | 'gray';
  trend?: 'up' | 'down' | 'stable';
}

// ============================================================================
// Export Types
// ============================================================================

export interface ComparisonReport {
  id: string;
  type: ComparisonType;
  createdAt: string;
  createdBy: string;
  title: string;
  description?: string;
  filters: ComparisonFilters;
  data: ComparisonViews;
  format: 'json' | 'csv' | 'pdf';
  downloadUrl: string;
  expiresAt?: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface ComparisonRequest {
  type: ComparisonType;
  filters: ComparisonFilters;
  options?: ComparisonOptions;
}

export interface ComparisonResponse {
  success: boolean;
  data: ComparisonViews;
  metadata: {
    generatedAt: string;
    processingTime: number;
    entityCount: number;
    dataPoints: number;
  };
  error?: {
    code: string;
    message: string;
  };
}

// ============================================================================
// Utility Types
// ============================================================================

export type SortField =
  | 'name'
  | 'successRate'
  | 'runtime'
  | 'cost'
  | 'throughput'
  | 'errorRate'
  | 'score';

export type SortOrder = 'asc' | 'desc';

export interface ComparisonSort {
  field: SortField;
  order: SortOrder;
}
