"""
Comparison Views Models
Pydantic models for side-by-side comparison views
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class ComparisonType(str, Enum):
    """Type of comparison"""
    AGENTS = "agents"
    PERIODS = "periods"
    WORKSPACES = "workspaces"
    METRICS = "metrics"


class RecommendationType(str, Enum):
    """Type of recommendation"""
    PERFORMANCE = "performance"
    COST = "cost"
    RELIABILITY = "reliability"
    USER_EXPERIENCE = "user_experience"


class RecommendationPriority(str, Enum):
    """Priority level of recommendation"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TrendDirection(str, Enum):
    """Trend direction"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class ChangeDirection(str, Enum):
    """Change direction interpretation"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class InsightType(str, Enum):
    """Type of insight"""
    TREND = "trend"
    ANOMALY = "anomaly"
    OPPORTUNITY = "opportunity"
    WARNING = "warning"


class InsightSeverity(str, Enum):
    """Severity of insight"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OutlierType(str, Enum):
    """Type of outlier"""
    HIGH = "high"
    LOW = "low"


class OutlierSeverity(str, Enum):
    """Severity of outlier"""
    MILD = "mild"
    MODERATE = "moderate"
    EXTREME = "extreme"


class CorrelationStrength(str, Enum):
    """Strength of correlation"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class CorrelationDirection(str, Enum):
    """Direction of correlation"""
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ExportFormat(str, Enum):
    """Export format"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"


class DiffColor(str, Enum):
    """Visual diff color"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    GRAY = "gray"


# ============================================================================
# Agent Comparison Models
# ============================================================================

class AgentMetrics(BaseModel):
    """Metrics for a single agent"""
    success_rate: float = Field(..., ge=0, le=100)
    average_runtime: float = Field(..., ge=0)
    total_runs: int = Field(..., ge=0)
    error_rate: float = Field(..., ge=0, le=100)
    cost_per_run: float = Field(..., ge=0)
    total_cost: float = Field(..., ge=0)
    p50_runtime: float = Field(..., ge=0)
    p95_runtime: float = Field(..., ge=0)
    p99_runtime: float = Field(..., ge=0)
    throughput: float = Field(..., ge=0)
    user_satisfaction: Optional[float] = Field(None, ge=0, le=5)
    credits_per_run: float = Field(..., ge=0)


class AgentComparisonItem(BaseModel):
    """Single agent in comparison"""
    id: str
    name: str
    version: Optional[str] = None
    metrics: AgentMetrics
    tags: Optional[List[str]] = None
    last_run_at: Optional[datetime] = None


class MetricDifference(BaseModel):
    """Difference between metrics"""
    best: str
    worst: str
    delta: float
    delta_percent: float
    values: Dict[str, float]


class Recommendation(BaseModel):
    """Optimization recommendation"""
    type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    affected_agents: List[str]
    potential_impact: Optional[Dict[str, float]] = None


class AgentComparison(BaseModel):
    """Agent comparison results"""
    agents: List[AgentComparisonItem]
    differences: Dict[str, MetricDifference]
    winner: str
    winner_score: float = Field(..., ge=0, le=100)
    recommendations: List[Recommendation]
    export_url: Optional[str] = None


# ============================================================================
# Period Comparison Models
# ============================================================================

class PeriodMetrics(BaseModel):
    """Metrics for a time period"""
    period: str
    start_date: datetime
    end_date: datetime
    total_runs: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=100)
    average_runtime: float = Field(..., ge=0)
    total_cost: float = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    active_agents: int = Field(..., ge=0)
    active_users: int = Field(..., ge=0)
    throughput: float = Field(..., ge=0)
    p95_runtime: float = Field(..., ge=0)
    credit_consumption: float = Field(..., ge=0)


class ChangeDetail(BaseModel):
    """Detail of change between periods"""
    absolute: float
    percent: float
    trend: TrendDirection
    significant: bool
    direction: ChangeDirection


class TimeSeriesPoint(BaseModel):
    """Single point in time series"""
    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesComparison(BaseModel):
    """Time series comparison data"""
    current_period_data: List[TimeSeriesPoint]
    previous_period_data: List[TimeSeriesPoint]
    metric: str
    unit: str


class ChangeMetrics(BaseModel):
    """Changes between periods"""
    total_runs: ChangeDetail
    success_rate: ChangeDetail
    average_runtime: ChangeDetail
    total_cost: ChangeDetail
    error_count: ChangeDetail
    active_agents: ChangeDetail
    active_users: ChangeDetail
    throughput: ChangeDetail
    p95_runtime: ChangeDetail
    credit_consumption: ChangeDetail


