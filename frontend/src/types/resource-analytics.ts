/**
 * Resource Analytics Type Definitions
 * Comprehensive types for resource utilization, cost optimization, and efficiency metrics
 */

export type TimeFrame = '24h' | '7d' | '30d' | '90d';
export type Granularity = 'hourly' | 'daily' | 'weekly';
export type ResourceType = 'compute' | 'tokens' | 'api' | 'storage' | 'network' | 'cost';
export type WasteType = 'idle_resources' | 'oversized_instances' | 'redundant_api_calls' |
  'inefficient_prompts' | 'unused_cache' | 'failed_execution_costs' |
  'rate_limit_waste' | 'token_overflow';
export type OptimizationCategory = 'compute' | 'tokens' | 'api' | 'storage' | 'network' | 'cost' | 'general';
export type BudgetStatus = 'no_budget' | 'within_budget' | 'warning' | 'critical' | 'over_budget';
export type ImplementationEffort = 'low' | 'medium' | 'high';
export type Priority = 'low' | 'medium' | 'high' | 'critical';

// ============================================================================
// Compute Resources
// ============================================================================
export interface CPUUsage {
  averagePercent: number;
  peakPercent: number;
  coreSeconds: number;
}

export interface MemoryUsage {
  averageMb: number;
  peakMb: number;
  allocationMb: number;
  averageAllocationMb?: number;
}

export interface GPUUsage {
  utilizationPercent: number;
  memoryMb: number;
  computeUnits: number;
  totalComputeUnits?: number;
  averageUtilizationPercent?: number;
  maxMemoryMb?: number;
}

export interface NetworkIO {
  bytesSent: number;
  bytesReceived: number;
  apiCalls: number;
  totalBytesTransferred?: number;
  totalBytesSent?: number;
  totalBytesReceived?: number;
  totalApiCalls?: number;
}

export interface ComputeMetrics {
  cpuUsage: CPUUsage;
  memoryUsage: MemoryUsage;
  gpuUsage?: GPUUsage;
  networkIo: NetworkIO;
  executionMetrics?: {
    totalExecutions: number;
    avgDurationMs: number;
    avgQueueWaitMs: number;
  };
}

// ============================================================================
// Token Metrics
// ============================================================================
export interface TokenDistribution {
  inputTokens: number;
  outputTokens: number;
  embeddingTokens: number;
  inputPercent: number;
  outputPercent: number;
  embeddingPercent: number;
}

export interface TokenAverages {
  tokensPerExecution: number;
  inputTokensPerExecution: number;
  outputTokensPerExecution: number;
}

export interface TokenEfficiency {
  tokensPerDollar: number;
  cacheHitRate: number;
  totalCacheHits: number;
  tokensPerSecond?: number;
}

export interface TokenCost {
  totalCostUsd: number;
  avgCostPerExecution: number;
  costPerThousandTokens: number;
}

export interface ModelUsage {
  provider: string;
  model: string;
  totalTokens: number;
  usageCount: number;
  costUsd: number;
}

export interface TokenMetrics {
  totalTokens: number;
  tokenDistribution: TokenDistribution;
  averages: TokenAverages;
  efficiency: TokenEfficiency;
  cost: TokenCost;
  modelUsage: ModelUsage[];
}

// ============================================================================
// API Metrics
// ============================================================================
export interface APICallStatistics {
  totalCalls: number;
  successfulCalls: number;
  failedCalls: number;
  rateLimitedCalls: number;
  timeoutCalls?: number;
}

export interface APILatencyMetrics {
  avgLatencyMs: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  p99LatencyMs: number;
  minLatencyMs: number;
  maxLatencyMs: number;
}

export interface APICostMetrics {
  totalCostUsd: number;
  costPerCall: number;
  wastedCostUsd: number;
  wastedCostFailedCalls?: number;
}

