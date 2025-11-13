"""Collaboration analytics API schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

__all__ = [
    # Enums
    "WorkflowType",
    "WorkflowStatus",
    "InteractionType",
    "DependencyType",
    "PatternType",
    "OptimizationGoal",
    # Request models
    "WorkflowCollaborationRequest",
    "CollaborationPatternRequest",
    "WorkflowOptimizationRequest",
    "CollectiveIntelligenceRequest",
    # Response models
    "WorkflowCollaborationResponse",
    "CollaborationPatternResponse",
    "WorkflowOptimizationResponse",
    "CollectiveIntelligenceResponse",
    "HandoffMetricsResponse",
    "DependencyAnalysisResponse",
    "LoadBalancingResponse",
    # Supporting models
    "AgentNode",
    "AgentInteractionEdge",
    "HandoffMetrics",
    "DependencyMetrics",
    "CollaborationCluster",
    "CollaborationPattern",
    "OptimizationStrategy",
    "CollectiveMetrics",
    "LoadDistribution",
]


class WorkflowType(str, Enum):
    """Workflow execution types."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    HYBRID = "hybrid"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class InteractionType(str, Enum):
    """Agent interaction types."""
    HANDOFF = "handoff"
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    SYNC = "sync"


class DependencyType(str, Enum):
    """Agent dependency types."""
    DATA = "data"
    CONTROL = "control"
    SEQUENCE = "sequence"
    CONDITIONAL = "conditional"


class PatternType(str, Enum):
    """Collaboration pattern types."""
    COMMON_WORKFLOW = "common_workflow"
    CLUSTER = "cluster"
    COMMUNICATION = "communication"
    BOTTLENECK = "bottleneck"


class OptimizationGoal(str, Enum):
    """Optimization goals."""
    EFFICIENCY = "efficiency"
    RELIABILITY = "reliability"
    SPEED = "speed"
    COST = "cost"


# =====================================================================
# Request Models
# =====================================================================


class WorkflowCollaborationRequest(BaseModel):
    """Request for workflow collaboration metrics."""
    workflow_id: str = Field(..., description="Workflow ID")
    include_handoffs: bool = Field(default=True, description="Include handoff details")
    include_dependencies: bool = Field(default=True, description="Include dependency analysis")
    include_patterns: bool = Field(default=False, description="Include detected patterns")


class CollaborationPatternRequest(BaseModel):
    """Request for collaboration pattern analysis."""
    workspace_id: str = Field(..., description="Workspace ID")
    timeframe: str = Field(default="30d", description="Analysis timeframe (e.g., '7d', '30d', '90d')")
    pattern_type: Optional[PatternType] = Field(default=None, description="Filter by pattern type")
    min_frequency: int = Field(default=2, description="Minimum occurrence frequency")
    include_optimization: bool = Field(default=True, description="Include optimization opportunities")


class WorkflowOptimizationRequest(BaseModel):
    """Request for workflow optimization recommendations."""
    workflow_id: str = Field(..., description="Workflow ID")
    optimization_goals: List[OptimizationGoal] = Field(
        default=[OptimizationGoal.EFFICIENCY, OptimizationGoal.RELIABILITY],
        description="Optimization goals"
    )
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Optimization constraints")


class CollectiveIntelligenceRequest(BaseModel):
    """Request for collective intelligence metrics."""
    workspace_id: str = Field(..., description="Workspace ID")
    metric_types: List[str] = Field(
        default=["emergence", "adaptation", "efficiency"],
        description="Metric types to analyze"
    )
    timeframe: str = Field(default="30d", description="Analysis timeframe")


# =====================================================================
# Supporting Models
# =====================================================================


class AgentNode(BaseModel):
    """Agent node in collaboration graph."""
    agent_id: str
    agent_name: Optional[str] = None
    role: Optional[str] = None
    responsibilities: List[str] = []
    execution_count: int = 0
    avg_processing_time_ms: float = 0.0
    success_rate: float = 0.0


class AgentInteractionEdge(BaseModel):
    """Agent interaction edge in collaboration graph."""
    source_agent_id: str
    target_agent_id: str
    interaction_type: InteractionType
    interaction_count: int = 0
    avg_interaction_time_ms: float = 0.0
    avg_data_size_bytes: int = 0
    error_rate: float = 0.0
    avg_quality_score: float = 0.0


class HandoffMetrics(BaseModel):
    """Handoff performance metrics."""
    handoff_id: str
    source_agent: str
    target_agent: str
    preparation_time_ms: int
    transfer_time_ms: int
    acknowledgment_time_ms: int
    total_handoff_time_ms: int
    data_size_bytes: int
    data_completeness: float
    schema_compatible: bool
    handoff_success: bool
    context_preserved: float
    information_loss: float


class DependencyMetrics(BaseModel):
    """Dependency analysis metrics."""
    agent_id: str
    depends_on_agent_id: str
    dependency_type: DependencyType
    dependency_strength: float
    is_circular: bool
    is_critical_path: bool
    avg_wait_time_ms: float
    failure_impact: float


class CollaborationCluster(BaseModel):
    """Detected collaboration cluster."""
    cluster_id: str
    agents: List[str]
    cohesion_score: float
    specialization: Optional[str] = None
    interaction_density: float
    avg_performance: float
    cluster_metrics: Dict[str, Any] = {}


class CollaborationPattern(BaseModel):
    """Detected collaboration pattern."""
    pattern_id: str
    pattern_type: PatternType
    pattern_name: str
    pattern_description: Optional[str] = None
    agents_involved: List[str]
    occurrence_frequency: int
    success_rate: float
    avg_performance: float
    efficiency_score: float
    optimization_opportunities: List[str] = []
    redundancy_detected: bool = False
    is_optimal: bool = False
    detection_confidence: float


