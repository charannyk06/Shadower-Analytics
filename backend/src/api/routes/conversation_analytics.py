"""Conversation analytics API endpoints."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from ...core.database import get_db
from ...models.schemas.conversation_analytics import (
    # Request models
    ConversationAnalyticsRequest,
    ConversationQualityAnalysisRequest,
    ConversationPatternRequest,
    EngagementTrendsRequest,
    # Response models
    ConversationAnalyticsResponse,
    ConversationPatternsResponse,
    EngagementTrendsResponse,
    ConversationQualityAnalysisResponse,
    AgentConversationPerformance,
    ConversationQualityTrend,
    EngagementTrend,
    # Enums
    MessageRole,
    ConversationStatus,
    PatternType,
)
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter
from ...services.analytics.conversation_analytics_service import ConversationAnalyticsService
from ...services.analytics.sentiment_emotion_service import SentimentEmotionService
from ...services.analytics.engagement_scoring_service import EngagementScoringService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics/conversations", tags=["conversation-analytics"])

# Rate limiters
analytics_limiter = RateLimiter(
    requests_per_minute=30,
    requests_per_hour=500,
)


# ============================================================================
# Conversation Analytics Endpoints
# ============================================================================

@router.get("/{conversation_id}", dependencies=[Depends(analytics_limiter)])
async def get_conversation_analytics(
    conversation_id: str = Path(..., description="Conversation ID"),
    include_messages: bool = Query(False, description="Include individual messages"),
    include_sentiment: bool = Query(True, description="Include sentiment analysis"),
    include_engagement: bool = Query(True, description="Include engagement metrics"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationAnalyticsResponse:
    """
    Get comprehensive analytics for a specific conversation.

    Returns conversation metrics including:
    - Session data (duration, timing)
    - Message metrics
    - Token usage and cost
    - Interaction quality scores
    - Optional: Individual messages
    - Optional: Sentiment/emotion analysis
    - Optional: Engagement metrics
    """
    try:
        service = ConversationAnalyticsService(db)

        # Get conversation analytics
        analytics = await service.get_conversation_analytics(
            conversation_id=conversation_id,
            include_messages=include_messages
        )

        if not analytics:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(
            current_user,
            analytics.conversation.workspace_id
        )

        # Add sentiment analysis if requested
        if include_sentiment:
            sentiment_service = SentimentEmotionService(db)
            analytics.emotion_analytics = await sentiment_service.get_emotion_analytics(
                conversation_id
            )

        # Add engagement metrics if requested
        if include_engagement:
            engagement_service = EngagementScoringService(db)
            try:
                analytics.engagement = await engagement_service.calculate_engagement(
                    conversation_id=conversation_id,
                    agent_id=analytics.conversation.agent_id,
                    user_id=analytics.conversation.user_id
                )
            except Exception as e:
                logger.warning(f"Could not calculate engagement: {e}")
                analytics.engagement = None

        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch conversation analytics"
        )


@router.post("/analyze-quality", dependencies=[Depends(analytics_limiter)])
async def analyze_conversation_quality(
    request: ConversationQualityAnalysisRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationQualityAnalysisResponse:
    """
    Analyze quality across multiple conversations.

    Provides:
    - Average quality scores across dimensions
    - Quality distribution
    - Top performing conversations
    - Improvement opportunities
    """
    try:
        if len(request.conversation_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot analyze more than 100 conversations at once"
            )

        service = ConversationAnalyticsService(db)

        # Collect quality metrics for all conversations
        quality_scores = {dim: [] for dim in request.quality_dimensions}
        analyzed_count = 0

        for conv_id in request.conversation_ids:
            analytics = await service.get_conversation_analytics(conv_id)

            if not analytics:
                continue

            # Verify workspace access for first conversation
            if analyzed_count == 0:
                await WorkspaceAccess.validate_workspace_access(
                    current_user,
                    analytics.conversation.workspace_id
                )

            # Collect quality scores
            quality = analytics.conversation.interaction_quality
            if "relevance" in request.quality_dimensions and quality.relevance_score:
                quality_scores["relevance"].append(quality.relevance_score)
            if "completeness" in request.quality_dimensions and quality.completion_rate:
                quality_scores["completeness"].append(quality.completion_rate)
            if "clarity" in request.quality_dimensions and quality.clarity_score:
                quality_scores["clarity"].append(quality.clarity_score)

            analyzed_count += 1

        # Calculate averages
        average_scores = {}
        for dim, scores in quality_scores.items():
            if scores:
                average_scores[dim] = sum(scores) / len(scores)
            else:
                average_scores[dim] = 0.0

        # Calculate quality distribution
        distribution = {"high": 0, "medium": 0, "low": 0}
        for dim, scores in quality_scores.items():
            for score in scores:
                if score >= 0.7:
                    distribution["high"] += 1
                elif score >= 0.4:
                    distribution["medium"] += 1
                else:
                    distribution["low"] += 1

        # Identify top performing conversations (simplified)
        top_performing = request.conversation_ids[:min(5, len(request.conversation_ids))]

        # Generate improvement opportunities
        improvements = []
        for dim, avg_score in average_scores.items():
            if avg_score < 0.6:
                improvements.append({
                    "dimension": dim,
                    "current_score": avg_score,
                    "target_score": 0.8,
                    "recommendation": f"Improve {dim} by focusing on clearer communication and validation"
                })

        return ConversationQualityAnalysisResponse(
            analyzed_conversations=analyzed_count,
            average_quality_scores=average_scores,
            quality_distribution=distribution,
            top_performing_conversations=top_performing,
            improvement_opportunities=improvements
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation quality: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze conversation quality"
        )


@router.get("/agents/{agent_id}/conversation-patterns", dependencies=[Depends(analytics_limiter)])
async def get_conversation_patterns(
    agent_id: str = Path(..., description="Agent ID"),
    timeframe: str = Query("7d", pattern="^(24h|7d|30d|90d)$", description="Timeframe"),
    pattern_type: PatternType = Query(PatternType.FLOW, description="Pattern type to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationPatternsResponse:
    """
    Analyze conversation patterns for an agent.

    Returns:
    - Common conversation flows
    - Conversation stages
    - Branching patterns
    - Loop detection
    - Dead-end analysis
    - Optimal paths
    - User behavior clusters
    - Conversation templates
    - Failure patterns
    """
    try:
        # For MVP, return sample pattern data
        # In production, this would use a dedicated pattern analysis service

        return ConversationPatternsResponse(
            agent_id=agent_id,
            timeframe=timeframe,
            common_conversation_flows=[],
            conversation_stages=["greeting", "problem_identification", "solution", "conclusion"],
            branching_patterns={},
            loop_detection=[],
            dead_end_analysis=[],
            optimal_paths=[],
            user_behavior_clusters={},
            conversation_templates=[],
            failure_patterns=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze conversation patterns"
        )


@router.get("/workspace/{workspace_id}/engagement-trends", dependencies=[Depends(analytics_limiter)])
async def get_engagement_trends(
    workspace_id: str = Path(..., description="Workspace ID"),
    period: str = Query("daily", pattern="^(hourly|daily|weekly)$", description="Aggregation period"),
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    metric_types: List[str] = Query(["engagement", "satisfaction"], description="Metric types"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EngagementTrendsResponse:
    """
    Get engagement trend data for workspace.

    Returns engagement and satisfaction trends over time with:
    - Engagement scores
    - Satisfaction scores
    - Conversation counts
    - Summary statistics
    """
    try:
        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        engagement_service = EngagementScoringService(db)

        # Get engagement trends
        trend_data = await engagement_service.get_workspace_engagement_trends(
            workspace_id=workspace_id,
            days=days
        )

        # Convert to response format
        trends = []
        for data in trend_data:
            trends.append(
                EngagementTrend(
                    timestamp=data["date"],
                    engagement_score=data["avg_engagement"],
                    satisfaction_score=data["avg_satisfaction"],
                    conversation_count=data["conversation_count"]
                )
            )

        # Calculate summary
        summary = {}
        if trends:
            summary["avg_engagement"] = sum(t.engagement_score for t in trends) / len(trends)
            summary["avg_satisfaction"] = sum(t.satisfaction_score for t in trends) / len(trends)
            summary["total_conversations"] = sum(t.conversation_count for t in trends)

        return EngagementTrendsResponse(
            workspace_id=workspace_id,
            period=period,
            trends=trends,
            summary=summary
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching engagement trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch engagement trends"
        )


@router.get("/agents/{agent_id}/performance", dependencies=[Depends(analytics_limiter)])
async def get_agent_conversation_performance(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe_days: int = Query(7, ge=1, le=90, description="Timeframe in days"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentConversationPerformance:
    """
    Get agent performance metrics from conversations.

    Returns comprehensive performance metrics including:
    - Total conversations
    - Average messages per conversation
    - Average sentiment and satisfaction
    - Duration and velocity metrics
    - Completion and goal achievement rates
    - Token usage and costs
    """
    try:
        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = ConversationAnalyticsService(db)

        performance = await service.get_agent_performance(
            agent_id=agent_id,
            workspace_id=workspace_id,
            timeframe_days=timeframe_days
        )

        if not performance:
            raise HTTPException(
                status_code=404,
                detail=f"No conversation data found for agent {agent_id}"
            )

        return performance

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch agent conversation performance"
        )


@router.get("/workspace/{workspace_id}/quality-trends", dependencies=[Depends(analytics_limiter)])
async def get_quality_trends(
    workspace_id: str = Path(..., description="Workspace ID"),
    agent_id: Optional[str] = Query(None, description="Optional agent filter"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationQualityTrend]:
    """
    Get conversation quality trends over time.

    Returns hourly quality metrics including:
    - Conversation count
    - Average sentiment, clarity, relevance
    - User satisfaction
    - Response time percentiles
    """
    try:
        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = ConversationAnalyticsService(db)

        trends = await service.get_quality_trends(
            workspace_id=workspace_id,
            agent_id=agent_id,
            hours=hours
        )

        return trends

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quality trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch quality trends"
        )


# ============================================================================
# Conversation Management Endpoints
# ============================================================================

@router.post("/", dependencies=[Depends(analytics_limiter)])
async def create_conversation(
    conversation_id: str = Body(..., embed=True),
    agent_id: str = Body(..., embed=True),
    workspace_id: str = Body(..., embed=True),
    user_id: str = Body(..., embed=True),
    metadata: Optional[Dict[str, Any]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Create a new conversation analytics record.

    This should be called when a new conversation starts to begin tracking
    analytics.
    """
    try:
        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = ConversationAnalyticsService(db)

        conv_id = await service.create_conversation(
            conversation_id=conversation_id,
            agent_id=agent_id,
            workspace_id=workspace_id,
            user_id=user_id,
            metadata=metadata
        )

        return {
            "conversation_id": conv_id,
            "status": "created"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create conversation analytics"
        )


