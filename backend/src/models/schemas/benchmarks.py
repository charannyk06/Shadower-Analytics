"""Agent benchmarking schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================================
# Enums
# =====================================================================


class BenchmarkCategory(str, Enum):
    """Benchmark suite categories."""

    SPEED = "speed"
    ACCURACY = "accuracy"
    COST = "cost"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    COMPREHENSIVE = "comprehensive"


class TestType(str, Enum):
    """Benchmark test types."""

    SYNTHETIC = "synthetic"
    REAL_WORLD = "real_world"
    STRESS = "stress"
    EDGE_CASE = "edge_case"
    REGRESSION = "regression"


class DatasetComplexity(str, Enum):
    """Dataset complexity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ExecutionStatus(str, Enum):
    """Benchmark execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ComparisonType(str, Enum):
    """Benchmark comparison types."""

    HEAD_TO_HEAD = "head_to_head"
    MULTI_AGENT = "multi_agent"
    TIME_SERIES = "time_series"
    REGRESSION = "regression"


class RegressionSeverity(str, Enum):
    """Regression severity levels."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class StressTestScenario(str, Enum):
    """Stress test scenarios."""

    HIGH_LOAD = "high_load"
    SUSTAINED_LOAD = "sustained_load"
    SPIKE_LOAD = "spike_load"
    MEMORY_PRESSURE = "memory_pressure"
    CONCURRENT_REQUESTS = "concurrent_requests"
    LARGE_INPUTS = "large_inputs"
    RATE_LIMITING = "rate_limiting"
    FAILURE_RECOVERY = "failure_recovery"


# =====================================================================
# Benchmark Suite Schemas
# =====================================================================


class BenchmarkSuiteConfig(BaseModel):
    """Benchmark suite configuration."""

    weights: Optional[Dict[str, float]] = Field(
        default={"accuracy": 0.3, "speed": 0.2, "efficiency": 0.2, "cost": 0.15, "reliability": 0.15},
        description="Metric weights for scoring"
    )
    thresholds: Optional[Dict[str, float]] = Field(default=None, description="Performance thresholds")
    scoringRules: Optional[Dict[str, Any]] = Field(default=None, alias="scoringRules", description="Custom scoring rules")

    class Config:
        populate_by_name = True


class BenchmarkSuiteBase(BaseModel):
    """Base benchmark suite schema."""

    suiteName: str = Field(..., alias="suiteName", max_length=255)
    category: BenchmarkCategory
    description: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=50)
    suiteConfig: Optional[BenchmarkSuiteConfig] = Field(default=None, alias="suiteConfig")
    baselineAgentId: Optional[str] = Field(default=None, alias="baselineAgentId")

    class Config:
        populate_by_name = True


class BenchmarkSuiteCreate(BenchmarkSuiteBase):
    """Schema for creating a benchmark suite."""

    createdBy: Optional[str] = Field(default=None, alias="createdBy")

    class Config:
        populate_by_name = True


class BenchmarkSuite(BenchmarkSuiteBase):
    """Complete benchmark suite schema."""

    id: str
    status: str = "active"
    createdBy: Optional[str] = Field(default=None, alias="createdBy")
    createdAt: datetime = Field(..., alias="createdAt")
    updatedAt: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Benchmark Definition Schemas
# =====================================================================


class DatasetConfig(BaseModel):
    """Dataset configuration for benchmarks."""

    size: Optional[int] = None
    complexity: Optional[DatasetComplexity] = None
    source: Optional[str] = None

    class Config:
        populate_by_name = True


class BenchmarkConstraints(BaseModel):
    """Benchmark execution constraints."""

    timeLimitMs: Optional[int] = Field(default=None, alias="timeLimitMs")
    memoryLimitMb: Optional[int] = Field(default=None, alias="memoryLimitMb")
    tokenLimit: Optional[int] = Field(default=None, alias="tokenLimit")
    costLimitUsd: Optional[float] = Field(default=None, alias="costLimitUsd")

    class Config:
        populate_by_name = True


