"""Dashboard API response schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# Enums
class GranularityEnum(str, Enum):
    """Time granularity options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ExportFormatEnum(str, Enum):
    """Export format options."""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"


class ExportStatusEnum(str, Enum):
    """Export job status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LeaderboardTypeEnum(str, Enum):
    """Leaderboard types."""
    USERS = "users"
    AGENTS = "agents"
    WORKSPACES = "workspaces"
    FEATURES = "features"


class ActivityTypeEnum(str, Enum):
    """User activity types."""
    LOGIN = "login"
    EXECUTION = "execution"
    API_CALL = "api_call"


# Base Models
class DateRange(BaseModel):
    """Date range for queries."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    start_date: str
    end_date: str


class APIResponse(BaseModel):
    """Base API response wrapper."""

    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Executive Dashboard Schemas
class RevenueMetrics(BaseModel):
    """Revenue metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_revenue: float
    mrr: float
    arr: float
    growth_rate: float


class DashboardUserMetrics(BaseModel):
    """User metrics for dashboard."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_users: int
    active_users: int
    new_users: int
    churn_rate: float


class UsageMetrics(BaseModel):
    """Usage metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_credits: int
    credits_consumed: int
    avg_credits_per_user: int


class PerformanceMetrics(BaseModel):
    """Performance metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    uptime: float
    avg_response_time: float
    error_rate: float


class ExecutiveSummaryResponse(BaseModel):
    """Executive summary response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    revenue_metrics: RevenueMetrics
    user_metrics: DashboardUserMetrics
    usage_metrics: UsageMetrics
    performance_metrics: PerformanceMetrics


class TrendDataPoint(BaseModel):
    """Single trend data point."""

    date: str
    value: float


class TrendMetric(BaseModel):
    """Trend data for a specific metric."""

    metric: str
    data: List[TrendDataPoint]


class ExecutiveTrendsResponse(BaseModel):
    """Executive trends response."""

    trends: List[TrendMetric]


# Agent Analytics Schemas
class AgentPerformanceMetric(BaseModel):
    """Agent performance metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    agent_id: str
    agent_name: str
    total_executions: int
    success_rate: float
    avg_execution_time: float
    error_rate: float
    credits_consumed: int
    user_satisfaction: Optional[float] = None


class AgentAggregates(BaseModel):
    """Agent aggregate metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_agents: int
    avg_success_rate: float
    total_executions: int


class AgentPerformanceResponse(BaseModel):
    """Agent performance response."""

    agents: List[AgentPerformanceMetric]
    aggregates: AgentAggregates


class AgentUsageDataPoint(BaseModel):
    """Agent usage data point."""

    timestamp: str
    executions: int
    unique_users: int
    credits: int
    errors: int


class AgentUsageResponse(BaseModel):
    """Agent usage response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    usage_pattern: List[AgentUsageDataPoint]
    peak_hours: List[int]
    busiest_days: List[str]


# User Activity Schemas
class UserActivityMetric(BaseModel):
    """User activity metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    user_id: str
    email: str
    last_active: str
    total_sessions: int
    total_executions: int
    credits_consumed: int
    favorite_agents: List[str]


class ActivitySummary(BaseModel):
    """Activity summary."""

    dau: int
    wau: int
    mau: int
    avg_session_duration: float = Field(alias="avgSessionDuration")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class UserActivityResponse(BaseModel):
    """User activity response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    users: List[UserActivityMetric]
    activity_summary: ActivitySummary


class EngagementMetrics(BaseModel):
    """Engagement metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    activation_rate: float
    retention_day_1: float
    retention_day_7: float
    retention_day_30: float


class CohortData(BaseModel):
    """Cohort data."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    cohort_date: str
    users: int
    retention: List[float]


class CohortAnalysis(BaseModel):
    """Cohort analysis."""

    cohorts: List[CohortData]


class UserEngagementResponse(BaseModel):
    """User engagement response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    engagement_metrics: EngagementMetrics
    cohort_analysis: CohortAnalysis


# Workspace Schemas
class WorkspaceInfo(BaseModel):
    """Workspace information."""

    id: str
    name: str
    created_at: str = Field(alias="createdAt")
    plan: str
    seats: int
    seats_used: int = Field(alias="seatsUsed")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class WorkspaceUsage(BaseModel):
    """Workspace usage."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_credits: int
    credits_consumed: int
    credits_remaining: int
    reset_date: str


class WorkspaceActivity(BaseModel):
    """Workspace activity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    active_users_today: int
    total_executions_today: int
    top_agents: List[str]


class WorkspaceOverviewResponse(BaseModel):
    """Workspace overview response."""

    workspace: WorkspaceInfo
    usage: WorkspaceUsage
    activity: WorkspaceActivity


class WorkspaceComparisonMetrics(BaseModel):
    """Workspace comparison metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_users: int
    credits_consumed: int
    avg_success_rate: float


class WorkspaceComparison(BaseModel):
    """Workspace comparison."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workspace_id: str
    workspace_name: str
    metrics: WorkspaceComparisonMetrics


class WorkspaceRankings(BaseModel):
    """Workspace rankings."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    by_users: List[str]
    by_usage: List[str]


class WorkspaceComparisonResponse(BaseModel):
    """Workspace comparison response."""

    comparisons: List[WorkspaceComparison]
    rankings: WorkspaceRankings


# Real-time Metrics Schemas
class RealtimeMetrics(BaseModel):
    """Real-time metrics."""

    timestamp: str
    metrics: Dict[str, Any]


# Leaderboard Schemas
class LeaderboardDetails(BaseModel):
    """Leaderboard entry details."""

    executions: Optional[int] = None
    success_rate: Optional[float] = Field(None, alias="successRate")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    rank: int
    entity_id: str
    entity_name: str
    score: float
    change: int
    details: LeaderboardDetails


class UserRank(BaseModel):
    """User's rank in leaderboard."""

    rank: int
    score: float
    percentile: float


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    leaderboard: List[LeaderboardEntry]
    user_rank: Optional[UserRank] = None


# Export Schemas
class ExportConfig(BaseModel):
    """Export configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    format: ExportFormatEnum
    data_types: List[str]
    date_range: DateRange


class ExportJobResponse(BaseModel):
    """Export job response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    job_id: str
    status: ExportStatusEnum
    estimated_time: Optional[int] = None


class ExportStatusResponse(BaseModel):
    """Export status response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    job_id: str
    status: ExportStatusEnum
    progress: Optional[float] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100, alias="perPage")
    sort_by: Optional[str] = Field(None, alias="sortBy")
    order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class PaginatedResponse(BaseModel):
    """Paginated response."""

    items: List[Any]
    total: int
    page: int
    per_page: int = Field(alias="perPage")
    pages: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# Error Response
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    status_code: int = Field(alias="statusCode")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
