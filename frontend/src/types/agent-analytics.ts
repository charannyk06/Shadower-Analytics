/**
 * Agent Analytics Type Definitions
 */

export type TimeFrame = '24h' | '7d' | '30d' | '90d' | 'all';

export interface RuntimeMetrics {
  average: number;
  median: number;
  min: number;
  max: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
  p99: number;
  standardDeviation: number;
}

export interface ThroughputMetrics {
  runsPerHour: number;
  runsPerDay: number;
  peakConcurrency: number;
  avgConcurrency: number;
}

export interface PerformanceMetrics {
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
  cancelledRuns: number;
  successRate: number;
  availabilityRate: number;
  runtime: RuntimeMetrics;
  throughput: ThroughputMetrics;
}

export interface ModelUsageDetail {
  calls: number;
  tokens: number;
  credits: number;
}

export interface ResourceUsage {
  totalCreditsConsumed: number;
  avgCreditsPerRun: number;
  totalTokensUsed: number;
  avgTokensPerRun: number;
  costPerRun: number;
  totalCost: number;
  modelUsage: Record<string, ModelUsageDetail>;
}

export interface ErrorTypeDetail {
  count: number;
  percentage: number;
  category: string;
  severity: string;
  lastOccurred: string | null;
  exampleMessage: string;
  avgRecoveryTime: number;
  autoRecoveryRate: number;
}

export interface ErrorPattern {
  pattern: string;
  frequency: number;
  impact: 'low' | 'medium' | 'high';
  suggestedFix: string;
}

export interface ErrorAnalysis {
  totalErrors: number;
  errorRate: number;
  errorsByType: Record<string, ErrorTypeDetail>;
  errorPatterns: ErrorPattern[];
  meanTimeToRecovery: number;
  autoRecoveryRate: number;
}

export interface RatingDistribution {
  '5': number;
  '4': number;
  '3': number;
  '2': number;
  '1': number;
}

export interface UserRatings {
  average: number;
  total: number;
  distribution: RatingDistribution;
}

export interface UserFeedback {
  userId: string;
  rating: number;
  comment: string;
  timestamp: string;
}

export interface TopUser {
  userId: string;
  runCount: number;
  successRate: number;
}

export interface UserMetrics {
  uniqueUsers: number;
  totalInteractions: number;
  avgInteractionsPerUser: number;
  userRatings: UserRatings;
  feedback: UserFeedback[];
  usageByHour: number[];
  usageByDayOfWeek: number[];
  topUsers: TopUser[];
}

export interface WorkspaceComparison {
  successRate: number;
  runtime: number;
  creditEfficiency: number;
}

export interface AllAgentsComparison {
  rank: number;
  percentile: number;
}

export interface PreviousPeriodComparison {
  runsChange: number;
  successRateChange: number;
  runtimeChange: number;
  costChange: number;
}

export interface ComparisonMetrics {
  vsWorkspaceAverage: WorkspaceComparison;
  vsAllAgents: AllAgentsComparison;
  vsPreviousPeriod: PreviousPeriodComparison;
}

export interface OptimizationSuggestion {
  type: 'performance' | 'cost' | 'reliability' | 'user_experience';
  title: string;
  description: string;
  estimatedImpact: string;
  effort: 'low' | 'medium' | 'high';
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  runs: number;
  successRate: number;
  avgRuntime: number;
  credits: number;
  errors: number;
}

export interface TrendData {
  daily: TimeSeriesDataPoint[];
  hourly: TimeSeriesDataPoint[];
}

export interface AgentAnalytics {
  agentId: string;
  workspaceId: string;
  timeframe: TimeFrame;
  generatedAt: string;
  performance: PerformanceMetrics;
  resources: ResourceUsage;
  errors: ErrorAnalysis;
  userMetrics: UserMetrics;
  comparison: ComparisonMetrics;
  optimizations: OptimizationSuggestion[];
  trends: TrendData;
}

export interface AgentListItem {
  agentId: string;
  agentName: string;
  agentType: string;
  workspaceId: string;
  totalRuns: number;
  successRate: number;
  avgRuntime: number;
  lastRunAt: string | null;
}

export interface AgentListResponse {
  agents: AgentListItem[];
  total: number;
  skip: number;
  limit: number;
}
