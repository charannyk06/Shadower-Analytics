/**
 * Type definitions for Agent Lifecycle Analytics
 *
 * Corresponds to backend Pydantic schemas in:
 * backend/src/models/schemas/agent_lifecycle.py
 */

// ============================================================================
// Enums
// ============================================================================

export enum AgentState {
  DRAFT = "draft",
  TESTING = "testing",
  STAGING = "staging",
  PRODUCTION = "production",
  DEPRECATED = "deprecated",
  ARCHIVED = "archived",
}

export enum DeploymentType {
  CANARY = "canary",
  BLUE_GREEN = "blue_green",
  ROLLING = "rolling",
  DIRECT = "direct",
}

export enum DeploymentStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
  ROLLED_BACK = "rolled_back",
}

export enum HealthStatus {
  EXCELLENT = "excellent",
  GOOD = "good",
  FAIR = "fair",
  POOR = "poor",
  CRITICAL = "critical",
}

export enum RetirementPriority {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
}

// ============================================================================
// Lifecycle Event Types
// ============================================================================

export interface LifecycleEvent {
  id: string;
  agentId: string;
  workspaceId: string;
  eventType: string;
  previousState: string | null;
  newState: string | null;
  triggeredBy: string;
  metadata: Record<string, any>;
  timestamp: string;
  createdAt: string;
}

export interface StateTransition {
  fromState: string | null;
  toState: string;
  transitionAt: string;
  durationInState: number | null;
  triggeredBy: string;
  transitionReason?: string;
  metadata: Record<string, any>;
}

export interface StateTransitionMatrix {
  fromState: string;
  toState: string;
  transitionCount: number;
  transitionProbability: number;
  avgTimeInSourceState: number;
}

// ============================================================================
// Version Types
// ============================================================================

export interface AgentVersion {
  id: string;
  agentId: string;
  workspaceId: string;
  version: string;
  versionNumber: number;
  description?: string;
  changelog?: string;
  capabilitiesAdded: string[];
  capabilitiesRemoved: string[];
  capabilitiesModified: string[];
  performanceImpact: Record<string, any>;
  linesOfCode?: number;
  cyclomaticComplexity?: number;
  cognitiveComplexity?: number;
  dependenciesCount?: number;
  status: string;
  isActive: boolean;
  createdAt: string;
  releasedAt?: string;
  deprecatedAt?: string;
}

export interface VersionPerformanceComparison {
  versionId: string;
  agentId: string;
  version: string;
  versionNumber: number;
  versionReleased?: string;
  totalExecutions: number;
  avgDuration: number;
  p50Duration: number;
  p95Duration: number;
  successRate: number;
  avgCredits: number;
  avgRating?: number;
  uniqueUsers: number;
  errorCount: number;
}

export interface VersionComparisonRequest {
  agentId: string;
  workspaceId: string;
  versionA: string;
  versionB: string;
  metrics?: string[];
}

export interface VersionComparisonResponse {
  agentId: string;
  versionA: VersionPerformanceComparison;
  versionB: VersionPerformanceComparison;
  comparison: {
    executionsDelta: number;
    successRateDelta: number;
    avgDurationDelta: number;
    avgCreditsDelta: number;
    errorCountDelta: number;
  };
  recommendation: string;
}

// ============================================================================
// Deployment Types
// ============================================================================

export interface Deployment {
  id: string;
  agentId: string;
  workspaceId: string;
  versionId?: string;
  deploymentType: string;
  environment: string;
  deploymentStrategy: Record<string, any>;
  rolloutPercentage: number;
  status: string;
  startedAt: string;
  completedAt?: string;
  durationSeconds?: number;
  successMetrics: Record<string, any>;
  failureReason?: string;
  rollbackFrom?: string;
  triggeredBy: string;
  createdAt: string;
}

export interface DeploymentMetrics {
  totalDeployments: number;
  successfulDeployments: number;
  failedDeployments: number;
  rollbackCount: number;
  successRate: number;
  avgDeploymentTimeMinutes: number;
  lastDeployment?: string;
}

export interface DeploymentPatternAnalysis {
  workspaceId: string;
  deploymentFrequency: Record<string, number>;
  preferredDeploymentWindows: Array<Record<string, any>>;
  deploymentVelocity: number;
  deploymentRiskScore: number;
  optimalDeploymentSize: number;
  recommendations: string[];
}

// ============================================================================
// Health Score Types
// ============================================================================

export interface ComponentScores {
  performanceScore: number;
  reliabilityScore: number;
  usageScore: number;
  maintenanceScore: number;
  costScore: number;
}

export interface HealthScore {
  id: string;
  agentId: string;
  workspaceId: string;
  overallScore: number;
  healthStatus: string;
  performanceScore?: number;
  reliabilityScore?: number;
  usageScore?: number;
  maintenanceScore?: number;
  costScore?: number;
  componentScores: ComponentScores;
  improvementRecommendations: Array<Record<string, any>>;
  trend?: string;
  previousScore?: number;
  scoreChange?: number;
  calculatedAt: string;
  calculationPeriodStart: string;
  calculationPeriodEnd: string;
  createdAt: string;
}

// ============================================================================
// Retirement Types
// ============================================================================

