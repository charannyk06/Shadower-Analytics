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

    @staticmethod
    async def broadcast_dashboard_update(
        workspace_id: str, section: str, data: Dict[str, Any]
    ):
        """
        Broadcast dashboard update.

        Args:
            workspace_id: Target workspace
            section: Dashboard section being updated
            data: Updated data
        """
        message = {
            "type": "dashboard_update",
            "section": section,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted dashboard_update ({section}) to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_alert_notification(
        workspace_id: str,
        severity: str,
        title: str,
        message: str,
        metric: str,
        value: float,
        threshold: float,
        alert_id: str,
    ):
        """
        Broadcast alert notification.

        Args:
            workspace_id: Target workspace
            severity: Alert severity (critical, warning, info)
            title: Alert title
            message: Alert message
            metric: Metric that triggered the alert
            value: Current metric value
            threshold: Threshold that was exceeded
            alert_id: Unique alert identifier
        """
        alert_message = {
            "type": "alert",
            "severity": severity,
            "title": title,
            "message": message,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "alert_id": alert_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, alert_message)
        logger.info(
            f"Broadcasted alert ({severity}) to workspace {workspace_id}: {title}"
        )

    @staticmethod
    async def broadcast_user_event(
        workspace_id: str,
        event: str,
        user_id: str,
        agent_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Broadcast user activity event.

        Args:
            workspace_id: Target workspace
            event: Event type (execution_started, execution_completed, etc.)
            user_id: User who triggered the event
            agent_id: Optional agent ID
            execution_id: Optional execution ID
            metadata: Optional additional metadata
        """
        message = {
            "type": "user_event",
            "event": event,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if agent_id:
            message["agent_id"] = agent_id
        if execution_id:
            message["execution_id"] = execution_id
        if metadata:
            message["metadata"] = metadata

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(f"Broadcasted user_event ({event}) to workspace {workspace_id}")

    @staticmethod
    async def broadcast_agent_update(
        workspace_id: str, agent_id: str, metrics: Dict[str, Any]
    ):
        """
        Broadcast agent performance update.

        Args:
            workspace_id: Target workspace
            agent_id: Agent ID
            metrics: Agent metrics
        """
        message = {
            "type": "agent_update",
            "agent_id": agent_id,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted agent_update for agent {agent_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_execution_progress(
        workspace_id: str,
        execution_id: str,
        agent_id: str,
        current_step: str,
        steps_completed: int,
        steps_total: int,
        progress_percent: float,
    ):
        """
        Broadcast execution progress update.

        Args:
            workspace_id: Target workspace
            execution_id: Execution ID
            agent_id: Agent ID
            current_step: Current step name
            steps_completed: Number of steps completed
            steps_total: Total number of steps
            progress_percent: Progress percentage (0-100)
        """
        message = {
            "type": "execution_progress",
            "event": "execution.progress",
            "data": {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "current_step": current_step,
                "steps_completed": steps_completed,
                "steps_total": steps_total,
                "progress_percent": progress_percent,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted execution_progress for execution {execution_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_execution_failed(
        workspace_id: str,
        execution_id: str,
        agent_id: str,
        error_type: str,
        error_message: str,
        duration_ms: int,
    ):
        """
        Broadcast execution failure.

        Args:
            workspace_id: Target workspace
            execution_id: Execution ID
            agent_id: Agent ID
            error_type: Error type
            error_message: Error message
            duration_ms: Duration in milliseconds before failure
        """
        message = {
            "type": "execution_failed",
            "event": "execution.failed",
            "data": {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "error_type": error_type,
                "error_message": error_message,
                "duration_ms": duration_ms,
                "failed_at": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.info(
            f"Broadcasted execution_failed for execution {execution_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_execution_analytics_update(
        workspace_id: str,
        agent_id: str,
        analytics_summary: Dict[str, Any],
    ):
        """
        Broadcast execution analytics update.

        Args:
            workspace_id: Target workspace
            agent_id: Agent ID
            analytics_summary: Analytics summary data
        """
        message = {
            "type": "execution_analytics_update",
            "event": "execution.analytics_update",
            "data": {
                "agent_id": agent_id,
                **analytics_summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.debug(
            f"Broadcasted execution_analytics_update for agent {agent_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_performance_alert(
        workspace_id: str,
        agent_id: str,
        alert_type: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: str,
    ):
        """
        Broadcast performance alert.

        Args:
            workspace_id: Target workspace
            agent_id: Agent ID
            alert_type: Alert type (e.g., 'duration_anomaly', 'high_failure_rate')
            metric_name: Metric name
            current_value: Current metric value
            threshold: Threshold value
            severity: Severity level (critical, high, medium, low)
        """
        message = {
            "type": "performance_alert",
            "event": "performance.alert",
            "data": {
                "agent_id": agent_id,
                "alert_type": alert_type,
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold,
                "severity": severity,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.warning(
            f"Broadcasted performance_alert ({alert_type}) for agent {agent_id} to workspace {workspace_id}"
        )

    @staticmethod
    async def broadcast_bottleneck_detected(
        workspace_id: str,
        agent_id: str,
        step_name: str,
        avg_duration_ms: int,
        impact_score: float,
        priority: str,
    ):
        """
        Broadcast bottleneck detection.

        Args:
            workspace_id: Target workspace
            agent_id: Agent ID
            step_name: Step name
            avg_duration_ms: Average duration in milliseconds
            impact_score: Impact score (0-100)
            priority: Priority level (critical, high, medium, low)
        """
        message = {
            "type": "bottleneck_detected",
            "event": "performance.bottleneck_detected",
            "data": {
                "agent_id": agent_id,
                "step_name": step_name,
                "avg_duration_ms": avg_duration_ms,
                "impact_score": impact_score,
                "priority": priority,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await manager.broadcast_to_workspace(workspace_id, message)
        logger.info(
            f"Broadcasted bottleneck_detected ({step_name}) for agent {agent_id} to workspace {workspace_id}"
        )


# Global instance
broadcaster = EventBroadcaster()
