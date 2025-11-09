"""Comprehensive workspace analytics service with proper error handling, caching, and logging."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from ..cache import cached, CacheKeys
from .constants import (
    TIMEFRAME_24H,
    TIMEFRAME_7D,
    TIMEFRAME_30D,
    TIMEFRAME_90D,
    MAX_QUERY_LIMIT,
    DEFAULT_PAGE_SIZE,
)

logger = logging.getLogger(__name__)


class WorkspaceAnalyticsConstants:
    """Constants for workspace analytics calculations."""

    # Activity thresholds for engagement levels
    ACTIVE_MEMBER_DAYS = 7
    ENGAGEMENT_HIGH_THRESHOLD = 50  # actions per week
    ENGAGEMENT_MEDIUM_THRESHOLD = 20  # actions per week

    # Health score weights
    HEALTH_WEIGHT_SUCCESS_RATE = 0.3
    HEALTH_WEIGHT_ACTIVITY = 0.25
    HEALTH_WEIGHT_ENGAGEMENT = 0.25
    HEALTH_WEIGHT_EFFICIENCY = 0.2

    # Limits for large result sets
    MAX_MEMBERS_LIMIT = 100
    MAX_DAILY_CONSUMPTION_DAYS = 90
    TOP_MEMBERS_LIMIT = 50

    # Default efficiency score when no runs
    DEFAULT_EFFICIENCY_SCORE = 100


class WorkspaceAnalyticsService:
    """Service for comprehensive workspace-level analytics."""

    def __init__(self, db: AsyncSession):
        """
        Initialize workspace analytics service.

        Args:
            db: Async database session
        """
        self.db = db
        logger.info("WorkspaceAnalyticsService initialized")

    @cached(
        key_func=lambda self, workspace_id, timeframe="30d", **kwargs:
            CacheKeys.workspace_analytics(workspace_id, timeframe),
        ttl=CacheKeys.TTL_MEDIUM
    )
    async def get_workspace_analytics(
        self,
        workspace_id: str,
        timeframe: str = "30d",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a workspace.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period (24h, 7d, 30d, 90d, all)
            user_id: Optional user ID for access control (validated at route level)

        Returns:
            Dictionary containing comprehensive workspace analytics

        Raises:
            ValueError: If workspace not found or invalid parameters
            SQLAlchemyError: If database operation fails
        """
        start_time = datetime.utcnow()
        logger.info(
            f"Fetching workspace analytics for workspace_id={workspace_id}, "
            f"timeframe={timeframe}"
        )

        try:
            end_date = datetime.utcnow()
            start_date = self._calculate_start_date(timeframe)

            # Parallel fetch all metrics for performance
            results = await asyncio.gather(
                self._get_workspace_overview(workspace_id, start_date, end_date),
                self._get_member_analytics(workspace_id, start_date, end_date),
                self._get_agent_usage(workspace_id, start_date, end_date),
                self._get_resource_consumption(workspace_id, start_date, end_date),
                self._get_activity_trends(workspace_id, start_date, end_date),
                return_exceptions=True,
            )

            # Handle any errors in parallel execution
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error in analytics component {i} for workspace {workspace_id}: {result}",
                        exc_info=result,
                    )
                    results[i] = {}

            overview, member_analytics, agent_usage, resource_consumption, activity_trends = results

            # Calculate health score
            health_score = self._calculate_health_score(overview, member_analytics, agent_usage)

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Workspace analytics completed for workspace_id={workspace_id} "
                f"in {duration:.2f}s"
            )

            return {
                "workspaceId": workspace_id,
                "timeframe": timeframe,
                "generatedAt": datetime.utcnow().isoformat(),
                "healthScore": health_score,
                "overview": overview,
                "memberAnalytics": member_analytics,
                "agentUsage": agent_usage,
                "resourceConsumption": resource_consumption,
                "activityTrends": activity_trends,
            }

        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching workspace analytics for workspace_id={workspace_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching workspace analytics for workspace_id={workspace_id}: {e}",
                exc_info=True,
            )
            raise

    async def _get_workspace_overview(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get workspace overview metrics.

        Args:
            workspace_id: Workspace identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary containing overview metrics
        """
        try:
            # Get basic workspace info
            workspace_query = text("""
                SELECT
                    workspace_id,
                    workspace_name,
                    created_at,
                    (SELECT COUNT(*) FROM public.workspace_members WHERE workspace_id = :workspace_id) as total_members,
                    (SELECT COUNT(*) FROM public.workspace_members
                     WHERE workspace_id = :workspace_id
                     AND last_active_at >= NOW() - INTERVAL '7 days') as active_members
                FROM public.workspaces
                WHERE workspace_id = :workspace_id
            """)

            result = await self.db.execute(workspace_query, {"workspace_id": workspace_id})
            workspace_data = result.fetchone()

            if not workspace_data:
                logger.warning(f"Workspace {workspace_id} not found")
                raise ValueError(f"Workspace {workspace_id} not found")

            # Get activity stats
            activity_query = text("""
                SELECT
                    COUNT(*) as total_activity,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(DISTINCT DATE(created_at)) as active_days
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND created_at BETWEEN :start_date AND :end_date
            """)

            activity_result = await self.db.execute(
                activity_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            activity_data = activity_result.fetchone()

            # Get agent run stats
            runs_query = text("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
                    AVG(runtime_seconds) as avg_runtime
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at BETWEEN :start_date AND :end_date
            """)

            runs_result = await self.db.execute(
                runs_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            runs_data = runs_result.fetchone()

            # Safe defaults with null handling
            total_members = workspace_data.total_members or 0
            active_members = workspace_data.active_members or 0
            total_activity = activity_data.total_activity if activity_data else 0
            total_runs = runs_data.total_runs if runs_data else 0
            successful_runs = runs_data.successful_runs if runs_data else 0
            failed_runs = runs_data.failed_runs if runs_data else 0

            success_rate = (
                round((successful_runs / total_runs * 100), 2) if total_runs > 0 else 0.0
            )

            return {
                "workspaceName": workspace_data.workspace_name or "",
                "createdAt": workspace_data.created_at.isoformat() if workspace_data.created_at else None,
                "totalMembers": total_members,
                "activeMembers": active_members,
                "memberActivityRate": round((active_members / total_members * 100), 2) if total_members > 0 else 0.0,
                "totalActivity": total_activity,
                "totalRuns": total_runs,
                "successfulRuns": successful_runs,
                "failedRuns": failed_runs,
                "successRate": success_rate,
                "avgRuntime": round(float(runs_data.avg_runtime or 0), 2) if runs_data else 0.0,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error in _get_workspace_overview: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in _get_workspace_overview: {e}")
            return self._get_empty_overview()

    async def _get_member_analytics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get member activity analytics with pagination support.

        Args:
            workspace_id: Workspace identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary containing member analytics
        """
        try:
            # Get member activity distribution (limited to prevent performance issues)
            member_query = text("""
                SELECT
                    user_id,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    MAX(created_at) as last_activity
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND created_at BETWEEN :start_date AND :end_date
                GROUP BY user_id
                ORDER BY activity_count DESC
                LIMIT :limit
            """)

            member_result = await self.db.execute(
                member_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": WorkspaceAnalyticsConstants.MAX_MEMBERS_LIMIT,
                },
            )

            members = []
            engagement_levels = {"high": 0, "medium": 0, "low": 0}

            for row in member_result.fetchall():
                activity_count = row.activity_count or 0

                # Determine engagement level
                if activity_count >= WorkspaceAnalyticsConstants.ENGAGEMENT_HIGH_THRESHOLD:
                    engagement = "high"
                    engagement_levels["high"] += 1
                elif activity_count >= WorkspaceAnalyticsConstants.ENGAGEMENT_MEDIUM_THRESHOLD:
                    engagement = "medium"
                    engagement_levels["medium"] += 1
                else:
                    engagement = "low"
                    engagement_levels["low"] += 1

                members.append({
                    "userId": str(row.user_id),
                    "activityCount": activity_count,
                    "activeDays": row.active_days or 0,
                    "lastActivity": row.last_activity.isoformat() if row.last_activity else None,
                    "engagement": engagement,
                })

            return {
                "topMembers": members[:WorkspaceAnalyticsConstants.TOP_MEMBERS_LIMIT],
                "engagementLevels": engagement_levels,
                "totalAnalyzed": len(members),
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error in _get_member_analytics: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in _get_member_analytics: {e}")
            return {"topMembers": [], "engagementLevels": {"high": 0, "medium": 0, "low": 0}, "totalAnalyzed": 0}

    async def _get_agent_usage(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get agent usage analytics.

        Args:
            workspace_id: Workspace identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary containing agent usage metrics
        """
        try:
            agent_query = text("""
                SELECT
                    COUNT(DISTINCT agent_id) as total_agents,
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                    AVG(runtime_seconds) as avg_runtime,
                    SUM(credits_consumed) as total_credits
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at BETWEEN :start_date AND :end_date
            """)

            result = await self.db.execute(
                agent_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            row = result.fetchone()

            if not row:
                return self._get_empty_agent_usage()

            total_runs = row.total_runs or 0
            successful_runs = row.successful_runs or 0

            # Calculate efficiency score with safe division
            efficiency_score = (
                int((successful_runs / total_runs * 100))
                if total_runs > 0
                else WorkspaceAnalyticsConstants.DEFAULT_EFFICIENCY_SCORE
            )

            return {
                "totalAgents": row.total_agents or 0,
                "totalRuns": total_runs,
                "successfulRuns": successful_runs,
                "successRate": round((successful_runs / total_runs * 100), 2) if total_runs > 0 else 0.0,
                "avgRuntime": round(float(row.avg_runtime or 0), 2),
                "totalCredits": round(float(row.total_credits or 0), 2),
                "efficiencyScore": efficiency_score,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error in _get_agent_usage: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in _get_agent_usage: {e}")
            return self._get_empty_agent_usage()

    async def _get_resource_consumption(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get resource consumption metrics with limit on historical data.

        Args:
            workspace_id: Workspace identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary containing resource consumption data
        """
        try:
            # Limit to last 90 days to prevent memory issues
            limited_start_date = max(
                start_date,
                end_date - timedelta(days=WorkspaceAnalyticsConstants.MAX_DAILY_CONSUMPTION_DAYS)
            )

            consumption_query = text("""
                SELECT
                    DATE(created_at) as date,
                    SUM(credits_consumed) as daily_credits,
                    COUNT(*) as daily_runs
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at BETWEEN :start_date AND :end_date
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT :limit
            """)

            result = await self.db.execute(
                consumption_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": limited_start_date,
                    "end_date": end_date,
                    "limit": WorkspaceAnalyticsConstants.MAX_DAILY_CONSUMPTION_DAYS,
                },
            )

            daily_data = [
                {
                    "date": row.date.isoformat(),
                    "credits": round(float(row.daily_credits or 0), 2),
                    "runs": row.daily_runs or 0,
                }
                for row in result.fetchall()
            ]

            total_credits = sum(d["credits"] for d in daily_data)
            avg_daily_credits = round(total_credits / len(daily_data), 2) if daily_data else 0.0

            return {
                "dailyConsumption": daily_data,
                "totalCredits": round(total_credits, 2),
                "avgDailyCredits": avg_daily_credits,
                "daysAnalyzed": len(daily_data),
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error in _get_resource_consumption: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in _get_resource_consumption: {e}")
            return {"dailyConsumption": [], "totalCredits": 0.0, "avgDailyCredits": 0.0, "daysAnalyzed": 0}

    async def _get_activity_trends(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get workspace activity trends over time.

        Args:
            workspace_id: Workspace identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary containing activity trend data
        """
        try:
            trends_query = text("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as total_activities,
                    COUNT(DISTINCT user_id) as active_users
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND created_at BETWEEN :start_date AND :end_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """)

            result = await self.db.execute(
                trends_query,
                {
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

            trends = [
                {
                    "date": row.date.isoformat(),
                    "activities": row.total_activities or 0,
                    "activeUsers": row.active_users or 0,
                }
                for row in result.fetchall()
            ]

            return {"trends": trends}

        except SQLAlchemyError as e:
            logger.error(f"Database error in _get_activity_trends: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in _get_activity_trends: {e}")
            return {"trends": []}

    def _calculate_health_score(
        self,
        overview: Dict[str, Any],
        member_analytics: Dict[str, Any],
        agent_usage: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate workspace health score based on multiple factors.

        Args:
            overview: Overview metrics
            member_analytics: Member analytics data
            agent_usage: Agent usage metrics

        Returns:
            Dictionary containing health score and components
        """
        try:
            # Success rate component (0-100)
            success_rate = overview.get("successRate", 0)
            success_component = success_rate

            # Activity component (0-100)
            activity_rate = overview.get("memberActivityRate", 0)
            activity_component = min(activity_rate, 100)

            # Engagement component (0-100)
            engagement_levels = member_analytics.get("engagementLevels", {})
            total_members = sum(engagement_levels.values())
            high_engagement = engagement_levels.get("high", 0)
            engagement_component = (
                (high_engagement / total_members * 100) if total_members > 0 else 0
            )

            # Efficiency component (0-100)
            efficiency_component = agent_usage.get("efficiencyScore", 0)

            # Weighted health score
            health_score = (
                success_component * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_SUCCESS_RATE
                + activity_component * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ACTIVITY
                + engagement_component * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ENGAGEMENT
                + efficiency_component * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_EFFICIENCY
            )

            return {
                "overall": round(health_score, 1),
                "components": {
                    "successRate": round(success_component, 1),
                    "activity": round(activity_component, 1),
                    "engagement": round(engagement_component, 1),
                    "efficiency": round(efficiency_component, 1),
                },
            }

        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return {"overall": 0.0, "components": {"successRate": 0.0, "activity": 0.0, "engagement": 0.0, "efficiency": 0.0}}

    def _calculate_start_date(self, timeframe: str) -> datetime:
        """
        Calculate start date based on timeframe string.

        Args:
            timeframe: Timeframe string (24h, 7d, 30d, 90d, all)

        Returns:
            Start datetime
        """
        now = datetime.utcnow()

        timeframe_map = {
            "24h": timedelta(days=TIMEFRAME_24H),
            "7d": timedelta(days=TIMEFRAME_7D),
            "30d": timedelta(days=TIMEFRAME_30D),
            "90d": timedelta(days=TIMEFRAME_90D),
            "all": timedelta(days=365 * 10),
        }

        return now - timeframe_map.get(timeframe, timedelta(days=TIMEFRAME_30D))

    # Helper methods for empty data structures
    def _get_empty_overview(self) -> Dict[str, Any]:
        """Return empty overview structure."""
        return {
            "workspaceName": "",
            "createdAt": None,
            "totalMembers": 0,
            "activeMembers": 0,
            "memberActivityRate": 0.0,
            "totalActivity": 0,
            "totalRuns": 0,
            "successfulRuns": 0,
            "failedRuns": 0,
            "successRate": 0.0,
            "avgRuntime": 0.0,
        }

    def _get_empty_agent_usage(self) -> Dict[str, Any]:
        """Return empty agent usage structure."""
        return {
            "totalAgents": 0,
            "totalRuns": 0,
            "successfulRuns": 0,
            "successRate": 0.0,
            "avgRuntime": 0.0,
            "totalCredits": 0.0,
            "efficiencyScore": WorkspaceAnalyticsConstants.DEFAULT_EFFICIENCY_SCORE,
        }
