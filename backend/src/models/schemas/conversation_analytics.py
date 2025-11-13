"""Conversation analytics schemas and data models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================================
# Enums
# =====================================================================

class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    """Conversation status types."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"


class OutcomeCategory(str, Enum):
    """Conversation outcome categories."""
    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"
    ABANDONED = "abandoned"


class EngagementLevel(str, Enum):
    """Engagement level categories."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PatternType(str, Enum):
    """Pattern types for conversation analysis."""
    FLOW = "flow"
    TOPIC = "topic"
    USER_BEHAVIOR = "user_behavior"
    FAILURE = "failure"


# =====================================================================
# Base Models
# =====================================================================

class SessionData(BaseModel):
    """Session timing and duration data."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    idle_time_ms: int = 0
    active_time_ms: int = 0

    class Config:
        populate_by_name = True


class MessageMetrics(BaseModel):
    """Message-level metrics."""
    total_messages: int = 0
    user_messages: int = 0
    agent_messages: int = 0
    system_messages: int = 0
    average_response_time_ms: Optional[int] = None
    message_velocity: Optional[float] = Field(None, description="Messages per minute")

    class Config:
        populate_by_name = True


class TokenUsage(BaseModel):
    """Token usage and cost metrics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    tokens_per_message: Optional[float] = None

    class Config:
        populate_by_name = True


class InteractionQuality(BaseModel):
    """Interaction quality scores."""
    sentiment_score: Optional[float] = Field(None, ge=0, le=1)
    clarity_score: Optional[float] = Field(None, ge=0, le=1)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    completion_rate: Optional[float] = Field(None, ge=0, le=1)
    user_satisfaction: Optional[float] = Field(None, ge=0, le=1)

    class Config:
        populate_by_name = True


class UserEmotion(BaseModel):
    """User emotion data."""
    primary: str = Field(..., description="Primary emotion: happy, frustrated, confused, satisfied, neutral")
    confidence: float = Field(..., ge=0, le=1)
    intensity: float = Field(..., ge=0, le=1)

    class Config:
        populate_by_name = True


class EmotionTimelinePoint(BaseModel):
    """Point in emotion timeline."""
    timestamp: datetime
    user_emotion: UserEmotion
    agent_response_appropriateness: float = Field(..., ge=0, le=1)

    class Config:
        populate_by_name = True


class EmotionTransition(BaseModel):
    """Emotion transition between states."""
    from_emotion: str = Field(..., alias="from")
    to_emotion: str = Field(..., alias="to")
    frequency: int
    avg_transition_time_ms: int

    class Config:
        populate_by_name = True


class OverallEmotionalJourney(BaseModel):
    """Overall emotional journey summary."""
    start_emotion: str
    end_emotion: str
    peak_positive: float
    peak_negative: float
    emotional_variance: float

    class Config:
        populate_by_name = True


class TurnDistribution(BaseModel):
    """Turn distribution between user and agent."""
    user_initiated: int = 0
    agent_initiated: int = 0

    class Config:
        populate_by_name = True


class TurnLengthStats(BaseModel):
    """Turn length statistics."""
    user_avg_length: float
    agent_avg_length: float
    length_correlation: float

    class Config:
        populate_by_name = True


class InterruptionPatterns(BaseModel):
    """Interruption pattern metrics."""
    user_interruptions: int = 0
    agent_interruptions: int = 0
    clarification_requests: int = 0

    class Config:
        populate_by_name = True


class ConversationDynamics(BaseModel):
    """Conversation dynamics metrics."""
    momentum_score: float = Field(..., ge=0, le=1, description="How well conversation flows")
    engagement_score: float = Field(..., ge=0, le=1)
    reciprocity_index: float = Field(..., ge=0, le=1, description="Balance of interaction")

    class Config:
        populate_by_name = True


class TurnPatterns(BaseModel):
    """Turn-taking pattern metrics."""
    average_turns: float
    turn_distribution: TurnDistribution
    turn_length_stats: TurnLengthStats
    interruption_patterns: InterruptionPatterns

    class Config:
        populate_by_name = True


class ErrorTypeDetail(BaseModel):
    """Error type breakdown."""
    error_type: str
    frequency: int
    examples: List[str] = []

    class Config:
        populate_by_name = True


class EntityPerformance(BaseModel):
    """Entity extraction performance metrics."""
    entity_type: str
    extraction_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    avg_confidence: float
    common_errors: List[ErrorTypeDetail] = []

    class Config:
        populate_by_name = True


class EntityRelationship(BaseModel):
    """Entity co-occurrence relationship."""
    entity_pairs: tuple[str, str]
    co_occurrence_frequency: int
    relationship_type: str

    class Config:
        populate_by_name = True


# =====================================================================
# Main Response Models
# =====================================================================

class ConversationAnalytics(BaseModel):
    """Complete conversation analytics."""
    conversation_id: str
    agent_id: str
    workspace_id: str
    user_id: str
    session_data: SessionData
    message_metrics: MessageMetrics
    token_usage: TokenUsage
    interaction_quality: InteractionQuality
    status: ConversationStatus = ConversationStatus.ACTIVE
    goal_achieved: Optional[bool] = None
    metadata: Dict[str, Any] = {}

    class Config:
        populate_by_name = True


class ConversationMessage(BaseModel):
    """Individual conversation message with analytics."""
    id: str
    conversation_id: str
    agent_id: str
    message_index: int
    role: MessageRole
    content: str
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None

    # Content analysis
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1)
    emotion_primary: Optional[str] = None
    emotion_confidence: Optional[float] = Field(None, ge=0, le=1)
    emotion_intensity: Optional[float] = Field(None, ge=0, le=1)

    # Intent and entities
    intent_classification: Optional[str] = None
    intent_confidence: Optional[float] = Field(None, ge=0, le=1)
    entity_extraction: Dict[str, Any] = {}

    # Quality metrics
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    completeness_score: Optional[float] = Field(None, ge=0, le=1)
    clarity_score: Optional[float] = Field(None, ge=0, le=1)

    # Error tracking
    error_occurred: bool = False
    error_type: Optional[str] = None
    retry_count: int = 0

    metadata: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        populate_by_name = True


class EmotionAnalytics(BaseModel):
    """Emotion and sentiment analytics."""
    conversation_id: str
    emotion_timeline: List[EmotionTimelinePoint]
    emotion_transitions: List[EmotionTransition]
    overall_emotional_journey: OverallEmotionalJourney

    class Config:
        populate_by_name = True


class TurnTakingMetrics(BaseModel):
    """Turn-taking analysis metrics."""
    conversation_id: str
    turn_patterns: TurnPatterns
    conversation_dynamics: ConversationDynamics

    class Config:
        populate_by_name = True


class ContextMetrics(BaseModel):
    """Context management metrics."""
    conversation_id: str
    agent_id: str
    context_tokens_used: int = 0
    useful_context_tokens: int = 0
    context_efficiency: Optional[float] = Field(None, ge=0, le=1)
    context_switches_per_conversation: int = 0
    topics_discussed: List[str] = []
    topic_switches: int = 0
    topic_coherence_score: Optional[float] = Field(None, ge=0, le=1)
    working_memory_usage: Optional[int] = None
    long_term_recall_count: int = 0
    reference_accuracy: Optional[float] = Field(None, ge=0, le=1)

    class Config:
        populate_by_name = True


class IntentRecognitionMetrics(BaseModel):
    """Intent recognition performance."""
    agent_id: str
    workspace_id: str
    intent_type: str
    total_occurrences: int
    avg_confidence: float
    accuracy: float
    avg_processing_time_ms: float
    top_phrases: List[str] = []

    class Config:
        populate_by_name = True


class EntityExtractionMetrics(BaseModel):
    """Entity extraction analytics."""
    agent_id: str
    entity_performance: List[EntityPerformance]
    entity_relationships: List[EntityRelationship]

    class Config:
        populate_by_name = True


class ResponseQualityMetrics(BaseModel):
    """Response quality analysis."""
    conversation_id: str
    message_id: str
    agent_id: str

    # Quality scores
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    completeness_score: Optional[float] = Field(None, ge=0, le=1)
    accuracy_score: Optional[float] = Field(None, ge=0, le=1)
    tone_appropriateness: Optional[float] = Field(None, ge=0, le=1)
    creativity_index: Optional[float] = Field(None, ge=0, le=1)
    personalization_level: Optional[float] = Field(None, ge=0, le=1)

    # Quality checks
    hallucination_detected: bool = False
    consistency_score: Optional[float] = Field(None, ge=0, le=1)
    clarity_score: Optional[float] = Field(None, ge=0, le=1)
    overall_quality_score: Optional[float] = Field(None, ge=0, le=1)

    class Config:
        populate_by_name = True


class EngagementMetrics(BaseModel):
    """User engagement metrics."""
    conversation_id: str
    agent_id: str
    user_id: str

    # Component scores
    interaction_depth: float = Field(..., ge=0, le=1)
    user_investment: float = Field(..., ge=0, le=1)
    conversation_momentum: float = Field(..., ge=0, le=1)
    topic_exploration: float = Field(..., ge=0, le=1)
    question_quality: float = Field(..., ge=0, le=1)
    feedback_indicators: float = Field(..., ge=0, le=1)
    overall_score: float = Field(..., ge=0, le=1)

    # Engagement categorization
    engagement_level: EngagementLevel

    # Recommendations
    recommendations: List[str] = []

    class Config:
        populate_by_name = True


class ConversationOutcome(BaseModel):
    """Conversation outcome metrics."""
    conversation_id: str
    agent_id: str
    workspace_id: str

    # Goal achievement
    goal_achieved: Optional[bool] = None
    tasks_completed: int = 0
    tasks_total: int = 0
    problems_solved: int = 0

    # Knowledge transfer
    knowledge_transferred_score: Optional[float] = Field(None, ge=0, le=1)

    # User satisfaction
    user_satisfaction_score: Optional[float] = Field(None, ge=0, le=1)
    follow_up_required: bool = False

    # Business metrics
    business_value_score: Optional[float] = None
    estimated_time_saved_minutes: Optional[float] = None
    cost_benefit_ratio: Optional[float] = None

    # Outcome categorization
    outcome_category: OutcomeCategory

    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        populate_by_name = True


class ConversationPattern(BaseModel):
    """Conversation pattern data."""
    pattern_type: PatternType
    pattern_data: Dict[str, Any]
    frequency: int
    confidence_score: float = Field(..., ge=0, le=1)

    class Config:
        populate_by_name = True


# =====================================================================
# Request Models
# =====================================================================

class ConversationAnalyticsRequest(BaseModel):
    """Request for conversation analytics."""
    conversation_id: str
    include_messages: bool = False
    include_sentiment: bool = True
    include_engagement: bool = True
    include_outcomes: bool = True

    class Config:
        populate_by_name = True


class ConversationQualityAnalysisRequest(BaseModel):
    """Request for quality analysis across conversations."""
    conversation_ids: List[str]
    quality_dimensions: List[str] = ["relevance", "completeness", "clarity"]

    class Config:
        populate_by_name = True


class ConversationPatternRequest(BaseModel):
    """Request for conversation pattern analysis."""
    agent_id: str
    timeframe: str = "7d"
    pattern_type: PatternType = PatternType.FLOW

    class Config:
        populate_by_name = True


class EngagementTrendsRequest(BaseModel):
    """Request for engagement trends."""
    workspace_id: str
    period: str = "daily"  # daily, weekly, monthly
    metric_types: List[str] = ["engagement", "satisfaction"]

    class Config:
        populate_by_name = True


# =====================================================================
# Response Models
# =====================================================================

class ConversationAnalyticsResponse(BaseModel):
    """Response with full conversation analytics."""
    conversation: ConversationAnalytics
    messages: Optional[List[ConversationMessage]] = None
    emotion_analytics: Optional[EmotionAnalytics] = None
    turn_taking: Optional[TurnTakingMetrics] = None
    context_metrics: Optional[ContextMetrics] = None
    engagement: Optional[EngagementMetrics] = None
    outcome: Optional[ConversationOutcome] = None
    response_quality: Optional[List[ResponseQualityMetrics]] = None

    class Config:
        populate_by_name = True


class ConversationPatternsResponse(BaseModel):
    """Response with conversation patterns."""
    agent_id: str
    timeframe: str
    common_conversation_flows: List[ConversationPattern]
    conversation_stages: List[str]
    branching_patterns: Dict[str, Any]
    loop_detection: List[Dict[str, Any]]
    dead_end_analysis: List[Dict[str, Any]]
    optimal_paths: List[List[str]]
    user_behavior_clusters: Dict[str, Any]
    conversation_templates: List[Dict[str, Any]]
    failure_patterns: List[ConversationPattern]

    class Config:
        populate_by_name = True


class EngagementTrend(BaseModel):
    """Engagement trend data point."""
    timestamp: datetime
    engagement_score: float
    satisfaction_score: float
    conversation_count: int

    class Config:
        populate_by_name = True


class EngagementTrendsResponse(BaseModel):
    """Response with engagement trends."""
    workspace_id: str
    period: str
    trends: List[EngagementTrend]
    summary: Dict[str, float]

    class Config:
        populate_by_name = True


class ConversationQualityAnalysisResponse(BaseModel):
    """Response with quality analysis across conversations."""
    analyzed_conversations: int
    average_quality_scores: Dict[str, float]
    quality_distribution: Dict[str, int]
    top_performing_conversations: List[str]
    improvement_opportunities: List[Dict[str, Any]]

    class Config:
        populate_by_name = True


class AgentConversationPerformance(BaseModel):
    """Agent performance metrics from conversations."""
    agent_id: str
    workspace_id: str
    total_conversations: int
    avg_messages_per_conversation: float
    avg_sentiment: float
    avg_satisfaction: float
    avg_duration_minutes: float
    avg_message_velocity: float
    completion_rate: float
    goal_achievement_rate: float
    avg_tokens_per_conversation: float
    avg_cost_per_conversation: float

    class Config:
        populate_by_name = True


class ConversationQualityTrend(BaseModel):
    """Conversation quality trend data point."""
    hour: datetime
    conversation_count: int
    avg_sentiment: float
    avg_clarity: float
    avg_relevance: float
    avg_satisfaction: float
    median_response_time_ms: float
    p95_response_time_ms: float

    class Config:
        populate_by_name = True


# =====================================================================
# Live Monitoring Models
# =====================================================================

class LiveConversationUpdate(BaseModel):
    """Live conversation update for WebSocket."""
    conversation_id: str
    agent_id: str
    workspace_id: str
    event_type: str  # message, sentiment_change, quality_alert
    timestamp: datetime
    data: Dict[str, Any]

    # Real-time metrics
    current_sentiment: Optional[float] = None
    current_engagement: Optional[float] = None
    response_time_ms: Optional[int] = None
    quality_score: Optional[float] = None

    class Config:
        populate_by_name = True


class ConversationAlert(BaseModel):
    """Conversation quality alert."""
    alert_id: str
    conversation_id: str
    alert_type: str  # negative_sentiment, slow_response, low_quality
    severity: str  # low, medium, high, critical
    message: str
    timestamp: datetime
    recommended_action: Optional[str] = None

    class Config:
        populate_by_name = True


class LiveMonitoringStats(BaseModel):
    """Live monitoring aggregated statistics."""
    active_conversations: int
    total_messages_last_hour: int
    avg_sentiment: float
    avg_engagement: float
    avg_response_time_ms: float
    active_alerts: List[ConversationAlert]

    class Config:
        populate_by_name = True
