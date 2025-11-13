"""Comprehensive resource utilization and analytics schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ============================================================================
# Enums
# ============================================================================
class ResourceType(str, Enum):
    """Resource types for tracking."""
    COMPUTE = "compute"
    TOKENS = "tokens"
    API = "api"
    STORAGE = "storage"
    NETWORK = "network"
    COST = "cost"


class WasteType(str, Enum):
    """Types of resource waste."""
    IDLE_RESOURCES = "idle_resources"
    OVERSIZED_INSTANCES = "oversized_instances"
    REDUNDANT_API_CALLS = "redundant_api_calls"
    INEFFICIENT_PROMPTS = "inefficient_prompts"
    UNUSED_CACHE = "unused_cache"
    FAILED_EXECUTION_COSTS = "failed_execution_costs"
    RATE_LIMIT_WASTE = "rate_limit_waste"
    TOKEN_OVERFLOW = "token_overflow"


class OptimizationCategory(str, Enum):
    """Categories for optimization recommendations."""
    COMPUTE = "compute"
    TOKENS = "tokens"
    API = "api"
    STORAGE = "storage"
    NETWORK = "network"
    COST = "cost"
    GENERAL = "general"


class BudgetStatus(str, Enum):
    """Budget status indicators."""
    NO_BUDGET = "no_budget"
    WITHIN_BUDGET = "within_budget"
    WARNING = "warning"
    CRITICAL = "critical"
    OVER_BUDGET = "over_budget"


class ImplementationEffort(str, Enum):
    """Implementation effort levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Compute Resource Schemas
# ============================================================================
class CPUUsage(BaseModel):
    """CPU usage metrics."""
    averagePercent: float = Field(..., alias="averagePercent", description="Average CPU utilization percentage")
    peakPercent: float = Field(..., alias="peakPercent", description="Peak CPU utilization percentage")
    coreSeconds: float = Field(..., alias="coreSeconds", description="Total core-seconds consumed")

    class Config:
        populate_by_name = True


class MemoryUsage(BaseModel):
    """Memory usage metrics."""
    averageMb: float = Field(..., alias="averageMb", description="Average memory usage in MB")
    peakMb: float = Field(..., alias="peakMb", description="Peak memory usage in MB")
    allocationMb: float = Field(..., alias="allocationMb", description="Total allocated memory in MB")

    class Config:
        populate_by_name = True


class GPUUsage(BaseModel):
    """GPU usage metrics."""
    utilizationPercent: float = Field(..., alias="utilizationPercent", description="GPU utilization percentage")
    memoryMb: float = Field(..., alias="memoryMb", description="GPU memory used in MB")
    computeUnits: float = Field(..., alias="computeUnits", description="GPU compute units consumed")

    class Config:
        populate_by_name = True


class NetworkIO(BaseModel):
    """Network I/O metrics."""
    bytesSent: int = Field(..., alias="bytesSent", description="Total bytes sent")
    bytesReceived: int = Field(..., alias="bytesReceived", description="Total bytes received")
    apiCalls: int = Field(..., alias="apiCalls", description="Total API calls made")

    class Config:
        populate_by_name = True


class ComputeResources(BaseModel):
    """Compute resource metrics."""
    cpuUsage: CPUUsage = Field(..., alias="cpuUsage")
    memoryUsage: MemoryUsage = Field(..., alias="memoryUsage")
    gpuUsage: Optional[GPUUsage] = Field(None, alias="gpuUsage")
    networkIo: NetworkIO = Field(..., alias="networkIo")

    class Config:
        populate_by_name = True


# ============================================================================
# LLM Resource Schemas
# ============================================================================
class LLMResources(BaseModel):
    """LLM resource usage metrics."""
    model: str = Field(..., description="Model name")
    modelProvider: str = Field(..., alias="modelProvider", description="Model provider")
    inputTokens: int = Field(..., alias="inputTokens", description="Input tokens consumed")
    outputTokens: int = Field(..., alias="outputTokens", description="Output tokens generated")
    embeddingTokens: int = Field(0, alias="embeddingTokens", description="Embedding tokens used")
    totalTokens: int = Field(..., alias="totalTokens", description="Total tokens")
    contextWindowUsed: int = Field(..., alias="contextWindowUsed", description="Context window utilized")
    promptCacheHits: int = Field(0, alias="promptCacheHits", description="Prompt cache hits")
    costUsd: float = Field(..., alias="costUsd", description="Cost in USD")

    class Config:
        populate_by_name = True