export interface APIBreakdown {
  endpoint: string;
  provider: string | null;
  totalCalls: number;
  successfulCalls: number;
  failedCalls: number;
  rateLimitedCalls: number;
  avgLatencyMs: number;
  p95LatencyMs: number;
  costUsd: number;
  errorRate: number;
}

export interface APIMetrics {
  totalApiCalls: number;
  successRate: number;
  statistics: APICallStatistics;
  cost: APICostMetrics;
  apiBreakdown: APIBreakdown[];
}

// ============================================================================
// Storage Metrics
// ============================================================================
export interface StorageMetrics {
  tempStorage: {
    averageMb: number;
    maxMb: number;
  };
  persistentStorage: {
    averageMb: number;
    maxMb: number;
  };
  cache: {
    averageSizeMb: number;
    maxSizeMb: number;
  };
  database: {
    totalOperations: number;
  };
  cost: {
    totalCostUsd: number;
  };
}

// ============================================================================
// Cost Analytics
// ============================================================================
export interface CostByCategory {
  computeCostUsd: number;
  tokenCostUsd: number;
  apiCostUsd: number;
  storageCostUsd: number;
  networkCostUsd: number;
}

export interface CostDistribution {
  computePercent: number;
  tokenPercent: number;
  apiPercent: number;
  storagePercent: number;
  networkPercent: number;
}

export interface CostBreakdown {
  totalCostUsd: number;
  costByCategory: CostByCategory;
  costDistribution: CostDistribution;
  averageCostPerExecution: number;
  totalExecutions: number;
}

// ============================================================================
// Efficiency Metrics
// ============================================================================
export interface EfficiencyMetrics {
  overallScore: number;
  tokensPerDollar: number;
  executionsPerDollar: number;
  throughputScore: number;
  costEfficiencyPercent: number;
  totalWasteCostUsd: number;
  percentileRank?: number;
  improvementAreas?: string[];
}

// ============================================================================
// Resource Usage Response
// ============================================================================
export interface ResourceUsage {
  agentId: string;
  workspaceId: string;
  timeframe: TimeFrame;
  periodStart: string;
  periodEnd: string;
  computeMetrics: ComputeMetrics;
  tokenMetrics: TokenMetrics;
  apiMetrics: APIMetrics;
  storageMetrics: StorageMetrics;
  costBreakdown: CostBreakdown;
  efficiencyMetrics: EfficiencyMetrics;
}

// ============================================================================
// Optimization
// ============================================================================
export interface OptimizationRecommendation {
  id?: string;
  type: string;
  category: OptimizationCategory;
  priority: Priority;
  title: string;
  description: string;
  reasoning?: string;
  currentValue?: number;
  recommendedValue?: number;
  estimatedSavingsUsd: number;
  estimatedSavingsPercent?: number;
  estimatedSavings?: string;
  implementationEffort: ImplementationEffort;
  implementationSteps?: string[];
  status?: string;
  createdAt?: string;
}

export interface CostOptimization {
  currentMonthlyCost: number;
  potentialSavings: number;
  optimizationRecommendations: OptimizationRecommendation[];
}

// ============================================================================
// Waste Detection
// ============================================================================
export interface WasteEvent {
  id: string;
  agentId: string;
  executionId?: string;
  workspaceId: string;
  wasteType: WasteType;
  wasteCategory: string;
  title: string;
  description: string;
  wasteAmount: number;
  wasteUnit: string;
  wasteCostUsd: number;
  confidenceScore: number;
  isResolved: boolean;
  detectedAt: string;
}

export interface WasteSummary {
  totalWasteCostUsd: number;
  wasteByType: Record<string, number>;
  unresolvedCount: number;
  potentialMonthlySavings: number;
}

// ============================================================================
// Forecasting
// ============================================================================
export interface ResourceForecast {
  resourceType: ResourceType;
  forecastHorizonDays: number;
  predictedValue: number;
  lowerBound: number;
  upperBound: number;
  confidenceLevel: number;
  confidence?: number;
  historicalAverage: number;
  historicalTrend: string;
  exceedsBudget: boolean;
  forecastDate: string;
  projectedValue?: number;
}

