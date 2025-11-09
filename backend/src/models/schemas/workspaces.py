"""Workspace schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class WorkspaceMetrics(BaseModel):
    """Workspace basic metrics."""

    workspace_id: str
    workspace_name: str
    total_users: int = 0
    total_agents: int = 0
    total_executions: int = 0
    created_at: Optional[datetime] = None


class WorkspaceStats(BaseModel):
    """Detailed workspace statistics."""

    workspace_id: str
    workspace_name: str
    total_users: int
    active_users: int
    total_agents: int
    active_agents: int
    total_executions: int
    success_rate: float
    avg_credits_per_day: float
    total_credits_used: int


# =====================================================================
# Workspace Analytics Schemas
# =====================================================================


class HealthFactors(BaseModel):
    """Health score breakdown by factor."""

    activity: int = Field(..., ge=0, le=100, description="Activity score (0-100)")
    engagement: int = Field(..., ge=0, le=100, description="Engagement score (0-100)")
    efficiency: int = Field(..., ge=0, le=100, description="Efficiency score (0-100)")
    reliability: int = Field(..., ge=0, le=100, description="Reliability score (0-100)")

    # Aliases for camelCase compatibility
    class Config:
        populate_by_name = True


class WorkspaceOverview(BaseModel):
    """Workspace overview metrics."""

    # Members
    total_members: int = Field(0, alias="totalMembers")
    active_members: int = Field(0, alias="activeMembers")
    pending_invites: int = Field(0, alias="pendingInvites")
    member_growth: float = Field(0.0, alias="memberGrowth", description="Member growth percentage")

    # Activity
    total_activity: int = Field(0, alias="totalActivity")
    avg_activity_per_member: float = Field(0.0, alias="avgActivityPerMember")
    last_activity_at: Optional[str] = Field(None, alias="lastActivityAt")
    activity_trend: Literal["increasing", "stable", "decreasing"] = Field("stable", alias="activityTrend")

    # Health Score
    health_score: int = Field(0, ge=0, le=100, alias="healthScore")
    health_factors: HealthFactors = Field(..., alias="healthFactors")

    # Status
    status: Literal["active", "idle", "at_risk", "churned"] = "active"
    days_active: int = Field(0, alias="daysActive")
    created_at: str = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True


class MembersByRole(BaseModel):
    """Member count breakdown by role."""

    owner: int = 0
    admin: int = 0
    member: int = 0
    viewer: int = 0

    class Config:
        populate_by_name = True


class MemberActivityItem(BaseModel):
    """Individual member activity metrics."""

    user_id: str = Field(..., alias="userId")
    user_name: str = Field(..., alias="userName")
    role: str
    activity_count: int = Field(0, alias="activityCount")
    last_active_at: Optional[str] = Field(None, alias="lastActiveAt")
    engagement_level: Literal["high", "medium", "low", "inactive"] = Field("low", alias="engagementLevel")

    class Config:
        populate_by_name = True


class TopContributor(BaseModel):
    """Top contributor metrics."""

    user_id: str = Field(..., alias="userId")
    user_name: str = Field(..., alias="userName")
    contribution: Dict[str, Any]  # agentRuns, successRate, creditsUsed

    class Config:
        populate_by_name = True


class InactiveMember(BaseModel):
    """Inactive member details."""

    user_id: str = Field(..., alias="userId")
    user_name: str = Field(..., alias="userName")
    last_active_at: str = Field(..., alias="lastActiveAt")
    days_since_active: int = Field(..., alias="daysSinceActive")

    class Config:
        populate_by_name = True


class MemberAnalytics(BaseModel):
    """Member analytics data."""

    members_by_role: MembersByRole = Field(..., alias="membersByRole")
    activity_distribution: List[MemberActivityItem] = Field(default_factory=list, alias="activityDistribution")
    top_contributors: List[TopContributor] = Field(default_factory=list, alias="topContributors")
    inactive_members: List[InactiveMember] = Field(default_factory=list, alias="inactiveMembers")

    class Config:
        populate_by_name = True


class AgentPerformance(BaseModel):
    """Individual agent performance metrics."""

    agent_id: str = Field(..., alias="agentId")
    agent_name: str = Field(..., alias="agentName")
    runs: int = 0
    success_rate: float = Field(0.0, alias="successRate")
    avg_runtime: float = Field(0.0, alias="avgRuntime", description="Average runtime in seconds")
    credits_consumed: float = Field(0.0, alias="creditsConsumed")
    last_run_at: Optional[str] = Field(None, alias="lastRunAt")

    class Config:
        populate_by_name = True


class AgentEfficiency(BaseModel):
    """Agent efficiency metrics."""

    most_efficient: Optional[str] = Field(None, alias="mostEfficient")
    least_efficient: Optional[str] = Field(None, alias="leastEfficient")
    avg_success_rate: float = Field(0.0, alias="avgSuccessRate")
    avg_runtime: float = Field(0.0, alias="avgRuntime")

    class Config:
        populate_by_name = True


class AgentUsage(BaseModel):
    """Agent usage analytics."""

    total_agents: int = Field(0, alias="totalAgents")
    active_agents: int = Field(0, alias="activeAgents")
    agents: List[AgentPerformance] = Field(default_factory=list)
    usage_by_agent: Dict[str, Any] = Field(default_factory=dict, alias="usageByAgent")
    agent_efficiency: AgentEfficiency = Field(..., alias="agentEfficiency")

    class Config:
        populate_by_name = True


class DailyConsumption(BaseModel):
    """Daily credit consumption."""

    date: str
    credits: float

    class Config:
        populate_by_name = True


class Credits(BaseModel):
    """Credit utilization metrics."""

    allocated: float = 0.0
    consumed: float = 0.0
    remaining: float = 0.0
    utilization_rate: float = Field(0.0, alias="utilizationRate")
    projected_exhaustion: Optional[str] = Field(None, alias="projectedExhaustion")
    consumption_by_model: Dict[str, Dict[str, float]] = Field(default_factory=dict, alias="consumptionByModel")
    daily_consumption: List[DailyConsumption] = Field(default_factory=list, alias="dailyConsumption")

    class Config:
        populate_by_name = True


class Storage(BaseModel):
    """Storage utilization metrics."""

    used: int = Field(0, description="Bytes used")
    limit: int = Field(10737418240, description="Storage limit in bytes (default 10GB)")
    utilization_rate: float = Field(0.0, alias="utilizationRate")
    breakdown: Dict[str, int] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class APIUsage(BaseModel):
    """API usage metrics."""

    total_calls: int = Field(0, alias="totalCalls")
    rate_limit: int = Field(0, alias="rateLimit")
    utilization_rate: float = Field(0.0, alias="utilizationRate")
    by_endpoint: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="byEndpoint")

    class Config:
        populate_by_name = True


class ResourceUtilization(BaseModel):
    """Resource utilization metrics."""

    credits: Credits
    storage: Storage
    api_usage: APIUsage = Field(..., alias="apiUsage")

    class Config:
        populate_by_name = True


class UsageLimit(BaseModel):
    """Usage vs limit tracking."""

    used: int
    limit: int

    class Config:
        populate_by_name = True


class BillingHistory(BaseModel):
    """Billing history item."""

    date: str
    amount: float
    status: Literal["paid", "pending", "failed"]

    class Config:
        populate_by_name = True


class BillingRecommendation(BaseModel):
    """Billing optimization recommendation."""

    type: Literal["upgrade", "downgrade", "add_on"]
    reason: str
    estimated_savings: float = Field(..., alias="estimatedSavings")

    class Config:
        populate_by_name = True


class Billing(BaseModel):
    """Billing and subscription information."""

    plan: str
    status: Literal["active", "trial", "past_due", "cancelled"]
    current_month_cost: float = Field(0.0, alias="currentMonthCost")
    projected_month_cost: float = Field(0.0, alias="projectedMonthCost")
    last_month_cost: float = Field(0.0, alias="lastMonthCost")
    limits: Dict[str, UsageLimit]
    history: List[BillingHistory] = Field(default_factory=list)
    recommendations: List[BillingRecommendation] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class WorkspaceRanking(BaseModel):
    """Workspace ranking information."""

    overall: int
    total_workspaces: int = Field(..., alias="totalWorkspaces")
    percentile: float

    class Config:
        populate_by_name = True


class Benchmarks(BaseModel):
    """Benchmark comparisons vs average."""

    activity_vs_avg: float = Field(..., alias="activityVsAvg", description="Percentage difference from average")
    efficiency_vs_avg: float = Field(..., alias="efficiencyVsAvg", description="Percentage difference from average")
    cost_vs_avg: float = Field(..., alias="costVsAvg", description="Percentage difference from average")

    class Config:
        populate_by_name = True


class SimilarWorkspace(BaseModel):
    """Similar workspace comparison."""

    workspace_id: str = Field(..., alias="workspaceId")
    similarity: float = Field(..., ge=0, le=100, description="Similarity score 0-100")
    metrics: Dict[str, Any]

    class Config:
        populate_by_name = True


class WorkspaceComparison(BaseModel):
    """Workspace comparison data (admin only)."""

    ranking: WorkspaceRanking
    benchmarks: Benchmarks
    similar_workspaces: List[SimilarWorkspace] = Field(default_factory=list, alias="similarWorkspaces")

    class Config:
        populate_by_name = True


class WorkspaceAnalytics(BaseModel):
    """Complete workspace analytics response."""

    workspace_id: str = Field(..., alias="workspaceId")
    workspace_name: str = Field(..., alias="workspaceName")
    plan: Literal["free", "starter", "pro", "enterprise"]
    timeframe: str
    overview: WorkspaceOverview
    member_analytics: MemberAnalytics = Field(..., alias="memberAnalytics")
    agent_usage: AgentUsage = Field(..., alias="agentUsage")
    resource_utilization: ResourceUtilization = Field(..., alias="resourceUtilization")
    billing: Billing
    comparison: Optional[WorkspaceComparison] = None

    class Config:
        populate_by_name = True