class BenchmarkDefinitionBase(BaseModel):
    """Base benchmark definition schema."""

    suiteId: str = Field(..., alias="suiteId")
    benchmarkName: str = Field(..., alias="benchmarkName", max_length=255)
    description: Optional[str] = None
    testType: TestType = Field(..., alias="testType")
    metricsMeasured: List[str] = Field(
        default=["accuracy", "speed", "efficiency", "cost", "reliability"],
        alias="metricsMeasured"
    )
    dataset: Optional[DatasetConfig] = None
    testData: Optional[Dict[str, Any]] = Field(default=None, alias="testData")
    constraints: Optional[BenchmarkConstraints] = None
    expectedOutputs: Optional[List[Any]] = Field(default=None, alias="expectedOutputs")
    scoringRubric: Dict[str, Any] = Field(..., alias="scoringRubric")
    numRuns: int = Field(default=5, alias="numRuns", ge=1, le=20)
    warmupRuns: int = Field(default=3, alias="warmupRuns", ge=0, le=10)
    parallelExecution: bool = Field(default=False, alias="parallelExecution")

    class Config:
        populate_by_name = True


class BenchmarkDefinitionCreate(BenchmarkDefinitionBase):
    """Schema for creating a benchmark definition."""

    pass


class BenchmarkDefinition(BenchmarkDefinitionBase):
    """Complete benchmark definition schema."""

    id: str
    createdAt: datetime = Field(..., alias="createdAt")
    updatedAt: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Benchmark Execution Schemas
# =====================================================================


class ExecutionEnvironment(BaseModel):
    """Execution environment details."""

    hardwareSpecs: Optional[Dict[str, Any]] = Field(default=None, alias="hardwareSpecs")
    runtimeConfig: Optional[Dict[str, Any]] = Field(default=None, alias="runtimeConfig")
    environmentVars: Optional[Dict[str, str]] = Field(default=None, alias="environmentVars")

    class Config:
        populate_by_name = True


class PerformanceScores(BaseModel):
    """Core performance scores (0-100 scale)."""

    accuracyScore: Optional[float] = Field(default=None, alias="accuracyScore", ge=0, le=100)
    speedScore: Optional[float] = Field(default=None, alias="speedScore", ge=0, le=100)
    efficiencyScore: Optional[float] = Field(default=None, alias="efficiencyScore", ge=0, le=100)
    costScore: Optional[float] = Field(default=None, alias="costScore", ge=0, le=100)
    reliabilityScore: Optional[float] = Field(default=None, alias="reliabilityScore", ge=0, le=100)
    overallScore: Optional[float] = Field(default=None, alias="overallScore", ge=0, le=100)

    class Config:
        populate_by_name = True


class QualityMetrics(BaseModel):
    """Output quality metrics."""

    outputCorrectness: Optional[float] = Field(default=None, alias="outputCorrectness", ge=0, le=100)
    outputCompleteness: Optional[float] = Field(default=None, alias="outputCompleteness", ge=0, le=100)
    outputRelevance: Optional[float] = Field(default=None, alias="outputRelevance", ge=0, le=100)

    class Config:
        populate_by_name = True


class BenchmarkExecutionBase(BaseModel):
    """Base benchmark execution schema."""

    suiteId: str = Field(..., alias="suiteId")
    benchmarkId: str = Field(..., alias="benchmarkId")
    agentId: str = Field(..., alias="agentId")
    agentVersion: Optional[str] = Field(default=None, alias="agentVersion")
    workspaceId: str = Field(..., alias="workspaceId")
    executionEnvironment: Optional[ExecutionEnvironment] = Field(default=None, alias="executionEnvironment")
    modelConfiguration: Optional[Dict[str, Any]] = Field(default=None, alias="modelConfiguration")

    class Config:
        populate_by_name = True


class BenchmarkExecutionCreate(BenchmarkExecutionBase):
    """Schema for creating a benchmark execution."""

    pass