class PeriodComparison(BaseModel):
    """Period-over-period comparison"""
    current: PeriodMetrics
    previous: PeriodMetrics
    change: ChangeMetrics
    improvements: List[str]
    regressions: List[str]
    summary: str
    time_series_comparison: Optional[TimeSeriesComparison] = None
    export_url: Optional[str] = None


# ============================================================================
# Workspace Comparison Models
# ============================================================================

class WorkspaceMetrics(BaseModel):
    """Metrics for a workspace"""
    workspace_id: str
    workspace_name: str
    total_runs: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=100)
    average_runtime: float = Field(..., ge=0)
    total_cost: float = Field(..., ge=0)
    active_agents: int = Field(..., ge=0)
    active_users: int = Field(..., ge=0)
    credit_usage: float = Field(..., ge=0)
    error_rate: float = Field(..., ge=0, le=100)
    throughput: float = Field(..., ge=0)
    user_satisfaction: Optional[float] = Field(None, ge=0, le=5)
    tags: Optional[List[str]] = None


class TopPerformer(BaseModel):
    """Top performing entity"""
    workspace_id: str
    workspace_name: str
    score: float = Field(..., ge=0, le=100)


class BenchmarkMetrics(BaseModel):
    """Benchmark metrics across workspaces"""
    average_success_rate: float = Field(..., ge=0, le=100)
    average_runtime: float = Field(..., ge=0)
    average_cost: float = Field(..., ge=0)
    average_throughput: float = Field(..., ge=0)
    top_performer: TopPerformer
    bottom_performer: TopPerformer


class WorkspaceRanking(BaseModel):
    """Ranking for a workspace"""
    rank: int = Field(..., ge=1)
    workspace_id: str
    workspace_name: str
    score: float = Field(..., ge=0, le=100)
    percentile: float = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]


class RankingMetrics(BaseModel):
    """Ranking metrics"""
    rankings: List[WorkspaceRanking]
    score_method: Literal["weighted", "composite", "custom"]
    weights: Optional[Dict[str, float]] = None


class ComparisonInsight(BaseModel):
    """Insight from comparison"""
    type: InsightType
    severity: InsightSeverity
    title: str
    description: str
    affected_workspaces: List[str]
    data_points: Optional[Dict[str, float]] = None


class WorkspaceComparison(BaseModel):
    """Workspace comparison results"""
    workspaces: List[WorkspaceMetrics]
    benchmarks: BenchmarkMetrics
    rankings: RankingMetrics
    insights: List[ComparisonInsight]
    export_url: Optional[str] = None


# ============================================================================
# Metric Comparison Models
# ============================================================================

class MetricEntity(BaseModel):
    """Entity in metric comparison"""
    id: str
    name: str
    value: float
    percentile: float = Field(..., ge=0, le=100)
    deviation_from_mean: float
    trend: Optional[Literal["increasing", "decreasing", "stable"]] = None
    sparkline_data: Optional[List[float]] = None


class MetricStatistics(BaseModel):
    """Statistical measures"""
    mean: float
    median: float
    standard_deviation: float
    min: float
    max: float
    p25: float
    p75: float
    p90: float
    p95: float
    p99: float
    variance: float
    coefficient_of_variation: float


class DistributionBucket(BaseModel):
    """Bucket in distribution"""
    min: float
    max: float
    count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)
    label: str


class MetricDistribution(BaseModel):
    """Distribution of metric values"""
    buckets: List[DistributionBucket]
    skewness: float
    kurtosis: float
    is_normal: bool


class MetricOutlier(BaseModel):
    """Outlier in metric data"""
    entity_id: str
    entity_name: str
    value: float
    z_score: float
    type: OutlierType
    severity: OutlierSeverity


class MetricCorrelation(BaseModel):
    """Correlation between metrics"""
    metric1: str
    metric2: str
    coefficient: float = Field(..., ge=-1, le=1)
    strength: CorrelationStrength
    direction: CorrelationDirection
    p_value: float = Field(..., ge=0, le=1)
    significant: bool


class MetricComparison(BaseModel):
    """Metric comparison results"""
    metric_name: str
    metric_type: Literal["performance", "cost", "reliability", "usage"]
    entities: List[MetricEntity]
    statistics: MetricStatistics
    distribution: MetricDistribution
    outliers: List[MetricOutlier]
    correlations: Optional[List[MetricCorrelation]] = None
    export_url: Optional[str] = None


# ============================================================================
# Visual Diff Models
# ============================================================================

