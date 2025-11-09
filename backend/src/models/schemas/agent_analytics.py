"""Comprehensive agent analytics schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class RuntimeMetrics(BaseModel):
    """Runtime statistics."""

    average: float = Field(..., description="Average runtime in seconds")
    median: float = Field(..., description="Median runtime in seconds")
    min: float = Field(..., description="Minimum runtime in seconds")
    max: float = Field(..., description="Maximum runtime in seconds")
    p50: float = Field(..., description="50th percentile runtime")
    p75: float = Field(..., description="75th percentile runtime")
    p90: float = Field(..., description="90th percentile runtime")
    p95: float = Field(..., description="95th percentile runtime")
    p99: float = Field(..., description="99th percentile runtime")
    standardDeviation: float = Field(..., alias="standardDeviation", description="Standard deviation")

    class Config:
        populate_by_name = True


class ThroughputMetrics(BaseModel):
    """Throughput statistics."""

    runsPerHour: float = Field(..., alias="runsPerHour")
    runsPerDay: float = Field(..., alias="runsPerDay")
    peakConcurrency: int = Field(..., alias="peakConcurrency")
    avgConcurrency: float = Field(..., alias="avgConcurrency")

    class Config:
        populate_by_name = True


class PerformanceMetrics(BaseModel):
    """Performance metrics."""

    totalRuns: int = Field(..., alias="totalRuns")
    successfulRuns: int = Field(..., alias="successfulRuns")
    failedRuns: int = Field(..., alias="failedRuns")
    cancelledRuns: int = Field(..., alias="cancelledRuns")
    successRate: float = Field(..., alias="successRate")
    availabilityRate: float = Field(..., alias="availabilityRate")
    runtime: RuntimeMetrics
    throughput: ThroughputMetrics

    class Config:
        populate_by_name = True


class ModelUsageDetail(BaseModel):
    """Model usage breakdown."""

    calls: int
    tokens: int
    credits: float


class ResourceUsage(BaseModel):
    """Resource usage metrics."""

    totalCreditsConsumed: float = Field(..., alias="totalCreditsConsumed")
    avgCreditsPerRun: float = Field(..., alias="avgCreditsPerRun")
    totalTokensUsed: int = Field(..., alias="totalTokensUsed")
    avgTokensPerRun: float = Field(..., alias="avgTokensPerRun")
    costPerRun: float = Field(..., alias="costPerRun")
    totalCost: float = Field(..., alias="totalCost")
    modelUsage: Dict[str, ModelUsageDetail] = Field(..., alias="modelUsage")

    class Config:
        populate_by_name = True


class ErrorTypeDetail(BaseModel):
    """Error type breakdown."""

    count: int
    percentage: float
    category: str
    severity: str
    lastOccurred: Optional[str] = Field(None, alias="lastOccurred")
    exampleMessage: str = Field(..., alias="exampleMessage")
    avgRecoveryTime: float = Field(..., alias="avgRecoveryTime")
    autoRecoveryRate: float = Field(..., alias="autoRecoveryRate")

    class Config:
        populate_by_name = True


class ErrorPattern(BaseModel):
    """Error pattern analysis."""

    pattern: str
    frequency: int
    impact: str = Field(..., description="Impact level: low, medium, high")
    suggestedFix: str = Field(..., alias="suggestedFix")

    class Config:
        populate_by_name = True


class ErrorAnalysis(BaseModel):
    """Error analysis metrics."""

    totalErrors: int = Field(..., alias="totalErrors")
    errorRate: float = Field(..., alias="errorRate")
    errorsByType: Dict[str, ErrorTypeDetail] = Field(..., alias="errorsByType")
    errorPatterns: List[ErrorPattern] = Field(..., alias="errorPatterns")
    meanTimeToRecovery: float = Field(..., alias="meanTimeToRecovery")
    autoRecoveryRate: float = Field(..., alias="autoRecoveryRate")

    class Config:
        populate_by_name = True


class RatingDistribution(BaseModel):
    """User rating distribution."""

    # Using string keys for JSON compatibility
    rating_5: int = Field(..., alias="5")
    rating_4: int = Field(..., alias="4")
    rating_3: int = Field(..., alias="3")
    rating_2: int = Field(..., alias="2")
    rating_1: int = Field(..., alias="1")

    class Config:
        populate_by_name = True


class UserRatings(BaseModel):
    """User ratings summary."""

    average: float
    total: int
    distribution: RatingDistribution


class UserFeedback(BaseModel):
    """Individual user feedback."""

    userId: str = Field(..., alias="userId")
    rating: int
    comment: str
    timestamp: str

    class Config:
        populate_by_name = True


class TopUser(BaseModel):
    """Top user by activity."""

    userId: str = Field(..., alias="userId")
    runCount: int = Field(..., alias="runCount")
    successRate: float = Field(..., alias="successRate")

    class Config:
        populate_by_name = True


class UserMetrics(BaseModel):
    """User interaction metrics."""

    uniqueUsers: int = Field(..., alias="uniqueUsers")
    totalInteractions: int = Field(..., alias="totalInteractions")
    avgInteractionsPerUser: float = Field(..., alias="avgInteractionsPerUser")
    userRatings: UserRatings = Field(..., alias="userRatings")
    feedback: List[UserFeedback] = Field(default_factory=list)
    usageByHour: List[int] = Field(..., alias="usageByHour")
    usageByDayOfWeek: List[int] = Field(..., alias="usageByDayOfWeek")
    topUsers: List[TopUser] = Field(..., alias="topUsers")

    class Config:
        populate_by_name = True


class WorkspaceComparison(BaseModel):
    """Comparison vs workspace average."""

    successRate: float = Field(..., alias="successRate")
    runtime: float
    creditEfficiency: float = Field(..., alias="creditEfficiency")

    class Config:
        populate_by_name = True


class AllAgentsComparison(BaseModel):
    """Comparison vs all agents."""

    rank: int
    percentile: float


class PreviousPeriodComparison(BaseModel):
    """Comparison vs previous period."""

    runsChange: float = Field(..., alias="runsChange")
    successRateChange: float = Field(..., alias="successRateChange")
    runtimeChange: float = Field(..., alias="runtimeChange")
    costChange: float = Field(..., alias="costChange")

    class Config:
        populate_by_name = True


class ComparisonMetrics(BaseModel):
    """Comparative analysis."""

    vsWorkspaceAverage: WorkspaceComparison = Field(..., alias="vsWorkspaceAverage")
    vsAllAgents: AllAgentsComparison = Field(..., alias="vsAllAgents")
    vsPreviousPeriod: PreviousPeriodComparison = Field(..., alias="vsPreviousPeriod")

    class Config:
        populate_by_name = True


class OptimizationSuggestion(BaseModel):
    """Optimization recommendation."""

    type: str = Field(..., description="Type: performance, cost, reliability, user_experience")
    title: str
    description: str
    estimatedImpact: str = Field(..., alias="estimatedImpact")
    effort: str = Field(..., description="Effort level: low, medium, high")

    class Config:
        populate_by_name = True


class TimeSeriesDataPoint(BaseModel):
    """Time series data point."""

    timestamp: str
    runs: int
    successRate: float = Field(..., alias="successRate")
    avgRuntime: float = Field(..., alias="avgRuntime")
    credits: float
    errors: int

    class Config:
        populate_by_name = True


class TrendData(BaseModel):
    """Trend time series data."""

    daily: List[TimeSeriesDataPoint] = Field(default_factory=list)
    hourly: List[TimeSeriesDataPoint] = Field(default_factory=list)


class AgentAnalyticsResponse(BaseModel):
    """Complete agent analytics response."""

    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    timeframe: str
    generatedAt: str = Field(..., alias="generatedAt")
    performance: PerformanceMetrics
    resources: ResourceUsage
    errors: ErrorAnalysis
    userMetrics: UserMetrics = Field(..., alias="userMetrics")
    comparison: ComparisonMetrics
    optimizations: List[OptimizationSuggestion] = Field(default_factory=list)
    trends: TrendData

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "agentId": "550e8400-e29b-41d4-a716-446655440000",
                "workspaceId": "660e8400-e29b-41d4-a716-446655440000",
                "timeframe": "7d",
                "generatedAt": "2025-11-09T10:00:00Z",
                "performance": {
                    "totalRuns": 1250,
                    "successfulRuns": 1180,
                    "failedRuns": 50,
                    "cancelledRuns": 20,
                    "successRate": 94.4,
                    "availabilityRate": 96.0,
                    "runtime": {
                        "average": 5.2,
                        "median": 4.8,
                        "min": 0.5,
                        "max": 45.3,
                        "p50": 4.8,
                        "p75": 6.2,
                        "p90": 8.5,
                        "p95": 12.1,
                        "p99": 25.3,
                        "standardDeviation": 3.4,
                    },
                    "throughput": {
                        "runsPerHour": 7.44,
                        "runsPerDay": 178.6,
                        "peakConcurrency": 5,
                        "avgConcurrency": 2.3,
                    },
                },
            }
        }


# Agent listing schemas
class AgentListItem(BaseModel):
    """Agent list item with summary metrics."""

    agentId: str = Field(..., alias="agentId")
    agentName: str = Field(..., alias="agentName")
    agentType: str = Field(..., alias="agentType")
    workspaceId: str = Field(..., alias="workspaceId")
    totalRuns: int = Field(..., alias="totalRuns")
    successRate: float = Field(..., alias="successRate")
    avgRuntime: float = Field(..., alias="avgRuntime")
    lastRunAt: Optional[str] = Field(None, alias="lastRunAt")

    class Config:
        populate_by_name = True


class AgentListResponse(BaseModel):
    """Agent list response."""

    agents: List[AgentListItem]
    total: int
    skip: int
    limit: int