class BenchmarkExecution(BenchmarkExecutionBase):
    """Complete benchmark execution schema."""

    id: str
    runNumber: int = Field(default=1, alias="runNumber")
    startTime: datetime = Field(..., alias="startTime")
    endTime: Optional[datetime] = Field(default=None, alias="endTime")
    totalDurationMs: Optional[int] = Field(default=None, alias="totalDurationMs")

    # Scores
    scores: Optional[PerformanceScores] = None
    qualityMetrics: Optional[QualityMetrics] = Field(default=None, alias="qualityMetrics")

    # Resource metrics
    tokensUsed: int = Field(default=0, alias="tokensUsed")
    apiCallsMade: int = Field(default=0, alias="apiCallsMade")
    memoryPeakMb: Optional[float] = Field(default=None, alias="memoryPeakMb")
    cpuUsagePercent: Optional[float] = Field(default=None, alias="cpuUsagePercent")

    # Comparative metrics
    percentileRank: Optional[float] = Field(default=None, alias="percentileRank")
    deviationFromBaseline: Optional[float] = Field(default=None, alias="deviationFromBaseline")

    # Results
    actualOutput: Optional[Dict[str, Any]] = Field(default=None, alias="actualOutput")
    validationResults: Optional[Dict[str, Any]] = Field(default=None, alias="validationResults")
    detailedMetrics: Optional[Dict[str, Any]] = Field(default=None, alias="detailedMetrics")

    # Status
    status: ExecutionStatus
    errorDetails: Optional[str] = Field(default=None, alias="errorDetails")

    createdAt: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class BenchmarkExecutionSummary(BaseModel):
    """Summary of benchmark execution results."""

    executionId: str = Field(..., alias="executionId")
    agentId: str = Field(..., alias="agentId")
    benchmarkName: str = Field(..., alias="benchmarkName")
    overallScore: Optional[float] = Field(default=None, alias="overallScore")
    status: ExecutionStatus
    duration: Optional[int] = None
    startTime: datetime = Field(..., alias="startTime")

    class Config:
        populate_by_name = True


# =====================================================================
# Benchmark Comparison Schemas
# =====================================================================


class MetricComparison(BaseModel):
    """Individual metric comparison."""

    metric: str
    agentAScore: float = Field(..., alias="agentAScore")
    agentBScore: float = Field(..., alias="agentBScore")
    difference: float
    percentageDifference: float = Field(..., alias="percentageDifference")
    winner: str

    class Config:
        populate_by_name = True


class BenchmarkComparisonBase(BaseModel):
    """Base benchmark comparison schema."""

    suiteId: str = Field(..., alias="suiteId")
    workspaceId: str = Field(..., alias="workspaceId")
    agentIds: List[str] = Field(..., alias="agentIds")
    comparisonType: ComparisonType = Field(..., alias="comparisonType")

    class Config:
        populate_by_name = True


class BenchmarkComparisonCreate(BenchmarkComparisonBase):
    """Schema for creating a benchmark comparison."""

    pass


class BenchmarkComparison(BenchmarkComparisonBase):
    """Complete benchmark comparison schema."""

    id: str
    agentCount: int = Field(..., alias="agentCount")
    overallWinner: Optional[str] = Field(default=None, alias="overallWinner")
    categoryWinners: Optional[Dict[str, str]] = Field(default=None, alias="categoryWinners")
    detailedMetrics: Dict[str, Any] = Field(..., alias="detailedMetrics")
    statisticalSignificance: Optional[Dict[str, float]] = Field(default=None, alias="statisticalSignificance")
    recommendations: Optional[List[str]] = None
    insights: Optional[List[str]] = None
    createdAt: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Benchmark Regression Schemas
# =====================================================================


class BenchmarkRegressionBase(BaseModel):
    """Base benchmark regression schema."""

    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    benchmarkId: str = Field(..., alias="benchmarkId")
    baselineVersion: Optional[str] = Field(default=None, alias="baselineVersion")
    currentVersion: Optional[str] = Field(default=None, alias="currentVersion")
    metricName: str = Field(..., alias="metricName")
    baselineValue: Optional[float] = Field(default=None, alias="baselineValue")
    currentValue: Optional[float] = Field(default=None, alias="currentValue")
    regressionPercentage: Optional[float] = Field(default=None, alias="regressionPercentage")
    severity: RegressionSeverity
    regressionType: Optional[str] = Field(default=None, alias="regressionType")

    class Config:
        populate_by_name = True