class VisualDiffItem(BaseModel):
    """Item in visual diff"""
    id: str
    name: str
    value: float
    baseline: float
    difference: float
    percent_difference: float
    highlight: bool
    color: DiffColor
    trend: Optional[TrendDirection] = None


class VisualDiff(BaseModel):
    """Visual diff display"""
    metric: str
    items: List[VisualDiffItem]
    highlight_threshold: Optional[float] = None


# ============================================================================
# Filters and Options Models
# ============================================================================

class ComparisonFilters(BaseModel):
    """Filters for comparison"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    agent_ids: Optional[List[str]] = None
    workspace_ids: Optional[List[str]] = None
    metric_names: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_success_rate: Optional[float] = Field(None, ge=0, le=100)
    max_cost: Optional[float] = Field(None, ge=0)

    @field_validator('end_date')
    @classmethod
    def validate_end_date_not_future(cls, v):
        """Validate end_date is not in the future"""
        if v and v > datetime.utcnow():
            raise ValueError("end_date cannot be in the future")
        return v

    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v, info):
        """Validate start_date is before end_date"""
        if v and info.data.get('end_date'):
            if v > info.data['end_date']:
                raise ValueError("start_date must be before end_date")

            # Ensure date range is reasonable (not more than 1 year)
            delta = info.data['end_date'] - v
            if delta.days > 365:
                raise ValueError("Date range cannot exceed 365 days")
        return v

    @field_validator('agent_ids')
    @classmethod
    def validate_agent_ids(cls, v):
        """Validate agent IDs are not empty strings"""
        if v:
            # Remove any empty strings
            v = [aid.strip() for aid in v if aid and aid.strip()]
            if not v:
                raise ValueError("agent_ids cannot contain only empty strings")
            if len(v) > 10:
                raise ValueError("Maximum 10 agents allowed for comparison")
        return v

    @field_validator('workspace_ids')
    @classmethod
    def validate_workspace_ids(cls, v):
        """Validate workspace IDs are not empty strings"""
        if v:
            # Remove any empty strings
            v = [wid.strip() for wid in v if wid and wid.strip()]
            if not v:
                raise ValueError("workspace_ids cannot contain only empty strings")
            if len(v) > 20:
                raise ValueError("Maximum 20 workspaces allowed for comparison")
        return v

    @field_validator('metric_names')
    @classmethod
    def validate_metric_names(cls, v):
        """Validate metric names are valid"""
        if v:
            valid_metrics = {
                "success_rate",
                "error_rate",
                "average_runtime",
                "throughput",
                "cost_per_run",
                "total_runs",
                "credits_per_run",
            }
            invalid = [m for m in v if m not in valid_metrics]
            if invalid:
                raise ValueError(f"Invalid metric names: {', '.join(invalid)}")
        return v


class ComparisonOptions(BaseModel):
    """Options for comparison"""
    include_time_series: bool = False
    include_recommendations: bool = True
    include_visual_diff: bool = True
    include_statistics: bool = True
    include_correlations: bool = False
    export_format: Optional[ExportFormat] = None
    group_by: Optional[Literal["day", "week", "month"]] = None


# ============================================================================
# Main Comparison Models
# ============================================================================

class ComparisonViews(BaseModel):
    """Main comparison views container"""
    type: ComparisonType
    timestamp: datetime
    agent_comparison: Optional[AgentComparison] = None
    period_comparison: Optional[PeriodComparison] = None
    workspace_comparison: Optional[WorkspaceComparison] = None
    metric_comparison: Optional[MetricComparison] = None


class ComparisonReport(BaseModel):
    """Comparison report for export"""
    id: str
    type: ComparisonType
    created_at: datetime
    created_by: str
    title: str
    description: Optional[str] = None
    filters: ComparisonFilters
    data: ComparisonViews
    format: ExportFormat
    download_url: str
    expires_at: Optional[datetime] = None


# ============================================================================
# Request/Response Models
# ============================================================================

class ComparisonRequest(BaseModel):
    """Request for comparison"""
    type: ComparisonType
    filters: ComparisonFilters
    options: Optional[ComparisonOptions] = None


class ComparisonMetadata(BaseModel):
    """Metadata about comparison"""
    generated_at: datetime
    processing_time: float = Field(..., ge=0)
    entity_count: int = Field(..., ge=0)
    data_points: int = Field(..., ge=0)


class ComparisonError(BaseModel):
    """Error response"""
    code: str
    message: str


class ComparisonResponse(BaseModel):
    """Response for comparison"""
    success: bool
    data: Optional[ComparisonViews] = None
    metadata: ComparisonMetadata
    error: Optional[ComparisonError] = None
