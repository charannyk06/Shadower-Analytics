"""Event broadcasting for WebSocket clients."""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .manager import manager

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Broadcast events to WebSocket clients."""

    @staticmethod
    async def broadcast_execution_started(
        workspace_id: str, agent_id: str, run_id: str, user_id: str
    ):
        """Broadcast when agent execution starts."""
        message = {
            "event": "execution_started",
            "data": {
                "agent_id": agent_id,
                "run_id": run_id,
                "user_id": user_id,
                "started_at": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted execution_started for run {run_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_execution_completed(
        workspace_id: str,
        agent_id: str,
        run_id: str,
        success: bool,
        runtime_seconds: float,
        credits_consumed: float,
    ):
        """Broadcast when agent execution completes."""
        message = {
            "event": "execution_completed",
            "data": {
                "agent_id": agent_id,
                "run_id": run_id,
                "success": success,
                "runtime_seconds": runtime_seconds,
                "credits_consumed": credits_consumed,
                "completed_at": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted execution_completed for run {run_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_metrics_update(
        workspace_id: str, metrics: Dict[str, Any]
    ):
        """Broadcast metrics update."""
        message = {
            "event": "metrics_update",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(f"Broadcasted metrics_update to workspace {workspace_id}")

    @staticmethod
    async def broadcast_execution_update(
        workspace_id: str, realtime_metrics: Dict[str, Any]
    ):
        """Broadcast real-time execution metrics update.

        Args:
            workspace_id: Target workspace
            realtime_metrics: Real-time execution metrics (currently running, queue depth, etc.)
        """
        message = {
            "event": "execution_update",
            "data": realtime_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(f"Broadcasted execution_update to workspace {workspace_id}")

    @staticmethod
    async def broadcast_alert(
        workspace_id: str, alert_type: str, alert_data: Dict[str, Any]
    ):
        """Broadcast alert notification."""
        message = {
            "event": "alert",
            "data": {"type": alert_type, **alert_data},
            "timestamp": datetime.utcnow().isoformat(),
            "priority": alert_data.get("priority", "medium"),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.info(
            f"Broadcasted {alert_type} alert to workspace {workspace_id} with priority {message['priority']}"
        )

    @staticmethod
    async def broadcast_agent_status_change(
        workspace_id: str,
        agent_id: str,
        old_status: str,
        new_status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Broadcast when an agent's status changes."""
        message = {
            "event": "agent_status_change",
            "data": {
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status,
                "metadata": metadata or {},
                "changed_at": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted agent_status_change for agent {agent_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_workspace_update(
        workspace_id: str, update_type: str, update_data: Dict[str, Any]
    ):
        """Broadcast general workspace update."""
        message = {
            "event": "workspace_update",
            "data": {"type": update_type, **update_data},
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted workspace_update ({update_type}) to workspace {workspace_id}"
        )


# Global instance
broadcaster = EventBroadcaster()
