"""
Pydantic schemas for Agent Lifecycle Analytics.

This module defines request and response models for agent lifecycle tracking,
including state transitions, version management, deployments, and health scoring.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class AgentState(str, Enum):
    """Agent lifecycle states."""
    DRAFT = "draft"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class DeploymentType(str, Enum):
    """Deployment strategy types."""
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    DIRECT = "direct"


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class HealthStatus(str, Enum):
    """Agent health status."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class RetirementPriority(str, Enum):
    """Retirement candidate priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Lifecycle Event Schemas
# ============================================================================

class LifecycleEventBase(BaseModel):
    """Base lifecycle event model."""
    agent_id: str = Field(..., description="Agent UUID")
    workspace_id: str = Field(..., description="Workspace UUID")
    event_type: str = Field(..., description="Type of lifecycle event")
    previous_state: Optional[str] = Field(None, description="Previous state")
    new_state: Optional[str] = Field(None, description="New state")
    triggered_by: str = Field("system", description="Who triggered the event")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LifecycleEventCreate(LifecycleEventBase):
    """Create lifecycle event request."""
    pass


class LifecycleEvent(LifecycleEventBase):
    """Lifecycle event response."""
    id: str
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StateTransition(BaseModel):
    """State transition detail."""
    from_state: Optional[str] = Field(None, description="Previous state")
    to_state: str = Field(..., description="New state")
    transition_at: datetime = Field(..., description="Transition timestamp")
    duration_in_state: Optional[float] = Field(None, description="Duration in previous state (seconds)")
    triggered_by: str = Field(..., description="user, system, api, automation")
    transition_reason: Optional[str] = Field(None, description="Reason for transition")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Version Schemas
# ============================================================================

class AgentVersionBase(BaseModel):
    """Base agent version model."""
    agent_id: str = Field(..., description="Agent UUID")
    workspace_id: str = Field(..., description="Workspace UUID")
    version: str = Field(..., description="Version string (e.g., 1.0.0)")
    version_number: int = Field(..., description="Sequential version number")
    description: Optional[str] = Field(None, description="Version description")
    changelog: Optional[str] = Field(None, description="What changed in this version")
    capabilities_added: List[str] = Field(default_factory=list)
    capabilities_removed: List[str] = Field(default_factory=list)
    capabilities_modified: List[str] = Field(default_factory=list)
    status: str = Field("draft", description="Version status")


class AgentVersionCreate(AgentVersionBase):
    """Create agent version request."""
    pass


class AgentVersion(AgentVersionBase):
    """Agent version response."""
    id: str
    performance_impact: Dict[str, Any] = Field(default_factory=dict)
    lines_of_code: Optional[int] = None
    cyclomatic_complexity: Optional[float] = None
    cognitive_complexity: Optional[float] = None
    dependencies_count: Optional[int] = None
    is_active: bool = False
    created_at: datetime
    released_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VersionPerformanceComparison(BaseModel):
    """Performance comparison between versions."""
    version_id: str
    agent_id: str
    version: str
    version_number: int
    version_released: Optional[datetime]
    total_executions: int
    avg_duration: float
    p50_duration: float
    p95_duration: float
    success_rate: float
    avg_credits: float
    avg_rating: Optional[float]
    unique_users: int
    error_count: int


# ============================================================================
# Deployment Schemas
# ============================================================================

class DeploymentBase(BaseModel):
    """Base deployment model."""
    agent_id: str = Field(..., description="Agent UUID")
    workspace_id: str = Field(..., description="Workspace UUID")
    version_id: str = Field(..., description="Version being deployed")
    deployment_type: str = Field(..., description="Deployment strategy")
    environment: str = Field("production", description="Target environment")
    deployment_strategy: Dict[str, Any] = Field(default_factory=dict)
    rollout_percentage: int = Field(100, ge=0, le=100)


class DeploymentCreate(DeploymentBase):
    """Create deployment request."""
    triggered_by: str = Field("system", description="Who triggered deployment")


class Deployment(DeploymentBase):
    """Deployment response."""
    id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    success_metrics: Dict[str, Any] = Field(default_factory=dict)
    failure_reason: Optional[str] = None
    rollback_from: Optional[str] = None
    triggered_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentMetrics(BaseModel):
    """Deployment success metrics."""
    total_deployments: int
    successful_deployments: int
    failed_deployments: int
    rollback_count: int
    success_rate: float
    avg_deployment_time_minutes: float
    last_deployment: Optional[datetime]


# ============================================================================
# Health Score Schemas
# ============================================================================

class ComponentScores(BaseModel):
    """Individual component scores."""
    performance_score: float = Field(..., ge=0, le=100)
    reliability_score: float = Field(..., ge=0, le=100)
    usage_score: float = Field(..., ge=0, le=100)
    maintenance_score: float = Field(..., ge=0, le=100)
    cost_score: float = Field(..., ge=0, le=100)


class HealthScoreBase(BaseModel):
    """Base health score model."""
    agent_id: str = Field(..., description="Agent UUID")
    workspace_id: str = Field(..., description="Workspace UUID")
    overall_score: float = Field(..., ge=0, le=100, description="Overall health score")
    health_status: str = Field(..., description="Health status category")
    component_scores: ComponentScores


class HealthScoreCreate(HealthScoreBase):
    """Create health score request."""
    calculation_period_start: datetime
    calculation_period_end: datetime


class HealthScore(HealthScoreBase):
    """Health score response."""
    id: str
    performance_score: float
    reliability_score: float
    usage_score: float
    maintenance_score: float
    cost_score: float
    improvement_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    trend: Optional[str] = None
    previous_score: Optional[float] = None
    score_change: Optional[float] = None
    calculated_at: datetime
    calculation_period_start: datetime
    calculation_period_end: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthScoreRequest(BaseModel):
    """Request to calculate health score."""
    agent_id: str
    workspace_id: str
    include_history: bool = Field(True, description="Include historical scores")
    prediction_days: int = Field(30, ge=0, le=90, description="Days to predict")


# ============================================================================
# Retirement Schemas
# ============================================================================

class RetirementCandidateBase(BaseModel):
    """Base retirement candidate model."""
    agent_id: str
    workspace_id: str
    days_since_last_use: int
    total_executions_30d: int = 0
    recent_avg_rating: Optional[float] = None
    active_users_30d: int = 0
    dependent_agents_count: int = 0
    retirement_priority: str
    retirement_score: float


class RetirementCandidate(RetirementCandidateBase):
    """Retirement candidate response."""
    id: str
    recommended_replacement_id: Optional[str] = None
    migration_effort: Optional[str] = None
    affected_workflows: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_migration_days: Optional[int] = None
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    status: str
    identified_at: datetime
    approved_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetirementCandidatesQuery(BaseModel):
    """Query parameters for retirement candidates."""
    workspace_id: str
    threshold_days: int = Field(90, ge=1, description="Days of inactivity threshold")
    min_priority: str = Field("medium", description="Minimum priority level")
    limit: int = Field(100, ge=1, le=1000)


class MigrationPathAnalysis(BaseModel):
    """Migration path analysis for retiring agent."""
    retiring_agent_id: str
    recommended_replacements: List[Dict[str, Any]] = Field(default_factory=list)
    affected_workflows: List[str] = Field(default_factory=list)
    estimated_migration_time: int
    risk_assessment: Dict[str, float]


# ============================================================================
# Lifecycle Analytics Response Schemas
# ============================================================================

class StateDuration(BaseModel):
    """Duration spent in each state."""
    state: str
    total_duration_seconds: float
    average_duration_seconds: float
    total_occurrences: int
    percentage_of_lifetime: float


class LifecycleTimeline(BaseModel):
    """Timeline visualization data."""
    timestamp: datetime
    state: str
    event: str
    triggered_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LifecycleMetrics(BaseModel):
    """Comprehensive lifecycle metrics."""
    current_state: str
    days_in_current_state: float
    total_days_since_creation: float
    total_transitions: int
    total_versions: int
    production_versions: int
    latest_version_number: int
    total_deployments: int
    successful_deployments: int
    deployment_success_rate: float
    rollback_count: int
    activation_lag: Optional[float] = Field(None, description="Days from created to active")
    deprecation_lag: Optional[float] = Field(None, description="Days from active to deprecated")


class StateTransitionMatrix(BaseModel):
    """State transition probability matrix."""
    from_state: str
    to_state: str
    transition_count: int
    transition_probability: float
    avg_time_in_source_state: float


class AgentLifecycleAnalytics(BaseModel):
    """Complete agent lifecycle analytics response."""
    agent_id: str
    workspace_id: str
    generated_at: datetime

    # Current state
    current_state: str
    current_state_since: datetime

    # Metrics
    lifecycle_metrics: LifecycleMetrics
    state_durations: List[StateDuration] = Field(default_factory=list)

    # Transitions
    transitions: List[StateTransition] = Field(default_factory=list)
    transition_matrix: List[StateTransitionMatrix] = Field(default_factory=list)

    # Timeline for visualization
    timeline: List[LifecycleTimeline] = Field(default_factory=list)

    # Versions
    versions: List[AgentVersion] = Field(default_factory=list)
    version_comparison: List[VersionPerformanceComparison] = Field(default_factory=list)

    # Deployments
    deployment_metrics: Optional[DeploymentMetrics] = None
    recent_deployments: List[Deployment] = Field(default_factory=list)

    # Health
    current_health_score: Optional[HealthScore] = None
    health_trend: Optional[str] = None

    # Retirement risk
    retirement_risk: Optional[str] = Field(None, description="low, medium, high")
    retirement_score: Optional[float] = None


class VersionComparisonRequest(BaseModel):
    """Request to compare two versions."""
    agent_id: str
    workspace_id: str
    version_a: str
    version_b: str
    metrics: List[str] = Field(
        default=["performance", "cost", "reliability"],
        description="Metrics to compare"
    )


class VersionComparisonResponse(BaseModel):
    """Version comparison response."""
    agent_id: str
    version_a: VersionPerformanceComparison
    version_b: VersionPerformanceComparison
    comparison: Dict[str, Any]
    recommendation: str


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class LifecycleAnalyticsQuery(BaseModel):
    """Query parameters for lifecycle analytics."""
    agent_id: str
    workspace_id: str
    timeframe: str = Field("all", pattern="^(24h|7d|30d|90d|all)$")
    include_predictions: bool = False
    include_versions: bool = True
    include_deployments: bool = True
    include_health: bool = True


class DeploymentPatternsQuery(BaseModel):
    """Query for deployment pattern analysis."""
    workspace_id: str
    timeframe: str = Field("30d", pattern="^(7d|30d|90d|all)$")
    agent_id: Optional[str] = None


class DeploymentPatternAnalysis(BaseModel):
    """Deployment pattern analysis response."""
    workspace_id: str
    deployment_frequency: Dict[str, float]
    preferred_deployment_windows: List[Dict[str, Any]]
    deployment_velocity: float
    deployment_risk_score: float
    optimal_deployment_size: int
    recommendations: List[str]


# ============================================================================
# Lifecycle Event Stream Schemas
# ============================================================================

class LifecycleEventSubscription(BaseModel):
    """Subscription request for lifecycle events."""
    agent_id: Optional[str] = None
    workspace_id: str
    event_types: List[str] = Field(default_factory=list, description="Filter by event types")


class LifecycleAlert(BaseModel):
    """Alert for lifecycle events."""
    alert_type: str
    severity: str
    agent_id: str
    workspace_id: str
    message: str
    event: LifecycleEvent
    timestamp: datetime