# ============================================================================
# Storage Resource Schemas
# ============================================================================
class StorageResources(BaseModel):
    """Storage resource metrics."""
    tempStorageMb: float = Field(..., alias="tempStorageMb", description="Temporary storage in MB")
    persistentStorageMb: float = Field(..., alias="persistentStorageMb", description="Persistent storage in MB")
    cacheSizeMb: float = Field(..., alias="cacheSizeMb", description="Cache size in MB")
    databaseOperations: int = Field(..., alias="databaseOperations", description="Database operations count")

    class Config:
        populate_by_name = True


# ============================================================================
# Cost Breakdown Schemas
# ============================================================================
class CostBreakdown(BaseModel):
    """Detailed cost breakdown."""
    computeCostUsd: float = Field(..., alias="computeCostUsd", description="Compute costs")
    tokenCostUsd: float = Field(..., alias="tokenCostUsd", description="Token costs")
    apiCostUsd: float = Field(..., alias="apiCostUsd", description="API costs")
    storageCostUsd: float = Field(..., alias="storageCostUsd", description="Storage costs")
    networkCostUsd: float = Field(..., alias="networkCostUsd", description="Network costs")
    totalCostUsd: float = Field(..., alias="totalCostUsd", description="Total costs")

    class Config:
        populate_by_name = True


# ============================================================================
# Resource Utilization Schemas
# ============================================================================
class ResourceUtilizationMetrics(BaseModel):
    """Complete resource utilization metrics."""
    agentId: str = Field(..., alias="agentId")
    executionId: str = Field(..., alias="executionId")
    workspaceId: str = Field(..., alias="workspaceId")
    timestamp: datetime
    computeResources: ComputeResources = Field(..., alias="computeResources")
    llmResources: LLMResources = Field(..., alias="llmResources")
    storageResources: StorageResources = Field(..., alias="storageResources")
    costBreakdown: CostBreakdown = Field(..., alias="costBreakdown")
    executionDurationMs: int = Field(..., alias="executionDurationMs")
    queueWaitTimeMs: int = Field(..., alias="queueWaitTimeMs")
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


# ============================================================================
# API Usage Schemas
# ============================================================================
class APICallStatistics(BaseModel):
    """API call statistics."""
    totalCalls: int = Field(..., alias="totalCalls")
    successfulCalls: int = Field(..., alias="successfulCalls")
    failedCalls: int = Field(..., alias="failedCalls")
    rateLimitedCalls: int = Field(..., alias="rateLimitedCalls")
    timeoutCalls: int = Field(0, alias="timeoutCalls")

    class Config:
        populate_by_name = True


class LatencyMetrics(BaseModel):
    """Latency metrics."""
    avgLatencyMs: float = Field(..., alias="avgLatencyMs")
    p50LatencyMs: float = Field(..., alias="p50LatencyMs")
    p95LatencyMs: float = Field(..., alias="p95LatencyMs")
    p99LatencyMs: float = Field(..., alias="p99LatencyMs")
    minLatencyMs: float = Field(..., alias="minLatencyMs")
    maxLatencyMs: float = Field(..., alias="maxLatencyMs")

    class Config:
        populate_by_name = True


class APICostMetrics(BaseModel):
    """API cost metrics."""
    totalCostUsd: float = Field(..., alias="totalCostUsd")
    costPerCall: float = Field(..., alias="costPerCall")
    wastedCostFailedCalls: float = Field(..., alias="wastedCostFailedCalls")

    class Config:
        populate_by_name = True


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    currentUsage: int = Field(..., alias="currentUsage")
    limit: int
    resetTime: datetime = Field(..., alias="resetTime")
    throttleIncidents: int = Field(..., alias="throttleIncidents")

    class Config:
        populate_by_name = True


class APIErrorAnalysis(BaseModel):
    """API error analysis."""
    errorTypes: Dict[str, int] = Field(..., alias="errorTypes")
    errorRate: float = Field(..., alias="errorRate")
    retrySuccessRate: float = Field(..., alias="retrySuccessRate")

    class Config:
        populate_by_name = True


class APIUsageMetrics(BaseModel):
    """Comprehensive API usage metrics."""
    agentId: str = Field(..., alias="agentId")
    apiEndpoint: str = Field(..., alias="apiEndpoint")
    apiProvider: Optional[str] = Field(None, alias="apiProvider")
    timePeriod: str = Field(..., alias="timePeriod")
    usageStats: APICallStatistics = Field(..., alias="usageStats")
    latencyMetrics: LatencyMetrics = Field(..., alias="latencyMetrics")
    costMetrics: APICostMetrics = Field(..., alias="costMetrics")
    rateLimiting: RateLimitInfo = Field(..., alias="rateLimiting")
    errorAnalysis: APIErrorAnalysis = Field(..., alias="errorAnalysis")

    class Config:
        populate_by_name = True


