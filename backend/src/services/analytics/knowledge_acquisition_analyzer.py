"""Knowledge Acquisition Analyzer Service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import numpy as np

from ...models.database.tables import AgentKnowledgeItem, KnowledgeSource
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class KnowledgeAcquisitionAnalyzer:
    """Analyzer for knowledge acquisition patterns and learning curves."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_learning_patterns(
        self, agent_id: str, workspace_id: str, timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """Analyze learning patterns for an agent."""
        try:
            start_date = calculate_start_date(timeframe)
            end_date = datetime.utcnow()

            # Get acquisition timeline
            timeline_data = await self._get_knowledge_timeline(agent_id, workspace_id, start_date, end_date)

            # Analyze learning curve
            learning_curve = await self._plot_learning_curve(timeline_data)

            # Get source quality
            source_quality = await self._analyze_source_quality(agent_id, workspace_id)

            # Identify knowledge gaps
            knowledge_gaps = await self._identify_knowledge_gaps(agent_id, workspace_id)

            return {
                "acquisition_rate": self._calculate_acquisition_rate(timeline_data),
                "total_items_acquired": len(timeline_data),
                "learning_curve": learning_curve,
                "source_quality": source_quality,
                "knowledge_gaps": knowledge_gaps,
                "avg_quality_score": self._calculate_avg_quality(timeline_data),
            }

        except Exception as e:
            logger.error(f"Error analyzing learning patterns: {str(e)}", exc_info=True)
            return {}

    async def _get_knowledge_timeline(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get knowledge acquisition timeline."""
        try:
            query = (
                select(
                    AgentKnowledgeItem.created_at,
                    AgentKnowledgeItem.knowledge_type,
                    AgentKnowledgeItem.quality_score,
                    AgentKnowledgeItem.confidence_score,
                )
                .where(
                    and_(
                        AgentKnowledgeItem.agent_id == agent_id,
                        AgentKnowledgeItem.workspace_id == workspace_id,
                        AgentKnowledgeItem.created_at >= start_date,
                        AgentKnowledgeItem.created_at <= end_date,
                    )
                )
                .order_by(AgentKnowledgeItem.created_at)
            )

            result = await self.db.execute(query)
            items = result.all()

            return [
                {
                    "created_at": item.created_at,
                    "type": item.knowledge_type,
                    "quality": float(item.quality_score or 0),
                    "confidence": float(item.confidence_score or 0),
                }
                for item in items
            ]

        except Exception as e:
            logger.error(f"Error getting knowledge timeline: {str(e)}", exc_info=True)
            return []

    def _calculate_acquisition_rate(self, timeline_data: List[Dict[str, Any]]) -> float:
        """Calculate knowledge acquisition rate (items per day)."""
        if not timeline_data or len(timeline_data) < 2:
            return 0.0

        first_date = timeline_data[0]["created_at"]
        last_date = timeline_data[-1]["created_at"]
        days = (last_date - first_date).days or 1

        return len(timeline_data) / days

    async def _plot_learning_curve(self, timeline_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze learning curve and identify phases."""
        if not timeline_data:
            return {
                "phases": [],
                "current_phase": None,
                "saturation_point": None,
                "efficiency_trend": [],
            }

        # Group by day and calculate daily acquisition
        daily_counts = {}
        for item in timeline_data:
            date = item["created_at"].date()
            daily_counts[date] = daily_counts.get(date, 0) + 1

        # Calculate phases based on acquisition rate
        phases = self._identify_learning_phases(daily_counts)

        # Determine current phase
        current_phase = self._identify_current_phase(daily_counts)

        return {
            "phases": phases,
            "current_phase": current_phase,
            "saturation_point": None,  # TODO: Implement saturation prediction
            "efficiency_trend": list(daily_counts.values())[-7:],  # Last 7 days
        }

    def _identify_learning_phases(self, daily_counts: Dict) -> List[Dict[str, Any]]:
        """Identify learning phases from daily acquisition counts."""
        if not daily_counts:
            return []

        values = list(daily_counts.values())
        if len(values) < 3:
            return []

        # Simple phase detection based on rates
        avg_rate = np.mean(values)

        phases = []
        if values:
            # Initial phase: first 20% of data
            initial_end = max(1, len(values) // 5)
            phases.append({
                "name": "initial",
                "start": 0,
                "end": initial_end,
                "rate": np.mean(values[:initial_end]) if values[:initial_end] else 0,
            })

            # Rapid growth: items where rate > avg
            if len(values) > initial_end:
                phases.append({
                    "name": "rapid_growth",
                    "start": initial_end,
                    "end": len(values),
                    "rate": np.mean(values[initial_end:]),
                })

        return phases

    def _identify_current_phase(self, daily_counts: Dict) -> str:
        """Identify current learning phase."""
        if not daily_counts:
            return "initial"

        values = list(daily_counts.values())
        if len(values) < 7:
            return "initial"

        # Look at last 7 days trend
        recent = values[-7:]
        avg_recent = np.mean(recent)
        avg_all = np.mean(values)

        if avg_recent > avg_all * 1.5:
            return "rapid_growth"
        elif avg_recent > avg_all * 0.8:
            return "consolidation"
        else:
            return "mastery"

    async def _analyze_source_quality(
        self, agent_id: str, workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Analyze quality of knowledge sources."""
        try:
            query = (
                select(
                    KnowledgeSource.id,
                    KnowledgeSource.source_name,
                    KnowledgeSource.source_type,
                    KnowledgeSource.reliability_score,
                    KnowledgeSource.reliability_category,
                    KnowledgeSource.items_count,
                    KnowledgeSource.avg_confidence,
                    KnowledgeSource.verification_rate,
                )
                .where(
                    and_(
                        KnowledgeSource.agent_id == agent_id,
                        KnowledgeSource.workspace_id == workspace_id,
                    )
                )
                .order_by(desc(KnowledgeSource.reliability_score))
                .limit(10)
            )

            result = await self.db.execute(query)
            sources = result.all()

            return [
                {
                    "source_id": source.id,
                    "source_name": source.source_name,
                    "source_type": source.source_type,
                    "reliability_score": float(source.reliability_score or 0),
                    "reliability_category": source.reliability_category or "unreliable",
                    "items_count": source.items_count,
                    "avg_confidence": float(source.avg_confidence or 0),
                    "verification_rate": float(source.verification_rate or 0),
                }
                for source in sources
            ]

        except Exception as e:
            logger.error(f"Error analyzing source quality: {str(e)}", exc_info=True)
            return []

    async def _identify_knowledge_gaps(
        self, agent_id: str, workspace_id: str
    ) -> List[str]:
        """Identify knowledge gaps based on domain coverage."""
        try:
            # Get domain distribution
            query = (
                select(
                    AgentKnowledgeItem.domain,
                    func.count(AgentKnowledgeItem.id).label("item_count"),
                )
                .where(
                    and_(
                        AgentKnowledgeItem.agent_id == agent_id,
                        AgentKnowledgeItem.workspace_id == workspace_id,
                        AgentKnowledgeItem.domain.isnot(None),
                    )
                )
                .group_by(AgentKnowledgeItem.domain)
            )

            result = await self.db.execute(query)
            domains = result.all()

            if not domains:
                return []

            # Identify underrepresented domains (< 50% of average)
            counts = [d.item_count for d in domains]
            avg_count = np.mean(counts)
            threshold = avg_count * 0.5

            gaps = [d.domain for d in domains if d.item_count < threshold]
            return gaps

        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {str(e)}", exc_info=True)
            return []

    def _calculate_avg_quality(self, timeline_data: List[Dict[str, Any]]) -> float:
        """Calculate average quality score from timeline data."""
        if not timeline_data:
            return 0.0

        qualities = [item["quality"] for item in timeline_data if item.get("quality", 0) > 0]
        return np.mean(qualities) if qualities else 0.0