export interface CostProjection {
  projectedDailyCost?: number;
  projectedWeeklyCost?: number;
  projectedMonthlyCost: number;
  lowerBound?: number;
  upperBound?: number;
  growthRate: number;
  budgetAlerts: string[];
}

export interface ForecastResponse {
  tokenUsage: ResourceForecast | null;
  computeUsage: ResourceForecast | null;
  projectedCosts: CostProjection | null;
  budgetAlerts: string[];
}

// ============================================================================
// Token Analysis
// ============================================================================
export interface TokenAnalysisResponse {
  tokenDistribution: {
    inputTokens: number;
    outputTokens: number;
    embeddingTokens: number;
    totalTokens: number;
    contextUtilization: {
      averageUsed: number;
      maxUsed: number;
    };
  };
  efficiencyMetrics: {
    tokensPerSecond: number;
    cacheHitRate: number;
    tokensPerDollar: number;
    totalCacheHits: number;
  };
  optimizationOpportunities: OptimizationRecommendation[];
  costAnalysis: {
    totalCost: number;
    totalTokens: number;
    avgCostPerDay: number;
    trendData: Array<{
      date: string;
      tokens: number;
      cost: number;
    }>;
  };
}

// ============================================================================
// Comprehensive Analytics
// ============================================================================
export interface ResourceAnalytics {
  agentId: string;
  workspaceId: string;
  timeframe: TimeFrame;
  tokenAnalysis: TokenAnalysisResponse;
  costOptimization: CostOptimization;
  wasteDetection: WasteSummary;
  forecasts: ForecastResponse;
}

// ============================================================================
// Budget Management
// ============================================================================
export interface TokenBudget {
  workspaceId: string;
  agentId?: string;
  dailyTokenBudget?: number;
  weeklyTokenBudget?: number;
  monthlyTokenBudget?: number;
  dailyCostBudgetUsd?: number;
  weeklyCostBudgetUsd?: number;
  monthlyCostBudgetUsd?: number;
  warningThresholdPercent: number;
  criticalThresholdPercent: number;
}

export interface BudgetUsage {
  dailyTokens: number;
  dailyCostUsd: number;
  dailyBudgetUsagePercent: number;
  dailyCostBudgetUsagePercent: number;
  rolling7dTokens: number;
  rolling30dTokens: number;
  rolling30dCostUsd: number;
  budgetStatus: BudgetStatus;
}

// ============================================================================
// Workspace Analytics
// ============================================================================
export interface WorkspaceCostAnalysis {
  workspaceId: string;
  period: string;
  totalCost: number;
  costByAgent: Record<string, number>;
  costBreakdown: CostByCategory & { totalCostUsd: number };
  costTrends?: Array<{
    date: string;
    cost: number;
  }>;
  projections?: CostProjection;
  optimizationPotential?: number;
}

// ============================================================================
// Efficiency Leaderboard
// ============================================================================
export interface EfficiencyLeaderboardEntry {
  agentId: string;
  rank: number;
  efficiencyScore: number;
  tokensPerDollar: number;
  executionsPerDollar: number;
  costEfficiencyPercent: number;
  monthlyCost: number;
}

export interface EfficiencyLeaderboard {
  workspaceId: string;
  metric: string;
  leaderboard: EfficiencyLeaderboardEntry[];
}

// ============================================================================
// Chart Data Types
// ============================================================================
export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface CostTrendData {
  date: string;
  compute: number;
  tokens: number;
  api: number;
  storage: number;
  network: number;
  total: number;
}

export interface TokenUsageData {
  date: string;
  inputTokens: number;
  outputTokens: number;
  embeddingTokens: number;
  totalTokens: number;
}