class BenchmarkRegression(BenchmarkRegressionBase):
    """Complete benchmark regression schema."""

    id: str
    baselineExecutionId: Optional[str] = Field(default=None, alias="baselineExecutionId")
    currentExecutionId: Optional[str] = Field(default=None, alias="currentExecutionId")
    impactAnalysis: Optional[Dict[str, Any]] = Field(default=None, alias="impactAnalysis")
    affectedUsersEstimate: Optional[int] = Field(default=None, alias="affectedUsersEstimate")
    businessImpact: Optional[str] = Field(default=None, alias="businessImpact")
    status: str = "detected"
    resolutionNotes: Optional[str] = Field(default=None, alias="resolutionNotes")
    resolvedAt: Optional[datetime] = Field(default=None, alias="resolvedAt")
    detectedAt: datetime = Field(..., alias="detectedAt")
    updatedAt: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Stress Test Schemas
# =====================================================================


class StressTestParameters(BaseModel):
    """Stress test parameters."""

    concurrentRequests: Optional[int] = Field(default=None, alias="concurrentRequests")
    durationSeconds: Optional[int] = Field(default=None, alias="durationSeconds")
    requestRate: Optional[float] = Field(default=None, alias="requestRate")
    dataSize: Optional[int] = Field(default=None, alias="dataSize")

    class Config:
        populate_by_name = True


class StressTestResultBase(BaseModel):
    """Base stress test result schema."""

    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    testScenario: StressTestScenario = Field(..., alias="testScenario")
    testParameters: StressTestParameters = Field(..., alias="testParameters")

    class Config:
        populate_by_name = True


class StressTestResultCreate(StressTestResultBase):
    """Schema for creating a stress test result."""

    pass


class StressTestResult(StressTestResultBase):
    """Complete stress test result schema."""

    id: str
    startTime: datetime = Field(..., alias="startTime")
    endTime: Optional[datetime] = Field(default=None, alias="endTime")
    durationSeconds: Optional[int] = Field(default=None, alias="durationSeconds")

    # Results
    maxThroughputRps: Optional[float] = Field(default=None, alias="maxThroughputRps")
    avgResponseTimeMs: Optional[float] = Field(default=None, alias="avgResponseTimeMs")
    p95ResponseTimeMs: Optional[float] = Field(default=None, alias="p95ResponseTimeMs")
    p99ResponseTimeMs: Optional[float] = Field(default=None, alias="p99ResponseTimeMs")
    errorRatePercent: Optional[float] = Field(default=None, alias="errorRatePercent")

    # Breaking points
    broke: bool = False
    breakingPointDescription: Optional[str] = Field(default=None, alias="breakingPointDescription")
    maxConcurrentRequests: Optional[int] = Field(default=None, alias="maxConcurrentRequests")
    maxMemoryMb: Optional[float] = Field(default=None, alias="maxMemoryMb")

    # Resource usage
    peakCpuPercent: Optional[float] = Field(default=None, alias="peakCpuPercent")
    peakMemoryMb: Optional[float] = Field(default=None, alias="peakMemoryMb")
    peakIoOperations: Optional[int] = Field(default=None, alias="peakIoOperations")

    # Resilience metrics
    recoveryTimeSeconds: Optional[float] = Field(default=None, alias="recoveryTimeSeconds")
    failureCount: int = Field(default=0, alias="failureCount")
    autoRecoverySuccess: Optional[bool] = Field(default=None, alias="autoRecoverySuccess")

    # Assessment
    resilienceScore: Optional[float] = Field(default=None, alias="resilienceScore")
    scalingLimitDescription: Optional[str] = Field(default=None, alias="scalingLimitDescription")
    recommendations: Optional[List[str]] = None

    status: str = "completed"
    createdAt: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Leaderboard Schemas
# =====================================================================


