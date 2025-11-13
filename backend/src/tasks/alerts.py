"""Alert evaluation Celery tasks."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID

from celery import Task
from src.celery_app import celery_app
from src.core.database import async_session_maker
from src.services.alerts import AlertEngine
from src.core.config import settings
from sqlalchemy import select
from src.models.database.tables import AlertRule, Alert

logger = logging.getLogger(__name__)


class AsyncDatabaseTask(Task):
    """Base task class that provides async database session handling."""

    def run_async(self, async_func, *args, **kwargs):
        """Run an async function synchronously with proper cleanup."""
        try:
            return asyncio.run(async_func(*args, **kwargs))
        except RuntimeError:
            # Fallback for edge cases
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                try:
                    loop.close()
                finally:
                    asyncio.set_event_loop(None)


@celery_app.task(
    name='tasks.alerts.evaluate_alert_rules',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
)
def evaluate_alert_rules_task(self, workspace_id: Optional[str] = None) -> Dict:
    """
    Celery task for evaluating alert rules.

    Args:
        workspace_id: Optional workspace ID to evaluate rules for.
                     If None, evaluates all active workspaces.

    Returns:
        Dictionary with evaluation results
    """
    try:
        logger.info(f"Starting alert rule evaluation task for workspace: {workspace_id or 'all'}")

        async def run_evaluation():
            async with async_session_maker() as db:
                alert_engine = AlertEngine(db)

                if workspace_id:
                    # Evaluate for specific workspace
                    triggered_alerts = await alert_engine.evaluate_alert_rules(workspace_id)
                    return {
                        'success': True,
                        'workspace_id': workspace_id,
                        'triggered_alerts': len(triggered_alerts),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    # Get all workspaces with active alert rules
                    from sqlalchemy import distinct
                    stmt = select(distinct(AlertRule.workspace_id)).where(
                        AlertRule.is_active == True
                    )
                    result = await db.execute(stmt)
                    workspace_ids = result.scalars().all()

                    total_triggered = 0
                    results = []

                    for ws_id in workspace_ids:
                        try:
                            triggered = await alert_engine.evaluate_alert_rules(str(ws_id))
                            total_triggered += len(triggered)
                            results.append({
                                'workspace_id': str(ws_id),
                                'triggered_alerts': len(triggered)
                            })
                        except Exception as e:
                            logger.error(f"Error evaluating rules for workspace {ws_id}: {str(e)}")
                            results.append({
                                'workspace_id': str(ws_id),
                                'error': str(e)
                            })

                    return {
                        'success': True,
                        'workspaces_evaluated': len(workspace_ids),
                        'total_triggered_alerts': total_triggered,
                        'results': results,
                        'timestamp': datetime.now().isoformat()
                    }

        result = self.run_async(run_evaluation)
        logger.info(f"Alert rule evaluation completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Alert rule evaluation task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.alerts.check_escalations',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
    default_retry_delay=120,  # 2 minutes
)
def check_escalations_task(self) -> Dict:
    """
    Celery task for checking alert escalations.

    Checks all unacknowledged alerts to see if they need escalation.

    Returns:
        Dictionary with escalation results
    """
    try:
        logger.info("Starting alert escalation check task")

        async def check_escalations():
            async with async_session_maker() as db:
                # Get all unacknowledged, unresolved alerts
                stmt = select(Alert).where(
                    Alert.acknowledged_at.is_(None),
                    Alert.resolved_at.is_(None)
                )
                result = await db.execute(stmt)
                alerts = result.scalars().all()

                alert_engine = AlertEngine(db)
                escalations_performed = 0

                for alert in alerts:
                    try:
                        escalated = await alert_engine.check_escalation_needed(
                            str(alert.id),
                            str(alert.workspace_id)
                        )
                        if escalated:
                            escalations_performed += 1
                    except Exception as e:
                        logger.error(f"Error checking escalation for alert {alert.id}: {str(e)}")

                return {
                    'success': True,
                    'alerts_checked': len(alerts),
                    'escalations_performed': escalations_performed,
                    'timestamp': datetime.now().isoformat()
                }

        result = self.run_async(check_escalations)
        logger.info(f"Escalation check completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Escalation check task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.alerts.cleanup_old_alerts',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
)
def cleanup_old_alerts_task(self, retention_days: int = 90) -> Dict:
    """
    Celery task for cleaning up old resolved alerts.

    Args:
        retention_days: Number of days to retain resolved alerts (default: 90)

    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info(f"Starting alert cleanup task (retention: {retention_days} days)")

        async def cleanup_alerts():
            async with async_session_maker() as db:
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=retention_days)

                # Find old resolved alerts
                stmt = select(Alert).where(
                    Alert.resolved_at.isnot(None),
                    Alert.resolved_at < cutoff_date
                )
                result = await db.execute(stmt)
                old_alerts = result.scalars().all()

                # Delete old alerts
                for alert in old_alerts:
                    await db.delete(alert)

                await db.commit()

                return {
                    'success': True,
                    'alerts_deleted': len(old_alerts),
                    'cutoff_date': cutoff_date.isoformat(),
                    'timestamp': datetime.now().isoformat()
                }

        result = self.run_async(cleanup_alerts)
        logger.info(f"Alert cleanup completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Alert cleanup task failed: {str(exc)}", exc_info=True)
        await db.rollback()
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.alerts.send_alert_digest',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
    default_retry_delay=180,  # 3 minutes
)
def send_alert_digest_task(self, workspace_id: str, digest_type: str = 'daily') -> Dict:
    """
    Celery task for sending alert digests.

    Args:
        workspace_id: Workspace ID to send digest for
        digest_type: Type of digest ('daily', 'weekly')

    Returns:
        Dictionary with digest sending results
    """
    try:
        logger.info(f"Starting alert digest task for workspace {workspace_id} ({digest_type})")

        async def send_digest():
            async with async_session_maker() as db:
                # Calculate time window
                if digest_type == 'daily':
                    start_time = datetime.now() - timedelta(days=1)
                elif digest_type == 'weekly':
                    start_time = datetime.now() - timedelta(weeks=1)
                else:
                    start_time = datetime.now() - timedelta(days=1)

                # Get alerts in timeframe
                stmt = select(Alert).where(
                    Alert.workspace_id == UUID(workspace_id),
                    Alert.triggered_at >= start_time
                ).order_by(Alert.triggered_at.desc())

                result = await db.execute(stmt)
                alerts = result.scalars().all()

                if not alerts:
                    return {
                        'success': True,
                        'message': 'No alerts in digest period',
                        'alert_count': 0
                    }

                # Calculate digest stats
                total_alerts = len(alerts)
                resolved_count = len([a for a in alerts if a.resolved_at])
                acknowledged_count = len([a for a in alerts if a.acknowledged_at and not a.resolved_at])
                active_count = len([a for a in alerts if not a.acknowledged_at and not a.resolved_at])

                # Group by severity
                severity_counts = {}
                for alert in alerts:
                    severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

                digest_data = {
                    'workspace_id': workspace_id,
                    'digest_type': digest_type,
                    'period_start': start_time.isoformat(),
                    'period_end': datetime.now().isoformat(),
                    'stats': {
                        'total_alerts': total_alerts,
                        'resolved': resolved_count,
                        'acknowledged': acknowledged_count,
                        'active': active_count,
                        'by_severity': severity_counts
                    }
                }

                # In production, this would send the digest via email/Slack
                logger.info(f"Alert digest generated: {digest_data}")

                return {
                    'success': True,
                    'digest_sent': True,
                    'alert_count': total_alerts,
                    'digest_data': digest_data,
                    'timestamp': datetime.now().isoformat()
                }

        result = self.run_async(send_digest)
        logger.info(f"Alert digest completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Alert digest task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.alerts.evaluate_single_rule',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
    default_retry_delay=30,
)
def evaluate_single_rule_task(self, rule_id: str) -> Dict:
    """
    Celery task for evaluating a single alert rule.

    Args:
        rule_id: Alert rule ID to evaluate

    Returns:
        Dictionary with evaluation results
    """
    try:
        logger.info(f"Starting single rule evaluation for rule {rule_id}")

        async def evaluate_rule():
            async with async_session_maker() as db:
                # Get rule
                stmt = select(AlertRule).where(AlertRule.id == UUID(rule_id))
                result = await db.execute(stmt)
                rule = result.scalar_one_or_none()

                if not rule:
                    return {
                        'success': False,
                        'error': 'Rule not found'
                    }

                if not rule.is_active:
                    return {
                        'success': False,
                        'error': 'Rule is not active'
                    }

                # Evaluate rule
                alert_engine = AlertEngine(db)
                triggered_alerts = await alert_engine.evaluate_alert_rules(
                    str(rule.workspace_id)
                )

                # Filter to this specific rule
                rule_alerts = [a for a in triggered_alerts if str(a.get('rule_id')) == rule_id]

                return {
                    'success': True,
                    'rule_id': rule_id,
                    'triggered': len(rule_alerts) > 0,
                    'alert_count': len(rule_alerts),
                    'timestamp': datetime.now().isoformat()
                }

        result = self.run_async(evaluate_rule)
        logger.info(f"Single rule evaluation completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Single rule evaluation failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)
