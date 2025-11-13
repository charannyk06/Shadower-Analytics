"""Knowledge Base Analytics Service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_, text
import numpy as np
from collections import defaultdict

from ...models.database.tables import (
    AgentKnowledgeItem,
    KnowledgeSource,
    KnowledgeValidationEvent,
    KnowledgeTransfer,
    KnowledgeRetrievalLog,
    KnowledgeDriftEvent,
    KnowledgeGraphMetric,
    KnowledgeDomain,
    KnowledgeLifecycleStage,
)
from ...models.schemas.knowledge_analytics import (
    KnowledgeGraphResponse,
    GraphMetrics,
    NodeTypeDistribution,
    EvolutionMetrics,
    KnowledgeDomainMetrics,
    QualityTrend,
)
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Service for knowledge base analytics and graph operations."""

    QUERY_TIMEOUT_SECONDS = 30
    MAX_GRAPH_NODES = 10000
    MAX_RECOMMENDATIONS = 10

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_knowledge_base_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        include_graph_metrics: bool = True,
        include_usage_patterns: bool = True,
        timeframe: str = "30d",
    ) -> Dict[str, Any]:
        """Get comprehensive knowledge base analytics for an agent.

        Args:
            agent_id: Agent identifier
            workspace_id: Workspace identifier
            include_graph_metrics: Include graph structure metrics
            include_usage_patterns: Include usage pattern analytics
            timeframe: Time window for metrics

        Returns:
            Dictionary containing knowledge base analytics
        """
        # Validate UUIDs
        try:
            uuid.UUID(agent_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {str(e)}")

        end_date = datetime.utcnow()
        start_date = calculate_start_date(timeframe)

        # Parallel fetch all metrics
        tasks = [
            self._get_basic_stats(agent_id, workspace_id),
            self._get_domain_coverage(agent_id, workspace_id),
        ]

        if include_graph_metrics:
            tasks.append(self._get_graph_metrics(agent_id, workspace_id))

        if include_usage_patterns:
            tasks.append(self._get_usage_patterns(agent_id, workspace_id, start_date, end_date))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            analytics = {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "basic_stats": results[0] if not isinstance(results[0], Exception) else {},
                "domain_coverage": results[1] if not isinstance(results[1], Exception) else [],
                "timestamp": datetime.utcnow(),
            }

            result_index = 2
            if include_graph_metrics:
                analytics["graph_metrics"] = (
                    results[result_index] if not isinstance(results[result_index], Exception) else {}
                )
                result_index += 1

            if include_usage_patterns:
                analytics["usage_patterns"] = (
                    results[result_index] if not isinstance(results[result_index], Exception) else {}
                )

            return analytics

        except Exception as e:
            logger.error(f"Error fetching knowledge base analytics: {str(e)}", exc_info=True)
            raise

    async def _get_basic_stats(self, agent_id: str, workspace_id: str) -> Dict[str, Any]:
        """Get basic knowledge base statistics."""
        try:
            query = select(
                func.count(AgentKnowledgeItem.id).label("total_items"),
                func.count(AgentKnowledgeItem.id).filter(
                    AgentKnowledgeItem.verification_status == "verified"
                ).label("verified_items"),
                func.avg(AgentKnowledgeItem.quality_score).label("avg_quality"),
                func.avg(AgentKnowledgeItem.confidence_score).label("avg_confidence"),
                func.sum(AgentKnowledgeItem.access_count).label("total_accesses"),
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                )
            )

            result = await self.db.execute(query)
            row = result.one()

            return {
                "total_items": row.total_items or 0,
                "verified_items": row.verified_items or 0,
                "verification_rate": (
                    (row.verified_items / row.total_items * 100) if row.total_items > 0 else 0
                ),
                "avg_quality_score": float(row.avg_quality or 0),
                "avg_confidence_score": float(row.avg_confidence or 0),
                "total_accesses": int(row.total_accesses or 0),
            }

        except Exception as e:
            logger.error(f"Error getting basic stats: {str(e)}", exc_info=True)
            return {}

    async def _get_domain_coverage(self, agent_id: str, workspace_id: str) -> List[Dict[str, Any]]:
        """Get knowledge domain coverage statistics."""
        try:
            query = (
                select(
                    AgentKnowledgeItem.domain,
                    AgentKnowledgeItem.subdomain,
                    func.count(AgentKnowledgeItem.id).label("item_count"),
                    func.avg(AgentKnowledgeItem.quality_score).label("avg_quality"),
                    func.avg(AgentKnowledgeItem.confidence_score).label("avg_confidence"),
                    func.max(AgentKnowledgeItem.updated_at).label("last_updated"),
                )
                .where(
                    and_(
                        AgentKnowledgeItem.agent_id == agent_id,
                        AgentKnowledgeItem.workspace_id == workspace_id,
                        AgentKnowledgeItem.domain.isnot(None),
                    )
                )
                .group_by(AgentKnowledgeItem.domain, AgentKnowledgeItem.subdomain)
                .order_by(desc("item_count"))
            )

            result = await self.db.execute(query)
            rows = result.all()

            domains = []
            for row in rows:
                domains.append({
                    "domain": row.domain,
                    "subdomain": row.subdomain,
                    "item_count": row.item_count,
                    "avg_quality": float(row.avg_quality or 0),
                    "avg_confidence": float(row.avg_confidence or 0),
                    "last_updated": row.last_updated,
                })

            return domains

        except Exception as e:
            logger.error(f"Error getting domain coverage: {str(e)}", exc_info=True)
            return []

    async def _get_graph_metrics(self, agent_id: str, workspace_id: str) -> Dict[str, Any]:
        """Get knowledge graph structure metrics."""
        try:
            # Get all knowledge items for graph analysis
            query = select(
                AgentKnowledgeItem.id,
                AgentKnowledgeItem.knowledge_type,
                AgentKnowledgeItem.related_items,
                AgentKnowledgeItem.prerequisite_items,
                AgentKnowledgeItem.node_degree,
                AgentKnowledgeItem.centrality_score,
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                )
            )

            result = await self.db.execute(query)
            items = result.all()

            if not items:
                return self._empty_graph_metrics()

            # Calculate graph metrics
            total_nodes = len(items)
            total_edges = sum(len(item.related_items or []) for item in items)

            # Graph density: actual edges / possible edges
            max_possible_edges = total_nodes * (total_nodes - 1)
            graph_density = (total_edges / max_possible_edges) if max_possible_edges > 0 else 0

            # Average degree
            degrees = [item.node_degree or 0 for item in items]
            avg_degree = np.mean(degrees) if degrees else 0

            # Node type distribution
            type_counts = defaultdict(int)
            for item in items:
                type_counts[item.knowledge_type] += 1

            # Quality metrics
            centralities = [item.centrality_score for item in items if item.centrality_score is not None]
            avg_centrality = np.mean(centralities) if centralities else 0

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "graph_density": float(graph_density),
                "average_degree": float(avg_degree),
                "clustering_coefficient": 0.0,  # TODO: Implement clustering calculation
                "connected_components": 1,  # TODO: Implement component detection
                "max_path_length": 0,  # TODO: Implement path length calculation
                "node_type_distribution": dict(type_counts),
                "avg_centrality": float(avg_centrality),
            }

        except Exception as e:
            logger.error(f"Error calculating graph metrics: {str(e)}", exc_info=True)
            return self._empty_graph_metrics()

    def _empty_graph_metrics(self) -> Dict[str, Any]:
        """Return empty graph metrics structure."""
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "graph_density": 0.0,
            "average_degree": 0.0,
            "clustering_coefficient": 0.0,
            "connected_components": 0,
            "max_path_length": 0,
            "node_type_distribution": {},
            "avg_centrality": 0.0,
        }

    async def _get_usage_patterns(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get knowledge usage patterns."""
        try:
            # Most accessed items
            query = (
                select(
                    AgentKnowledgeItem.id,
                    AgentKnowledgeItem.knowledge_type,
                    AgentKnowledgeItem.domain,
                    AgentKnowledgeItem.access_count,
                    AgentKnowledgeItem.usefulness_score,
                )
                .where(
                    and_(
                        AgentKnowledgeItem.agent_id == agent_id,
                        AgentKnowledgeItem.workspace_id == workspace_id,
                        AgentKnowledgeItem.access_count > 0,
                    )
                )
                .order_by(desc(AgentKnowledgeItem.access_count))
                .limit(10)
            )

            result = await self.db.execute(query)
            most_accessed = result.all()

            # Usage by type
            type_query = (
                select(
                    AgentKnowledgeItem.knowledge_type,
                    func.sum(AgentKnowledgeItem.access_count).label("total_accesses"),
                    func.count(AgentKnowledgeItem.id).label("item_count"),
                )
                .where(
                    and_(
                        AgentKnowledgeItem.agent_id == agent_id,
                        AgentKnowledgeItem.workspace_id == workspace_id,
                    )
                )
                .group_by(AgentKnowledgeItem.knowledge_type)
            )

            type_result = await self.db.execute(type_query)
            usage_by_type = type_result.all()

            return {
                "most_accessed_items": [
                    {
                        "item_id": item.id,
                        "type": item.knowledge_type,
                        "domain": item.domain,
                        "access_count": item.access_count,
                        "usefulness_score": float(item.usefulness_score or 0),
                    }
                    for item in most_accessed
                ],
                "usage_by_type": {
                    item.knowledge_type: {
                        "total_accesses": int(item.total_accesses or 0),
                        "item_count": item.item_count,
                    }
                    for item in usage_by_type
                },
            }

        except Exception as e:
            logger.error(f"Error getting usage patterns: {str(e)}", exc_info=True)
            return {}

    async def get_knowledge_item_details(self, knowledge_item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific knowledge item."""
        try:
            query = select(AgentKnowledgeItem).where(AgentKnowledgeItem.id == knowledge_item_id)
            result = await self.db.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                return None

            return {
                "id": item.id,
                "agent_id": item.agent_id,
                "workspace_id": item.workspace_id,
                "knowledge_type": item.knowledge_type,
                "domain": item.domain,
                "subdomain": item.subdomain,
                "content": item.content,
                "quality_score": item.quality_score,
                "confidence_score": item.confidence_score,
                "verification_status": item.verification_status,
                "access_count": item.access_count,
                "last_accessed": item.last_accessed,
                "usefulness_score": item.usefulness_score,
                "node_degree": item.node_degree,
                "centrality_score": item.centrality_score,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "tags": item.tags,
                "metadata": item.metadata,
            }

        except Exception as e:
            logger.error(f"Error getting knowledge item details: {str(e)}", exc_info=True)
            return None

    async def save_graph_metrics_snapshot(
        self, agent_id: str, workspace_id: str, snapshot_type: str = "scheduled"
    ) -> Optional[str]:
        """Save a snapshot of current knowledge graph metrics.

        Args:
            agent_id: Agent identifier
            workspace_id: Workspace identifier
            snapshot_type: Type of snapshot (scheduled, on_demand, post_optimization)

        Returns:
            Snapshot ID if successful, None otherwise
        """
        try:
            # Get current graph metrics
            metrics = await self._get_graph_metrics(agent_id, workspace_id)

            if not metrics or metrics.get("total_nodes", 0) == 0:
                logger.warning(f"No knowledge items found for agent {agent_id}")
                return None

            # Create snapshot record
            snapshot = KnowledgeGraphMetric(
                agent_id=agent_id,
                workspace_id=workspace_id,
                total_nodes=metrics["total_nodes"],
                total_edges=metrics["total_edges"],
                graph_density=metrics["graph_density"],
                average_degree=metrics["average_degree"],
                clustering_coefficient=metrics.get("clustering_coefficient", 0.0),
                connected_components=metrics.get("connected_components", 1),
                max_path_length=metrics.get("max_path_length", 0),
                snapshot_type=snapshot_type,
            )

            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)

            logger.info(f"Saved graph metrics snapshot {snapshot.id} for agent {agent_id}")
            return snapshot.id

        except Exception as e:
            logger.error(f"Error saving graph metrics snapshot: {str(e)}", exc_info=True)
            await self.db.rollback()
            return None

    async def get_graph_evolution(
        self, agent_id: str, workspace_id: str, timeframe: str = "30d"
    ) -> List[Dict[str, Any]]:
        """Get knowledge graph evolution over time.

        Args:
            agent_id: Agent identifier
            workspace_id: Workspace identifier
            timeframe: Time window for evolution analysis

        Returns:
            List of graph metric snapshots over time
        """
        try:
            start_date = calculate_start_date(timeframe)

            query = (
                select(KnowledgeGraphMetric)
                .where(
                    and_(
                        KnowledgeGraphMetric.agent_id == agent_id,
                        KnowledgeGraphMetric.workspace_id == workspace_id,
                        KnowledgeGraphMetric.created_at >= start_date,
                    )
                )
                .order_by(KnowledgeGraphMetric.created_at)
            )

            result = await self.db.execute(query)
            snapshots = result.scalars().all()

            return [
                {
                    "timestamp": snapshot.created_at,
                    "total_nodes": snapshot.total_nodes,
                    "total_edges": snapshot.total_edges,
                    "graph_density": snapshot.graph_density,
                    "average_degree": snapshot.average_degree,
                    "quality_trend": snapshot.quality_trend,
                    "snapshot_type": snapshot.snapshot_type,
                }
                for snapshot in snapshots
            ]

        except Exception as e:
            logger.error(f"Error getting graph evolution: {str(e)}", exc_info=True)
            return []
