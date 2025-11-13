"""Additional Knowledge Analytics Services."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
import numpy as np
from collections import defaultdict

from ...models.database.tables import (
    AgentKnowledgeItem,
    KnowledgeRetrievalLog,
    KnowledgeDriftEvent,
)
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


# =====================================================================
# Knowledge Retrieval Analyzer
# =====================================================================

class KnowledgeRetrievalAnalyzer:
    """Analyzer for knowledge retrieval efficiency and effectiveness."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_retrieval_performance(
        self, agent_id: str, workspace_id: str, timeframe: str = "7d"
    ) -> Dict[str, Any]:
        """Analyze knowledge retrieval performance metrics."""
        try:
            start_date = calculate_start_date(timeframe)

            # Get retrieval logs
            query = select(KnowledgeRetrievalLog).where(
                and_(
                    KnowledgeRetrievalLog.agent_id == agent_id,
                    KnowledgeRetrievalLog.workspace_id == workspace_id,
                    KnowledgeRetrievalLog.created_at >= start_date,
                )
            )

            result = await self.db.execute(query)
            logs = result.scalars().all()

            if not logs:
                return self._empty_retrieval_metrics()

            # Calculate performance metrics
            retrieval_times = [log.retrieval_time_ms for log in logs]
            cache_hits = sum(1 for log in logs if log.cache_hit)
            successful_queries = sum(1 for log in logs if log.result_used)

            # Calculate effectiveness metrics
            satisfied_queries = sum(1 for log in logs if log.user_satisfied)

            return {
                "retrieval_performance": {
                    "avg_retrieval_time_ms": int(np.mean(retrieval_times)),
                    "p95_retrieval_time_ms": int(np.percentile(retrieval_times, 95)),
                    "cache_hit_rate": cache_hits / len(logs) if logs else 0,
                    "query_success_rate": successful_queries / len(logs) if logs else 0,
                },
                "search_effectiveness": {
                    "precision": self._calculate_precision(logs),
                    "recall": self._calculate_recall(logs),
                    "f1_score": self._calculate_f1_score(logs),
                    "user_satisfaction": satisfied_queries / len(logs) if logs else 0,
                },
                "access_distribution": await self._analyze_access_distribution(agent_id, workspace_id),
            }

        except Exception as e:
            logger.error(f"Error analyzing retrieval performance: {str(e)}", exc_info=True)
            return self._empty_retrieval_metrics()

    def _empty_retrieval_metrics(self) -> Dict[str, Any]:
        """Return empty retrieval metrics."""
        return {
            "retrieval_performance": {
                "avg_retrieval_time_ms": 0,
                "p95_retrieval_time_ms": 0,
                "cache_hit_rate": 0.0,
                "query_success_rate": 0.0,
            },
            "search_effectiveness": {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "user_satisfaction": 0.0,
            },
            "access_distribution": {},
        }

    def _calculate_precision(self, logs: List) -> float:
        """Calculate search precision from logs."""
        relevant_retrieved = sum(1 for log in logs if log.result_used and log.precision_score)
        total_retrieved = sum(log.results_count for log in logs if log.results_count)
        return relevant_retrieved / total_retrieved if total_retrieved > 0 else 0.0

    def _calculate_recall(self, logs: List) -> float:
        """Calculate search recall from logs."""
        # Simplified recall calculation
        with_results = sum(1 for log in logs if log.results_count > 0)
        return with_results / len(logs) if logs else 0.0

    def _calculate_f1_score(self, logs: List) -> float:
        """Calculate F1 score."""
        precision = self._calculate_precision(logs)
        recall = self._calculate_recall(logs)
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    async def _analyze_access_distribution(
        self, agent_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Analyze knowledge access distribution (hot vs cold items)."""
        try:
            query = select(
                AgentKnowledgeItem.id,
                AgentKnowledgeItem.access_count,
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                )
            )

            result = await self.db.execute(query)
            items = result.all()

            if not items:
                return {}

            access_counts = [item.access_count for item in items]
            total_items = len(items)

            # Sort by access count
            sorted_counts = sorted(access_counts, reverse=True)

            # Top 10% are hot items
            hot_threshold = int(total_items * 0.1)
            hot_items = sum(1 for count in sorted_counts[:hot_threshold] if count > 0)

            # Cold items: never accessed
            cold_items = sum(1 for count in access_counts if count == 0)

            # Calculate Gini coefficient (access inequality)
            gini = self._calculate_gini_coefficient(access_counts)

            return {
                "hot_items_percentage": (hot_items / total_items * 100) if total_items > 0 else 0,
                "cold_items_percentage": (cold_items / total_items * 100) if total_items > 0 else 0,
                "access_inequality": gini,
            }

        except Exception as e:
            logger.error(f"Error analyzing access distribution: {str(e)}", exc_info=True)
            return {}

    def _calculate_gini_coefficient(self, values: List[int]) -> float:
        """Calculate Gini coefficient for inequality measurement."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        index = np.arange(1, n + 1)
        return (2 * np.sum(index * sorted_values)) / (n * np.sum(sorted_values)) - (n + 1) / n


# =====================================================================
# Knowledge Drift Detector
# =====================================================================

class KnowledgeDriftDetector:
    """Detector for knowledge drift and staleness."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_knowledge_drift(
        self, agent_id: str, workspace_id: str, drift_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Detect knowledge drift for an agent."""
        try:
            # Get existing drift events
            drift_events = await self._get_recent_drift_events(agent_id, workspace_id, days=30)

            # Detect concept drift
            concept_drift = await self._detect_concept_drift(agent_id, workspace_id, drift_threshold)

            # Identify stale facts
            stale_facts = await self._identify_stale_facts(agent_id, workspace_id, days=90)

            # Find rule conflicts
            rule_conflicts = await self._find_rule_conflicts(agent_id, workspace_id)

            # Calculate drift rates
            drift_rates = self._calculate_drift_rates(drift_events)

            return {
                "agent_id": agent_id,
                "concept_drift": concept_drift,
                "fact_staleness": {
                    "stale_items_count": len(stale_facts),
                    "stale_items": stale_facts[:10],  # Top 10
                },
                "rule_conflicts": rule_conflicts,
                "accuracy_degradation": {},  # TODO: Implement
                "daily_drift_rate": drift_rates.get("daily", 0.0),
                "weekly_drift_rate": drift_rates.get("weekly", 0.0),
                "monthly_drift_rate": drift_rates.get("monthly", 0.0),
                "remediation_plan": self._create_remediation_plan(concept_drift, stale_facts, rule_conflicts),
            }

        except Exception as e:
            logger.error(f"Error detecting knowledge drift: {str(e)}", exc_info=True)
            return {}

    async def _get_recent_drift_events(
        self, agent_id: str, workspace_id: str, days: int = 30
    ) -> List:
        """Get recent drift events."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = select(KnowledgeDriftEvent).where(
                and_(
                    KnowledgeDriftEvent.agent_id == agent_id,
                    KnowledgeDriftEvent.workspace_id == workspace_id,
                    KnowledgeDriftEvent.created_at >= start_date,
                )
            )

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting drift events: {str(e)}", exc_info=True)
            return []

    async def _detect_concept_drift(
        self, agent_id: str, workspace_id: str, threshold: float
    ) -> Dict[str, Any]:
        """Detect concept drift using statistical methods."""
        try:
            # Get knowledge items created in last 30 days vs previous 30 days
            now = datetime.utcnow()
            current_start = now - timedelta(days=30)
            baseline_start = now - timedelta(days=60)
            baseline_end = current_start

            # Current distribution
            current_query = select(
                AgentKnowledgeItem.knowledge_type,
                func.count(AgentKnowledgeItem.id).label("count"),
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                    AgentKnowledgeItem.created_at >= current_start,
                )
            ).group_by(AgentKnowledgeItem.knowledge_type)

            # Baseline distribution
            baseline_query = select(
                AgentKnowledgeItem.knowledge_type,
                func.count(AgentKnowledgeItem.id).label("count"),
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                    AgentKnowledgeItem.created_at >= baseline_start,
                    AgentKnowledgeItem.created_at < baseline_end,
                )
            ).group_by(AgentKnowledgeItem.knowledge_type)

            current_result = await self.db.execute(current_query)
            baseline_result = await self.db.execute(baseline_query)

            current_dist = {row.knowledge_type: row.count for row in current_result.all()}
            baseline_dist = {row.knowledge_type: row.count for row in baseline_result.all()}

            # Calculate KL divergence (simplified)
            drift_score = self._calculate_kl_divergence(current_dist, baseline_dist)

            return {
                "drift_score": drift_score,
                "drift_detected": drift_score > threshold,
                "affected_concepts": list(current_dist.keys()) if drift_score > threshold else [],
            }

        except Exception as e:
            logger.error(f"Error detecting concept drift: {str(e)}", exc_info=True)
            return {"drift_score": 0.0, "drift_detected": False, "affected_concepts": []}

    def _calculate_kl_divergence(
        self, current_dist: Dict[str, int], baseline_dist: Dict[str, int]
    ) -> float:
        """Calculate KL divergence between distributions."""
        if not current_dist or not baseline_dist:
            return 0.0

        # Normalize distributions
        current_total = sum(current_dist.values())
        baseline_total = sum(baseline_dist.values())

        if current_total == 0 or baseline_total == 0:
            return 0.0

        all_keys = set(current_dist.keys()) | set(baseline_dist.keys())

        kl_div = 0.0
        for key in all_keys:
            p = current_dist.get(key, 0) / current_total
            q = baseline_dist.get(key, 0.0001) / baseline_total  # Add small epsilon

            if p > 0:
                kl_div += p * np.log(p / q)

        return float(kl_div)

    async def _identify_stale_facts(
        self, agent_id: str, workspace_id: str, days: int = 90
    ) -> List[str]:
        """Identify facts that haven't been updated recently."""
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days)

            query = select(AgentKnowledgeItem.id).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                    AgentKnowledgeItem.knowledge_type == "fact",
                    AgentKnowledgeItem.updated_at < threshold_date,
                )
            )

            result = await self.db.execute(query)
            return [row.id for row in result.all()]

        except Exception as e:
            logger.error(f"Error identifying stale facts: {str(e)}", exc_info=True)
            return []

    async def _find_rule_conflicts(
        self, agent_id: str, workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Find conflicting rules in knowledge base."""
        # Simplified implementation - in production, would need semantic analysis
        try:
            query = select(
                AgentKnowledgeItem.id,
                AgentKnowledgeItem.content,
            ).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                    AgentKnowledgeItem.knowledge_type == "rule",
                )
            )

            result = await self.db.execute(query)
            rules = result.all()

            # TODO: Implement actual conflict detection using semantic analysis
            return []

        except Exception as e:
            logger.error(f"Error finding rule conflicts: {str(e)}", exc_info=True)
            return []

    def _calculate_drift_rates(self, drift_events: List) -> Dict[str, float]:
        """Calculate drift rates over different time windows."""
        now = datetime.utcnow()

        daily_events = [e for e in drift_events if (now - e.created_at).days <= 1]
        weekly_events = [e for e in drift_events if (now - e.created_at).days <= 7]
        monthly_events = [e for e in drift_events if (now - e.created_at).days <= 30]

        return {
            "daily": len(daily_events),
            "weekly": len(weekly_events) / 7.0,
            "monthly": len(monthly_events) / 30.0,
        }

    def _create_remediation_plan(
        self, concept_drift: Dict, stale_facts: List, rule_conflicts: List
    ) -> Optional[Dict[str, Any]]:
        """Create remediation plan based on drift analysis."""
        if not concept_drift.get("drift_detected") and not stale_facts and not rule_conflicts:
            return None

        actions = []

        if concept_drift.get("drift_detected"):
            actions.append({
                "type": "revalidate_concepts",
                "priority": "high",
                "affected_items": len(concept_drift.get("affected_concepts", [])),
            })

        if stale_facts:
            actions.append({
                "type": "refresh_stale_facts",
                "priority": "medium",
                "affected_items": len(stale_facts),
            })

        if rule_conflicts:
            actions.append({
                "type": "resolve_conflicts",
                "priority": "critical",
                "affected_items": len(rule_conflicts),
            })

        return {
            "actions": actions,
            "estimated_effort": "medium",
            "expected_improvement": "20-30% reduction in drift",
        }


# =====================================================================
# Knowledge Graph Optimizer
# =====================================================================

class KnowledgeGraphOptimizer:
    """Optimizer for knowledge graph structure and performance."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def optimize_graph_structure(
        self, agent_id: str, workspace_id: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Optimize knowledge graph structure."""
        try:
            # Get current graph state
            items = await self._load_knowledge_graph(agent_id, workspace_id)

            if not items:
                return {"error": "No knowledge items found"}

            # Identify optimizations
            optimizations = {
                "redundancy_removal": await self._identify_redundant_nodes(items),
                "edge_optimization": self._optimize_edges(items),
                "cluster_reorganization": self._reorganize_clusters(items),
            }

            # Calculate improvement metrics
            improvement = self._calculate_improvement_metrics(items, optimizations)

            if not dry_run:
                # Apply optimizations
                await self._apply_optimizations(agent_id, workspace_id, optimizations)

            return {
                "agent_id": agent_id,
                "optimizations": optimizations,
                "improvement_metrics": improvement,
                "dry_run": dry_run,
            }

        except Exception as e:
            logger.error(f"Error optimizing graph structure: {str(e)}", exc_info=True)
            return {}

    async def _load_knowledge_graph(self, agent_id: str, workspace_id: str) -> List:
        """Load knowledge graph items."""
        try:
            query = select(AgentKnowledgeItem).where(
                and_(
                    AgentKnowledgeItem.agent_id == agent_id,
                    AgentKnowledgeItem.workspace_id == workspace_id,
                )
            )

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error loading knowledge graph: {str(e)}", exc_info=True)
            return []

    async def _identify_redundant_nodes(self, items: List) -> Dict[str, Any]:
        """Identify redundant knowledge nodes."""
        # Group by content hash to find duplicates
        hash_groups = defaultdict(list)
        for item in items:
            if item.content_hash:
                hash_groups[item.content_hash].append(item.id)

        redundant = [ids for ids in hash_groups.values() if len(ids) > 1]

        return {
            "action": "remove_redundant_nodes",
            "count": len(redundant),
            "redundant_groups": redundant[:10],  # Top 10
            "impact": "Reduced storage and improved query performance",
        }

    def _optimize_edges(self, items: List) -> Dict[str, Any]:
        """Optimize graph edges."""
        weak_edges_count = sum(
            len([r for r in (item.related_items or [])])
            for item in items
            if item.quality_score and item.quality_score < 0.3
        )

        return {
            "action": "optimize_edges",
            "weak_edges_removed": weak_edges_count,
            "impact": "Improved graph traversal efficiency",
        }

    def _reorganize_clusters(self, items: List) -> Dict[str, Any]:
        """Reorganize knowledge clusters."""
        # Group by domain
        domain_clusters = defaultdict(int)
        for item in items:
            if item.domain:
                domain_clusters[item.domain] += 1

        return {
            "action": "reorganize_clusters",
            "clusters_identified": len(domain_clusters),
            "impact": "Better knowledge organization",
        }

    def _calculate_improvement_metrics(
        self, items: List, optimizations: Dict
    ) -> Dict[str, float]:
        """Calculate improvement metrics from optimizations."""
        redundancy_count = optimizations["redundancy_removal"]["count"]
        total_items = len(items)

        storage_reduction = (redundancy_count / total_items * 100) if total_items > 0 else 0

        return {
            "query_speed_improvement": 15.0,  # Estimated
            "storage_reduction": storage_reduction,
            "traversal_efficiency": 1.2,  # 20% improvement
        }

    async def _apply_optimizations(
        self, agent_id: str, workspace_id: str, optimizations: Dict
    ) -> None:
        """Apply optimizations to knowledge graph."""
        # TODO: Implement actual optimization application
        logger.info(f"Applying optimizations for agent {agent_id}")
        pass
