"""Real-time metrics service for WebSocket streaming."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
import logging

logger = logging.getLogger(__name__)


class RealtimeMetricsService:
    """Service for fetching real-time metrics for WebSocket streaming."""

    @staticmethod
    async def get_active_users_count(
        db: AsyncSession, workspace_id: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get count of active users in real-time.

        Args:
            db: Database session
            workspace_id: Workspace ID
            filters: Optional filters (agent_id, timeframe, etc.)

        Returns:
            Dictionary with active users metrics
        """
        try:
            # Get active users in last 5 minutes
            since = datetime.utcnow() - timedelta(minutes=5)

            query = text(
                """
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND started_at >= :since
                """
            )

            params = {"workspace_id": workspace_id, "since": since}

            # Add agent filter if provided
            if filters and filters.get("agent_id"):
                query = text(
                    """
                    SELECT COUNT(DISTINCT user_id) as active_users
                    FROM execution_logs
                    WHERE workspace_id = :workspace_id
                    AND agent_id = :agent_id
                    AND started_at >= :since
                    """
                )
                params["agent_id"] = filters["agent_id"]

            result = await db.execute(query, params)
            row = result.fetchone()

            return {
                "active_users": row[0] if row else 0,
                "timeframe": "5m",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching active users: {e}")
            return {"active_users": 0, "error": str(e)}

    @staticmethod
    async def get_credits_consumed(
        db: AsyncSession, workspace_id: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get credits consumed in real-time.

        Args:
            db: Database session
            workspace_id: Workspace ID
            filters: Optional filters

        Returns:
            Dictionary with credits consumed metrics
        """
        try:
            # Get credits consumed in last hour
            since = datetime.utcnow() - timedelta(hours=1)

            query = text(
                """
                SELECT
                    COALESCE(SUM(credits_consumed), 0) as total_credits,
                    COUNT(*) as execution_count
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND started_at >= :since
                """
            )

            result = await db.execute(
                query, {"workspace_id": workspace_id, "since": since}
            )
            row = result.fetchone()

            return {
                "credits_consumed": float(row[0]) if row else 0.0,
                "execution_count": row[1] if row else 0,
                "timeframe": "1h",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching credits consumed: {e}")
            return {"credits_consumed": 0.0, "error": str(e)}

    @staticmethod
    async def get_error_rate(
        db: AsyncSession, workspace_id: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get error rate in real-time.

        Args:
            db: Database session
            workspace_id: Workspace ID
            filters: Optional filters

        Returns:
            Dictionary with error rate metrics
        """
        try:
            # Get error rate in last 15 minutes
            since = datetime.utcnow() - timedelta(minutes=15)

            query = text(
                """
                SELECT
                    COUNT(*) as total_executions,
                    COUNT(*) FILTER (WHERE success = false) as failed_executions
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND started_at >= :since
                """
            )

            result = await db.execute(
                query, {"workspace_id": workspace_id, "since": since}
            )
            row = result.fetchone()

            total = row[0] if row else 0
            failed = row[1] if row else 0
            error_rate = (failed / total * 100) if total > 0 else 0.0

            return {
                "error_rate": round(error_rate, 2),
                "total_executions": total,
                "failed_executions": failed,
                "timeframe": "15m",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching error rate: {e}")
            return {"error_rate": 0.0, "error": str(e)}

    @staticmethod
    async def get_agent_performance(
        db: AsyncSession, workspace_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """
        Get real-time agent performance metrics.

        Args:
            db: Database session
            workspace_id: Workspace ID
            agent_id: Agent ID

        Returns:
            Dictionary with agent performance metrics
        """
        try:
            # Get metrics for last 30 minutes
            since = datetime.utcnow() - timedelta(minutes=30)

            query = text(
                """
                SELECT
                    COUNT(*) as executions,
                    COUNT(*) FILTER (WHERE success = true) as successful,
                    AVG(runtime_seconds) as avg_runtime,
                    COUNT(DISTINCT user_id) as active_users
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND agent_id = :agent_id
                AND started_at >= :since
                """
            )

            result = await db.execute(
                query, {"workspace_id": workspace_id, "agent_id": agent_id, "since": since}
            )
            row = result.fetchone()

            executions = row[0] if row else 0
            successful = row[1] if row else 0
            success_rate = (successful / executions * 100) if executions > 0 else 0.0

            return {
                "agent_id": agent_id,
                "executions": executions,
                "success_rate": round(success_rate, 1),
                "avg_response_time": round(float(row[2]), 2) if row and row[2] else 0.0,
                "active_users": row[3] if row else 0,
                "timeframe": "30m",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching agent performance: {e}")
            return {"agent_id": agent_id, "error": str(e)}

    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession, workspace_id: str
    ) -> Dict[str, Any]:
        """
        Get real-time dashboard summary.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Dictionary with dashboard summary
        """
        try:
            # Get summary for last hour
            since = datetime.utcnow() - timedelta(hours=1)

            query = text(
                """
                SELECT
                    COUNT(DISTINCT user_id) as active_users,
                    COALESCE(SUM(credits_consumed), 0) as credits_consumed,
                    COUNT(*) as total_executions,
                    COUNT(*) FILTER (WHERE success = true) as successful_executions,
                    AVG(runtime_seconds) as avg_runtime
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND started_at >= :since
                """
            )

            result = await db.execute(
                query, {"workspace_id": workspace_id, "since": since}
            )
            row = result.fetchone()

            total = row[2] if row else 0
            successful = row[3] if row else 0
            success_rate = (successful / total * 100) if total > 0 else 0.0

            return {
                "active_users": row[0] if row else 0,
                "credits_consumed": float(row[1]) if row else 0.0,
                "total_executions": total,
                "success_rate": round(success_rate, 1),
                "avg_runtime": round(float(row[4]), 2) if row and row[4] else 0.0,
                "timeframe": "1h",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching dashboard summary: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_execution_queue_status(
        db: AsyncSession, workspace_id: str
    ) -> Dict[str, Any]:
        """
        Get current execution queue status.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Dictionary with queue status
        """
        try:
            # Get currently running executions (last 5 minutes, no end time)
            since = datetime.utcnow() - timedelta(minutes=5)

            query = text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE completed_at IS NULL) as running,
                    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                AND started_at >= :since
                """
            )

            result = await db.execute(
                query, {"workspace_id": workspace_id, "since": since}
            )
            row = result.fetchone()

            return {
                "currently_running": row[0] if row else 0,
                "completed_recently": row[1] if row else 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching queue status: {e}")
            return {"currently_running": 0, "error": str(e)}