# ============================================================================
# Token Analytics Schemas
# ============================================================================
class TokenDistribution(BaseModel):
    """Token distribution analysis."""
    inputTokenPercent: float = Field(..., alias="inputTokenPercent")
    outputTokenPercent: float = Field(..., alias="outputTokenPercent")
    embeddingTokenPercent: float = Field(..., alias="embeddingTokenPercent")

    class Config:
        populate_by_name = True


class TokenEfficiencyMetrics(BaseModel):
    """Token efficiency metrics."""
    tokensPerExecution: float = Field(..., alias="tokensPerExecution")
    tokensPerDollar: float = Field(..., alias="tokensPerDollar")
    cacheHitRate: float = Field(..., alias="cacheHitRate")
    contextWindowUtilization: float = Field(..., alias="contextWindowUtilization")

    class Config:
        populate_by_name = True


class PromptOptimization(BaseModel):
    """Prompt optimization suggestions."""
    redundantTokens: int = Field(..., alias="redundantTokens")
    compressionRatio: float = Field(..., alias="compressionRatio")
    savingsPercent: float = Field(..., alias="savingsPercent")
    costSavingsUsd: float = Field(..., alias="costSavingsUsd")

    class Config:
        populate_by_name = True


class TokenAnalysis(BaseModel):
    """Comprehensive token analysis."""
    totalTokens: int = Field(..., alias="totalTokens")
    totalCostUsd: float = Field(..., alias="totalCostUsd")
    distribution: TokenDistribution
    efficiency: TokenEfficiencyMetrics
    optimization: PromptOptimization

    class Config:
        populate_by_name = True


# ============================================================================
# Budget Schemas
# ============================================================================
class TokenBudget(BaseModel):
    """Token budget configuration."""
    workspaceId: str = Field(..., alias="workspaceId")
    agentId: Optional[str] = Field(None, alias="agentId")
    dailyTokenBudget: Optional[int] = Field(None, alias="dailyTokenBudget")
    weeklyTokenBudget: Optional[int] = Field(None, alias="weeklyTokenBudget")
    monthlyTokenBudget: Optional[int] = Field(None, alias="monthlyTokenBudget")
    dailyCostBudgetUsd: Optional[float] = Field(None, alias="dailyCostBudgetUsd")
    weeklyCostBudgetUsd: Optional[float] = Field(None, alias="weeklyCostBudgetUsd")
    monthlyCostBudgetUsd: Optional[float] = Field(None, alias="monthlyCostBudgetUsd")
    warningThresholdPercent: int = Field(80, alias="warningThresholdPercent")
    criticalThresholdPercent: int = Field(90, alias="criticalThresholdPercent")

    class Config:
        populate_by_name = True


class BudgetUsage(BaseModel):
    """Budget usage tracking."""
    dailyTokens: int = Field(..., alias="dailyTokens")
    dailyCostUsd: float = Field(..., alias="dailyCostUsd")
    dailyBudgetUsagePercent: float = Field(..., alias="dailyBudgetUsagePercent")
    dailyCostBudgetUsagePercent: float = Field(..., alias="dailyCostBudgetUsagePercent")
    rolling7dTokens: int = Field(..., alias="rolling7dTokens")
    rolling30dTokens: int = Field(..., alias="rolling30dTokens")
    rolling30dCostUsd: float = Field(..., alias="rolling30dCostUsd")
    budgetStatus: BudgetStatus = Field(..., alias="budgetStatus")

    class Config:
        populate_by_name = True


# ============================================================================
# Optimization Schemas
# ============================================================================
class OptimizationRecommendation(BaseModel):
    """Resource optimization recommendation."""
    id: str
    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    optimizationType: str = Field(..., alias="optimizationType")
    category: OptimizationCategory
    priority: Priority
    title: str
    description: str
    reasoning: str
    currentValue: Optional[float] = Field(None, alias="currentValue")
    recommendedValue: Optional[float] = Field(None, alias="recommendedValue")
    estimatedSavingsUsd: float = Field(..., alias="estimatedSavingsUsd")
    estimatedSavingsPercent: float = Field(..., alias="estimatedSavingsPercent")
    implementationEffort: ImplementationEffort = Field(..., alias="implementationEffort")
    implementationSteps: Optional[List[str]] = Field(None, alias="implementationSteps")
    status: str
    createdAt: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True


