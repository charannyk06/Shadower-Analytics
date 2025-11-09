/**
 * Leaderboard type definitions
 */

export type TimeFrame = "24h" | "7d" | "30d" | "90d" | "all";

export type RankChange = "up" | "down" | "same" | "new";

export type Badge = "gold" | "silver" | "bronze";

export type Tier = "platinum" | "gold" | "silver" | "bronze";

export type AgentCriteria =
  | "runs"
  | "success_rate"
  | "speed"
  | "efficiency"
  | "popularity";

export type UserCriteria =
  | "activity"
  | "efficiency"
  | "contribution"
  | "savings";

export type WorkspaceCriteria =
  | "activity"
  | "efficiency"
  | "growth"
  | "innovation";

// ===================================================================
// AGENT LEADERBOARD
// ===================================================================

export interface AgentInfo {
  id: string;
  name: string;
  type: string;
  workspace: string;
}

export interface AgentMetrics {
  totalRuns: number;
  successRate: number;
  avgRuntime: number;
  creditsPerRun: number;
  uniqueUsers: number;
}

export interface AgentRanking {
  rank: number;
  previousRank: number | null;
  change: RankChange;
  agent: AgentInfo;
  metrics: AgentMetrics;
  score: number;
  percentile: number;
  badge?: Badge;
}

export interface AgentLeaderboardData {
  criteria: AgentCriteria;
  rankings: AgentRanking[];
}

export interface AgentLeaderboardResponse {
  criteria: AgentCriteria;
  timeframe: TimeFrame;
  rankings: AgentRanking[];
  total: number;
  offset: number;
  limit: number;
  cached?: boolean;
  calculatedAt: string;
}

// ===================================================================
// USER LEADERBOARD
// ===================================================================

export interface UserInfo {
  id: string;
  name: string;
  avatar?: string;
  workspace: string;
}

export interface UserMetrics {
  totalActions: number;
  successRate: number;
  creditsUsed: number;
  creditsSaved: number;
  agentsUsed: number;
}

export interface UserRanking {
  rank: number;
  previousRank: number | null;
  change: RankChange;
  user: UserInfo;
  metrics: UserMetrics;
  score: number;
  percentile: number;
  achievements: string[];
}

export interface UserLeaderboardData {
  criteria: UserCriteria;
  rankings: UserRanking[];
}

export interface UserLeaderboardResponse {
  criteria: UserCriteria;
  timeframe: TimeFrame;
  rankings: UserRanking[];
  total: number;
  offset: number;
  limit: number;
  calculatedAt: string;
}

// ===================================================================
// WORKSPACE LEADERBOARD
// ===================================================================

export interface WorkspaceInfo {
  id: string;
  name: string;
  plan: string;
  memberCount: number;
}

export interface WorkspaceMetrics {
  totalActivity: number;
  activeUsers: number;
  agentCount: number;
  successRate: number;
  healthScore: number;
}

export interface WorkspaceRanking {
  rank: number;
  previousRank: number | null;
  change: RankChange;
  workspace: WorkspaceInfo;
  metrics: WorkspaceMetrics;
  score: number;
  tier: Tier;
}

export interface WorkspaceLeaderboardData {
  criteria: WorkspaceCriteria;
  rankings: WorkspaceRanking[];
}

export interface WorkspaceLeaderboardResponse {
  criteria: WorkspaceCriteria;
  timeframe: TimeFrame;
  rankings: WorkspaceRanking[];
  total: number;
  offset: number;
  limit: number;
  calculatedAt: string;
}

// ===================================================================
// QUERY PARAMETERS
// ===================================================================

export interface LeaderboardQuery {
  timeframe?: TimeFrame;
  limit?: number;
  offset?: number;
}

export interface AgentLeaderboardQuery extends LeaderboardQuery {
  workspaceId: string;
  criteria?: AgentCriteria;
}

export interface UserLeaderboardQuery extends LeaderboardQuery {
  workspaceId: string;
  criteria?: UserCriteria;
}

export interface WorkspaceLeaderboardQuery extends LeaderboardQuery {
  criteria?: WorkspaceCriteria;
}

// ===================================================================
// MY RANK RESPONSE
// ===================================================================

export interface MyAgentRankResponse {
  agentId: string;
  rank: number | null;
  percentile?: number;
  score?: number;
  badge?: Badge;
  change?: RankChange;
  message?: string;
}

// ===================================================================
// HELPER TYPES
// ===================================================================

export interface LeaderboardFilters {
  timeframe: TimeFrame;
  criteria: AgentCriteria | UserCriteria | WorkspaceCriteria;
  search?: string;
}

export type LeaderboardType = "agents" | "users" | "workspaces";

export interface LeaderboardStats {
  totalParticipants: number;
  myRank?: number;
  myPercentile?: number;
  topScore: number;
  averageScore: number;
}
