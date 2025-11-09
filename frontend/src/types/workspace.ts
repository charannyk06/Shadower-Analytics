/**
 * Workspace Analytics Types
 * Matches backend Pydantic schemas with camelCase naming
 */

export type TimeFrame = '24h' | '7d' | '30d' | '90d' | 'all';
export type WorkspacePlan = 'free' | 'starter' | 'pro' | 'enterprise';
export type WorkspaceStatus = 'active' | 'idle' | 'at_risk' | 'churned';
export type ActivityTrend = 'increasing' | 'stable' | 'decreasing';
export type EngagementLevel = 'high' | 'medium' | 'low' | 'inactive';
export type UserRole = 'owner' | 'admin' | 'member' | 'viewer';
export type BillingStatus = 'active' | 'trial' | 'past_due' | 'cancelled';
export type RecommendationType = 'upgrade' | 'downgrade' | 'add_on';
export type BillingHistoryStatus = 'paid' | 'pending' | 'failed';

export interface HealthFactors {
  activity: number;
  engagement: number;
  efficiency: number;
  reliability: number;
}

export interface WorkspaceOverview {
  totalMembers: number;
  activeMembers: number;
  pendingInvites: number;
  memberGrowth: number;
  totalActivity: number;
  avgActivityPerMember: number;
  lastActivityAt: string | null;
  activityTrend: ActivityTrend;
  healthScore: number;
  healthFactors: HealthFactors;
  status: WorkspaceStatus;
  daysActive: number;
  createdAt: string;
}

export interface MembersByRole {
  owner: number;
  admin: number;
  member: number;
  viewer: number;
}

export interface MemberActivityItem {
  userId: string;
  userName: string;
  role: UserRole;
  activityCount: number;
  lastActiveAt: string | null;
  engagementLevel: EngagementLevel;
}

export interface TopContributor {
  userId: string;
  userName: string;
  contribution: {
    agentRuns: number;
    successRate: number;
    creditsUsed: number;
  };
}

export interface InactiveMember {
  userId: string;
  userName: string;
  lastActiveAt: string;
  daysSinceActive: number;
}

export interface MemberAnalytics {
  membersByRole: MembersByRole;
  activityDistribution: MemberActivityItem[];
  topContributors: TopContributor[];
  inactiveMembers: InactiveMember[];
}

export interface AgentPerformance {
  agentId: string;
  agentName: string;
  runs: number;
  successRate: number;
  avgRuntime: number;
  creditsConsumed: number;
  lastRunAt: string | null;
}

export interface AgentEfficiency {
  mostEfficient: string | null;
  leastEfficient: string | null;
  avgSuccessRate: number;
  avgRuntime: number;
}

export interface AgentUsage {
  totalAgents: number;
  activeAgents: number;
  agents: AgentPerformance[];
  usageByAgent: Record<string, any>;
  agentEfficiency: AgentEfficiency;
}

export interface DailyConsumption {
  date: string;
  credits: number;
}

export interface Credits {
  allocated: number;
  consumed: number;
  remaining: number;
  utilizationRate: number;
  projectedExhaustion: string | null;
  consumptionByModel: Record<string, {
    credits: number;
    percentage: number;
  }>;
  dailyConsumption: DailyConsumption[];
}

export interface Storage {
  used: number;
  limit: number;
  utilizationRate: number;
  breakdown: Record<string, number>;
}

export interface APIUsage {
  totalCalls: number;
  rateLimit: number;
  utilizationRate: number;
  byEndpoint: Record<string, {
    calls: number;
    avgLatency: number;
  }>;
}

export interface ResourceUtilization {
  credits: Credits;
  storage: Storage;
  apiUsage: APIUsage;
}

export interface UsageLimit {
  used: number;
  limit: number;
}

export interface BillingHistory {
  date: string;
  amount: number;
  status: BillingHistoryStatus;
}

export interface BillingRecommendation {
  type: RecommendationType;
  reason: string;
  estimatedSavings: number;
}

export interface Billing {
  plan: string;
  status: BillingStatus;
  currentMonthCost: number;
  projectedMonthCost: number;
  lastMonthCost: number;
  limits: Record<string, UsageLimit>;
  history: BillingHistory[];
  recommendations: BillingRecommendation[];
}

export interface WorkspaceRanking {
  overall: number;
  totalWorkspaces: number;
  percentile: number;
}

export interface Benchmarks {
  activityVsAvg: number;
  efficiencyVsAvg: number;
  costVsAvg: number;
}

export interface SimilarWorkspace {
  workspaceId: string;
  similarity: number;
  metrics: Record<string, any>;
}

export interface WorkspaceComparison {
  ranking: WorkspaceRanking;
  benchmarks: Benchmarks;
  similarWorkspaces: SimilarWorkspace[];
}

export interface WorkspaceAnalytics {
  workspaceId: string;
  workspaceName: string;
  plan: WorkspacePlan;
  timeframe: TimeFrame;
  overview: WorkspaceOverview;
  memberAnalytics: MemberAnalytics;
  agentUsage: AgentUsage;
  resourceUtilization: ResourceUtilization;
  billing: Billing;
  comparison?: WorkspaceComparison;
}

/**
 * API Query Parameters
 */
export interface WorkspaceAnalyticsParams {
  workspaceId: string;
  timeframe?: TimeFrame;
  includeComparison?: boolean;
}
