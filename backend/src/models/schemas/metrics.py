"""Metric schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class TimeRange(BaseModel):
    """Time range for queries."""

    start_date: date
    end_date: date


class Period(BaseModel):
    """Time period with start and end timestamps."""

    start: str
    end: str


class MetricValue(BaseModel):
    """Single metric value with timestamp."""

    timestamp: datetime
    value: float
    metric_name: str


class TimeSeriesData(BaseModel):
    """Time series data point."""

    timestamp: str
    value: float
    label: Optional[str] = None
    total: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None


class UserMetrics(BaseModel):
    """User engagement metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    dau: int
    dau_change: float
    wau: int
    wau_change: float
    mau: int
    mau_change: float
    new_users: int
    churned_users: int
    active_rate: float


class ExecutionMetrics(BaseModel):
    """Execution performance metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_runs: int
    total_runs_change: float
    successful_runs: int
    failed_runs: int
    success_rate: float
    success_rate_change: float
    avg_runtime: float
    p95_runtime: float
    total_credits_used: int
    credits_change: float


class BusinessMetrics(BaseModel):
    """Business and financial metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    mrr: float
    mrr_change: float
    arr: float
    ltv: float
    cac: float
    ltv_cac_ratio: float
    active_workspaces: int
    paid_workspaces: int
    trial_workspaces: int
    churn_rate: float


class TopAgent(BaseModel):
    """Top performing agent."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    name: str
    runs: int
    success_rate: float
    avg_runtime: float


class AgentMetrics(BaseModel):
    """Agent performance metrics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_agents: int
    active_agents: int
    top_agents: List[TopAgent]


class TopUser(BaseModel):
    """Top user by activity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    name: str
    email: str
    total_runs: int
    credits_used: int
    last_active: str


class Alert(BaseModel):
    """System alert."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    type: str
    message: str
    severity: str
    triggered_at: str


class TrendData(BaseModel):
    """Trend data for all metrics."""

    execution: List[TimeSeriesData]
    users: List[TimeSeriesData]
    revenue: List[TimeSeriesData]
    errors: List[TimeSeriesData]


class ExecutiveMetrics(BaseModel):
    """Legacy executive dashboard metrics."""

    mrr: float = Field(..., description="Monthly Recurring Revenue")
    churn_rate: float = Field(..., description="Customer churn rate")
    ltv: float = Field(..., description="Customer Lifetime Value")
    dau: int = Field(..., description="Daily Active Users")
    wau: int = Field(..., description="Weekly Active Users")
    mau: int = Field(..., description="Monthly Active Users")
    total_executions: int = Field(default=0)
    success_rate: float = Field(default=0.0)


class ExecutiveDashboardResponse(BaseModel):
    """Comprehensive executive dashboard response."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    timeframe: str
    period: Period
    user_metrics: UserMetrics
    execution_metrics: ExecutionMetrics
    business_metrics: BusinessMetrics
    agent_metrics: AgentMetrics
    trends: TrendData
    active_alerts: List[Alert]
    top_users: Optional[List[TopUser]] = []


class MetricTrend(BaseModel):
    """Metric trend data."""

    metric_name: str
    values: List[MetricValue]
    trend_direction: str  # 'up', 'down', 'stable'
    change_percentage: float
