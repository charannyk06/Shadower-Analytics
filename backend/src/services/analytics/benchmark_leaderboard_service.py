"""Benchmark leaderboard service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text

from ...models.database.tables import BenchmarkExecution, BenchmarkLeaderboard
from ...models.schemas.benchmarks import BenchmarkCategory

logger = logging.getLogger(__name__)


class BenchmarkLeaderboardService:
    """Service for generating and retrieving benchmark leaderboards."""

    def __init__(self, db: AsyncSession):
        """Initialize the leaderboard service."""
        self.db = db

    async def get_leaderboard(
        self,
        category: str = "overall",
        metric: str = "all",
        limit: int = 20,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get benchmark leaderboard.

        Args:
            category: Benchmark category to filter by
            metric: Specific metric or "all"
            limit: Maximum number of entries to return
            workspace_id: Optional workspace ID to filter by

        Returns:
            Dictionary containing leaderboard data
        """
        # First try to use materialized view
        try:
            return await self._get_leaderboard_from_view(
                category, metric, limit, workspace_id
            )
        except Exception as e:
            logger.warning(f"Failed to load from materialized view: {str(e)}")
            # Fallback to dynamic calculation
            return await self._calculate_leaderboard_dynamic(
                category, metric, limit, workspace_id
            )

    async def _get_leaderboard_from_view(
        self,
        category: str,
        metric: str,
        limit: int,
        workspace_id: Optional[str],
    ) -> Dict[str, Any]:
        """Get leaderboard data from materialized view."""
        query = select(BenchmarkLeaderboard)

        if category != "overall":
            query = query.where(BenchmarkLeaderboard.benchmark_category == category)

        if workspace_id:
            query = query.where(BenchmarkLeaderboard.workspace_id == workspace_id)

        # Order by specified metric or overall
        if metric == "accuracy":
            query = query.order_by(BenchmarkLeaderboard.accuracy_rank)
        elif metric == "speed":
            query = query.order_by(BenchmarkLeaderboard.speed_rank)
        elif metric == "efficiency":
            query = query.order_by(BenchmarkLeaderboard.efficiency_rank)
        elif metric == "cost":
            query = query.order_by(BenchmarkLeaderboard.cost_rank)
        elif metric == "reliability":
            query = query.order_by(BenchmarkLeaderboard.reliability_rank)
        else:
            query = query.order_by(BenchmarkLeaderboard.overall_rank)

        query = query.limit(limit)

        result = await self.db.execute(query)
        entries = result.scalars().all()

        return {
            "category": category,
            "metric": metric,
            "entries": [
                {
                    "agentId": e.agent_id,
                    "benchmarkCategory": e.benchmark_category,
                    "avgAccuracy": float(e.avg_accuracy) if e.avg_accuracy else None,
                    "avgSpeed": float(e.avg_speed) if e.avg_speed else None,
                    "avgEfficiency": float(e.avg_efficiency) if e.avg_efficiency else None,
                    "avgCost": float(e.avg_cost) if e.avg_cost else None,
                    "avgReliability": float(e.avg_reliability) if e.avg_reliability else None,
                    "avgOverall": float(e.avg_overall) if e.avg_overall else None,
                    "accuracyRank": e.accuracy_rank,
                    "speedRank": e.speed_rank,
                    "efficiencyRank": e.efficiency_rank,
                    "costRank": e.cost_rank,
                    "reliabilityRank": e.reliability_rank,
                    "overallRank": e.overall_rank,
                    "benchmarksCompleted": e.benchmarks_completed,
                }
                for e in entries
            ],
            "totalAgents": len(entries),
            "lastUpdated": datetime.utcnow().isoformat(),
        }

    async def _calculate_leaderboard_dynamic(
        self,
        category: str,
        metric: str,
        limit: int,
        workspace_id: Optional[str],
    ) -> Dict[str, Any]:
        """Calculate leaderboard dynamically from execution data."""
        # Get latest executions for each agent (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        subquery = (
            select(
                BenchmarkExecution.agent_id,
                BenchmarkExecution.benchmark_id,
                func.max(BenchmarkExecution.created_at).label("max_date"),
            )
            .where(
                and_(
                    BenchmarkExecution.status == "completed",
                    BenchmarkExecution.created_at >= cutoff_date,
                )
            )
            .group_by(BenchmarkExecution.agent_id, BenchmarkExecution.benchmark_id)
            .subquery()
        )

        # Calculate averages per agent
        query = (
            select(
                BenchmarkExecution.agent_id,
                func.avg(BenchmarkExecution.accuracy_score).label("avg_accuracy"),
                func.avg(BenchmarkExecution.speed_score).label("avg_speed"),
                func.avg(BenchmarkExecution.efficiency_score).label("avg_efficiency"),
                func.avg(BenchmarkExecution.cost_score).label("avg_cost"),
                func.avg(BenchmarkExecution.reliability_score).label("avg_reliability"),
                func.avg(BenchmarkExecution.overall_score).label("avg_overall"),
                func.count(func.distinct(BenchmarkExecution.benchmark_id)).label(
                    "benchmarks_completed"
                ),
            )
            .join(
                subquery,
                and_(
                    BenchmarkExecution.agent_id == subquery.c.agent_id,
                    BenchmarkExecution.benchmark_id == subquery.c.benchmark_id,
                    BenchmarkExecution.created_at == subquery.c.max_date,
                ),
            )
            .group_by(BenchmarkExecution.agent_id)
        )

        if workspace_id:
            query = query.where(BenchmarkExecution.workspace_id == workspace_id)

        # Order by specified metric
        if metric == "accuracy":
            query = query.order_by(desc("avg_accuracy"))
        elif metric == "speed":
            query = query.order_by(desc("avg_speed"))
        elif metric == "efficiency":
            query = query.order_by(desc("avg_efficiency"))
        elif metric == "cost":
            query = query.order_by(desc("avg_cost"))
        elif metric == "reliability":
            query = query.order_by(desc("avg_reliability"))
        else:
            query = query.order_by(desc("avg_overall"))

        query = query.limit(limit)

        result = await self.db.execute(query)
        rows = result.fetchall()

        # Assign ranks
        entries = []
        for rank, row in enumerate(rows, start=1):
            entries.append(
                {
                    "agentId": row.agent_id,
                    "benchmarkCategory": category,
                    "avgAccuracy": float(row.avg_accuracy) if row.avg_accuracy else None,
                    "avgSpeed": float(row.avg_speed) if row.avg_speed else None,
                    "avgEfficiency": float(row.avg_efficiency) if row.avg_efficiency else None,
                    "avgCost": float(row.avg_cost) if row.avg_cost else None,
                    "avgReliability": float(row.avg_reliability) if row.avg_reliability else None,
                    "avgOverall": float(row.avg_overall) if row.avg_overall else None,
                    "overallRank": rank,
                    "benchmarksCompleted": row.benchmarks_completed,
                }
            )

        return {
            "category": category,
            "metric": metric,
            "entries": entries,
            "totalAgents": len(entries),
            "lastUpdated": datetime.utcnow().isoformat(),
        }

    async def compare_agents(
        self,
        agent_ids: List[str],
        suite_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare multiple agents head-to-head.

        Args:
            agent_ids: List of agent IDs to compare
            suite_id: Optional suite ID to filter by

        Returns:
            Dictionary containing comparison results
        """
        if len(agent_ids) < 2:
            raise ValueError("At least 2 agents required for comparison")

        # Get latest benchmark results for each agent
        results_by_agent = {}

        for agent_id in agent_ids:
            query = (
                select(BenchmarkExecution)
                .where(
                    and_(
                        BenchmarkExecution.agent_id == agent_id,
                        BenchmarkExecution.status == "completed",
                    )
                )
                .order_by(desc(BenchmarkExecution.created_at))
                .limit(10)
            )

            if suite_id:
                query = query.where(BenchmarkExecution.suite_id == suite_id)

            result = await self.db.execute(query)
            executions = result.scalars().all()

            if executions:
                # Calculate averages
                results_by_agent[agent_id] = {
                    "avgAccuracy": sum(e.accuracy_score or 0 for e in executions)
                    / len(executions),
                    "avgSpeed": sum(e.speed_score or 0 for e in executions)
                    / len(executions),
                    "avgEfficiency": sum(e.efficiency_score or 0 for e in executions)
                    / len(executions),
                    "avgCost": sum(e.cost_score or 0 for e in executions)
                    / len(executions),
                    "avgReliability": sum(e.reliability_score or 0 for e in executions)
                    / len(executions),
                    "avgOverall": sum(e.overall_score or 0 for e in executions)
                    / len(executions),
                    "totalBenchmarks": len(executions),
                }

        # Determine winners for each category
        category_winners = {}
        metrics = ["avgAccuracy", "avgSpeed", "avgEfficiency", "avgCost", "avgReliability", "avgOverall"]

        for metric in metrics:
            scores = {
                agent_id: results.get(metric, 0)
                for agent_id, results in results_by_agent.items()
            }
            if scores:
                winner = max(scores, key=scores.get)
                category_winners[metric] = winner

        # Determine overall winner (most category wins)
        winner_counts = {}
        for winner in category_winners.values():
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        overall_winner = max(winner_counts, key=winner_counts.get) if winner_counts else None

        return {
            "agentIds": agent_ids,
            "overallWinner": overall_winner,
            "categoryWinners": category_winners,
            "detailedMetrics": results_by_agent,
            "comparisonType": "multi_agent" if len(agent_ids) > 2 else "head_to_head",
        }

    async def refresh_leaderboard_cache(self) -> Dict[str, Any]:
        """Refresh the benchmark leaderboard materialized view.

        Returns:
            Dictionary with refresh status
        """
        try:
            await self.db.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.benchmark_leaderboard")
            )
            await self.db.commit()

            return {
                "status": "success",
                "message": "Benchmark leaderboard cache refreshed",
                "refreshedAt": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to refresh leaderboard cache: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to refresh cache: {str(e)}",
            }