class LeaderboardEntry(BaseModel):
    """Benchmark leaderboard entry."""

    agentId: str = Field(..., alias="agentId")
    agentName: Optional[str] = Field(default=None, alias="agentName")
    benchmarkCategory: str = Field(..., alias="benchmarkCategory")
    avgAccuracy: Optional[float] = Field(default=None, alias="avgAccuracy")
    avgSpeed: Optional[float] = Field(default=None, alias="avgSpeed")
    avgEfficiency: Optional[float] = Field(default=None, alias="avgEfficiency")
    avgCost: Optional[float] = Field(default=None, alias="avgCost")
    avgReliability: Optional[float] = Field(default=None, alias="avgReliability")
    avgOverall: Optional[float] = Field(default=None, alias="avgOverall")
    accuracyRank: Optional[int] = Field(default=None, alias="accuracyRank")
    speedRank: Optional[int] = Field(default=None, alias="speedRank")
    efficiencyRank: Optional[int] = Field(default=None, alias="efficiencyRank")
    costRank: Optional[int] = Field(default=None, alias="costRank")
    reliabilityRank: Optional[int] = Field(default=None, alias="reliabilityRank")
    overallRank: Optional[int] = Field(default=None, alias="overallRank")
    benchmarksCompleted: Optional[int] = Field(default=None, alias="benchmarksCompleted")
    lastBenchmarkDate: Optional[datetime] = Field(default=None, alias="lastBenchmarkDate")

    class Config:
        populate_by_name = True
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Leaderboard API response."""

    category: str
    entries: List[LeaderboardEntry]
    totalAgents: int = Field(..., alias="totalAgents")
    lastUpdated: datetime = Field(..., alias="lastUpdated")

    class Config:
        populate_by_name = True


# =====================================================================
# Cost Performance Analysis Schemas
# =====================================================================


class CostPerformanceAnalysis(BaseModel):
    """Cost performance analysis schema."""

    id: str
    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    analysisDate: datetime = Field(..., alias="analysisDate")

    # Cost metrics
    totalCostUsd: float = Field(default=0, alias="totalCostUsd")
    costPerTask: Optional[float] = Field(default=None, alias="costPerTask")
    costPerSuccess: Optional[float] = Field(default=None, alias="costPerSuccess")

    # Performance metrics
    avgPerformanceScore: Optional[float] = Field(default=None, alias="avgPerformanceScore")
    performancePerDollar: Optional[float] = Field(default=None, alias="performancePerDollar")

    # Efficiency metrics
    tokenEfficiency: Optional[float] = Field(default=None, alias="tokenEfficiency")
    resourceEfficiency: Optional[float] = Field(default=None, alias="resourceEfficiency")
    timeEfficiency: Optional[float] = Field(default=None, alias="timeEfficiency")
    overallEfficiency: Optional[float] = Field(default=None, alias="overallEfficiency")

    # Optimization
    optimalConfigurations: Optional[List[Dict[str, Any]]] = Field(default=None, alias="optimalConfigurations")
    currentConfiguration: Optional[Dict[str, Any]] = Field(default=None, alias="currentConfiguration")
    estimatedSavingsUsd: Optional[float] = Field(default=None, alias="estimatedSavingsUsd")
    optimizationOpportunities: Optional[List[Dict[str, Any]]] = Field(default=None, alias="optimizationOpportunities")

    createdAt: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


# =====================================================================
# Request/Response Schemas
# =====================================================================


class RunBenchmarkRequest(BaseModel):
    """Request to run a benchmark."""

    agentId: str = Field(..., alias="agentId")
    suiteId: str = Field(..., alias="suiteId")
    configuration: Optional[Dict[str, Any]] = None
    asyncExecution: bool = Field(default=False, alias="asyncExecution")

    class Config:
        populate_by_name = True


class RunBenchmarkResponse(BaseModel):
    """Response from running a benchmark."""

    executionId: str = Field(..., alias="executionId")
    status: ExecutionStatus
    message: str
    estimatedCompletionTime: Optional[datetime] = Field(default=None, alias="estimatedCompletionTime")

    class Config:
        populate_by_name = True


class DetectRegressionsRequest(BaseModel):
    """Request to detect regressions."""

    agentId: str = Field(..., alias="agentId")
    currentVersion: str = Field(..., alias="currentVersion")
    baselineVersion: Optional[str] = Field(default=None, alias="baselineVersion")
    threshold: float = Field(default=10.0, ge=0, le=100)

    class Config:
        populate_by_name = True


class DetectRegressionsResponse(BaseModel):
    """Response from regression detection."""

    hasRegressions: bool = Field(..., alias="hasRegressions")
    regressions: List[BenchmarkRegression]
    overallHealth: str = Field(..., alias="overallHealth")
    recommendedAction: str = Field(..., alias="recommendedAction")

    class Config:
        populate_by_name = True
