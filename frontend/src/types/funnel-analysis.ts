/**
 * Funnel Analysis type definitions
 */

export type FunnelStatus = "active" | "paused" | "archived";

export type FunnelTimeframe = "24h" | "7d" | "30d" | "90d";

export type JourneyStatus = "in_progress" | "completed" | "abandoned";

export type SegmentPerformance = "above" | "below" | "average";

// ===================================================================
// FUNNEL DEFINITION
// ===================================================================

export interface FunnelStep {
  stepId: string;
  stepName: string;
  event: string;
  filters?: Record<string, any>;
}

export interface FunnelDefinition {
  funnelId: string;
  name: string;
  description?: string;
  steps: FunnelStep[];
  stepCount?: number;
  timeframe: FunnelTimeframe;
  segmentBy?: string;
  status: FunnelStatus;
  createdBy?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface FunnelDefinitionCreate {
  name: string;
  description?: string;
  steps: FunnelStep[];
  timeframe?: FunnelTimeframe;
  segmentBy?: string;
}

export interface FunnelDefinitionUpdate {
  name?: string;
  description?: string;
  steps?: FunnelStep[];
  timeframe?: FunnelTimeframe;
  segmentBy?: string;
  status?: FunnelStatus;
}

export interface FunnelDefinitionListResponse {
  funnels: FunnelDefinition[];
  total: number;
}

// ===================================================================
// FUNNEL STEP METRICS
// ===================================================================

export interface FunnelStepMetrics {
  totalUsers: number;
  uniqueUsers: number;
  conversionRate: number;
  avgTimeToComplete?: number;
  dropOffRate: number;
}

export interface DropOffReason {
  reason: string;
  count: number;
  percentage: number;
}

export interface FunnelStepResult {
  stepId: string;
  stepName: string;
  event: string;
  metrics: FunnelStepMetrics;
  dropOffReasons: DropOffReason[];
}

// ===================================================================
// FUNNEL ANALYSIS
// ===================================================================

export interface FunnelOverallMetrics {
  totalConversion: number;
  avgTimeToComplete?: number;
  biggestDropOff?: string;
  biggestDropOffRate?: number;
  improvementPotential: number;
}

export interface FunnelSegmentResult {
  segmentName: string;
  conversionRate: number;
  performance: SegmentPerformance;
}

export interface FunnelAnalysisResult {
  funnelId: string;
  funnelName: string;
  steps: FunnelStepResult[];
  overall: FunnelOverallMetrics;
  segments?: FunnelSegmentResult[];
  analysisStart: string;
  analysisEnd: string;
  calculatedAt: string;
}

// ===================================================================
// USER JOURNEY
// ===================================================================

export interface JourneyPathStep {
  stepId: string;
  stepName: string;
  timestamp: string;
}

export interface UserFunnelJourney {
  userId: string;
  startedAt: string;
  completedAt?: string;
  status: JourneyStatus;
  lastStepReached?: string;
  journeyPath: JourneyPathStep[];
  totalTimeSpent?: number;
  timePerStep?: Record<string, number>;
  userSegment?: string;
}

export interface UserFunnelJourneysResponse {
  journeys: UserFunnelJourney[];
  total: number;
  limit: number;
  offset: number;
}

// ===================================================================
// FUNNEL PERFORMANCE SUMMARY
// ===================================================================

export interface FunnelPerformanceSummaryItem {
  funnelId: string;
  funnelName: string;
  stepCount: number;
  conversionRate: number;
  healthScore: number;
  totalCompletions: number;
  totalAbandonments: number;
  lastAnalyzed?: string;
}

export interface FunnelPerformanceSummaryResponse {
  funnels: FunnelPerformanceSummaryItem[];
  timeframe: FunnelTimeframe;
  generatedAt: string;
}

// ===================================================================
// QUERY PARAMETERS
// ===================================================================

export interface FunnelAnalysisQueryParams {
  funnelId: string;
  workspaceId: string;
  startDate?: string;
  endDate?: string;
  segmentName?: string;
}

export interface FunnelJourneysQueryParams {
  funnelId: string;
  workspaceId: string;
  status?: JourneyStatus;
  limit?: number;
  offset?: number;
}

export interface FunnelPerformanceSummaryQueryParams {
  workspaceId: string;
  timeframe?: FunnelTimeframe;
}

// ===================================================================
// CHART DATA
// ===================================================================

export interface FunnelChartDataPoint {
  step: string;
  stepOrder: number;
  users: number;
  conversionRate: number;
  dropOffRate: number;
}

export interface FunnelComparisonData {
  stepName: string;
  current: number;
  previous: number;
  change: number;
}

export interface DropOffAnalysisData {
  step: string;
  dropOffRate: number;
  reasons: DropOffReason[];
}

// ===================================================================
// UI STATE
// ===================================================================

export interface FunnelAnalysisFilters {
  timeframe: FunnelTimeframe;
  segmentName?: string;
  startDate?: Date;
  endDate?: Date;
}

export interface FunnelAnalysisState {
  loading: boolean;
  error?: string;
  funnelDefinition?: FunnelDefinition;
  analysisResult?: FunnelAnalysisResult;
  journeys?: UserFunnelJourneysResponse;
  filters: FunnelAnalysisFilters;
}
