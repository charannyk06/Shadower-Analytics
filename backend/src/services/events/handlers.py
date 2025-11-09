"""Event handlers for cache invalidation."""

from typing import Dict, Any
import logging

from ..cache.keys import CacheKeys
from ...core.redis import get_redis_client

logger = logging.getLogger(__name__)


class EventHandlers:
    """Event handlers for automatic cache invalidation."""

    @staticmethod
    async def on_agent_run_completed(event: Dict[str, Any]):
        """
        Handle agent run completion event.

        Invalidates cache for the agent and related workspace metrics.

        Args:
            event: Event data containing agent_id and workspace_id
        """
        agent_id = event.get("agent_id")
        workspace_id = event.get("workspace_id")

        if not agent_id or not workspace_id:
            logger.warning("Missing agent_id or workspace_id in agent run completed event")
            return

        try:
            redis_client = await get_redis_client()

            # Invalidate agent-specific cache
            agent_pattern = CacheKeys.get_agent_pattern(agent_id)
            deleted_agent = await redis_client.flush_pattern(agent_pattern)

            # Invalidate workspace executive dashboard
            exec_patterns = [
                CacheKeys.get_pattern(CacheKeys.EXECUTIVE_PREFIX, "dashboard", workspace_id, "*"),
                CacheKeys.get_pattern(CacheKeys.AGENT_PREFIX, "top", workspace_id, "*"),
                CacheKeys.get_pattern(CacheKeys.METRICS_PREFIX, "runs", workspace_id, "*"),
            ]

            total_deleted = deleted_agent
            for pattern in exec_patterns:
                deleted = await redis_client.flush_pattern(pattern)
                total_deleted += deleted

            logger.info(
                f"Agent run completed: Invalidated {total_deleted} cache entries "
                f"for agent {agent_id} and workspace {workspace_id}"
            )

        except Exception as e:
            logger.error(f"Failed to invalidate cache on agent run completed: {e}")

    @staticmethod
    async def on_agent_run_started(event: Dict[str, Any]):
        """
        Handle agent run started event.

        Updates real-time metrics cache.

        Args:
            event: Event data containing agent_id and workspace_id
        """
        agent_id = event.get("agent_id")
        workspace_id = event.get("workspace_id")

        if not agent_id or not workspace_id:
            return

        try:
            redis_client = await get_redis_client()

            # Invalidate real-time metrics (short TTL items)
            patterns = [
                CacheKeys.get_pattern(
                    CacheKeys.METRICS_PREFIX, "realtime", workspace_id, "*"
                ),
            ]

            total_deleted = 0
            for pattern in patterns:
                deleted = await redis_client.flush_pattern(pattern)
                total_deleted += deleted

            if total_deleted > 0:
                logger.info(
                    f"Agent run started: Invalidated {total_deleted} real-time cache entries"
                )

        except Exception as e:
            logger.error(f"Failed to invalidate cache on agent run started: {e}")

    @staticmethod
    async def on_user_activity(event: Dict[str, Any]):
        """
        Handle user activity event.

        Invalidates DAU/WAU/MAU and user-specific caches.

        Args:
            event: Event data containing user_id and workspace_id
        """
        user_id = event.get("user_id")
        workspace_id = event.get("workspace_id")

        if not user_id or not workspace_id:
            return

        try:
            redis_client = await get_redis_client()

            # Only invalidate active user metrics and user activity cache
            patterns = [
                CacheKeys.get_pattern(
                    CacheKeys.METRICS_PREFIX, "users", "active", workspace_id, "*"
                ),
                CacheKeys.get_pattern(CacheKeys.USER_PREFIX, "activity", user_id, "*"),
            ]

            total_deleted = 0
            for pattern in patterns:
                deleted = await redis_client.flush_pattern(pattern)
                total_deleted += deleted

            logger.debug(
                f"User activity: Invalidated {total_deleted} cache entries "
                f"for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to invalidate cache on user activity: {e}")

    @staticmethod
    async def on_workspace_updated(event: Dict[str, Any]):
        """
        Handle workspace update event.

        Invalidates all workspace-related caches.

        Args:
            event: Event data containing workspace_id
        """
        workspace_id = event.get("workspace_id")

        if not workspace_id:
            return

        try:
            redis_client = await get_redis_client()

            # Get all workspace patterns
            patterns = CacheKeys.get_workspace_pattern(workspace_id)

            total_deleted = 0
            for pattern in patterns:
                deleted = await redis_client.flush_pattern(pattern)
                total_deleted += deleted

            logger.info(
                f"Workspace updated: Invalidated {total_deleted} cache entries "
                f"for workspace {workspace_id}"
            )

        except Exception as e:
            logger.error(f"Failed to invalidate cache on workspace updated: {e}")

    @staticmethod
    async def on_credit_transaction(event: Dict[str, Any]):
        """
        Handle credit transaction event.

        Invalidates credit-related metrics cache.

        Args:
            event: Event data containing workspace_id
        """
        workspace_id = event.get("workspace_id")

        if not workspace_id:
            return

        try:
            redis_client = await get_redis_client()

            # Invalidate credit metrics
            patterns = [
                CacheKeys.get_pattern(CacheKeys.METRICS_PREFIX, "credits", workspace_id, "*"),
                CacheKeys.get_pattern(CacheKeys.EXECUTIVE_PREFIX, "dashboard", workspace_id, "*"),
            ]

            total_deleted = 0
            for pattern in patterns:
                deleted = await redis_client.flush_pattern(pattern)
                total_deleted += deleted

            logger.info(
                f"Credit transaction: Invalidated {total_deleted} cache entries "
                f"for workspace {workspace_id}"
            )

        except Exception as e:
            logger.error(f"Failed to invalidate cache on credit transaction: {e}")

    @staticmethod
    async def on_report_generated(event: Dict[str, Any]):
        """
        Handle report generation event.

        Caches the generated report.

        Args:
            event: Event data containing report_id and data
        """
        report_id = event.get("report_id")
        report_data = event.get("data")
        report_format = event.get("format", "json")

        if not report_id or not report_data:
            return

        try:
            redis_client = await get_redis_client()

            # Cache the report with longer TTL
            key = CacheKeys.report_data(report_id, report_format)
            await redis_client.set(key, report_data, expire=CacheKeys.TTL_DAY)

            logger.info(f"Cached generated report: {report_id} ({report_format})")

        except Exception as e:
            logger.error(f"Failed to cache generated report: {e}")
