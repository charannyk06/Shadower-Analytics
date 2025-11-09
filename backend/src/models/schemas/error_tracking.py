"""Error tracking schema models."""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorSample(BaseModel):
    """Sample error occurrence."""
    errorId: str
    message: str
    stackTrace: str
    occurredAt: datetime


class ErrorTypeDetail(BaseModel):
    """Error type details."""
    type: str
    category: str
    count: int
    percentage: float
    trend: Literal['increasing', 'stable', 'decreasing']
    severity: Literal['low', 'medium', 'high', 'critical']
    samples: List[Dict[str, Any]] = Field(default_factory=list)


class ErrorOverview(BaseModel):
    """Error overview metrics."""
    totalErrors: int
    uniqueErrors: int
    affectedUsers: int
    affectedAgents: int
    errorRate: float
    errorRateChange: float
    criticalErrorRate: float
    userImpact: float
    systemImpact: Literal['low', 'medium', 'high', 'critical']
    estimatedRevenueLoss: float
    avgRecoveryTime: float
    autoRecoveryRate: float
    manualInterventions: int


class ErrorCategories(BaseModel):
    """Error categorization."""
    byType: List[ErrorTypeDetail]
    bySeverity: Dict[str, int]
    bySource: Dict[str, int]


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    timestamp: str
    count: int
    criticalCount: int
    uniqueErrors: int


class ErrorSpike(BaseModel):
    """Error spike details."""
    startTime: str
    endTime: Optional[str] = None
    peakErrors: int
    totalErrors: int
    primaryCause: str
    resolved: bool


class ErrorPattern(BaseModel):
    """Error pattern details."""
    pattern: str
    frequency: int
    lastOccurrence: str
    correlation: str


class ErrorTimeline(BaseModel):
    """Error timeline data."""
    errorsByTime: List[TimeSeriesPoint]
    spikes: List[ErrorSpike]
    patterns: List[ErrorPattern]


class ErrorImpact(BaseModel):
    """Error impact metrics."""
    usersAffected: int
    executionsAffected: int
    creditsLost: float
    cascadingFailures: int


class ErrorResolution(BaseModel):
    """Error resolution details."""
    resolvedAt: str
    resolvedBy: Optional[str] = None
    resolution: str
    rootCause: str
    preventiveMeasures: List[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Detailed error information."""
    errorId: str
    fingerprint: str
    type: str
    message: str
    severity: Literal['low', 'medium', 'high', 'critical']
    status: Literal['new', 'acknowledged', 'investigating', 'resolved', 'ignored']
    firstSeen: str
    lastSeen: str
    occurrences: int
    affectedUsers: List[str] = Field(default_factory=list)
    affectedAgents: List[str] = Field(default_factory=list)
    stackTrace: str
    context: Dict[str, Any] = Field(default_factory=dict)
    impact: ErrorImpact
    resolution: Optional[ErrorResolution] = None


class TopError(BaseModel):
    """Top error summary."""
    errorId: str
    type: str
    count: int
    lastSeen: str


class TopErrorByImpact(BaseModel):
    """Top error by impact."""
    errorId: str
    type: str
    usersAffected: int
    creditsLost: float


class UnresolvedError(BaseModel):
    """Unresolved error summary."""
    errorId: str
    type: str
    age: float
    priority: int


class TopErrors(BaseModel):
    """Top errors by various metrics."""
    byOccurrence: List[TopError]
    byImpact: List[TopErrorByImpact]
    unresolved: List[UnresolvedError]


class AgentCorrelation(BaseModel):
    """Agent to error correlation."""
    agentId: str
    agentName: str
    errorTypes: List[str]
    errorRate: float
    commonCause: str


class UserCorrelation(BaseModel):
    """User to error correlation."""
    userId: str
    errorTypes: List[str]
    frequency: int
    possibleCause: str


class ErrorChain(BaseModel):
    """Error chain analysis."""
    rootError: str
    cascadingErrors: List[str]
    totalImpact: int
    preventable: bool


class ErrorCorrelations(BaseModel):
    """Error correlations and patterns."""
    agentCorrelation: List[AgentCorrelation]
    userCorrelation: List[UserCorrelation]
    errorChains: List[ErrorChain]


class RecoveryTimeMetrics(BaseModel):
    """Recovery time metrics."""
    avg: float
    median: float
    p95: float


class RecoveryMethod(BaseModel):
    """Recovery method details."""
    method: str
    successRate: float
    avgTime: float
    usageCount: int


class FailedRecovery(BaseModel):
    """Failed recovery attempt."""
    errorId: str
    attemptedMethods: List[str]
    failureReason: str


class RecoveryAnalysis(BaseModel):
    """Recovery analysis data."""
    recoveryTimes: Dict[str, RecoveryTimeMetrics]
    recoveryMethods: List[RecoveryMethod]
    failedRecoveries: List[FailedRecovery]


class ErrorTrackingResponse(BaseModel):
    """Complete error tracking response."""
    workspaceId: str
    timeframe: str
    overview: ErrorOverview
    categories: ErrorCategories
    timeline: ErrorTimeline
    errors: List[ErrorDetail]
    topErrors: TopErrors
    correlations: ErrorCorrelations
    recovery: RecoveryAnalysis


class TrackErrorRequest(BaseModel):
    """Request to track a new error."""
    type: str
    message: str
    severity: Literal['low', 'medium', 'high', 'critical'] = 'medium'
    stackTrace: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResolveErrorRequest(BaseModel):
    """Request to resolve an error."""
    resolvedBy: str
    resolution: str
    rootCause: Optional[str] = None
    preventiveMeasures: List[str] = Field(default_factory=list)
