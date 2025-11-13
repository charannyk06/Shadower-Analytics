"""Sentiment and emotion analysis service for conversations."""

import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from ...models.schemas.conversation_analytics import (
    EmotionAnalytics,
    UserEmotion,
    EmotionTimelinePoint,
    EmotionTransition,
    OverallEmotionalJourney,
)

logger = logging.getLogger(__name__)


class SentimentEmotionService:
    """Service for analyzing sentiment and emotions in conversations."""

    # Emotion keywords for simple classification
    EMOTION_KEYWORDS = {
        "happy": ["happy", "great", "excellent", "wonderful", "fantastic", "love", "awesome", "perfect", "thanks", "thank you"],
        "frustrated": ["frustrated", "annoying", "annoyed", "terrible", "horrible", "awful", "hate", "angry", "mad"],
        "confused": ["confused", "unclear", "don't understand", "not sure", "what", "help", "explain"],
        "satisfied": ["good", "fine", "okay", "works", "satisfied", "solved", "resolved"],
        "neutral": ["okay", "fine", "sure", "yes", "no"]
    }

    # Sentiment polarity words
    POSITIVE_WORDS = [
        "good", "great", "excellent", "wonderful", "fantastic", "amazing", "awesome",
        "perfect", "love", "like", "helpful", "useful", "clear", "easy", "fast", "thanks"
    ]

    NEGATIVE_WORDS = [
        "bad", "poor", "terrible", "horrible", "awful", "hate", "dislike", "difficult",
        "slow", "unclear", "confusing", "frustrating", "broken", "error", "problem", "issue"
    ]

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text using simple keyword-based approach.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score between -1 (negative) and 1 (positive)
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        positive_count = sum(1 for word in words if word in self.POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in self.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Calculate sentiment score
        sentiment = (positive_count - negative_count) / total
        return max(-1.0, min(1.0, sentiment))

    def detect_emotion(self, text: str) -> Tuple[str, float, float]:
        """
        Detect primary emotion in text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (emotion, confidence, intensity)
        """
        if not text:
            return "neutral", 0.5, 0.0

        text_lower = text.lower()

        # Count emotion keyword matches
        emotion_scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score

        if not emotion_scores:
            return "neutral", 0.5, 0.0

        # Get primary emotion
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        max_score = emotion_scores[primary_emotion]
        total_score = sum(emotion_scores.values())

        # Calculate confidence and intensity
        confidence = max_score / total_score if total_score > 0 else 0.5
        intensity = min(1.0, max_score / 3.0)  # Normalize to 0-1

        return primary_emotion, confidence, intensity

    async def analyze_message_sentiment(
        self,
        message_id: str,
        conversation_id: str,
        content: str
    ) -> Dict[str, any]:
        """
        Analyze sentiment and emotion for a message and store results.

        Args:
            message_id: Message identifier
            conversation_id: Conversation identifier
            content: Message content

        Returns:
            Dict with sentiment and emotion data
        """
        try:
            # Analyze sentiment
            sentiment_score = self.analyze_sentiment(content)

            # Detect emotion
            emotion, confidence, intensity = self.detect_emotion(content)

            # Update message with sentiment/emotion data
            query = text("""
                UPDATE analytics.conversation_messages
                SET
                    sentiment_score = :sentiment_score,
                    emotion_primary = :emotion_primary,
                    emotion_confidence = :emotion_confidence,
                    emotion_intensity = :emotion_intensity
                WHERE id = :message_id
            """)

            await self.db.execute(
                query,
                {
                    "message_id": message_id,
                    "sentiment_score": sentiment_score,
                    "emotion_primary": emotion,
                    "emotion_confidence": confidence,
                    "emotion_intensity": intensity
                }
            )
            await self.db.commit()

            # Record in emotion timeline
            await self._record_emotion_timeline(
                conversation_id, message_id, emotion, confidence, intensity
            )

            return {
                "sentiment_score": sentiment_score,
                "emotion_primary": emotion,
                "emotion_confidence": confidence,
                "emotion_intensity": intensity
            }

        except Exception as e:
            logger.error(f"Error analyzing message sentiment: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_emotion_analytics(
        self,
        conversation_id: str
    ) -> Optional[EmotionAnalytics]:
        """
        Get comprehensive emotion analytics for a conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            EmotionAnalytics or None
        """
        try:
            # Get emotion timeline
            timeline = await self._get_emotion_timeline(conversation_id)

            if not timeline:
                return None

            # Get emotion transitions
            transitions = await self._calculate_emotion_transitions(conversation_id)

            # Calculate emotional journey
            journey = await self._calculate_emotional_journey(conversation_id, timeline)

            return EmotionAnalytics(
                conversation_id=conversation_id,
                emotion_timeline=timeline,
                emotion_transitions=transitions,
                overall_emotional_journey=journey
            )

        except Exception as e:
            logger.error(f"Error getting emotion analytics: {e}", exc_info=True)
            raise

    async def analyze_sentiment_progression(
        self,
        conversation_id: str
    ) -> Dict[str, any]:
        """
        Analyze sentiment progression throughout conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dict with sentiment progression data
        """
        try:
            query = text("""
                SELECT
                    message_index,
                    role,
                    sentiment_score,
                    created_at
                FROM analytics.conversation_messages
                WHERE conversation_id = :conversation_id
                  AND sentiment_score IS NOT NULL
                ORDER BY message_index ASC
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            rows = result.fetchall()

            if not rows:
                return {"sentiment_timeline": [], "sentiment_shifts": []}

            # Build timeline
            timeline = []
            for row in rows:
                timeline.append({
                    "index": row.message_index,
                    "role": row.role,
                    "sentiment": float(row.sentiment_score),
                    "magnitude": abs(float(row.sentiment_score)),
                    "timestamp": row.created_at
                })

            # Detect significant shifts
            shifts = []
            for i in range(1, len(timeline)):
                current = timeline[i]
                previous = timeline[i-1]

                shift = current["sentiment"] - previous["sentiment"]
                if abs(shift) > 0.3:  # Significant shift threshold
                    shifts.append({
                        "at_index": current["index"],
                        "shift_magnitude": shift,
                        "from_sentiment": previous["sentiment"],
                        "to_sentiment": current["sentiment"],
                        "trigger": f"Message {current['index']}"
                    })

            # Store sentiment progression
            await self._store_sentiment_progression(conversation_id, timeline, shifts)

            return {
                "sentiment_timeline": timeline,
                "sentiment_shifts": shifts
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment progression: {e}", exc_info=True)
            raise

    async def _record_emotion_timeline(
        self,
        conversation_id: str,
        message_id: str,
        emotion: str,
        confidence: float,
        intensity: float
    ) -> None:
        """Record emotion in timeline."""
        try:
            query = text("""
                INSERT INTO analytics.conversation_emotion_timeline (
                    conversation_id, message_id, user_emotion_primary,
                    user_emotion_confidence, user_emotion_intensity,
                    occurred_at
                )
                VALUES (
                    :conversation_id, :message_id, :emotion,
                    :confidence, :intensity, :occurred_at
                )
            """)

            await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "emotion": emotion,
                    "confidence": confidence,
                    "intensity": intensity,
                    "occurred_at": datetime.utcnow()
                }
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error recording emotion timeline: {e}", exc_info=True)
            await self.db.rollback()

    async def _get_emotion_timeline(
        self,
        conversation_id: str
    ) -> List[EmotionTimelinePoint]:
        """Get emotion timeline for conversation."""
        try:
            query = text("""
                SELECT
                    occurred_at,
                    user_emotion_primary,
                    user_emotion_confidence,
                    user_emotion_intensity,
                    agent_response_appropriateness
                FROM analytics.conversation_emotion_timeline
                WHERE conversation_id = :conversation_id
                ORDER BY occurred_at ASC
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            rows = result.fetchall()

            timeline = []
            for row in rows:
                timeline.append(
                    EmotionTimelinePoint(
                        timestamp=row.occurred_at,
                        user_emotion=UserEmotion(
                            primary=row.user_emotion_primary,
                            confidence=float(row.user_emotion_confidence),
                            intensity=float(row.user_emotion_intensity)
                        ),
                        agent_response_appropriateness=float(row.agent_response_appropriateness or 0.5)
                    )
                )

            return timeline

        except Exception as e:
            logger.error(f"Error getting emotion timeline: {e}", exc_info=True)
            raise

    async def _calculate_emotion_transitions(
        self,
        conversation_id: str
    ) -> List[EmotionTransition]:
        """Calculate emotion transitions."""
        try:
            query = text("""
                WITH emotion_sequence AS (
                    SELECT
                        user_emotion_primary,
                        occurred_at,
                        LAG(user_emotion_primary) OVER (ORDER BY occurred_at) as prev_emotion,
                        LEAD(occurred_at) OVER (ORDER BY occurred_at) as next_time
                    FROM analytics.conversation_emotion_timeline
                    WHERE conversation_id = :conversation_id
                )
                SELECT
                    prev_emotion as from_emotion,
                    user_emotion_primary as to_emotion,
                    COUNT(*) as frequency,
                    AVG(EXTRACT(EPOCH FROM (next_time - occurred_at)) * 1000)::integer as avg_transition_time_ms
                FROM emotion_sequence
                WHERE prev_emotion IS NOT NULL
                  AND prev_emotion != user_emotion_primary
                GROUP BY prev_emotion, user_emotion_primary
                ORDER BY frequency DESC
            """)

            result = await self.db.execute(query, {"conversation_id": conversation_id})
            rows = result.fetchall()

            transitions = []
            for row in rows:
                transitions.append(
                    EmotionTransition(
                        from_emotion=row.from_emotion,
                        to_emotion=row.to_emotion,
                        frequency=row.frequency,
                        avg_transition_time_ms=row.avg_transition_time_ms or 0
                    )
                )

            return transitions

        except Exception as e:
            logger.error(f"Error calculating emotion transitions: {e}", exc_info=True)
            raise

    async def _calculate_emotional_journey(
        self,
        conversation_id: str,
        timeline: List[EmotionTimelinePoint]
    ) -> OverallEmotionalJourney:
        """Calculate overall emotional journey."""
        if not timeline:
            return OverallEmotionalJourney(
                start_emotion="neutral",
                end_emotion="neutral",
                peak_positive=0.0,
                peak_negative=0.0,
                emotional_variance=0.0
            )

        # Map emotions to sentiment values for peak calculation
        emotion_sentiment = {
            "happy": 1.0,
            "satisfied": 0.7,
            "neutral": 0.0,
            "confused": -0.3,
            "frustrated": -0.8
        }

        sentiments = [
            emotion_sentiment.get(point.user_emotion.primary, 0.0)
            for point in timeline
        ]

        # Calculate variance
        if len(sentiments) > 1:
            mean = sum(sentiments) / len(sentiments)
            variance = sum((x - mean) ** 2 for x in sentiments) / len(sentiments)
        else:
            variance = 0.0

        return OverallEmotionalJourney(
            start_emotion=timeline[0].user_emotion.primary,
            end_emotion=timeline[-1].user_emotion.primary,
            peak_positive=max(sentiments) if sentiments else 0.0,
            peak_negative=min(sentiments) if sentiments else 0.0,
            emotional_variance=variance
        )

    async def _store_sentiment_progression(
        self,
        conversation_id: str,
        timeline: List[Dict],
        shifts: List[Dict]
    ) -> None:
        """Store sentiment progression analysis."""
        try:
            # Extract start and end emotions
            start_emotion = "neutral"
            end_emotion = "neutral"

            if timeline:
                # Simple mapping based on sentiment
                if timeline[0]["sentiment"] > 0.3:
                    start_emotion = "positive"
                elif timeline[0]["sentiment"] < -0.3:
                    start_emotion = "negative"

                if timeline[-1]["sentiment"] > 0.3:
                    end_emotion = "positive"
                elif timeline[-1]["sentiment"] < -0.3:
                    end_emotion = "negative"

            sentiments = [point["sentiment"] for point in timeline]

            query = text("""
                INSERT INTO analytics.conversation_sentiment_progression (
                    conversation_id, sentiment_timeline, sentiment_shifts,
                    start_emotion, end_emotion, peak_positive, peak_negative,
                    emotional_variance
                )
                VALUES (
                    :conversation_id, :timeline::jsonb, :shifts::jsonb,
                    :start_emotion, :end_emotion, :peak_positive, :peak_negative,
                    :variance
                )
                ON CONFLICT (conversation_id) DO UPDATE SET
                    sentiment_timeline = EXCLUDED.sentiment_timeline,
                    sentiment_shifts = EXCLUDED.sentiment_shifts,
                    start_emotion = EXCLUDED.start_emotion,
                    end_emotion = EXCLUDED.end_emotion,
                    peak_positive = EXCLUDED.peak_positive,
                    peak_negative = EXCLUDED.peak_negative,
                    emotional_variance = EXCLUDED.emotional_variance
            """)

            # Calculate variance
            if len(sentiments) > 1:
                mean = sum(sentiments) / len(sentiments)
                variance = sum((x - mean) ** 2 for x in sentiments) / len(sentiments)
            else:
                variance = 0.0

            await self.db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "timeline": timeline,
                    "shifts": shifts,
                    "start_emotion": start_emotion,
                    "end_emotion": end_emotion,
                    "peak_positive": max(sentiments) if sentiments else 0.0,
                    "peak_negative": min(sentiments) if sentiments else 0.0,
                    "variance": variance
                }
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error storing sentiment progression: {e}", exc_info=True)
            await self.db.rollback()
