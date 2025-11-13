"""Collaboration analytics service."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import networkx as nx
import numpy as np
from collections import defaultdict

from src.models.database.tables import (
    MultiAgentWorkflow,
    AgentInteraction,
    AgentHandoff,
    AgentDependency,
    CollaborationMetrics,
    WorkflowExecutionStep,
    CollaborationPattern,
    LoadBalancingMetric,
)

logger = logging.getLogger(__name__)


class CollaborationAnalyticsService:
    """Service for analyzing agent collaboration metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workflow_collaboration_metrics(
        self,
        workflow_id: str,
        include_handoffs: bool = True,
        include_dependencies: bool = True,
        include_patterns: bool = False,
    ) -> Dict[str, Any]:
        """Get collaboration metrics for a specific workflow."""
        try:
            # Get workflow
            workflow_query = select(MultiAgentWorkflow).where(
                MultiAgentWorkflow.workflow_id == workflow_id
            )
            result = await self.db.execute(workflow_query)
            workflow = result.scalar_one_or_none()

            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Get agent nodes (unique agents in workflow)
            agent_nodes = await self._get_workflow_agents(workflow_id)

            # Get interactions
            interactions = await self._get_workflow_interactions(workflow_id)

            # Prepare response
            response = {
                "workflow_id": workflow.workflow_id,
                "workflow_name": workflow.workflow_name,
                "workflow_type": workflow.workflow_type,
                "status": workflow.status,
                "started_at": workflow.started_at,
                "completed_at": workflow.completed_at,
                "total_duration_ms": workflow.total_duration_ms,
                "agents_involved": workflow.agents_involved,
                "handoffs_count": workflow.handoffs_count,
                "parallel_executions": workflow.parallel_executions,
                "coordination_efficiency": workflow.coordination_efficiency or 0.0,
                "communication_overhead": workflow.communication_overhead or 0.0,
                "bottleneck_score": workflow.bottleneck_score or 0.0,
                "synergy_index": workflow.synergy_index or 0.0,
                "agent_nodes": agent_nodes,
                "interactions": interactions,
                "handoffs": [],
                "dependencies": [],
                "detected_patterns": [],
            }

            # Get handoffs if requested
            if include_handoffs:
                response["handoffs"] = await self._get_workflow_handoffs(workflow_id)

            # Get dependencies if requested
            if include_dependencies:
                response["dependencies"] = await self._get_workflow_dependencies(
                    workflow.workspace_id, [node["agent_id"] for node in agent_nodes]
                )

            # Get patterns if requested
            if include_patterns:
                response["detected_patterns"] = await self._get_workflow_patterns(
                    workflow.workspace_id, workflow_id
                )

            return response

        except Exception as e:
            logger.error(f"Error getting workflow collaboration metrics: {e}")
            raise

    async def _get_workflow_agents(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get unique agents involved in a workflow with their metrics."""
        query = select(
            WorkflowExecutionStep.agent_id,
            func.count(WorkflowExecutionStep.id).label("execution_count"),
            func.avg(WorkflowExecutionStep.duration_ms).label("avg_processing_time_ms"),
            func.sum(
                func.case(
                    (WorkflowExecutionStep.status == "completed", 1), else_=0
                )
            ).label("success_count"),
            func.count(WorkflowExecutionStep.id).label("total_count"),
        ).where(WorkflowExecutionStep.workflow_id == workflow_id).group_by(
            WorkflowExecutionStep.agent_id
        )

        result = await self.db.execute(query)
        agents = []

        for row in result:
            success_rate = row.success_count / row.total_count if row.total_count > 0 else 0.0
            agents.append({
                "agent_id": row.agent_id,
                "agent_name": None,  # Would be populated from agent service
                "role": None,
                "responsibilities": [],
                "execution_count": row.execution_count,
                "avg_processing_time_ms": float(row.avg_processing_time_ms or 0),
                "success_rate": success_rate,
            })

        return agents

    async def _get_workflow_interactions(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Get agent interactions in a workflow."""
        query = select(
            AgentInteraction.source_agent_id,
            AgentInteraction.target_agent_id,
            AgentInteraction.interaction_type,
            func.count(AgentInteraction.id).label("interaction_count"),
            func.avg(AgentInteraction.interaction_duration_ms).label("avg_interaction_time_ms"),
            func.avg(AgentInteraction.payload_size_bytes).label("avg_data_size_bytes"),
            func.sum(
                func.case((AgentInteraction.error_occurred == True, 1), else_=0)
            ).label("error_count"),
            func.avg(AgentInteraction.data_quality_score).label("avg_quality_score"),
        ).where(AgentInteraction.workflow_id == workflow_id).group_by(
            AgentInteraction.source_agent_id,
            AgentInteraction.target_agent_id,
            AgentInteraction.interaction_type,
        )

        result = await self.db.execute(query)
        interactions = []

        for row in result:
            error_rate = row.error_count / row.interaction_count if row.interaction_count > 0 else 0.0
            interactions.append({
                "source_agent_id": row.source_agent_id,
                "target_agent_id": row.target_agent_id,
                "interaction_type": row.interaction_type,
                "interaction_count": row.interaction_count,
                "avg_interaction_time_ms": float(row.avg_interaction_time_ms or 0),
                "avg_data_size_bytes": int(row.avg_data_size_bytes or 0),
                "error_rate": error_rate,
                "avg_quality_score": float(row.avg_quality_score or 0),
            })

        return interactions

    async def _get_workflow_handoffs(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get handoff metrics for a workflow."""
        query = select(AgentHandoff).where(AgentHandoff.workflow_id == workflow_id)
        result = await self.db.execute(query)
        handoffs = result.scalars().all()

        return [
            {
                "handoff_id": h.handoff_id,
                "source_agent": h.source_agent_id,
                "target_agent": h.target_agent_id,
                "preparation_time_ms": h.preparation_time_ms,
                "transfer_time_ms": h.transfer_time_ms,
                "acknowledgment_time_ms": h.acknowledgment_time_ms,
                "total_handoff_time_ms": h.total_handoff_time_ms,
                "data_size_bytes": h.data_size_bytes,
                "data_completeness": h.data_completeness,
                "schema_compatible": h.schema_compatible,
                "handoff_success": h.handoff_success,
                "context_preserved": h.context_preserved,
                "information_loss": h.information_loss,
            }
            for h in handoffs
        ]

    async def _get_workflow_dependencies(
        self, workspace_id: str, agent_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get dependencies for agents in a workflow."""
        query = select(AgentDependency).where(
            and_(
                AgentDependency.workspace_id == workspace_id,
                AgentDependency.is_active == True,
                or_(
                    AgentDependency.agent_id.in_(agent_ids),
                    AgentDependency.depends_on_agent_id.in_(agent_ids),
                ),
            )
        )

        result = await self.db.execute(query)
        dependencies = result.scalars().all()

        return [
            {
                "agent_id": d.agent_id,
                "depends_on_agent_id": d.depends_on_agent_id,
                "dependency_type": d.dependency_type,
                "dependency_strength": d.dependency_strength,
                "is_circular": d.is_circular,
                "is_critical_path": d.is_critical_path,
                "avg_wait_time_ms": 0.0,  # Would be calculated from execution logs
                "failure_impact": d.dependency_strength,  # Simplified
            }
            for d in dependencies
        ]

    async def _get_workflow_patterns(
        self, workspace_id: str, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Get detected patterns for a workflow."""
        # This would query detected patterns that match the workflow
        # For now, return empty list as pattern detection would be a separate process
        return []

    async def analyze_collaboration_patterns(
        self,
        workspace_id: str,
        timeframe: str = "30d",
        pattern_type: Optional[str] = None,
        min_frequency: int = 2,
    ) -> Dict[str, Any]:
        """Analyze collaboration patterns in a workspace."""
        try:
            # Parse timeframe
            days = int(timeframe.replace("d", ""))
            start_date = datetime.utcnow() - timedelta(days=days)

            # Get existing patterns
            query = select(CollaborationPattern).where(
                and_(
                    CollaborationPattern.workspace_id == workspace_id,
                    CollaborationPattern.detected_at >= start_date,
                    CollaborationPattern.occurrence_frequency >= min_frequency,
                )
            )

            if pattern_type:
                query = query.where(CollaborationPattern.pattern_type == pattern_type)

            result = await self.db.execute(query)
            patterns = result.scalars().all()

            # Group patterns by type
            patterns_by_type = defaultdict(list)
            for pattern in patterns:
                pattern_dict = {
                    "pattern_id": pattern.pattern_id,
                    "pattern_type": pattern.pattern_type,
                    "pattern_name": pattern.pattern_name,
                    "pattern_description": pattern.pattern_description,
                    "agents_involved": pattern.agents_involved,
                    "occurrence_frequency": pattern.occurrence_frequency,
                    "success_rate": pattern.success_rate,
                    "avg_performance": pattern.avg_performance,
                    "efficiency_score": pattern.efficiency_score,
                    "optimization_opportunities": pattern.optimization_opportunities or [],
                    "redundancy_detected": pattern.redundancy_detected,
                    "is_optimal": pattern.is_optimal,
                    "detection_confidence": pattern.detection_confidence,
                }
                patterns_by_type[pattern.pattern_type].append(pattern_dict)

            response = {
                "workspace_id": workspace_id,
                "analysis_period": {
                    "start": start_date,
                    "end": datetime.utcnow(),
                },
                "total_patterns_detected": len(patterns),
                "common_workflows": patterns_by_type.get("common_workflow", []),
                "collaboration_clusters": await self._detect_collaboration_clusters(
                    workspace_id, start_date
                ),
                "communication_patterns": patterns_by_type.get("communication", []),
                "bottleneck_patterns": patterns_by_type.get("bottleneck", []),
                "emergent_behaviors": [],  # Would be detected through ML analysis
                "synergy_opportunities": [],  # Would be identified through pattern analysis
                "redundancy_detected": [
                    p["pattern_name"]
                    for p in patterns
                    if p.redundancy_detected
                ],
            }

            return response

        except Exception as e:
            logger.error(f"Error analyzing collaboration patterns: {e}")
            raise

    async def _detect_collaboration_clusters(
        self, workspace_id: str, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Detect collaboration clusters using graph analysis."""
        try:
            # Get agent interactions
            query = select(
                AgentInteraction.source_agent_id,
                AgentInteraction.target_agent_id,
                func.count(AgentInteraction.id).label("interaction_count"),
            ).where(
                and_(
                    AgentInteraction.workspace_id == workspace_id,
                    AgentInteraction.created_at >= start_date,
                )
            ).group_by(
                AgentInteraction.source_agent_id,
                AgentInteraction.target_agent_id,
            )

            result = await self.db.execute(query)

            # Build interaction graph
            G = nx.Graph()
            for row in result:
                G.add_edge(
                    row.source_agent_id,
                    row.target_agent_id,
                    weight=row.interaction_count,
                )

            if len(G.nodes()) == 0:
                return []

            # Detect communities using Louvain algorithm
            # Note: This is a simplified version. In production, you'd use a proper community detection library
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
            except ImportError:
                # Fallback: use connected components
                partition = {node: i for i, component in enumerate(nx.connected_components(G)) for node in component}

            # Group agents by cluster
            clusters = defaultdict(list)
            for agent_id, cluster_id in partition.items():
                clusters[cluster_id].append(agent_id)

            # Calculate cluster metrics
            cluster_list = []
            for cluster_id, agents in clusters.items():
                if len(agents) < 2:
                    continue

                # Calculate cohesion (internal edge density)
                subgraph = G.subgraph(agents)
                n = len(agents)
                m = subgraph.number_of_edges()
                max_edges = n * (n - 1) / 2
                cohesion = m / max_edges if max_edges > 0 else 0

                cluster_list.append({
                    "cluster_id": f"cluster_{cluster_id}",
                    "agents": agents,
                    "cohesion_score": cohesion,
                    "specialization": None,  # Would be determined from agent roles
                    "interaction_density": cohesion,
                    "avg_performance": 0.0,  # Would be calculated from metrics
                    "cluster_metrics": {
                        "agent_count": len(agents),
                        "internal_edges": m,
                    },
                })

            return cluster_list

        except Exception as e:
            logger.error(f"Error detecting collaboration clusters: {e}")
            return []

    async def optimize_workflow(
        self,
        workflow_id: str,
        optimization_goals: List[str],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate workflow optimization recommendations."""
        try:
            # Get workflow metrics
            collaboration_metrics = await self.get_workflow_collaboration_metrics(
                workflow_id, include_handoffs=True, include_dependencies=True
            )

            # Analyze bottlenecks
            bottlenecks = self._identify_bottlenecks(collaboration_metrics)

            # Analyze inefficiencies
            inefficiencies = self._identify_inefficiencies(collaboration_metrics)

            # Analyze failure points
            failure_points = self._identify_failure_points(collaboration_metrics)

            # Generate optimization strategies
            strategies = self._generate_optimization_strategies(
                collaboration_metrics,
                bottlenecks,
                inefficiencies,
                failure_points,
                optimization_goals,
                constraints,
            )

            # Calculate optimization potential
            optimization_potential = self._calculate_optimization_potential(
                bottlenecks, inefficiencies, failure_points
            )

            response = {
                "workflow_id": workflow_id,
                "workflow_name": collaboration_metrics["workflow_name"],
                "current_performance": {
                    "duration_ms": collaboration_metrics["total_duration_ms"],
                    "coordination_efficiency": collaboration_metrics["coordination_efficiency"],
                    "communication_overhead": collaboration_metrics["communication_overhead"],
                    "bottleneck_score": collaboration_metrics["bottleneck_score"],
                    "synergy_index": collaboration_metrics["synergy_index"],
                },
                "optimization_potential": optimization_potential,
                "bottlenecks": bottlenecks,
                "inefficiencies": inefficiencies,
                "failure_points": failure_points,
                "optimization_strategies": strategies,
                "estimated_improvements": self._estimate_improvements(strategies),
                "priority_rank": 1,  # Would be calculated based on optimization potential
            }

            return response

        except Exception as e:
            logger.error(f"Error optimizing workflow: {e}")
            raise

    def _identify_bottlenecks(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify bottlenecks in workflow execution."""
        bottlenecks = []

        # Check for slow agents
        for agent in metrics["agent_nodes"]:
            if agent["avg_processing_time_ms"] > 5000:  # 5 seconds threshold
                bottlenecks.append({
                    "type": "slow_agent",
                    "agent_id": agent["agent_id"],
                    "issue": f"Agent processing time is {agent['avg_processing_time_ms']}ms",
                    "impact": "high",
                })

        # Check for slow handoffs
        for handoff in metrics["handoffs"]:
            if handoff["total_handoff_time_ms"] > 1000:  # 1 second threshold
                bottlenecks.append({
                    "type": "slow_handoff",
                    "source": handoff["source_agent"],
                    "target": handoff["target_agent"],
                    "issue": f"Handoff time is {handoff['total_handoff_time_ms']}ms",
                    "impact": "medium",
                })

        return bottlenecks

    def _identify_inefficiencies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify inefficiencies in workflow execution."""
        inefficiencies = []

        # Check for high communication overhead
        if metrics["communication_overhead"] > 20:  # 20% threshold
            inefficiencies.append({
                "type": "high_overhead",
                "value": metrics["communication_overhead"],
                "issue": f"Communication overhead is {metrics['communication_overhead']}%",
                "recommendation": "Consider reducing inter-agent communication or using batch processing",
            })

        # Check for low coordination efficiency
        if metrics["coordination_efficiency"] < 0.7:  # 70% threshold
            inefficiencies.append({
                "type": "low_coordination",
                "value": metrics["coordination_efficiency"],
                "issue": f"Coordination efficiency is {metrics['coordination_efficiency']}",
                "recommendation": "Improve agent coordination through better workflow design",
            })

        return inefficiencies

    def _identify_failure_points(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential failure points in workflow."""
        failure_points = []

        # Check for agents with low success rates
        for agent in metrics["agent_nodes"]:
            if agent["success_rate"] < 0.9:  # 90% threshold
                failure_points.append({
                    "type": "unreliable_agent",
                    "agent_id": agent["agent_id"],
                    "success_rate": agent["success_rate"],
                    "issue": f"Agent success rate is {agent['success_rate']}",
                })

        # Check for failed handoffs
        for handoff in metrics["handoffs"]:
            if not handoff["handoff_success"]:
                failure_points.append({
                    "type": "handoff_failure",
                    "source": handoff["source_agent"],
                    "target": handoff["target_agent"],
                    "issue": "Handoff failed",
                })

        return failure_points

    def _generate_optimization_strategies(
        self,
        metrics: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]],
        inefficiencies: List[Dict[str, Any]],
        failure_points: List[Dict[str, Any]],
        optimization_goals: List[str],
        constraints: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate optimization strategies based on analysis."""
        strategies = []

        # Address bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "slow_agent":
                strategies.append({
                    "strategy_type": "performance_optimization",
                    "recommendation": f"Optimize or parallelize agent {bottleneck['agent_id']}",
                    "estimated_improvement": "30-50% reduction in processing time",
                    "complexity": "medium",
                    "priority": 4,
                })
            elif bottleneck["type"] == "slow_handoff":
                strategies.append({
                    "strategy_type": "handoff_optimization",
                    "recommendation": f"Optimize handoff between {bottleneck['source']} and {bottleneck['target']}",
                    "estimated_improvement": "20-30% reduction in handoff time",
                    "complexity": "low",
                    "priority": 3,
                })

        # Address inefficiencies
        for inefficiency in inefficiencies:
            if inefficiency["type"] == "high_overhead":
                strategies.append({
                    "strategy_type": "communication_optimization",
                    "recommendation": "Implement message batching or reduce communication frequency",
                    "estimated_improvement": "15-25% reduction in communication overhead",
                    "complexity": "medium",
                    "priority": 3,
                })

        # Address failure points
        for failure in failure_points:
            if failure["type"] == "unreliable_agent":
                strategies.append({
                    "strategy_type": "reliability_improvement",
                    "recommendation": f"Add retry logic or fallback for agent {failure['agent_id']}",
                    "estimated_improvement": "10-20% improvement in success rate",
                    "complexity": "low",
                    "priority": 5,
                })

        return strategies

    def _calculate_optimization_potential(
        self,
        bottlenecks: List[Dict[str, Any]],
        inefficiencies: List[Dict[str, Any]],
        failure_points: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall optimization potential (0-1 score)."""
        # Simple scoring based on number and severity of issues
        bottleneck_score = min(len(bottlenecks) * 0.2, 0.4)
        inefficiency_score = min(len(inefficiencies) * 0.15, 0.3)
        failure_score = min(len(failure_points) * 0.2, 0.3)

        return min(bottleneck_score + inefficiency_score + failure_score, 1.0)

    def _estimate_improvements(self, strategies: List[Dict[str, Any]]) -> Dict[str, str]:
        """Estimate overall improvements from strategies."""
        if not strategies:
            return {}

        return {
            "duration": "20-40% reduction in total workflow duration",
            "efficiency": "15-30% improvement in coordination efficiency",
            "reliability": "10-20% improvement in success rate",
            "cost": "10-15% reduction in resource costs",
        }

    async def get_collective_intelligence_metrics(
        self,
        workspace_id: str,
        metric_types: List[str],
        timeframe: str = "30d",
    ) -> Dict[str, Any]:
        """Get collective intelligence metrics for a workspace."""
        try:
            # Parse timeframe
            days = int(timeframe.replace("d", ""))
            start_date = datetime.utcnow() - timedelta(days=days)
            end_date = datetime.utcnow()

            # Get collaboration metrics for the period
            query = select(CollaborationMetrics).where(
                and_(
                    CollaborationMetrics.workspace_id == workspace_id,
                    CollaborationMetrics.period_start >= start_date,
                    CollaborationMetrics.period_end <= end_date,
                )
            )

            result = await self.db.execute(query)
            metrics_list = result.scalars().all()

            if not metrics_list:
                # Return default values if no data
                return self._get_default_collective_intelligence_response(
                    workspace_id, start_date, end_date
                )

            # Calculate aggregate metrics
            diversity_index = np.mean([m.diversity_index for m in metrics_list if m.diversity_index])
            collective_accuracy = np.mean([m.collective_accuracy for m in metrics_list if m.collective_accuracy])
            emergence_score = np.mean([m.emergence_score for m in metrics_list if m.emergence_score])
            adaptation_rate = np.mean([m.adaptation_rate for m in metrics_list if m.adaptation_rate])

            # Calculate synergy factor (simplified)
            synergy_factor = (diversity_index + collective_accuracy + emergence_score) / 3

            response = {
                "workspace_id": workspace_id,
                "analysis_period": {
                    "start": start_date,
                    "end": end_date,
                },
                "metrics": {
                    "diversity_index": float(diversity_index) if not np.isnan(diversity_index) else 0.0,
                    "collective_accuracy": float(collective_accuracy) if not np.isnan(collective_accuracy) else 0.0,
                    "emergence_score": float(emergence_score) if not np.isnan(emergence_score) else 0.0,
                    "adaptation_rate": float(adaptation_rate) if not np.isnan(adaptation_rate) else 0.0,
                    "synergy_factor": float(synergy_factor) if not np.isnan(synergy_factor) else 0.0,
                    "decision_quality": 0.0,  # Would be calculated from decision outcomes
                    "consensus_efficiency": 0.0,  # Would be calculated from consensus metrics
                    "collective_learning_rate": 0.0,  # Would be calculated from learning metrics
                },
                "agent_contributions": [],  # Would be populated from agent-level metrics
                "emergent_capabilities": [],  # Would be detected through analysis
                "emergence_score": float(emergence_score) if not np.isnan(emergence_score) else 0.0,
                "synergy_factor": float(synergy_factor) if not np.isnan(synergy_factor) else 0.0,
                "decision_quality_metrics": {},
                "consensus_metrics": {},
                "collective_learning_rate": 0.0,
                "adaptation_metrics": {},
            }

            return response

        except Exception as e:
            logger.error(f"Error getting collective intelligence metrics: {e}")
            raise

    def _get_default_collective_intelligence_response(
        self, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get default collective intelligence response when no data is available."""
        return {
            "workspace_id": workspace_id,
            "analysis_period": {
                "start": start_date,
                "end": end_date,
            },
            "metrics": {
                "diversity_index": 0.0,
                "collective_accuracy": 0.0,
                "emergence_score": 0.0,
                "adaptation_rate": 0.0,
                "synergy_factor": 0.0,
                "decision_quality": 0.0,
                "consensus_efficiency": 0.0,
                "collective_learning_rate": 0.0,
            },
            "agent_contributions": [],
            "emergent_capabilities": [],
            "emergence_score": 0.0,
            "synergy_factor": 0.0,
            "decision_quality_metrics": {},
            "consensus_metrics": {},
            "collective_learning_rate": 0.0,
            "adaptation_metrics": {},
        }
