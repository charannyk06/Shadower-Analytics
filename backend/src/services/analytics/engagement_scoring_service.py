"""Engagement scoring service for conversation analytics."""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from ...models.schemas.conversation_analytics import (
    EngagementMetrics,
    EngagementLevel,
)

logger = logging.getLogger(__name__)


class EngagementScoringService:
    """Service for calculating user engagement scores in conversations."""

    # Weights for engagement score components
    COMPONENT_WEIGHTS = {
        "interaction_depth": 0.2,
        "user_investment": 0.25,
        "conversation_momentum": 0.15,
        "topic_exploration": 0.15,
        "question_quality": 0.15,
        "feedback_indicators": 0.1
    }

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def calculate_engagement(
        self,
        conversation_id: str,
        agent_id: str,
        user_id: str
    ) -> EngagementMetrics:
        """
        Calculate comprehensive engagement metrics for a conversation.

        Args:
            conversation_id: Conversation identifier
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            EngagementMetrics
        """
        try:
            # Get conversation data
            conversation_data = await self._get_conversation_data(conversation_id)

            if not conversation_data:
                raise ValueError(f"Conversation {conversation_id} not found")

            # Calculate component scores
            interaction_depth = self._calculate_interaction_depth(conversation_data)
            user_investment = self._calculate_user_investment(conversation_data)
            conversation_momentum = self._calculate_momentum(conversation_data)
            topic_exploration = self._calculate_topic_exploration(conversation_data)
            question_quality = self._calculate_question_quality(conversation_data)
            feedback_indicators = self._calculate_feedback_indicators(conversation_data)

            # Calculate overall score
            overall_score = self._calculate_weighted_score({
                "interaction_depth": interaction_depth,
                "user_investment": user_investment,
                "conversation_momentum": conversation_momentum,
                "topic_exploration": topic_exploration,
                "question_quality": question_quality,
                "feedback_indicators": feedback_indicators
            })

            # Categorize engagement level
            engagement_level = self._categorize_engagement(overall_score)

            # Generate recommendations
            recommendations = self._generate_recommendations({
                "interaction_depth": interaction_depth,
                "user_investment": user_investment,
                "conversation_momentum": conversation_momentum,
                "topic_exploration": topic_exploration,
                "question_quality": question_quality,
                "feedback_indicators": feedback_indicators
            })

            # Create engagement metrics
            metrics = EngagementMetrics(
                conversation_id=conversation_id,
                agent_id=agent_id,
                user_id=user_id,
                interaction_depth=interaction_depth,
                user_investment=user_investment,
                conversation_momentum=conversation_momentum,
                topic_exploration=topic_exploration,
                question_quality=question_quality,
                feedback_indicators=feedback_indicators,
                overall_score=overall_score,
                engagement_level=engagement_level,
                recommendations=recommendations
            )

            # Store metrics
            await self._store_engagement_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating engagement: {e}", exc_info=True)
            raise

    def _calculate_interaction_depth(self, data: Dict) -> float:
        """
        Calculate interaction depth based on message count and complexity.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        total_messages = data.get("total_messages", 0)
        user_messages = data.get("user_messages", 0)
        avg_message_length = data.get("avg_user_message_length", 0)

        # Score based on number of exchanges
        message_score = min(1.0, user_messages / 10.0)  # Max at 10 messages

        # Score based on message length (complexity)
        length_score = min(1.0, avg_message_length / 100.0)  # Max at 100 chars

        # Combined score
        return (message_score * 0.7 + length_score * 0.3)

    def _calculate_user_investment(self, data: Dict) -> float:
        """
        Calculate user investment based on time spent and effort.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        total_duration_min = data.get("total_duration_ms", 0) / 1000.0 / 60.0
        user_messages = data.get("user_messages", 0)

        # Time investment score
        time_score = min(1.0, total_duration_min / 5.0)  # Max at 5 minutes

        # Message frequency score
        if total_duration_min > 0:
            message_frequency = user_messages / total_duration_min
            freq_score = min(1.0, message_frequency / 2.0)  # Max at 2 messages/min
        else:
            freq_score = 0.0

        return (time_score * 0.6 + freq_score * 0.4)

    def _calculate_momentum(self, data: Dict) -> float:
        """
        Calculate conversation momentum based on response times and flow.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        avg_response_time_ms = data.get("average_response_time_ms", 0)
        message_velocity = data.get("message_velocity", 0)

        # Response time score (lower is better)
        if avg_response_time_ms > 0:
            response_score = max(0.0, 1.0 - (avg_response_time_ms / 10000.0))  # Penalty after 10s
        else:
            response_score = 0.5

        # Message velocity score
        velocity_score = min(1.0, message_velocity / 5.0)  # Max at 5 messages/min

        return (response_score * 0.5 + velocity_score * 0.5)

    def _calculate_topic_exploration(self, data: Dict) -> float:
        """
        Calculate topic exploration based on unique topics discussed.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        topics_discussed = data.get("topics_discussed", [])
        topic_switches = data.get("topic_switches", 0)

        # Score based on unique topics
        unique_topics = len(set(topics_discussed))
        topic_score = min(1.0, unique_topics / 5.0)  # Max at 5 topics

        # Moderate topic switching is good
        if topic_switches > 0:
            switch_score = min(1.0, max(0.3, 1.0 - abs(topic_switches - 3) / 5.0))
        else:
            switch_score = 0.5

        return (topic_score * 0.6 + switch_score * 0.4)

    def _calculate_question_quality(self, data: Dict) -> float:
        """
        Calculate question quality based on user questions.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        question_count = data.get("user_questions", 0)
        clarification_requests = data.get("clarification_requests", 0)

        # Score based on questions asked
        question_score = min(1.0, question_count / 3.0)  # Max at 3 questions

        # Clarification indicates engagement
        clarification_score = min(1.0, clarification_requests / 2.0)

        return (question_score * 0.7 + clarification_score * 0.3)

    def _calculate_feedback_indicators(self, data: Dict) -> float:
        """
        Calculate feedback indicators from user responses.

        Args:
            data: Conversation data

        Returns:
            Score between 0 and 1
        """
        avg_sentiment = data.get("avg_sentiment", 0.0)
        explicit_feedback = data.get("explicit_feedback_count", 0)

        # Normalize sentiment from [-1, 1] to [0, 1]
        sentiment_score = (avg_sentiment + 1.0) / 2.0

        # Explicit feedback score
        feedback_score = min(1.0, explicit_feedback / 2.0)

        return (sentiment_score * 0.6 + feedback_score * 0.4)

    def _calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall engagement score."""
        overall = 0.0
        for component, weight in self.COMPONENT_WEIGHTS.items():
            overall += scores.get(component, 0.0) * weight

        return min(1.0, max(0.0, overall))

    def _categorize_engagement(self, score: float) -> EngagementLevel:
        """Categorize engagement level based on score."""
        if score >= 0.8:
            return EngagementLevel.VERY_HIGH
        elif score >= 0.6:
            return EngagementLevel.HIGH
        elif score >= 0.4:
            return EngagementLevel.MEDIUM
        elif score >= 0.2:
            return EngagementLevel.LOW
        else:
            return EngagementLevel.VERY_LOW

    def _generate_recommendations(self, scores: Dict[str, float]) -> List[str]:
        """Generate engagement improvement recommendations."""
        recommendations = []

        # Check each component and provide suggestions
        if scores.get("interaction_depth", 0) < 0.5:
            recommendations.append(
                "Encourage deeper interaction by asking follow-up questions"
            )

        if scores.get("user_investment", 0) < 0.5:
            recommendations.append(
                "Improve user investment by providing more engaging content"
            )

        if scores.get("conversation_momentum", 0) < 0.5:
            recommendations.append(
                "Improve response times to maintain conversation momentum"
            )

        if scores.get("topic_exploration", 0) < 0.5:
            recommendations.append(
                "Explore related topics to maintain user interest"
            )

        if scores.get("question_quality", 0) < 0.5:
            recommendations.append(
                "Ask better questions to encourage user engagement"
            )

        if scores.get("feedback_indicators", 0) < 0.5:
            recommendations.append(
                "Improve response quality to increase positive sentiment"
            )

        if not recommendations:
            recommendations.append("Engagement is good - maintain current approach")

        return recommendations

    async def _get_conversation_data(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation data for engagement calculation."""
        try:
            query = text("""
                WITH message_stats AS (
                    SELECT
                        COUNT(*) FILTER (WHERE role = 'user') as user_messages,
                        COUNT(*) FILTER (WHERE role = 'user' AND content LIKE '%?%') as user_questions,
                        AVG(LENGTH(content)) FILTER (WHERE role = 'user') as avg_user_message_length,
                        AVG(sentiment_score) as avg_sentiment
                    FROM analytics.conversation_messages
                    WHERE conversation_id = :conversation_id
                ),
                context_stats AS (
                    SELECT
                        topics_discussed,
                        topic_switches,
                        long_term_recall_count as explicit_feedback_count
                    FROM analytics.conversation_context_metrics
                    WHERE conversation_id = :conversation_id
                    LIMIT 1
                ),
                turn_stats AS (
                    SELECT
                        clarification_requests
                    FROM analytics.conversation_turn_metrics
                    WHERE conversation_id = :conversation_id
                    LIMIT 1
                )
                SELECT
                    ca.total_messages,
                    ca.user_messages,
                    ca.total_duration_ms,
                    ca.average_response_time_ms,
                    ca.message_velocity,
                    ms.user_questions,
                    ms.avg_user_message_length,
                    ms.avg_sentiment,
                    cs.topics_discussed,
                    cs.topic_switches,
                    cs.explicit_feedback_count,
                    ts.clarification_requests
                FROM analytics.conversation_analytics ca
                LEFT JOIN message_stats ms ON true
                LEFT JOIN context_stats cs ON true
                LEFT JOIN turn_stats ts ON true
                WHERE ca.conversation_id = :conversation_id
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            row = result.fetchone()

            if not row:
                return None

            # Convert to dict
            return {
                "total_messages": row.total_messages or 0,
                "user_messages": row.user_messages or 0,
                "total_duration_ms": row.total_duration_ms or 0,
                "average_response_time_ms": row.average_response_time_ms or 0,
                "message_velocity": float(row.message_velocity or 0),
                "user_questions": row.user_questions or 0,
                "avg_user_message_length": float(row.avg_user_message_length or 0),
                "avg_sentiment": float(row.avg_sentiment or 0),
                "topics_discussed": row.topics_discussed or [],
                "topic_switches": row.topic_switches or 0,
                "explicit_feedback_count": row.explicit_feedback_count or 0,
                "clarification_requests": row.clarification_requests or 0
            }

        except Exception as e:
            logger.error(f"Error getting conversation data: {e}", exc_info=True)
            return None

    async def _store_engagement_metrics(self, metrics: EngagementMetrics) -> None:
        """Store engagement metrics in database."""
        try:
            query = text("""
                INSERT INTO analytics.conversation_engagement_metrics (
                    conversation_id, agent_id, user_id,
                    interaction_depth, user_investment, conversation_momentum,
                    topic_exploration, question_quality, feedback_indicators,
                    overall_score, engagement_level, recommendations
                )
                VALUES (
                    :conversation_id, :agent_id, :user_id,
                    :interaction_depth, :user_investment, :conversation_momentum,
                    :topic_exploration, :question_quality, :feedback_indicators,
                    :overall_score, :engagement_level, :recommendations::jsonb
                )
                ON CONFLICT (conversation_id) DO UPDATE SET
                    interaction_depth = EXCLUDED.interaction_depth,
                    user_investment = EXCLUDED.user_investment,
                    conversation_momentum = EXCLUDED.conversation_momentum,
                    topic_exploration = EXCLUDED.topic_exploration,
                    question_quality = EXCLUDED.question_quality,
                    feedback_indicators = EXCLUDED.feedback_indicators,
                    overall_score = EXCLUDED.overall_score,
                    engagement_level = EXCLUDED.engagement_level,
                    recommendations = EXCLUDED.recommendations
            """)

            await self.db.execute(
                query,
                {
                    "conversation_id": metrics.conversation_id,
                    "agent_id": metrics.agent_id,
                    "user_id": metrics.user_id,
                    "interaction_depth": metrics.interaction_depth,
                    "user_investment": metrics.user_investment,
                    "conversation_momentum": metrics.conversation_momentum,
                    "topic_exploration": metrics.topic_exploration,
                    "question_quality": metrics.question_quality,
                    "feedback_indicators": metrics.feedback_indicators,
                    "overall_score": metrics.overall_score,
                    "engagement_level": metrics.engagement_level.value,
                    "recommendations": metrics.recommendations
                }
            )
            await self.db.commit()

            logger.info(f"Stored engagement metrics for conversation {metrics.conversation_id}")

        except Exception as e:
            logger.error(f"Error storing engagement metrics: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_workspace_engagement_trends(
        self,
        workspace_id: str,
        days: int = 7
    ) -> List[Dict]:
        """
        Get engagement trends for workspace over time.

        Args:
            workspace_id: Workspace identifier
            days: Number of days to analyze

        Returns:
            List of trend data points
        """
        try:
            query = text("""
                SELECT
                    DATE_TRUNC('day', ca.created_at) as date,
                    AVG(cem.overall_score) as avg_engagement,
                    AVG(ca.user_satisfaction) as avg_satisfaction,
                    COUNT(DISTINCT cem.conversation_id) as conversation_count
                FROM analytics.conversation_engagement_metrics cem
                JOIN analytics.conversation_analytics ca
                    ON cem.conversation_id = ca.conversation_id
                WHERE ca.workspace_id = :workspace_id
                  AND ca.created_at >= NOW() - INTERVAL ':days days'
                GROUP BY DATE_TRUNC('day', ca.created_at)
                ORDER BY date DESC
            """)

            result = await self.db.execute(
                query,
                {"workspace_id": workspace_id, "days": days}
            )
            rows = result.fetchall()

            trends = []
            for row in rows:
                trends.append({
                    "date": row.date,
                    "avg_engagement": float(row.avg_engagement or 0),
                    "avg_satisfaction": float(row.avg_satisfaction or 0),
                    "conversation_count": row.conversation_count or 0
                })

            return trends

        except Exception as e:
            logger.error(f"Error getting engagement trends: {e}", exc_info=True)
            raise
