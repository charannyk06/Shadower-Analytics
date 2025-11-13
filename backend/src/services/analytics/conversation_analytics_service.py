"""Conversation analytics service for tracking and analyzing agent conversations."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.sql import text

from ...models.schemas.conversation_analytics import (
    ConversationAnalytics,
    ConversationMessage,
    SessionData,
    MessageMetrics,
    TokenUsage,
    InteractionQuality,
    ConversationStatus,
    MessageRole,
    EngagementMetrics,
    EngagementLevel,
    ConversationOutcome,
    OutcomeCategory,
    ContextMetrics,
    ResponseQualityMetrics,
    TurnTakingMetrics,
    ConversationAnalyticsResponse,
    AgentConversationPerformance,
    ConversationQualityTrend,
)

logger = logging.getLogger(__name__)


class ConversationAnalyticsService:
    """Service for managing conversation analytics."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_conversation(
        self,
        conversation_id: str,
        agent_id: str,
        workspace_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation analytics record.

        Args:
            conversation_id: Unique conversation identifier
            agent_id: Agent identifier
            workspace_id: Workspace identifier
            user_id: User identifier
            metadata: Optional metadata

        Returns:
            conversation_id
        """
        try:
            query = text("""
                INSERT INTO analytics.conversation_analytics (
                    conversation_id, agent_id, workspace_id, user_id,
                    start_time, status, metadata
                )
                VALUES (
                    :conversation_id, :agent_id, :workspace_id, :user_id,
                    :start_time, :status, :metadata::jsonb
                )
                ON CONFLICT (conversation_id) DO NOTHING
                RETURNING conversation_id
            """)

            result = await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "start_time": datetime.utcnow(),
                    "status": ConversationStatus.ACTIVE.value,
                    "metadata": metadata or {}
                }
            )
            await self.db.commit()

            logger.info(f"Created conversation analytics for conversation_id={conversation_id}")
            return conversation_id

        except Exception as e:
            logger.error(f"Error creating conversation analytics: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def record_message(
        self,
        conversation_id: str,
        agent_id: str,
        message_index: int,
        role: MessageRole,
        content: str,
        tokens_used: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        sentiment_score: Optional[float] = None,
        intent_classification: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a conversation message with analytics.

        Args:
            conversation_id: Conversation identifier
            agent_id: Agent identifier
            message_index: Message position in conversation
            role: Message role (user, agent, system)
            content: Message content
            tokens_used: Number of tokens used
            response_time_ms: Response time in milliseconds
            sentiment_score: Sentiment score (-1 to 1)
            intent_classification: Classified intent
            metadata: Additional metadata

        Returns:
            message_id
        """
        try:
            message_id = str(uuid4())

            query = text("""
                INSERT INTO analytics.conversation_messages (
                    id, conversation_id, agent_id, message_index, role, content,
                    tokens_used, response_time_ms, sentiment_score,
                    intent_classification, metadata
                )
                VALUES (
                    :id, :conversation_id, :agent_id, :message_index, :role,
                    :content, :tokens_used, :response_time_ms, :sentiment_score,
                    :intent_classification, :metadata::jsonb
                )
                RETURNING id
            """)

            await self.db.execute(
                query,
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "message_index": message_index,
                    "role": role.value,
                    "content": content,
                    "tokens_used": tokens_used,
                    "response_time_ms": response_time_ms,
                    "sentiment_score": sentiment_score,
                    "intent_classification": intent_classification,
                    "metadata": metadata or {}
                }
            )
            await self.db.commit()

            # Update conversation metrics asynchronously
            await self._update_conversation_metrics(conversation_id)

            logger.debug(f"Recorded message for conversation_id={conversation_id}, index={message_index}")
            return message_id

        except Exception as e:
            logger.error(f"Error recording message: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def end_conversation(
        self,
        conversation_id: str,
        status: ConversationStatus = ConversationStatus.COMPLETED,
        goal_achieved: Optional[bool] = None
    ) -> None:
        """
        End a conversation and finalize metrics.

        Args:
            conversation_id: Conversation identifier
            status: Final status
            goal_achieved: Whether conversation goal was achieved
        """
        try:
            query = text("""
                UPDATE analytics.conversation_analytics
                SET
                    end_time = :end_time,
                    total_duration_ms = EXTRACT(EPOCH FROM (:end_time - start_time)) * 1000,
                    status = :status,
                    goal_achieved = :goal_achieved,
                    updated_at = :updated_at
                WHERE conversation_id = :conversation_id
            """)

            end_time = datetime.utcnow()

            await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "end_time": end_time,
                    "status": status.value,
                    "goal_achieved": goal_achieved,
                    "updated_at": end_time
                }
            )
            await self.db.commit()

            # Calculate final metrics
            await self._calculate_final_metrics(conversation_id)

            logger.info(f"Ended conversation {conversation_id} with status {status.value}")

        except Exception as e:
            logger.error(f"Error ending conversation: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_conversation_analytics(
        self,
        conversation_id: str,
        include_messages: bool = False
    ) -> Optional[ConversationAnalyticsResponse]:
        """
        Get comprehensive analytics for a conversation.

        Args:
            conversation_id: Conversation identifier
            include_messages: Whether to include individual messages

        Returns:
            ConversationAnalyticsResponse or None if not found
        """
        try:
            # Get conversation analytics
            query = text("""
                SELECT
                    conversation_id, agent_id, workspace_id, user_id,
                    start_time, end_time, total_duration_ms, idle_time_ms, active_time_ms,
                    total_messages, user_messages, agent_messages, system_messages,
                    average_response_time_ms, message_velocity,
                    input_tokens, output_tokens, total_tokens, cost_usd, tokens_per_message,
                    sentiment_score, clarity_score, relevance_score, completion_rate, user_satisfaction,
                    status, goal_achieved, metadata
                FROM analytics.conversation_analytics
                WHERE conversation_id = :conversation_id
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            row = result.fetchone()

            if not row:
                return None

            # Build conversation analytics
            conversation = ConversationAnalytics(
                conversation_id=str(row.conversation_id),
                agent_id=str(row.agent_id),
                workspace_id=str(row.workspace_id),
                user_id=str(row.user_id),
                session_data=SessionData(
                    start_time=row.start_time,
                    end_time=row.end_time,
                    total_duration_ms=row.total_duration_ms,
                    idle_time_ms=row.idle_time_ms or 0,
                    active_time_ms=row.active_time_ms or 0
                ),
                message_metrics=MessageMetrics(
                    total_messages=row.total_messages or 0,
                    user_messages=row.user_messages or 0,
                    agent_messages=row.agent_messages or 0,
                    system_messages=row.system_messages or 0,
                    average_response_time_ms=row.average_response_time_ms,
                    message_velocity=float(row.message_velocity) if row.message_velocity else None
                ),
                token_usage=TokenUsage(
                    input_tokens=row.input_tokens or 0,
                    output_tokens=row.output_tokens or 0,
                    total_tokens=row.total_tokens or 0,
                    cost_usd=float(row.cost_usd) if row.cost_usd else 0.0,
                    tokens_per_message=float(row.tokens_per_message) if row.tokens_per_message else None
                ),
                interaction_quality=InteractionQuality(
                    sentiment_score=float(row.sentiment_score) if row.sentiment_score else None,
                    clarity_score=float(row.clarity_score) if row.clarity_score else None,
                    relevance_score=float(row.relevance_score) if row.relevance_score else None,
                    completion_rate=float(row.completion_rate) if row.completion_rate else None,
                    user_satisfaction=float(row.user_satisfaction) if row.user_satisfaction else None
                ),
                status=ConversationStatus(row.status),
                goal_achieved=row.goal_achieved,
                metadata=row.metadata or {}
            )

            # Get messages if requested
            messages = None
            if include_messages:
                messages = await self._get_conversation_messages(conversation_id)

            return ConversationAnalyticsResponse(
                conversation=conversation,
                messages=messages
            )

        except Exception as e:
            logger.error(f"Error getting conversation analytics: {e}", exc_info=True)
            raise

    async def get_agent_performance(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe_days: int = 7
    ) -> Optional[AgentConversationPerformance]:
        """
        Get agent performance metrics from conversations.

        Args:
            agent_id: Agent identifier
            workspace_id: Workspace identifier
            timeframe_days: Number of days to analyze

        Returns:
            AgentConversationPerformance or None
        """
        try:
            query = text("""
                SELECT
                    agent_id,
                    workspace_id,
                    COUNT(DISTINCT conversation_id) as total_conversations,
                    AVG(total_messages) as avg_messages_per_conversation,
                    AVG(sentiment_score) as avg_sentiment,
                    AVG(user_satisfaction) as avg_satisfaction,
                    AVG(total_duration_ms / 1000.0 / 60.0) as avg_duration_minutes,
                    AVG(message_velocity) as avg_message_velocity,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)::float /
                        NULLIF(COUNT(*), 0) as completion_rate,
                    SUM(CASE WHEN goal_achieved THEN 1 ELSE 0 END)::float /
                        NULLIF(COUNT(*), 0) as goal_achievement_rate,
                    AVG(total_tokens) as avg_tokens_per_conversation,
                    AVG(cost_usd) as avg_cost_per_conversation
                FROM analytics.conversation_analytics
                WHERE agent_id = :agent_id
                  AND workspace_id = :workspace_id
                  AND start_time >= :start_date
                  AND end_time IS NOT NULL
                GROUP BY agent_id, workspace_id
            """)

            start_date = datetime.utcnow() - timedelta(days=timeframe_days)

            result = await self.db.execute(
                query,
                {
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                    "start_date": start_date
                }
            )
            row = result.fetchone()

            if not row:
                return None

            return AgentConversationPerformance(
                agent_id=str(row.agent_id),
                workspace_id=str(row.workspace_id),
                total_conversations=row.total_conversations or 0,
                avg_messages_per_conversation=float(row.avg_messages_per_conversation or 0),
                avg_sentiment=float(row.avg_sentiment or 0),
                avg_satisfaction=float(row.avg_satisfaction or 0),
                avg_duration_minutes=float(row.avg_duration_minutes or 0),
                avg_message_velocity=float(row.avg_message_velocity or 0),
                completion_rate=float(row.completion_rate or 0),
                goal_achievement_rate=float(row.goal_achievement_rate or 0),
                avg_tokens_per_conversation=float(row.avg_tokens_per_conversation or 0),
                avg_cost_per_conversation=float(row.avg_cost_per_conversation or 0)
            )

        except Exception as e:
            logger.error(f"Error getting agent performance: {e}", exc_info=True)
            raise

    async def get_quality_trends(
        self,
        workspace_id: str,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> List[ConversationQualityTrend]:
        """
        Get conversation quality trends over time.

        Args:
            workspace_id: Workspace identifier
            agent_id: Optional agent filter
            hours: Number of hours to analyze

        Returns:
            List of quality trend data points
        """
        try:
            agent_filter = "AND agent_id = :agent_id" if agent_id else ""

            query = text(f"""
                SELECT
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as conversation_count,
                    AVG(sentiment_score) as avg_sentiment,
                    AVG(clarity_score) as avg_clarity,
                    AVG(relevance_score) as avg_relevance,
                    AVG(user_satisfaction) as avg_satisfaction,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY average_response_time_ms) as median_response_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY average_response_time_ms) as p95_response_time
                FROM analytics.conversation_analytics
                WHERE workspace_id = :workspace_id
                  AND start_time >= :start_time
                  AND end_time IS NOT NULL
                  {agent_filter}
                GROUP BY DATE_TRUNC('hour', start_time)
                ORDER BY hour DESC
            """)

            start_time = datetime.utcnow() - timedelta(hours=hours)

            params = {
                "workspace_id": workspace_id,
                "start_time": start_time
            }
            if agent_id:
                params["agent_id"] = agent_id

            result = await self.db.execute(query, params)
            rows = result.fetchall()

            trends = []
            for row in rows:
                trends.append(
                    ConversationQualityTrend(
                        hour=row.hour,
                        conversation_count=row.conversation_count or 0,
                        avg_sentiment=float(row.avg_sentiment or 0),
                        avg_clarity=float(row.avg_clarity or 0),
                        avg_relevance=float(row.avg_relevance or 0),
                        avg_satisfaction=float(row.avg_satisfaction or 0),
                        median_response_time_ms=float(row.median_response_time or 0),
                        p95_response_time_ms=float(row.p95_response_time or 0)
                    )
                )

            return trends

        except Exception as e:
            logger.error(f"Error getting quality trends: {e}", exc_info=True)
            raise

    async def _update_conversation_metrics(self, conversation_id: str) -> None:
        """Update aggregate conversation metrics."""
        try:
            # Calculate message-based metrics
            query = text("""
                UPDATE analytics.conversation_analytics ca
                SET
                    total_messages = (
                        SELECT COUNT(*) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id
                    ),
                    user_messages = (
                        SELECT COUNT(*) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id AND role = 'user'
                    ),
                    agent_messages = (
                        SELECT COUNT(*) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id AND role = 'agent'
                    ),
                    system_messages = (
                        SELECT COUNT(*) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id AND role = 'system'
                    ),
                    total_tokens = (
                        SELECT COALESCE(SUM(tokens_used), 0) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id
                    ),
                    average_response_time_ms = (
                        SELECT AVG(response_time_ms) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id AND response_time_ms IS NOT NULL
                    ),
                    sentiment_score = (
                        SELECT AVG(sentiment_score) FROM analytics.conversation_messages
                        WHERE conversation_id = :conversation_id AND sentiment_score IS NOT NULL
                    ),
                    updated_at = :updated_at
                WHERE conversation_id = :conversation_id
            """)

            await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "updated_at": datetime.utcnow()
                }
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error updating conversation metrics: {e}", exc_info=True)
            await self.db.rollback()

    async def _calculate_final_metrics(self, conversation_id: str) -> None:
        """Calculate final metrics when conversation ends."""
        try:
            # Calculate message velocity (messages per minute)
            query = text("""
                UPDATE analytics.conversation_analytics
                SET
                    message_velocity = CASE
                        WHEN total_duration_ms > 0 THEN
                            (total_messages::float / (total_duration_ms / 1000.0 / 60.0))
                        ELSE 0
                    END,
                    tokens_per_message = CASE
                        WHEN total_messages > 0 THEN
                            (total_tokens::float / total_messages)
                        ELSE 0
                    END,
                    active_time_ms = total_duration_ms, -- Simplified for now
                    updated_at = :updated_at
                WHERE conversation_id = :conversation_id
            """)

            await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "updated_at": datetime.utcnow()
                }
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error calculating final metrics: {e}", exc_info=True)
            await self.db.rollback()

    async def _get_conversation_messages(
        self,
        conversation_id: str
    ) -> List[ConversationMessage]:
        """Get all messages for a conversation."""
        try:
            query = text("""
                SELECT
                    id, conversation_id, agent_id, message_index, role, content,
                    tokens_used, response_time_ms, sentiment_score, emotion_primary,
                    emotion_confidence, emotion_intensity, intent_classification,
                    intent_confidence, entity_extraction, relevance_score,
                    completeness_score, clarity_score, error_occurred, error_type,
                    retry_count, metadata, created_at
                FROM analytics.conversation_messages
                WHERE conversation_id = :conversation_id
                ORDER BY message_index ASC
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            rows = result.fetchall()

            messages = []
            for row in rows:
                messages.append(
                    ConversationMessage(
                        id=str(row.id),
                        conversation_id=str(row.conversation_id),
                        agent_id=str(row.agent_id),
                        message_index=row.message_index,
                        role=MessageRole(row.role),
                        content=row.content,
                        tokens_used=row.tokens_used,
                        response_time_ms=row.response_time_ms,
                        sentiment_score=float(row.sentiment_score) if row.sentiment_score else None,
                        emotion_primary=row.emotion_primary,
                        emotion_confidence=float(row.emotion_confidence) if row.emotion_confidence else None,
                        emotion_intensity=float(row.emotion_intensity) if row.emotion_intensity else None,
                        intent_classification=row.intent_classification,
                        intent_confidence=float(row.intent_confidence) if row.intent_confidence else None,
                        entity_extraction=row.entity_extraction or {},
                        relevance_score=float(row.relevance_score) if row.relevance_score else None,
                        completeness_score=float(row.completeness_score) if row.completeness_score else None,
                        clarity_score=float(row.clarity_score) if row.clarity_score else None,
                        error_occurred=row.error_occurred or False,
                        error_type=row.error_type,
                        retry_count=row.retry_count or 0,
                        metadata=row.metadata or {},
                        created_at=row.created_at
                    )
                )

            return messages

        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}", exc_info=True)
            raise

    async def refresh_materialized_views(self) -> None:
        """Refresh conversation analytics materialized views."""
        try:
            query = text("SELECT analytics.refresh_conversation_materialized_views()")
            await self.db.execute(query)
            await self.db.commit()

            logger.info("Refreshed conversation analytics materialized views")

        except Exception as e:
            logger.error(f"Error refreshing materialized views: {e}", exc_info=True)
            await self.db.rollback()