class OptimizationStrategy(BaseModel):
    """Optimization strategy recommendation."""
    strategy_type: str
    recommendation: str
    estimated_improvement: str
    complexity: str = "low"  # low, medium, high
    priority: int = 1  # 1-5, 5 being highest


class CollectiveMetrics(BaseModel):
    """Collective intelligence metrics."""
    diversity_index: float
    collective_accuracy: float
    emergence_score: float
    adaptation_rate: float
    synergy_factor: float
    decision_quality: float
    consensus_efficiency: float
    collective_learning_rate: float


class LoadDistribution(BaseModel):
    """Agent load distribution."""
    agent_id: str
    execution_count: int
    total_processing_time_ms: int
    avg_queue_length: float
    peak_load: int
    idle_time_percentage: float
    load_variance: float
    status: str = "normal"  # normal, overloaded, underutilized


# =====================================================================
# Response Models
# =====================================================================


class WorkflowCollaborationResponse(BaseModel):
    """Workflow collaboration metrics response."""
    workflow_id: str
    workflow_name: str
    workflow_type: WorkflowType
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None

    # Collaboration metrics
    agents_involved: int
    handoffs_count: int
    parallel_executions: int
    coordination_efficiency: float
    communication_overhead: float
    bottleneck_score: float
    synergy_index: float

    # Detailed data
    agent_nodes: List[AgentNode] = []
    interactions: List[AgentInteractionEdge] = []
    handoffs: List[HandoffMetrics] = []
    dependencies: List[DependencyMetrics] = []
    detected_patterns: List[CollaborationPattern] = []


class CollaborationPatternResponse(BaseModel):
    """Collaboration pattern analysis response."""
    workspace_id: str
    analysis_period: Dict[str, datetime]
    total_patterns_detected: int

    # Patterns by type
    common_workflows: List[CollaborationPattern] = []
    collaboration_clusters: List[CollaborationCluster] = []
    communication_patterns: List[CollaborationPattern] = []
    bottleneck_patterns: List[CollaborationPattern] = []

    # Insights
    emergent_behaviors: List[str] = []
    synergy_opportunities: List[str] = []
    redundancy_detected: List[str] = []


class WorkflowOptimizationResponse(BaseModel):
    """Workflow optimization recommendations response."""
    workflow_id: str
    workflow_name: str
    current_performance: Dict[str, Any]
    optimization_potential: float  # 0-1 score

    # Identified issues
    bottlenecks: List[Dict[str, Any]] = []
    inefficiencies: List[Dict[str, Any]] = []
    failure_points: List[Dict[str, Any]] = []

    # Optimization strategies
    optimization_strategies: List[OptimizationStrategy] = []

    # Estimated improvements
    estimated_improvements: Dict[str, str] = {}
    priority_rank: int


class CollectiveIntelligenceResponse(BaseModel):
    """Collective intelligence metrics response."""
    workspace_id: str
    analysis_period: Dict[str, datetime]

    # Core metrics
    metrics: CollectiveMetrics

    # Agent-level metrics
    agent_contributions: List[Dict[str, Any]] = []

    # Emergent intelligence
    emergent_capabilities: List[str] = []
    emergence_score: float
    synergy_factor: float

    # Decision making
    decision_quality_metrics: Dict[str, float] = {}
    consensus_metrics: Dict[str, float] = {}

    # Learning and adaptation
    collective_learning_rate: float
    adaptation_metrics: Dict[str, float] = {}


class HandoffMetricsResponse(BaseModel):
    """Handoff metrics response."""
    workflow_id: str
    total_handoffs: int
    successful_handoffs: int
    failed_handoffs: int
    avg_handoff_time_ms: float

    # Performance breakdown
    avg_preparation_time_ms: float
    avg_transfer_time_ms: float
    avg_acknowledgment_time_ms: float

    # Quality metrics
    avg_data_completeness: float
    avg_context_preserved: float
    avg_information_loss: float
    schema_compatibility_rate: float

    # Detailed handoffs
    handoffs: List[HandoffMetrics] = []

    # Optimization opportunities
    optimization_strategies: List[OptimizationStrategy] = []


class DependencyAnalysisResponse(BaseModel):
    """Dependency analysis response."""
    workspace_id: str
    total_dependencies: int
    max_dependency_depth: int

    # Dependency graph metrics
    circular_dependencies: List[List[str]] = []
    critical_path: List[str] = []
    bottleneck_agents: List[str] = []

    # Risk assessment
    single_points_of_failure: List[str] = []
    cascade_risk_score: float
    redundancy_gaps: List[Dict[str, Any]] = []

    # Detailed dependencies
    dependencies: List[DependencyMetrics] = []

    # Optimization recommendations
    parallelization_opportunities: List[Dict[str, Any]] = []
    dependency_reduction_suggestions: List[str] = []
    load_balancing_recommendations: List[str] = []


class LoadBalancingResponse(BaseModel):
    """Load balancing metrics response."""
    workspace_id: str
    period: Dict[str, datetime]

    # Load distribution
    load_distribution: List[LoadDistribution]

    # Imbalance metrics
    gini_coefficient: float  # 0 = perfect equality, 1 = maximum inequality
    load_skewness: float
    load_variance: float

    # Identified issues
    overloaded_agents: List[str] = []
    underutilized_agents: List[str] = []

    # Recommendations
    rebalancing_strategy: Optional[str] = None
    agent_scaling_recommendations: Dict[str, str] = {}
    workflow_reassignment_suggestions: List[Dict[str, Any]] = []