export interface RetirementCandidate {
  id: string;
  agentId: string;
  workspaceId: string;
  daysSinceLastUse: number;
  totalExecutions30d: number;
  recentAvgRating?: number;
  activeUsers30d: number;
  dependentAgentsCount: number;
  retirementPriority: string;
  retirementScore: number;
  recommendedReplacementId?: string;
  migrationEffort?: string;
  affectedWorkflows: Array<Record<string, any>>;
  estimatedMigrationDays?: number;
  riskAssessment: Record<string, any>;
  status: string;
  identifiedAt: string;
  approvedAt?: string;
  retiredAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface MigrationPathAnalysis {
  retiringAgentId: string;
  recommendedReplacements: Array<{
    agentId: string;
    similarityScore: number;
    capabilityCoverage: number;
    migrationEffort: "low" | "medium" | "high";
    userAdoptionPrediction: number;
  }>;
  affectedWorkflows: string[];
  estimatedMigrationTime: number;
  riskAssessment: {
    dataLossRisk: number;
    functionalityGapRisk: number;
    userDisruptionRisk: number;
  };
}

// ============================================================================
// Lifecycle Analytics Response Types
// ============================================================================

export interface StateDuration {
  state: string;
  totalDurationSeconds: number;
  averageDurationSeconds: number;
  totalOccurrences: number;
  percentageOfLifetime: number;
}

export interface LifecycleTimeline {
  timestamp: string;
  state: string;
  event: string;
  triggeredBy: string;
  metadata: Record<string, any>;
}

export interface LifecycleMetrics {
  currentState: string;
  daysInCurrentState: number;
  totalDaysSinceCreation: number;
  totalTransitions: number;
  totalVersions: number;
  productionVersions: number;
  latestVersionNumber: number;
  totalDeployments: number;
  successfulDeployments: number;
  deploymentSuccessRate: number;
  rollbackCount: number;
  activationLag?: number;
  deprecationLag?: number;
}

export interface AgentLifecycleAnalytics {
  agentId: string;
  workspaceId: string;
  generatedAt: string;

  // Current state
  currentState: string;
  currentStateSince: string;

  // Metrics
  lifecycleMetrics: LifecycleMetrics;
  stateDurations: StateDuration[];

  // Transitions
  transitions: StateTransition[];
  transitionMatrix: StateTransitionMatrix[];

  // Timeline for visualization
  timeline: LifecycleTimeline[];

  // Versions
  versions: AgentVersion[];
  versionComparison: VersionPerformanceComparison[];

  // Deployments
  deploymentMetrics?: DeploymentMetrics;
  recentDeployments: Deployment[];

  // Health
  currentHealthScore?: HealthScore;
  healthTrend?: string;

  // Retirement risk
  retirementRisk?: string;
  retirementScore?: number;
}

// ============================================================================
// Query Parameter Types
// ============================================================================

export interface LifecycleAnalyticsQuery {
  agentId: string;
  workspaceId: string;
  timeframe?: "24h" | "7d" | "30d" | "90d" | "all";
  includePredictions?: boolean;
  includeVersions?: boolean;
  includeDeployments?: boolean;
  includeHealth?: boolean;
}

export interface RetirementCandidatesQuery {
  workspaceId: string;
  thresholdDays?: number;
  minPriority?: "low" | "medium" | "high" | "critical";
  limit?: number;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface LifecycleStatusResponse {
  agentId: string;
  workspaceId: string;
  currentState: {
    state: string;
    transitionAt: string;
    daysInState: number;
    triggeredBy: string;
    metadata: Record<string, any>;
  };
}

export interface TransitionsResponse {
  agentId: string;
  workspaceId: string;
  timeframe: string;
  transitions: StateTransition[];
  totalTransitions: number;
}

export interface LifecycleEventResponse {
  eventId: string;
  message: string;
}

// ============================================================================
// Chart Data Types (for visualizations)
// ============================================================================

export interface StateTimelineData {
  date: string;
  state: string;
  duration: number;
}

export interface TransitionFlowData {
  source: string;
  target: string;
  value: number;
  probability: number;
}

export interface VersionPerformanceTrendData {
  version: string;
  versionNumber: number;
  executions: number;
  successRate: number;
  avgDuration: number;
  cost: number;
}

export interface HealthScoreTrendData {
  date: string;
  overallScore: number;
  performanceScore: number;
  reliabilityScore: number;
  usageScore: number;
  maintenanceScore: number;
  costScore: number;
}

// ============================================================================
// Utility Types
// ============================================================================

export type LifecycleTimeframe = "24h" | "7d" | "30d" | "90d" | "all";

export type StateColor = {
  [key in AgentState]: {
    bg: string;
    text: string;
    border: string;
  };
};

export const STATE_COLORS: StateColor = {
  [AgentState.DRAFT]: {
    bg: "bg-gray-100",
    text: "text-gray-800",
    border: "border-gray-300",
  },
  [AgentState.TESTING]: {
    bg: "bg-blue-100",
    text: "text-blue-800",
    border: "border-blue-300",
  },
  [AgentState.STAGING]: {
    bg: "bg-yellow-100",
    text: "text-yellow-800",
    border: "border-yellow-300",
  },
  [AgentState.PRODUCTION]: {
    bg: "bg-green-100",
    text: "text-green-800",
    border: "border-green-300",
  },
  [AgentState.DEPRECATED]: {
    bg: "bg-orange-100",
    text: "text-orange-800",
    border: "border-orange-300",
  },
  [AgentState.ARCHIVED]: {
    bg: "bg-red-100",
    text: "text-red-800",
    border: "border-red-300",
  },
};