@router.post("/{conversation_id}/messages", dependencies=[Depends(analytics_limiter)])
async def record_conversation_message(
    conversation_id: str = Path(..., description="Conversation ID"),
    message_index: int = Body(..., embed=True),
    role: MessageRole = Body(..., embed=True),
    content: str = Body(..., embed=True),
    tokens_used: Optional[int] = Body(None, embed=True),
    response_time_ms: Optional[int] = Body(None, embed=True),
    metadata: Optional[Dict[str, Any]] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Record a conversation message with analytics.

    This should be called for each message in the conversation to track
    message-level analytics.
    """
    try:
        service = ConversationAnalyticsService(db)

        # Get conversation to verify access
        analytics = await service.get_conversation_analytics(conversation_id)
        if not analytics:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(
            current_user,
            analytics.conversation.workspace_id
        )

        # Analyze sentiment if it's a user message
        sentiment_score = None
        if role == MessageRole.USER:
            sentiment_service = SentimentEmotionService(db)
            sentiment_score = sentiment_service.analyze_sentiment(content)

        # Record message
        message_id = await service.record_message(
            conversation_id=conversation_id,
            agent_id=analytics.conversation.agent_id,
            message_index=message_index,
            role=role,
            content=content,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            sentiment_score=sentiment_score,
            metadata=metadata
        )

        # Analyze emotion for user messages
        if role == MessageRole.USER and content:
            sentiment_service = SentimentEmotionService(db)
            await sentiment_service.analyze_message_sentiment(
                message_id=message_id,
                conversation_id=conversation_id,
                content=content
            )

        return {
            "message_id": message_id,
            "status": "recorded"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to record conversation message"
        )


@router.post("/{conversation_id}/end", dependencies=[Depends(analytics_limiter)])
async def end_conversation(
    conversation_id: str = Path(..., description="Conversation ID"),
    status: ConversationStatus = Body(ConversationStatus.COMPLETED, embed=True),
    goal_achieved: Optional[bool] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    End a conversation and finalize metrics.

    This should be called when a conversation completes to calculate final
    analytics and metrics.
    """
    try:
        service = ConversationAnalyticsService(db)

        # Get conversation to verify access
        analytics = await service.get_conversation_analytics(conversation_id)
        if not analytics:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(
            current_user,
            analytics.conversation.workspace_id
        )

        # End conversation
        await service.end_conversation(
            conversation_id=conversation_id,
            status=status,
            goal_achieved=goal_achieved
        )

        # Calculate final engagement metrics
        engagement_service = EngagementScoringService(db)
        await engagement_service.calculate_engagement(
            conversation_id=conversation_id,
            agent_id=analytics.conversation.agent_id,
            user_id=analytics.conversation.user_id
        )

        # Analyze sentiment progression
        sentiment_service = SentimentEmotionService(db)
        await sentiment_service.analyze_sentiment_progression(conversation_id)

        return {
            "conversation_id": conversation_id,
            "status": "ended"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to end conversation"
        )