# ============================================================================
# Waste Detection Schemas
# ============================================================================
class WasteEvent(BaseModel):
    """Resource waste event."""
    id: str
    agentId: str = Field(..., alias="agentId")
    executionId: Optional[str] = Field(None, alias="executionId")
    workspaceId: str = Field(..., alias="workspaceId")
    wasteType: WasteType = Field(..., alias="wasteType")
    wasteCategory: str = Field(..., alias="wasteCategory")
    title: str
    description: str
    wasteAmount: float = Field(..., alias="wasteAmount")
    wasteUnit: str = Field(..., alias="wasteUnit")
    wasteCostUsd: float = Field(..., alias="wasteCostUsd")
    confidenceScore: float = Field(..., alias="confidenceScore")
    isResolved: bool = Field(False, alias="isResolved")
    detectedAt: datetime = Field(..., alias="detectedAt")

    class Config:
        populate_by_name = True


class WasteSummary(BaseModel):
    """Waste detection summary."""
    totalWasteCostUsd: float = Field(..., alias="totalWasteCostUsd")
    wasteByType: Dict[str, float] = Field(..., alias="wasteByType")
    unresolvedCount: int = Field(..., alias="unresolvedCount")
    potentialMonthlySavings: float = Field(..., alias="potentialMonthlySavings")

    class Config:
        populate_by_name = True


# ============================================================================
# Forecast Schemas
# ============================================================================
class ResourceForecast(BaseModel):
    """Resource demand forecast."""
    resourceType: ResourceType = Field(..., alias="resourceType")
    forecastHorizonDays: int = Field(..., alias="forecastHorizonDays")
    predictedValue: float = Field(..., alias="predictedValue")
    lowerBound: float = Field(..., alias="lowerBound")
    upperBound: float = Field(..., alias="upperBound")
    confidenceLevel: float = Field(..., alias="confidenceLevel")
    historicalAverage: float = Field(..., alias="historicalAverage")
    historicalTrend: str = Field(..., alias="historicalTrend")
    exceedsBudget: bool = Field(..., alias="exceedsBudget")
    forecastDate: date = Field(..., alias="forecastDate")

    class Config:
        populate_by_name = True


class CostProjection(BaseModel):
    """Cost projection analysis."""
    projectedDailyCost: float = Field(..., alias="projectedDailyCost")
    projectedWeeklyCost: float = Field(..., alias="projectedWeeklyCost")
    projectedMonthlyCost: float = Field(..., alias="projectedMonthlyCost")
    growthRate: float = Field(..., alias="growthRate")
    budgetAlerts: List[str] = Field(..., alias="budgetAlerts")

    class Config:
        populate_by_name = True


# ============================================================================
# Efficiency Schemas
# ============================================================================
class EfficiencyScore(BaseModel):
    """Agent efficiency scoring."""
    overallScore: float = Field(..., alias="overallScore", description="Overall efficiency score 0-100")
    tokensPerDollar: float = Field(..., alias="tokensPerDollar")
    executionsPerDollar: float = Field(..., alias="executionsPerDollar")
    throughputScore: float = Field(..., alias="throughputScore")
    costEfficiencyPercent: float = Field(..., alias="costEfficiencyPercent")
    percentileRank: Optional[int] = Field(None, alias="percentileRank")
    improvementAreas: List[str] = Field(..., alias="improvementAreas")

    class Config:
        populate_by_name = True


# ============================================================================
# Response Schemas
# ============================================================================
class ResourceAnalyticsResponse(BaseModel):
    """Complete resource analytics response."""
    agentId: str = Field(..., alias="agentId")
    workspaceId: str = Field(..., alias="workspaceId")
    timePeriod: str = Field(..., alias="timePeriod")
    resourceMetrics: ResourceUtilizationMetrics = Field(..., alias="resourceMetrics")
    tokenAnalysis: TokenAnalysis = Field(..., alias="tokenAnalysis")
    costBreakdown: CostBreakdown = Field(..., alias="costBreakdown")
    efficiencyScore: EfficiencyScore = Field(..., alias="efficiencyScore")
    budgetUsage: Optional[BudgetUsage] = Field(None, alias="budgetUsage")
    optimizations: List[OptimizationRecommendation] = []
    wasteDetection: WasteSummary = Field(..., alias="wasteDetection")
    forecasts: List[ResourceForecast] = []

    class Config:
        populate_by_name = True


class CostAnalysisResponse(BaseModel):
    """Cost analysis response."""
    workspaceId: str = Field(..., alias="workspaceId")
    period: str
    totalCost: float = Field(..., alias="totalCost")
    costByAgent: Dict[str, float] = Field(..., alias="costByAgent")
    costBreakdown: CostBreakdown = Field(..., alias="costBreakdown")
    costTrends: List[Dict[str, Any]] = Field(..., alias="costTrends")
    projections: CostProjection
    optimizationPotential: float = Field(..., alias="optimizationPotential")

    class Config:
        populate_by_name = True
