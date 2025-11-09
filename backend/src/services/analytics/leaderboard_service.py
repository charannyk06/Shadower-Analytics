"""Leaderboard service for competitive rankings."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.dialects.postgresql import insert

from ...models.database.tables import (
    AgentLeaderboard,
    UserLeaderboard,
    WorkspaceLeaderboard,
)
from ...models.schemas.leaderboards import (
    TimeFrame,
    AgentCriteria,
    UserCriteria,
    WorkspaceCriteria,
    AgentLeaderboardQuery,
    UserLeaderboardQuery,
    WorkspaceLeaderboardQuery,
)
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class LeaderboardService:
    """Service for managing competitive rankings and leaderboards."""

    # Query timeout in seconds
    QUERY_TIMEOUT_SECONDS = 30

    # Caching configuration
    CACHE_TTL_SECONDS = {
        "24h": 300,  # 5 minutes
        "7d": 900,  # 15 minutes
        "30d": 1800,  # 30 minutes
        "90d": 3600,  # 1 hour
        "all": 7200,  # 2 hours
    }

    # Ranking thresholds
    MIN_RUNS_FOR_AGENT_RANKING = 5
    MIN_ACTIONS_FOR_USER_RANKING = 1
    MIN_ACTIVITY_FOR_WORKSPACE_RANKING = 10

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===================================================================
    # AGENT LEADERBOARD
    # ===================================================================

    async def get_agent_leaderboard(
        self,
        workspace_id: str,
        query: AgentLeaderboardQuery,
    ) -> Dict[str, Any]:
        """Get agent leaderboard rankings.

        Args:
            workspace_id: Workspace ID to filter by
            query: Query parameters (timeframe, criteria, limit, offset)

        Returns:
            Agent leaderboard data with rankings
        """
        try:
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid workspace ID: {str(e)}")

        # Try to get cached rankings first
        cached_rankings = await self._get_cached_agent_rankings(
            workspace_id,
            query.timeframe.value,
            query.criteria.value,
        )

        if cached_rankings:
            # Apply pagination to cached results
            start_idx = query.offset
            end_idx = query.offset + query.limit
            paginated = cached_rankings[start_idx:end_idx]

            return {
                "criteria": query.criteria.value,
                "timeframe": query.timeframe.value,
                "rankings": paginated,
                "total": len(cached_rankings),
                "offset": query.offset,
                "limit": query.limit,
                "cached": True,
                "calculatedAt": datetime.utcnow().isoformat(),
            }

        # Calculate fresh rankings
        rankings = await self._calculate_agent_rankings(
            workspace_id,
            query.timeframe,
            query.criteria,
        )

        # Store in cache
        await self._cache_agent_rankings(rankings, workspace_id, query.timeframe.value, query.criteria.value)

        # Apply pagination
        start_idx = query.offset
        end_idx = query.offset + query.limit
        paginated = rankings[start_idx:end_idx]

        return {
            "criteria": query.criteria.value,
            "timeframe": query.timeframe.value,
            "rankings": paginated,
            "total": len(rankings),
            "offset": query.offset,
            "limit": query.limit,
            "cached": False,
            "calculatedAt": datetime.utcnow().isoformat(),
        }

    async def _calculate_agent_rankings(
        self,
        workspace_id: str,
        timeframe: TimeFrame,
        criteria: AgentCriteria,
    ) -> List[Dict[str, Any]]:
        """Calculate agent rankings based on criteria."""

        start_date = calculate_start_date(timeframe.value)
        end_date = datetime.utcnow()

        # Build score calculation based on criteria
        score_formula = self._get_agent_score_formula(criteria)

        query = text(f"""
            WITH agent_metrics AS (
                SELECT
                    a.id AS agent_id,
                    a.name AS agent_name,
                    a.type AS agent_type,
                    a.workspace_id,
                    w.name AS workspace_name,
                    COUNT(ae.id) AS total_runs,
                    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
                    ROUND(AVG(ae.duration), 2) AS avg_runtime,
                    ROUND(AVG(ae.credits_used), 2) AS credits_per_run,
                    COUNT(DISTINCT ae.user_id) AS unique_users,
                    {score_formula} AS score
                FROM public.agents a
                LEFT JOIN public.agent_executions ae ON a.id = ae.agent_id
                    AND ae.created_at >= :start_date
                    AND ae.created_at <= :end_date
                    AND ae.deleted_at IS NULL
                LEFT JOIN public.workspaces w ON a.workspace_id = w.id
                WHERE a.workspace_id = :workspace_id
                    AND a.deleted_at IS NULL
                GROUP BY a.id, a.name, a.type, a.workspace_id, w.name
                HAVING COUNT(ae.id) >= :min_runs
            ),
            ranked_agents AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY score DESC, total_runs DESC) AS rank,
                    COUNT(*) OVER () AS total_count
                FROM agent_metrics
            )
            SELECT
                rank,
                agent_id,
                agent_name,
                agent_type,
                workspace_id,
                workspace_name,
                total_runs,
                success_rate,
                avg_runtime,
                credits_per_run,
                unique_users,
                score,
                ROUND(((total_count - rank + 1.0) / total_count * 100.0)::NUMERIC, 2) AS percentile,
                total_count
            FROM ranked_agents
            ORDER BY rank ASC
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
                "min_runs": self.MIN_RUNS_FOR_AGENT_RANKING,
            },
        )

        rows = result.fetchall()

        rankings = []
        for row in rows:
            # Determine badge
            badge = None
            if row.rank == 1:
                badge = "gold"
            elif row.rank == 2:
                badge = "silver"
            elif row.rank == 3:
                badge = "bronze"

            rankings.append({
                "rank": row.rank,
                "previousRank": None,  # Will be updated by background job
                "change": "new",
                "agent": {
                    "id": str(row.agent_id),
                    "name": row.agent_name,
                    "type": row.agent_type,
                    "workspace": row.workspace_name or "",
                },
                "metrics": {
                    "totalRuns": row.total_runs,
                    "successRate": float(row.success_rate or 0),
                    "avgRuntime": float(row.avg_runtime or 0),
                    "creditsPerRun": float(row.credits_per_run or 0),
                    "uniqueUsers": row.unique_users,
                },
                "score": float(row.score),
                "percentile": float(row.percentile),
                "badge": badge,
            })

        return rankings

    def _get_agent_score_formula(self, criteria: AgentCriteria) -> str:
        """Get SQL formula for calculating agent score based on criteria."""

        formulas = {
            AgentCriteria.RUNS: """
                (COUNT(ae.id) * 1.0)
            """,
            AgentCriteria.SUCCESS_RATE: """
                (
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.7) +
                    (LEAST(COUNT(ae.id), 100) * 0.3)
                )
            """,
            AgentCriteria.SPEED: """
                (
                    GREATEST(0, 100 - (COALESCE(AVG(ae.duration), 0) / 1000)) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.3)
                )
            """,
            AgentCriteria.EFFICIENCY: """
                (
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.4) +
                    (GREATEST(0, 100 - (COALESCE(AVG(ae.credits_used), 0) / 10)) * 0.3) +
                    (GREATEST(0, 100 - (COALESCE(AVG(ae.duration), 0) / 1000)) * 0.3)
                )
            """,
            AgentCriteria.POPULARITY: """
                (
                    (COUNT(DISTINCT ae.user_id) * 10.0) +
                    (COUNT(ae.id) * 0.5) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.2)
                )
            """,
        }

        return formulas.get(criteria, formulas[AgentCriteria.SUCCESS_RATE])

    async def _get_cached_agent_rankings(
        self,
        workspace_id: str,
        timeframe: str,
        criteria: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached agent rankings from database."""

        query = select(AgentLeaderboard).where(
            and_(
                AgentLeaderboard.workspace_id == workspace_id,
                AgentLeaderboard.timeframe == timeframe,
                AgentLeaderboard.criteria == criteria,
                AgentLeaderboard.calculated_at >= datetime.utcnow() - timedelta(seconds=self.CACHE_TTL_SECONDS.get(timeframe, 900)),
            )
        ).order_by(AgentLeaderboard.rank.asc())

        result = await self.db.execute(query)
        records = result.scalars().all()

        if not records:
            return None

        rankings = []
        for record in records:
            rankings.append({
                "rank": record.rank,
                "previousRank": record.previous_rank,
                "change": record.rank_change,
                "agent": {
                    "id": str(record.agent_id),
                    "name": "",  # Will be joined in production
                    "type": "",
                    "workspace": "",
                },
                "metrics": {
                    "totalRuns": record.total_runs,
                    "successRate": float(record.success_rate),
                    "avgRuntime": float(record.avg_runtime),
                    "creditsPerRun": float(record.credits_per_run),
                    "uniqueUsers": record.unique_users,
                },
                "score": float(record.score),
                "percentile": float(record.percentile),
                "badge": record.badge,
            })

        return rankings

    async def _cache_agent_rankings(
        self,
        rankings: List[Dict[str, Any]],
        workspace_id: str,
        timeframe: str,
        criteria: str,
    ):
        """Cache agent rankings to database."""

        for ranking in rankings:
            # Upsert ranking
            stmt = insert(AgentLeaderboard).values(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                agent_id=ranking["agent"]["id"],
                rank=ranking["rank"],
                previous_rank=ranking.get("previousRank"),
                rank_change=ranking["change"],
                timeframe=timeframe,
                criteria=criteria,
                total_runs=ranking["metrics"]["totalRuns"],
                success_rate=ranking["metrics"]["successRate"],
                avg_runtime=ranking["metrics"]["avgRuntime"],
                credits_per_run=ranking["metrics"]["creditsPerRun"],
                unique_users=ranking["metrics"]["uniqueUsers"],
                score=ranking["score"],
                percentile=ranking["percentile"],
                badge=ranking.get("badge"),
                calculated_at=datetime.utcnow(),
            ).on_conflict_do_update(
                constraint="unique_agent_leaderboard",
                set_={
                    "rank": ranking["rank"],
                    "score": ranking["score"],
                    "percentile": ranking["percentile"],
                    "total_runs": ranking["metrics"]["totalRuns"],
                    "success_rate": ranking["metrics"]["successRate"],
                    "avg_runtime": ranking["metrics"]["avgRuntime"],
                    "credits_per_run": ranking["metrics"]["creditsPerRun"],
                    "unique_users": ranking["metrics"]["uniqueUsers"],
                    "badge": ranking.get("badge"),
                    "calculated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )

            await self.db.execute(stmt)

        await self.db.commit()

    # ===================================================================
    # USER LEADERBOARD
    # ===================================================================

    async def get_user_leaderboard(
        self,
        workspace_id: str,
        query: UserLeaderboardQuery,
    ) -> Dict[str, Any]:
        """Get user leaderboard rankings.

        Args:
            workspace_id: Workspace ID to filter by
            query: Query parameters (timeframe, criteria, limit, offset)

        Returns:
            User leaderboard data with rankings
        """
        try:
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid workspace ID: {str(e)}")

        # Calculate fresh rankings
        rankings = await self._calculate_user_rankings(
            workspace_id,
            query.timeframe,
            query.criteria,
        )

        # Apply pagination
        start_idx = query.offset
        end_idx = query.offset + query.limit
        paginated = rankings[start_idx:end_idx]

        return {
            "criteria": query.criteria.value,
            "timeframe": query.timeframe.value,
            "rankings": paginated,
            "total": len(rankings),
            "offset": query.offset,
            "limit": query.limit,
            "calculatedAt": datetime.utcnow().isoformat(),
        }

    async def _calculate_user_rankings(
        self,
        workspace_id: str,
        timeframe: TimeFrame,
        criteria: UserCriteria,
    ) -> List[Dict[str, Any]]:
        """Calculate user rankings based on criteria."""

        start_date = calculate_start_date(timeframe.value)
        end_date = datetime.utcnow()

        score_formula = self._get_user_score_formula(criteria)

        query = text(f"""
            WITH user_metrics AS (
                SELECT
                    u.id AS user_id,
                    u.name AS user_name,
                    u.email AS user_email,
                    u.workspace_id,
                    w.name AS workspace_name,
                    COUNT(DISTINCT ae.id) AS total_actions,
                    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
                    COALESCE(SUM(ae.credits_used), 0) AS credits_used,
                    0 AS credits_saved,
                    COUNT(DISTINCT ae.agent_id) AS agents_used,
                    {score_formula} AS score
                FROM public.users u
                LEFT JOIN public.agent_executions ae ON u.id = ae.user_id
                    AND ae.created_at >= :start_date
                    AND ae.created_at <= :end_date
                    AND ae.deleted_at IS NULL
                LEFT JOIN public.workspaces w ON u.workspace_id = w.id
                WHERE u.workspace_id = :workspace_id
                    AND u.deleted_at IS NULL
                GROUP BY u.id, u.name, u.email, u.workspace_id, w.name
                HAVING COUNT(DISTINCT ae.id) >= :min_actions
            ),
            ranked_users AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY score DESC, total_actions DESC) AS rank,
                    COUNT(*) OVER () AS total_count
                FROM user_metrics
            )
            SELECT
                rank,
                user_id,
                user_name,
                user_email,
                workspace_id,
                workspace_name,
                total_actions,
                success_rate,
                credits_used,
                credits_saved,
                agents_used,
                score,
                ROUND(((total_count - rank + 1.0) / total_count * 100.0)::NUMERIC, 2) AS percentile,
                total_count
            FROM ranked_users
            ORDER BY rank ASC
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
                "min_actions": self.MIN_ACTIONS_FOR_USER_RANKING,
            },
        )

        rows = result.fetchall()

        rankings = []
        for row in rows:
            achievements = self._calculate_user_achievements(row)

            rankings.append({
                "rank": row.rank,
                "previousRank": None,
                "change": "new",
                "user": {
                    "id": str(row.user_id),
                    "name": row.user_name or "Unknown",
                    "avatar": None,
                    "workspace": row.workspace_name or "",
                },
                "metrics": {
                    "totalActions": row.total_actions,
                    "successRate": float(row.success_rate or 0),
                    "creditsUsed": float(row.credits_used or 0),
                    "creditsSaved": float(row.credits_saved or 0),
                    "agentsUsed": row.agents_used,
                },
                "score": float(row.score),
                "percentile": float(row.percentile),
                "achievements": achievements,
            })

        return rankings

    def _get_user_score_formula(self, criteria: UserCriteria) -> str:
        """Get SQL formula for calculating user score based on criteria."""

        formulas = {
            UserCriteria.ACTIVITY: """
                (
                    (COUNT(DISTINCT ae.id) * 1.0) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.5) +
                    (COUNT(DISTINCT ae.agent_id) * 5.0)
                )
            """,
            UserCriteria.EFFICIENCY: """
                (
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.6) +
                    (GREATEST(0, 100 - (COALESCE(SUM(ae.credits_used), 0) / NULLIF(COUNT(ae.id), 0) / 10)) * 0.4)
                )
            """,
            UserCriteria.CONTRIBUTION: """
                (
                    (COUNT(DISTINCT ae.id) * 0.5) +
                    (COUNT(DISTINCT ae.agent_id) * 10.0) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.3)
                )
            """,
            UserCriteria.SAVINGS: """
                (
                    (GREATEST(0, 1000 - COALESCE(SUM(ae.credits_used), 0)) * 0.1) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.3)
                )
            """,
        }

        return formulas.get(criteria, formulas[UserCriteria.ACTIVITY])

    def _calculate_user_achievements(self, row) -> List[str]:
        """Calculate user achievements based on metrics."""

        achievements = []

        if row.total_actions >= 100:
            achievements.append("Century Club")
        if row.success_rate >= 95:
            achievements.append("Perfectionist")
        if row.agents_used >= 10:
            achievements.append("Explorer")
        if row.rank <= 10:
            achievements.append("Top Performer")

        return achievements

    # ===================================================================
    # WORKSPACE LEADERBOARD
    # ===================================================================

    async def get_workspace_leaderboard(
        self,
        query: WorkspaceLeaderboardQuery,
    ) -> Dict[str, Any]:
        """Get workspace leaderboard rankings.

        Args:
            query: Query parameters (timeframe, criteria, limit, offset)

        Returns:
            Workspace leaderboard data with rankings
        """

        rankings = await self._calculate_workspace_rankings(
            query.timeframe,
            query.criteria,
        )

        # Apply pagination
        start_idx = query.offset
        end_idx = query.offset + query.limit
        paginated = rankings[start_idx:end_idx]

        return {
            "criteria": query.criteria.value,
            "timeframe": query.timeframe.value,
            "rankings": paginated,
            "total": len(rankings),
            "offset": query.offset,
            "limit": query.limit,
            "calculatedAt": datetime.utcnow().isoformat(),
        }

    async def _calculate_workspace_rankings(
        self,
        timeframe: TimeFrame,
        criteria: WorkspaceCriteria,
    ) -> List[Dict[str, Any]]:
        """Calculate workspace rankings based on criteria."""

        start_date = calculate_start_date(timeframe.value)
        end_date = datetime.utcnow()

        score_formula = self._get_workspace_score_formula(criteria)

        query = text(f"""
            WITH workspace_metrics AS (
                SELECT
                    w.id AS workspace_id,
                    w.name AS workspace_name,
                    w.plan,
                    (SELECT COUNT(*) FROM public.users WHERE workspace_id = w.id AND deleted_at IS NULL) AS member_count,
                    COUNT(DISTINCT ae.id) AS total_activity,
                    COUNT(DISTINCT ae.user_id) AS active_users,
                    COUNT(DISTINCT ae.agent_id) AS agent_count,
                    ROUND(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 2) AS success_rate,
                    ROUND(
                        (
                            (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.4) +
                            (LEAST(COUNT(DISTINCT ae.user_id), 100) * 0.5 * 0.3) +
                            (LEAST(COUNT(DISTINCT ae.agent_id), 50) * 1.0 * 0.3)
                        ), 2
                    ) AS health_score,
                    {score_formula} AS score
                FROM public.workspaces w
                LEFT JOIN public.agent_executions ae ON w.id = ae.workspace_id
                    AND ae.created_at >= :start_date
                    AND ae.created_at <= :end_date
                    AND ae.deleted_at IS NULL
                WHERE w.deleted_at IS NULL
                GROUP BY w.id, w.name, w.plan
                HAVING COUNT(DISTINCT ae.id) >= :min_activity
            ),
            ranked_workspaces AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY score DESC, total_activity DESC) AS rank,
                    COUNT(*) OVER () AS total_count
                FROM workspace_metrics
            )
            SELECT
                rank,
                workspace_id,
                workspace_name,
                plan,
                member_count,
                total_activity,
                active_users,
                agent_count,
                success_rate,
                health_score,
                score,
                ROUND(((total_count - rank + 1.0) / total_count * 100.0)::NUMERIC, 2) AS percentile,
                total_count
            FROM ranked_workspaces
            ORDER BY rank ASC
        """)

        result = await self.db.execute(
            query,
            {
                "start_date": start_date,
                "end_date": end_date,
                "min_activity": self.MIN_ACTIVITY_FOR_WORKSPACE_RANKING,
            },
        )

        rows = result.fetchall()

        rankings = []
        for row in rows:
            # Determine tier based on percentile
            percentile = float(row.percentile)
            if percentile >= 95:
                tier = "platinum"
            elif percentile >= 80:
                tier = "gold"
            elif percentile >= 60:
                tier = "silver"
            else:
                tier = "bronze"

            rankings.append({
                "rank": row.rank,
                "previousRank": None,
                "change": "new",
                "workspace": {
                    "id": str(row.workspace_id),
                    "name": row.workspace_name,
                    "plan": row.plan or "free",
                    "memberCount": row.member_count or 0,
                },
                "metrics": {
                    "totalActivity": row.total_activity,
                    "activeUsers": row.active_users,
                    "agentCount": row.agent_count,
                    "successRate": float(row.success_rate or 0),
                    "healthScore": float(row.health_score or 0),
                },
                "score": float(row.score),
                "tier": tier,
            })

        return rankings

    def _get_workspace_score_formula(self, criteria: WorkspaceCriteria) -> str:
        """Get SQL formula for calculating workspace score based on criteria."""

        formulas = {
            WorkspaceCriteria.ACTIVITY: """
                (
                    (COUNT(DISTINCT ae.id) * 0.1) +
                    (COUNT(DISTINCT ae.user_id) * 10.0) +
                    (COUNT(DISTINCT ae.agent_id) * 5.0) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 1.0)
                )
            """,
            WorkspaceCriteria.EFFICIENCY: """
                (
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.5) +
                    (LEAST(COUNT(DISTINCT ae.agent_id), 50) * 2.0) +
                    (LEAST(COUNT(DISTINCT ae.user_id), 100) * 1.0)
                )
            """,
            WorkspaceCriteria.GROWTH: """
                (
                    (COUNT(DISTINCT ae.user_id) * 10.0) +
                    (COUNT(DISTINCT ae.agent_id) * 5.0) +
                    (COUNT(DISTINCT ae.id) * 0.05)
                )
            """,
            WorkspaceCriteria.INNOVATION: """
                (
                    (COUNT(DISTINCT ae.agent_id) * 10.0) +
                    (COUNT(DISTINCT ae.user_id) * 5.0) +
                    (COALESCE(AVG(CASE WHEN ae.status = 'success' THEN 100.0 ELSE 0.0 END), 0) * 0.5)
                )
            """,
        }

        return formulas.get(criteria, formulas[WorkspaceCriteria.ACTIVITY])

    # ===================================================================
    # REFRESH AND MAINTENANCE
    # ===================================================================

    async def refresh_all_leaderboards(self, workspace_id: str):
        """Refresh all leaderboards for a workspace.

        This should be called periodically by a background job.
        """

        tasks = []

        # Agent leaderboards
        for timeframe in [TimeFrame.SEVEN_DAYS, TimeFrame.THIRTY_DAYS]:
            for criteria in AgentCriteria:
                query = AgentLeaderboardQuery(timeframe=timeframe, criteria=criteria)
                tasks.append(self.get_agent_leaderboard(workspace_id, query))

        # User leaderboards
        for timeframe in [TimeFrame.SEVEN_DAYS, TimeFrame.THIRTY_DAYS]:
            for criteria in UserCriteria:
                query = UserLeaderboardQuery(timeframe=timeframe, criteria=criteria)
                tasks.append(self.get_user_leaderboard(workspace_id, query))

        # Execute all in parallel
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Refreshed all leaderboards for workspace {workspace_id}")
