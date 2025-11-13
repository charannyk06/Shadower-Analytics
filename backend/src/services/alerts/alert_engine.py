"""Core alert engine service."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from ...models.database.tables import (
    AlertRule,
    Alert,
    EscalationPolicy,
    AlertSuppression,
    NotificationHistory
)
from .conditions import get_condition_evaluator, ConditionValidator
from .channels import AlertChannelService

logger = logging.getLogger(__name__)


class AlertEngine:
    """Core alert engine for rule evaluation and alert management."""

    def __init__(self, db: AsyncSession, config: Optional[Dict[str, Any]] = None):
        self.db = db
        self.config = config or {}
        self.channel_service = AlertChannelService(db, config.get("channels", {}))
        self.cooldowns = {}  # In-memory cooldown tracking (would use Redis in production)

    async def evaluate_alert_rules(
        self,
        workspace_id: str,
        metric_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all active alert rules for workspace.

        Args:
            workspace_id: Workspace ID
            metric_data: Optional current metric data

        Returns:
            List of triggered alerts
        """
        try:
            # Get active alert rules for workspace
            rules = await self._get_active_rules(workspace_id)

            if not rules:
                logger.info(f"No active alert rules for workspace {workspace_id}")
                return []

            triggered_alerts = []

            # Evaluate each rule
            for rule in rules:
                try:
                    # Check if rule is in cooldown
                    if self._is_in_cooldown(str(rule.id)):
                        logger.debug(f"Rule {rule.id} is in cooldown period")
                        continue

                    # Check if rule should be evaluated based on interval
                    if not self._should_evaluate_rule(rule):
                        continue

                    # Evaluate rule condition
                    is_triggered, context = await self._evaluate_rule(rule, metric_data)

                    # Update last evaluated timestamp
                    await self._update_rule_evaluated_time(rule.id)

                    if is_triggered:
                        # Check for alert suppression
                        if await self._is_suppressed(workspace_id, rule, context):
                            logger.info(f"Alert suppressed for rule {rule.id}")
                            continue

                        # Create alert
                        alert = await self._create_alert(rule, context)

                        # Send notifications
                        await self.send_alert(
                            alert,
                            rule.notification_channels,
                            workspace_id
                        )

                        # Apply cooldown
                        self._apply_cooldown(str(rule.id), rule.cooldown_minutes)

                        # Update rule last triggered time
                        await self._update_rule_triggered_time(rule.id)

                        triggered_alerts.append(alert)

                        # Check if escalation is needed
                        if rule.escalation_policy_id:
                            await self._schedule_escalation_check(alert["id"], rule.escalation_policy_id)

                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.id}: {str(e)}")
                    continue

            return triggered_alerts

        except Exception as e:
            logger.error(f"Error in evaluate_alert_rules: {str(e)}")
            return []

    async def _get_active_rules(self, workspace_id: str) -> List[AlertRule]:
        """Get active alert rules for workspace."""
        stmt = select(AlertRule).where(
            and_(
                AlertRule.workspace_id == UUID(workspace_id),
                AlertRule.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def _should_evaluate_rule(self, rule: AlertRule) -> bool:
        """Check if rule should be evaluated based on check interval."""
        if rule.last_evaluated_at is None:
            return True

        time_since_last_check = datetime.now() - rule.last_evaluated_at
        check_interval = timedelta(minutes=rule.check_interval_minutes)

        return time_since_last_check >= check_interval

    async def _evaluate_rule(
        self,
        rule: AlertRule,
        metric_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate a single alert rule."""
        try:
            # Get condition evaluator
            evaluator = get_condition_evaluator(rule.condition_type, self.db)

            if not evaluator:
                logger.error(f"No evaluator found for condition type: {rule.condition_type}")
                return False, None

            # Evaluate condition
            is_triggered, context = await evaluator.evaluate(
                str(rule.workspace_id),
                rule.metric_type,
                rule.condition_config,
                metric_data
            )

            return is_triggered, context

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {str(e)}")
            return False, None

    async def _create_alert(
        self,
        rule: AlertRule,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new alert instance."""
        try:
            alert_title = self._generate_alert_title(rule, context)
            alert_message = self._generate_alert_message(rule, context)

            alert = Alert(
                workspace_id=rule.workspace_id,
                rule_id=rule.id,
                alert_title=alert_title,
                alert_message=alert_message,
                severity=rule.severity,
                metric_value=context.get("current_value"),
                threshold_value=context.get("threshold_value"),
                triggered_at=datetime.now(),
                alert_context=context,
                notification_sent=False,
                notification_channels=rule.notification_channels,
                escalated=False,
                escalation_level=0
            )

            self.db.add(alert)
            await self.db.commit()
            await self.db.refresh(alert)

            return self._alert_to_dict(alert)

        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            await self.db.rollback()
            raise

    def _generate_alert_title(self, rule: AlertRule, context: Dict[str, Any]) -> str:
        """Generate alert title."""
        metric_type = context.get("metric_type", rule.metric_type)
        current_value = context.get("current_value")

        title = f"{rule.rule_name}"

        if current_value is not None:
            title += f" - Current: {current_value}"

        return title

    def _generate_alert_message(self, rule: AlertRule, context: Dict[str, Any]) -> str:
        """Generate alert message."""
        message = rule.description or f"Alert triggered for {rule.metric_type}"

        if context.get("current_value") is not None:
            message += f"\n\nCurrent Value: {context['current_value']}"

        if context.get("threshold_value") is not None:
            message += f"\nThreshold: {context['threshold_value']}"

        if context.get("operator"):
            message += f"\nCondition: value {context['operator']} threshold"

        return message

    async def send_alert(
        self,
        alert: Dict[str, Any],
        channels_config: List[Dict[str, Any]],
        workspace_id: str
    ) -> Dict[str, Any]:
        """
        Send alert through specified channels.

        Args:
            alert: Alert data
            channels_config: Channel configurations
            workspace_id: Workspace ID

        Returns:
            Delivery results
        """
        try:
            # Send through channel service
            results = await self.channel_service.send_alert(
                alert,
                channels_config,
                str(alert.get("id"))
            )

            # Update alert notification status
            if results["successful"] > 0:
                await self._mark_alert_notified(alert["id"])

            return results

        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return {
                "total_channels": len(channels_config),
                "successful": 0,
                "failed": len(channels_config),
                "error": str(e)
            }

    async def check_escalation_needed(
        self,
        alert_id: str,
        workspace_id: str
    ) -> bool:
        """
        Check if alert needs escalation based on acknowledgment time.

        Args:
            alert_id: Alert ID
            workspace_id: Workspace ID

        Returns:
            True if escalation occurred
        """
        try:
            # Get alert
            stmt = select(Alert).where(Alert.id == UUID(alert_id))
            result = await self.db.execute(stmt)
            alert = result.scalar_one_or_none()

            if not alert or alert.acknowledged_at or alert.resolved_at:
                return False

            # Get escalation policy
            if not alert.rule_id:
                return False

            stmt = select(AlertRule).where(AlertRule.id == alert.rule_id)
            result = await self.db.execute(stmt)
            rule = result.scalar_one_or_none()

            if not rule or not rule.escalation_policy_id:
                return False

            stmt = select(EscalationPolicy).where(
                EscalationPolicy.id == rule.escalation_policy_id
            )
            result = await self.db.execute(stmt)
            policy = result.scalar_one_or_none()

            if not policy or not policy.is_active:
                return False

            # Check escalation levels
            current_level = alert.escalation_level
            time_since_trigger = datetime.now() - alert.triggered_at

            escalation_levels = policy.escalation_levels
            if not isinstance(escalation_levels, list):
                return False

            # Find next escalation level
            for level in escalation_levels:
                level_num = level.get("level", 0)
                delay_minutes = level.get("delay_minutes", 0)

                if level_num > current_level:
                    if time_since_trigger.total_seconds() / 60 >= delay_minutes:
                        # Escalate
                        await self._escalate_alert(alert, level)
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking escalation: {str(e)}")
            return False

    async def _escalate_alert(self, alert: Alert, escalation_level: Dict[str, Any]):
        """Escalate alert to next level."""
        try:
            # Update alert escalation level
            alert.escalated = True
            alert.escalation_level = escalation_level.get("level", 0)

            # Send notifications to escalation channels
            channels = escalation_level.get("channels", [])
            recipients = escalation_level.get("recipients", [])

            channels_config = [
                {
                    "type": channel,
                    "recipients": recipients
                }
                for channel in channels
            ]

            alert_dict = self._alert_to_dict(alert)
            alert_dict["alert_message"] += f"\n\n[ESCALATED to Level {escalation_level.get('level')}]"

            await self.channel_service.send_alert(
                alert_dict,
                channels_config,
                str(alert.id)
            )

            await self.db.commit()

            logger.info(f"Alert {alert.id} escalated to level {escalation_level.get('level')}")

        except Exception as e:
            logger.error(f"Error escalating alert: {str(e)}")
            await self.db.rollback()

    def apply_alert_suppression(
        self,
        alert_type: str,
        workspace_id: str,
        duration_minutes: int = 60
    ):
        """
        Apply alert suppression to prevent fatigue.

        Args:
            alert_type: Type of alert to suppress
            workspace_id: Workspace ID
            duration_minutes: Suppression duration
        """
        # Store suppression in memory (would use Redis in production)
        suppression_key = f"{workspace_id}:{alert_type}"
        self.cooldowns[suppression_key] = datetime.now() + timedelta(minutes=duration_minutes)

        logger.info(f"Alert suppression applied for {suppression_key} for {duration_minutes} minutes")

    async def _is_suppressed(
        self,
        workspace_id: str,
        rule: AlertRule,
        context: Dict[str, Any]
    ) -> bool:
        """Check if alert should be suppressed."""
        try:
            # Check active suppressions
            now = datetime.now()

            stmt = select(AlertSuppression).where(
                and_(
                    AlertSuppression.workspace_id == UUID(workspace_id),
                    AlertSuppression.start_time <= now,
                    AlertSuppression.end_time >= now
                )
            )
            result = await self.db.execute(stmt)
            suppressions = result.scalars().all()

            for suppression in suppressions:
                # Check if suppression pattern matches
                pattern = suppression.pattern

                if pattern.get("rule_id") and str(pattern.get("rule_id")) == str(rule.id):
                    return True

                if pattern.get("metric_type") == rule.metric_type:
                    return True

                if pattern.get("severity") == rule.severity:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking suppression: {str(e)}")
            return False

    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id in self.cooldowns:
            cooldown_until = self.cooldowns[rule_id]
            if datetime.now() < cooldown_until:
                return True
            else:
                # Cooldown expired, remove it
                del self.cooldowns[rule_id]

        return False

    def _apply_cooldown(self, rule_id: str, cooldown_minutes: int):
        """Apply cooldown period to rule."""
        cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        self.cooldowns[rule_id] = cooldown_until

    async def _schedule_escalation_check(self, alert_id: UUID, policy_id: UUID):
        """Schedule escalation check for alert."""
        # This would schedule a Celery task to check escalation later
        # For now, just log it
        logger.info(f"Escalation check scheduled for alert {alert_id}")

    async def _update_rule_evaluated_time(self, rule_id: UUID):
        """Update rule's last evaluated timestamp."""
        try:
            stmt = (
                update(AlertRule)
                .where(AlertRule.id == rule_id)
                .values(last_evaluated_at=datetime.now())
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating rule evaluated time: {str(e)}")
            await self.db.rollback()

    async def _update_rule_triggered_time(self, rule_id: UUID):
        """Update rule's last triggered timestamp."""
        try:
            stmt = (
                update(AlertRule)
                .where(AlertRule.id == rule_id)
                .values(last_triggered_at=datetime.now())
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating rule triggered time: {str(e)}")
            await self.db.rollback()

    async def _mark_alert_notified(self, alert_id: str):
        """Mark alert as notified."""
        try:
            stmt = (
                update(Alert)
                .where(Alert.id == UUID(alert_id))
                .values(notification_sent=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error marking alert as notified: {str(e)}")
            await self.db.rollback()

    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert Alert ORM object to dictionary."""
        return {
            "id": str(alert.id),
            "workspace_id": str(alert.workspace_id),
            "rule_id": str(alert.rule_id),
            "alert_title": alert.alert_title,
            "alert_message": alert.alert_message,
            "severity": alert.severity,
            "metric_value": float(alert.metric_value) if alert.metric_value is not None else None,
            "threshold_value": float(alert.threshold_value) if alert.threshold_value is not None else None,
            "triggered_at": alert.triggered_at,
            "acknowledged_at": alert.acknowledged_at,
            "acknowledged_by": str(alert.acknowledged_by) if alert.acknowledged_by else None,
            "resolved_at": alert.resolved_at,
            "resolved_by": str(alert.resolved_by) if alert.resolved_by else None,
            "resolution_notes": alert.resolution_notes,
            "alert_context": alert.alert_context,
            "notification_sent": alert.notification_sent,
            "notification_channels": alert.notification_channels,
            "escalated": alert.escalated,
            "escalation_level": alert.escalation_level
        }

    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user_id: User acknowledging the alert
            notes: Optional notes

        Returns:
            True if successful
        """
        try:
            stmt = (
                update(Alert)
                .where(Alert.id == UUID(alert_id))
                .values(
                    acknowledged_at=datetime.now(),
                    acknowledged_by=UUID(user_id)
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Alert {alert_id} acknowledged by {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            await self.db.rollback()
            return False

    async def resolve_alert(
        self,
        alert_id: str,
        user_id: str,
        resolution_notes: str,
        permanent_fix: bool = False
    ) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID
            user_id: User resolving the alert
            resolution_notes: Resolution description
            permanent_fix: Whether this is a permanent fix

        Returns:
            True if successful
        """
        try:
            stmt = (
                update(Alert)
                .where(Alert.id == UUID(alert_id))
                .values(
                    resolved_at=datetime.now(),
                    resolved_by=UUID(user_id),
                    resolution_notes=resolution_notes
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Alert {alert_id} resolved by {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            await self.db.rollback()
            return False

    async def validate_alert_condition(
        self,
        condition_type: str,
        condition_config: Dict[str, Any],
        test_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate alert condition syntax and logic.

        Args:
            condition_type: Type of condition
            condition_config: Condition configuration
            test_data: Optional test data

        Returns:
            tuple of (is_valid, error_message)
        """
        return ConditionValidator.validate_condition(condition_type, condition_config)
