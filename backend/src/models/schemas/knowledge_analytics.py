"""Knowledge Base Analytics schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# Enums
class KnowledgeType(str, Enum):
    """Knowledge item types."""
    FACT = "fact"
    RULE = "rule"
    PROCEDURE = "procedure"
    CONCEPT = "concept"
    EXAMPLE = "example"
    RELATIONSHIP = "relationship"


class VerificationStatus(str, Enum):
    """Verification status."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    OUTDATED = "outdated"


class DriftType(str, Enum):
    """Knowledge drift types."""
    CONCEPT_DRIFT = "concept_drift"
    FACT_STALENESS = "fact_staleness"
    RULE_CONFLICT = "rule_conflict"
    ACCURACY_DEGRADATION = "accuracy_degradation"
    SEMANTIC_SHIFT = "semantic_shift"


class QualityTrend(str, Enum):
    """Quality trend directions."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class LifecycleStage(str, Enum):
    """Knowledge lifecycle stages."""
    ACQUISITION = "acquisition"
    VALIDATION = "validation"
    ACTIVE_USE = "active_use"
    MAINTENANCE = "maintenance"
    DEPRECATION = "deprecation"
    ARCHIVED = "archived"


# Knowledge Item Schemas
class KnowledgeItemBase(BaseModel):
    """Base knowledge item schema."""
    knowledge_type: KnowledgeType
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    content: str
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeItemCreate(KnowledgeItemBase):
    """Schema for creating a knowledge item."""
    agent_id: str
    workspace_id: str
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    embedding_vector: Optional[List[float]] = None


class KnowledgeItemResponse(KnowledgeItemBase):
    """Schema for knowledge item response."""
    id: str
    agent_id: str
    workspace_id: str
    content_hash: Optional[str] = None
    quality_score: Optional[float] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    usefulness_score: Optional[float] = None
    node_degree: int = 0
    centrality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Knowledge Graph Schemas
class GraphMetrics(BaseModel):
    """Knowledge graph structure metrics."""
    total_nodes: int
    total_edges: int
    graph_density: float
    average_degree: float
    clustering_coefficient: float
    connected_components: int
    max_path_length: int


class NodeTypeDistribution(BaseModel):
    """Distribution of node types in knowledge graph."""
    concepts: int = 0
    facts: int = 0
    procedures: int = 0
    examples: int = 0
    rules: int = 0
    relationships: int = 0


class EvolutionMetrics(BaseModel):
    """Knowledge graph evolution metrics."""
    growth_rate: float
    update_frequency: float
    deprecation_rate: float
    quality_trend: QualityTrend


class KnowledgeDomainMetrics(BaseModel):
    """Knowledge domain coverage metrics."""
    domain: str
    coverage: float
    depth: float
    quality_score: float
    last_updated: datetime


class KnowledgeGraphResponse(BaseModel):
    """Complete knowledge graph analytics response."""
    agent_id: str
    knowledge_base_id: str
    graph_metrics: GraphMetrics
    node_types: NodeTypeDistribution
    knowledge_domains: List[KnowledgeDomainMetrics]
    evolution_metrics: EvolutionMetrics


# Knowledge Acquisition Schemas
class LearningPhase(BaseModel):
    """Learning curve phase."""
    name: Literal["initial", "rapid_growth", "consolidation", "mastery"]
    start: int
    end: int
    rate: float


class LearningCurveAnalysis(BaseModel):
    """Learning curve analysis."""
    phases: List[LearningPhase]
    current_phase: Optional[str] = None
    saturation_point: Optional[int] = None
    efficiency_trend: List[float] = Field(default_factory=list)


class SourceQualityMetrics(BaseModel):
    """Knowledge source quality metrics."""
    source_id: str
    source_name: str
    source_type: str
    items_from_source: int
    avg_confidence: float
    avg_usefulness: float
    verification_rate: float
    reliability_score: float
    reliability_category: Literal["highly_reliable", "reliable", "moderately_reliable", "unreliable"]
    source_rank: int


class AcquisitionMetrics(BaseModel):
    """Knowledge acquisition analytics."""
    acquisition_rate: float
    total_items_acquired: int
    avg_quality_score: float
    source_quality: List[SourceQualityMetrics]
    learning_curve: LearningCurveAnalysis
    knowledge_gaps: List[str] = Field(default_factory=list)


# Knowledge Retrieval Schemas
class RetrievalPerformanceMetrics(BaseModel):
    """Knowledge retrieval performance."""
    avg_retrieval_time_ms: int
    p95_retrieval_time_ms: int
    cache_hit_rate: float
    index_efficiency: float
    query_success_rate: float


class AccessDistribution(BaseModel):
    """Knowledge access distribution."""
    hot_items_percentage: float
    cold_items_percentage: float
    access_inequality: float  # Gini coefficient


class SearchEffectiveness(BaseModel):
    """Search effectiveness metrics."""
    precision: float
    recall: float
    f1_score: float
    avg_results_examined: int
    user_satisfaction: float


class RetrievalMetricsResponse(BaseModel):
    """Complete retrieval metrics response."""
    agent_id: str
    retrieval_performance: RetrievalPerformanceMetrics
    access_distribution: AccessDistribution
    search_effectiveness: SearchEffectiveness
    most_accessed_items: List[Dict[str, Any]] = Field(default_factory=list)


# Knowledge Validation Schemas
class ValidationEventCreate(BaseModel):
    """Create validation event."""
    knowledge_item_id: str
    agent_id: str
    workspace_id: str
    validation_type: Literal["manual", "automated", "crowd_sourced", "cross_reference", "usage_based"]
    is_valid: bool
    confidence_level: Optional[float] = Field(None, ge=0, le=1)
    validator_id: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    corrections_applied: Dict[str, Any] = Field(default_factory=dict)
    business_impact: Optional[Literal["none", "low", "medium", "high", "critical"]] = None


class ValidationEventResponse(BaseModel):
    """Validation event response."""
    id: str
    knowledge_item_id: str
    agent_id: str
    validation_type: str
    is_valid: bool
    confidence_level: Optional[float] = None
    affected_decisions: int = 0
    affected_users: int = 0
    business_impact: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Knowledge Drift Schemas
class DriftDetectionResult(BaseModel):
    """Drift detection result."""
    drift_type: DriftType
    drift_score: float
    drift_detected: bool
    affected_concepts: List[str] = Field(default_factory=list)


class ConceptDriftAnalysis(BaseModel):
    """Concept drift analysis."""
    drift_score: float
    drift_detected: bool
    affected_concepts: List[str]


class DriftAnalysisResponse(BaseModel):
    """Complete drift analysis response."""
    agent_id: str
    concept_drift: ConceptDriftAnalysis
    fact_staleness: Dict[str, Any]
    rule_conflicts: List[Dict[str, Any]]
    accuracy_degradation: Dict[str, Any]
    daily_drift_rate: Optional[float] = None
    weekly_drift_rate: Optional[float] = None
    monthly_drift_rate: Optional[float] = None
    remediation_plan: Optional[Dict[str, Any]] = None


class DriftEventCreate(BaseModel):
    """Create drift event."""
    agent_id: str
    workspace_id: str
    knowledge_item_id: Optional[str] = None
    drift_type: DriftType
    drift_score: float
    severity: Literal["low", "medium", "high", "critical"]
    baseline_value: Optional[Dict[str, Any]] = None
    current_value: Optional[Dict[str, Any]] = None
    affected_concepts: List[str] = Field(default_factory=list)


# Knowledge Transfer Schemas
class KnowledgeTransferCreate(BaseModel):
    """Create knowledge transfer."""
    source_agent_id: str
    target_agent_id: str
    workspace_id: str
    knowledge_item_ids: List[str]
    knowledge_domain: Optional[str] = None
    transfer_type: Literal["full_copy", "adaptive_copy", "reference", "merge"]


class KnowledgeTransferResponse(BaseModel):
    """Knowledge transfer response."""
    id: str
    source_agent_id: str
    target_agent_id: str
    workspace_id: str
    transferred_items_count: int
    failed_items_count: int
    transfer_successful: bool
    knowledge_quality_score: Optional[float] = None
    performance_improvement: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransferEffectivenessMetrics(BaseModel):
    """Transfer effectiveness metrics."""
    source_agent_id: str
    target_agent_id: str
    transfer_count: int
    success_rate: float
    avg_performance_gain: float
    transfer_effectiveness: Literal["highly_effective", "effective", "moderately_effective", "ineffective"]


# Knowledge Utilization Schemas
class UtilizationMetrics(BaseModel):
    """Knowledge utilization metrics."""
    overall_usage_rate: float
    knowledge_coverage: float
    redundancy_ratio: float
    knowledge_roi: float


class DecisionImpact(BaseModel):
    """Decision impact metrics."""
    decisions_influenced: int
    decision_quality_improvement: float
    error_reduction: float


class PerformanceCorrelation(BaseModel):
    """Performance correlation metrics."""
    accuracy_correlation: float
    speed_correlation: float
    user_satisfaction_correlation: float


class EffectivenessAnalysis(BaseModel):
    """Effectiveness analysis."""
    decision_impact: DecisionImpact
    performance_correlation: PerformanceCorrelation


class OptimizationRecommendations(BaseModel):
    """Optimization recommendations."""
    unused_knowledge: List[str]
    high_value_knowledge: List[str]
    knowledge_to_deprecate: List[str]
    knowledge_to_expand: List[str]


class KnowledgeUsageAnalytics(BaseModel):
    """Complete knowledge usage analytics."""
    agent_id: str
    utilization_metrics: UtilizationMetrics
    usage_patterns: Dict[str, Any]
    effectiveness_analysis: EffectivenessAnalysis
    optimization_recommendations: OptimizationRecommendations


# Knowledge Lifecycle Schemas
class LifecycleStageHistory(BaseModel):
    """Lifecycle stage history entry."""
    stage: LifecycleStage
    entered_at: datetime
    duration_days: float
    trigger_event: str


class HealthMetrics(BaseModel):
    """Knowledge item health metrics."""
    accuracy_score: float
    relevance_score: float
    usage_frequency: float
    last_validation: Optional[datetime] = None
    update_needed: bool


class LifecyclePredictions(BaseModel):
    """Lifecycle predictions."""
    expected_deprecation_date: Optional[datetime] = None
    maintenance_priority: Literal["high", "medium", "low"]
    refresh_recommendation: str


class KnowledgeLifecycle(BaseModel):
    """Complete knowledge lifecycle information."""
    knowledge_item_id: str
    current_stage: LifecycleStage
    stage_history: List[LifecycleStageHistory]
    health_metrics: HealthMetrics
    lifecycle_predictions: LifecyclePredictions


# Graph Optimization Schemas
class OptimizationAction(BaseModel):
    """Graph optimization action."""
    action: str
    count: int
    impact: str


class OptimizationImprovement(BaseModel):
    """Optimization improvement metrics."""
    query_speed_improvement: float
    storage_reduction: float
    traversal_efficiency: float


class GraphOptimizationResult(BaseModel):
    """Graph optimization result."""
    agent_id: str
    optimizations: Dict[str, List[OptimizationAction]]
    improvement_metrics: OptimizationImprovement
    new_graph_metrics: GraphMetrics


# Request Schemas
class KnowledgeBaseOptimizationRequest(BaseModel):
    """Knowledge base optimization request."""
    optimization_type: Literal["comprehensive", "redundancy", "edges", "clusters", "paths"] = "comprehensive"
    dry_run: bool = True


class KnowledgeDriftDetectionRequest(BaseModel):
    """Drift detection request."""
    time_window: str = "30d"
    drift_threshold: float = Field(0.3, ge=0, le=1)


class KnowledgeTransferAnalysisRequest(BaseModel):
    """Knowledge transfer analysis request."""
    source_agent_id: str
    target_agent_id: str
    knowledge_domain: Optional[str] = None


# API Response Schemas
class KnowledgeBaseAnalyticsResponse(BaseModel):
    """Complete knowledge base analytics response."""
    agent_id: str
    workspace_id: str
    graph_analytics: Optional[KnowledgeGraphResponse] = None
    acquisition_analytics: Optional[AcquisitionMetrics] = None
    retrieval_analytics: Optional[RetrievalMetricsResponse] = None
    usage_analytics: Optional[KnowledgeUsageAnalytics] = None
    drift_analysis: Optional[DriftAnalysisResponse] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingQualityMetrics(BaseModel):
    """Embedding quality assessment."""
    embedding_coverage: float
    embedding_freshness: float
    clustering_quality: float
    semantic_coherence: float
    outdated_embeddings: float


class SemanticSearchAnalysis(BaseModel):
    """Semantic search performance analysis."""
    embedding_quality: EmbeddingQualityMetrics
    semantic_accuracy: Dict[str, float]
    query_understanding: Dict[str, Any]
    result_relevance: float
    optimization_opportunities: List[Dict[str, Any]]


# Materialized View Schemas
class SourceQualityView(BaseModel):
    """Source quality materialized view."""
    agent_id: str
    source_id: str
    source_type: str
    source_name: str
    items_from_source: int
    avg_confidence: float
    avg_usefulness: float
    total_accesses: int
    verification_rate: float
    reliability_score: float
    reliability_category: str
    source_rank: int

    model_config = ConfigDict(from_attributes=True)


class TransferAnalyticsView(BaseModel):
    """Transfer analytics materialized view."""
    source_agent_id: str
    target_agent_id: str
    workspace_id: str
    transfer_count: int
    avg_quality: float
    success_rate: float
    avg_adaptation_time: float
    avg_performance_gain: float
    total_items_transferred: int
    total_items_failed: int
    overall_performance_gain: Optional[float] = None
    transfer_effectiveness: str

    model_config = ConfigDict(from_attributes=True)
