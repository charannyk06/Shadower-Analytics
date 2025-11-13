"""Agent execution analytics schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TokensUsed(BaseModel):
    """Tokens usage breakdown."""

    prompt: int = Field(..., description="Prompt tokens used")
    completion: int = Field(..., description="Completion tokens used")
    total: int = Field(..., description="Total tokens used")


class ExecutionStep(BaseModel):
    """Individual execution step details."""

    stepIndex: int = Field(..., alias="stepIndex")
    stepName: str = Field(..., alias="stepName")
    stepType: Optional[str] = Field(None, alias="stepType")  # 'action', 'decision', 'loop', 'api_call'
    startTime: Optional[str] = Field(None, alias="startTime")
    endTime: Optional[str] = Field(None, alias="endTime")
    durationMs: Optional[int] = Field(None, alias="durationMs")
    status: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    tokensUsed: Optional[int] = Field(None, alias="tokensUsed")

    class Config:
        populate_by_name = True


class ExecutionDetail(BaseModel):
    """Detailed execution information."""

    executionId: str = Field(..., alias="executionId")
    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    userId: str = Field(..., alias="userId")

    # Execution details
    triggerType: Optional[str] = Field(None, alias="triggerType")
    triggerSource: Optional[Dict[str, Any]] = Field(None, alias="triggerSource")
    inputData: Optional[Dict[str, Any]] = Field(None, alias="inputData")
    outputData: Optional[Dict[str, Any]] = Field(None, alias="outputData")

    # Performance metrics
    startTime: str = Field(..., alias="startTime")
    endTime: Optional[str] = Field(None, alias="endTime")
    durationMs: Optional[int] = Field(None, alias="durationMs")
    status: str
    errorMessage: Optional[str] = Field(None, alias="errorMessage")
    errorType: Optional[str] = Field(None, alias="errorType")

    # Resource usage
    creditsConsumed: int = Field(..., alias="creditsConsumed")
    tokensUsed: Optional[TokensUsed] = Field(None, alias="tokensUsed")
    apiCallsCount: int = Field(..., alias="apiCallsCount")
    memoryUsageMb: Optional[float] = Field(None, alias="memoryUsageMb")

    # Execution path
    stepsTotal: Optional[int] = Field(None, alias="stepsTotal")
    stepsCompleted: Optional[int] = Field(None, alias="stepsCompleted")
    executionGraph: Optional[Dict[str, Any]] = Field(None, alias="executionGraph")

    # Context
    environment: Optional[str] = None
    runtimeMode: Optional[str] = Field(None, alias="runtimeMode")
    version: Optional[str] = None

    createdAt: str = Field(..., alias="createdAt")
    updatedAt: str = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True


class ExecutionSummary(BaseModel):
    """Execution summary statistics."""

    totalExecutions: int = Field(..., alias="totalExecutions")
    successfulExecutions: int = Field(..., alias="successfulExecutions")
    failedExecutions: int = Field(..., alias="failedExecutions")
    timeoutExecutions: int = Field(..., alias="timeoutExecutions")
    successRate: float = Field(..., ge=0, le=100, alias="successRate")
    avgDurationMs: float = Field(..., alias="avgDurationMs")
    medianDurationMs: float = Field(..., alias="medianDurationMs")
    p95DurationMs: float = Field(..., alias="p95DurationMs")
    p99DurationMs: float = Field(..., alias="p99DurationMs")
    totalCreditsConsumed: int = Field(..., alias="totalCreditsConsumed")
    avgCreditsPerExecution: float = Field(..., alias="avgCreditsPerExecution")

    class Config:
        populate_by_name = True


class ExecutionTrendPoint(BaseModel):
    """Execution trend data point."""

    timestamp: str
    executionCount: int = Field(..., alias="executionCount")
    successRate: float = Field(..., alias="successRate")
    avgDuration: float = Field(..., alias="avgDuration")
    failureCount: int = Field(..., alias="failureCount")
    creditsUsed: int = Field(..., alias="creditsUsed")

    class Config:
        populate_by_name = True


class FailureDetail(BaseModel):
    """Failure analysis detail."""

    errorType: str = Field(..., alias="errorType")
    count: int
    percentage: float
    avgDurationBeforeFailure: float = Field(..., alias="avgDurationBeforeFailure")
    lastOccurred: Optional[str] = Field(None, alias="lastOccurred")
    exampleMessage: Optional[str] = Field(None, alias="exampleMessage")

    class Config:
        populate_by_name = True


class FailureAnalysis(BaseModel):
    """Failure analysis metrics."""

    totalFailures: int = Field(..., alias="totalFailures")
    failureRate: float = Field(..., alias="failureRate")
    failuresByType: List[FailureDetail] = Field(..., alias="failuresByType")
    commonPatterns: List[str] = Field(default_factory=list, alias="commonPatterns")

    class Config:
        populate_by_name = True


class PerformanceMetrics(BaseModel):
    """Performance metrics for executions."""

    avgDurationMs: float = Field(..., alias="avgDurationMs")
    medianDurationMs: float = Field(..., alias="medianDurationMs")
    minDurationMs: float = Field(..., alias="minDurationMs")
    maxDurationMs: float = Field(..., alias="maxDurationMs")
    p50DurationMs: float = Field(..., alias="p50DurationMs")
    p75DurationMs: float = Field(..., alias="p75DurationMs")
    p90DurationMs: float = Field(..., alias="p90DurationMs")
    p95DurationMs: float = Field(..., alias="p95DurationMs")
    p99DurationMs: float = Field(..., alias="p99DurationMs")
    stdDeviation: float = Field(..., alias="stdDeviation")

    class Config:
        populate_by_name = True


class HourlyPattern(BaseModel):
    """Hourly execution pattern."""

    hour: int
    executionCount: int = Field(..., alias="executionCount")
    avgDurationMs: float = Field(..., alias="avgDurationMs")
    successRate: float = Field(..., alias="successRate")

    class Config:
        populate_by_name = True


class ExecutionPathPattern(BaseModel):
    """Execution path pattern analysis."""

    executionPath: str = Field(..., alias="executionPath")
    frequency: int
    avgDurationMs: float = Field(..., alias="avgDurationMs")
    avgCredits: float = Field(..., alias="avgCredits")
    successRate: float = Field(..., alias="successRate")

    class Config:
        populate_by_name = True


class BottleneckDetail(BaseModel):
    """Execution bottleneck detail."""

    stepName: str = Field(..., alias="stepName")
    avgDurationMs: int = Field(..., alias="avgDurationMs")
    durationVariance: float = Field(..., alias="durationVariance")
    executionCount: int = Field(..., alias="executionCount")
    p95DurationMs: Optional[int] = Field(None, alias="p95DurationMs")
    p99DurationMs: Optional[int] = Field(None, alias="p99DurationMs")
    impactScore: Optional[float] = Field(None, alias="impactScore")  # 0-100 score
    optimizationPriority: Optional[str] = Field(None, alias="optimizationPriority")  # 'critical', 'high', 'medium', 'low'

    class Config:
        populate_by_name = True


class ExecutionPatternAnalysis(BaseModel):
    """Execution pattern analysis results."""

    hourlyPatterns: List[HourlyPattern] = Field(..., alias="hourlyPatterns")
    executionPaths: List[ExecutionPathPattern] = Field(..., alias="executionPaths")
    bottlenecks: List[BottleneckDetail]
    optimizationSuggestions: List[str] = Field(..., alias="optimizationSuggestions")

    class Config:
        populate_by_name = True


class ExecutionAnalyticsResponse(BaseModel):
    """Complete execution analytics response."""

    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    timeframe: str
    generatedAt: str = Field(..., alias="generatedAt")

    summary: ExecutionSummary
    trends: List[ExecutionTrendPoint]
    performance: PerformanceMetrics
    failureAnalysis: FailureAnalysis = Field(..., alias="failureAnalysis")
    patterns: Optional[ExecutionPatternAnalysis] = None
    recentExecutions: List[ExecutionDetail] = Field(default_factory=list, alias="recentExecutions")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "agentId": "550e8400-e29b-41d4-a716-446655440000",
                "workspaceId": "660e8400-e29b-41d4-a716-446655440000",
                "timeframe": "7d",
                "generatedAt": "2025-11-13T10:00:00Z",
                "summary": {
                    "totalExecutions": 1250,
                    "successfulExecutions": 1180,
                    "failedExecutions": 50,
                    "timeoutExecutions": 20,
                    "successRate": 94.4,
                    "avgDurationMs": 5200,
                    "medianDurationMs": 4800,
                    "p95DurationMs": 12100,
                    "p99DurationMs": 25300,
                    "totalCreditsConsumed": 12500,
                    "avgCreditsPerExecution": 10.0
                }
            }
        }


class LiveExecution(BaseModel):
    """Live execution status."""

    executionId: str = Field(..., alias="executionId")
    agentId: str = Field(..., alias="agentId")
    status: str
    startTime: str = Field(..., alias="startTime")
    currentStep: Optional[str] = Field(None, alias="currentStep")
    stepsCompleted: int = Field(..., alias="stepsCompleted")
    stepsTotal: Optional[int] = Field(None, alias="stepsTotal")
    progressPercent: float = Field(..., ge=0, le=100, alias="progressPercent")

    class Config:
        populate_by_name = True


class LiveExecutionUpdate(BaseModel):
    """Live execution update event."""

    type: str  # 'started', 'progress', 'completed', 'failed'
    execution: LiveExecution
    timestamp: str


class ExecutionStepsResponse(BaseModel):
    """Execution steps response."""

    executionId: str = Field(..., alias="executionId")
    steps: List[ExecutionStep]
    totalSteps: int = Field(..., alias="totalSteps")
    completedSteps: int = Field(..., alias="completedSteps")

    class Config:
        populate_by_name = True


class WorkspaceExecutionAnalytics(BaseModel):
    """Workspace-level execution analytics."""

    workspaceId: str = Field(..., alias="workspaceId")
    timeframe: str
    totalExecutions: int = Field(..., alias="totalExecutions")
    successRate: float = Field(..., alias="successRate")
    avgDurationMs: float = Field(..., alias="avgDurationMs")
    totalCredits: int = Field(..., alias="totalCredits")
    activeAgents: int = Field(..., alias="activeAgents")
    trends: List[ExecutionTrendPoint]
    topAgents: List[Dict[str, Any]] = Field(..., alias="topAgents")

    class Config:
        populate_by_name = True


class ExecutionComparison(BaseModel):
    """Execution comparison between time periods."""

    currentPeriod: ExecutionSummary = Field(..., alias="currentPeriod")
    previousPeriod: ExecutionSummary = Field(..., alias="previousPeriod")
    executionsChange: float = Field(..., alias="executionsChange")
    successRateChange: float = Field(..., alias="successRateChange")
    durationChange: float = Field(..., alias="durationChange")
    creditsChange: float = Field(..., alias="creditsChange")

    class Config:
        populate_by_name = True


# Request schemas
class ExecutionAnalyticsRequest(BaseModel):
    """Request for execution analytics."""

    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    timeframe: str = Field(default="7d", description="Time frame: 24h, 7d, 30d, 90d, all")
    skipCache: bool = Field(default=False, alias="skipCache")

    class Config:
        populate_by_name = True


class BatchExecutionAnalysisRequest(BaseModel):
    """Batch execution analysis request."""

    agentIds: List[str] = Field(..., alias="agentIds")
    workspaceId: str = Field(..., alias="workspaceId")
    timeframe: str = Field(default="7d")

    class Config:
        populate_by_name = True
