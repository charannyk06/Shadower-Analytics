"""Notification channels for alert delivery."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import aiohttp
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.database.tables import NotificationHistory, Alert

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Base class for notification channels."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Send notification.

        Returns:
            tuple of (success, error_message, response_data)
        """
        raise NotImplementedError("Subclasses must implement send()")

    def format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert for notification."""
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
            "emergency": "🔥"
        }

        emoji = severity_emoji.get(alert.get("severity", "info"), "⚠️")

        message = f"{emoji} **Alert: {alert['alert_title']}**\n\n"
        message += f"**Severity:** {alert['severity'].upper()}\n"
        message += f"**Message:** {alert['alert_message']}\n"

        if alert.get("metric_value") is not None:
            message += f"**Current Value:** {alert['metric_value']}\n"

        if alert.get("threshold_value") is not None:
            message += f"**Threshold:** {alert['threshold_value']}\n"

        message += f"**Triggered:** {alert.get('triggered_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

        if alert.get("alert_context"):
            message += f"\n**Context:**\n```json\n{alert['alert_context']}\n```\n"

        return message


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send email notification."""
        try:
            # Get SMTP configuration from config
            smtp_host = self.config.get("smtp_host", "localhost")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_user = self.config.get("smtp_user")
            smtp_password = self.config.get("smtp_password")
            from_email = self.config.get("from_email", "alerts@shadower-analytics.com")

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert['severity'].upper()}] {alert['alert_title']}"
            msg["From"] = from_email
            msg["To"] = recipient

            # Create text and HTML versions
            text_content = self.format_alert_message(alert)
            html_content = self._create_html_email(alert)

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email (using asyncio to make it non-blocking)
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp,
                smtp_host,
                smtp_port,
                smtp_user,
                smtp_password,
                from_email,
                recipient,
                msg
            )

            logger.info(f"Email notification sent to {recipient}")
            return True, None, {"recipient": recipient, "sent_at": datetime.now().isoformat()}

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False, str(e), None

    def _send_smtp(self, host, port, user, password, from_email, to_email, msg):
        """Send email via SMTP (blocking operation)."""
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)

    def _create_html_email(self, alert: Dict[str, Any]) -> str:
        """Create HTML email template."""
        severity_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "critical": "#e74c3c",
            "emergency": "#c0392b"
        }

        color = severity_colors.get(alert.get("severity", "info"), "#3498db")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert['alert_title']}</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Severity: {alert['severity'].upper()}</p>
                </div>
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <p><strong>Message:</strong> {alert['alert_message']}</p>
                    {'<p><strong>Current Value:</strong> ' + str(alert.get('metric_value', 'N/A')) + '</p>' if alert.get('metric_value') is not None else ''}
                    {'<p><strong>Threshold:</strong> ' + str(alert.get('threshold_value', 'N/A')) + '</p>' if alert.get('threshold_value') is not None else ''}
                    <p><strong>Triggered:</strong> {alert.get('triggered_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,  # Slack webhook URL
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send Slack notification."""
        try:
            webhook_url = recipient

            # Create Slack message payload
            payload = self._create_slack_payload(alert)

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent successfully")
                        return True, None, {"status_code": response.status}
                    else:
                        error_text = await response.text()
                        logger.error(f"Slack notification failed: {error_text}")
                        return False, f"HTTP {response.status}: {error_text}", None

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False, str(e), None

    def _create_slack_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create Slack message payload."""
        severity_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "critical": "#e74c3c",
            "emergency": "#c0392b"
        }

        color = severity_colors.get(alert.get("severity", "info"), "#3498db")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alert['alert_title']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert['severity'].upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Triggered:*\n{alert.get('triggered_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n{alert['alert_message']}"
                }
            }
        ]

        # Add metric values if available
        if alert.get("metric_value") is not None or alert.get("threshold_value") is not None:
            fields = []
            if alert.get("metric_value") is not None:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Current Value:*\n{alert['metric_value']}"
                })
            if alert.get("threshold_value") is not None:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Threshold:*\n{alert['threshold_value']}"
                })

            blocks.append({
                "type": "section",
                "fields": fields
            })

        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }


class WebhookChannel(NotificationChannel):
    """Custom webhook notification channel."""

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,  # Webhook URL
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send webhook notification."""
        try:
            webhook_url = recipient

            # Create payload
            payload = {
                "alert_id": str(alert.get("id", "")),
                "workspace_id": str(alert.get("workspace_id", "")),
                "alert_title": alert["alert_title"],
                "alert_message": alert["alert_message"],
                "severity": alert["severity"],
                "metric_value": alert.get("metric_value"),
                "threshold_value": alert.get("threshold_value"),
                "triggered_at": alert.get("triggered_at", datetime.now()).isoformat(),
                "alert_context": alert.get("alert_context", {})
            }

            # Send webhook
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_text = await response.text()

                    if response.status in [200, 201, 202, 204]:
                        logger.info(f"Webhook notification sent to {webhook_url}")
                        return True, None, {
                            "status_code": response.status,
                            "response": response_text[:500]  # Limit response size
                        }
                    else:
                        logger.error(f"Webhook notification failed: HTTP {response.status}")
                        return False, f"HTTP {response.status}: {response_text[:200]}", None

        except asyncio.TimeoutError:
            logger.error(f"Webhook notification timeout: {webhook_url}")
            return False, "Request timeout", None
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False, str(e), None


class SMSChannel(NotificationChannel):
    """SMS notification channel (using Twilio or similar)."""

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,  # Phone number
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send SMS notification."""
        try:
            # SMS provider configuration
            provider = self.config.get("provider", "twilio")

            # Create short message for SMS
            message = self._create_sms_message(alert)

            if provider == "twilio":
                return await self._send_via_twilio(recipient, message)
            else:
                return False, f"Unsupported SMS provider: {provider}", None

        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return False, str(e), None

    def _create_sms_message(self, alert: Dict[str, Any]) -> str:
        """Create short SMS message."""
        severity = alert["severity"].upper()
        title = alert["alert_title"][:50]  # Truncate long titles
        message = f"[{severity}] {title}\n"

        if alert.get("metric_value") is not None:
            message += f"Value: {alert['metric_value']}\n"

        return message[:160]  # SMS character limit

    async def _send_via_twilio(self, phone_number: str, message: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send SMS via Twilio API."""
        # This is a placeholder - actual Twilio integration would require twilio package
        logger.info(f"Would send SMS to {phone_number}: {message}")

        # In production, this would call Twilio API:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(body=message, from_=from_number, to=phone_number)

        return True, None, {"provider": "twilio", "to": phone_number}


class PagerDutyChannel(NotificationChannel):
    """PagerDuty notification channel."""

    async def send(
        self,
        alert: Dict[str, Any],
        recipient: str,  # PagerDuty integration key
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send PagerDuty notification."""
        try:
            integration_key = recipient

            # Create PagerDuty event
            payload = {
                "routing_key": integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": alert["alert_title"],
                    "severity": self._map_severity_to_pagerduty(alert["severity"]),
                    "source": "shadower-analytics",
                    "timestamp": alert.get("triggered_at", datetime.now()).isoformat(),
                    "custom_details": {
                        "alert_message": alert["alert_message"],
                        "metric_value": alert.get("metric_value"),
                        "threshold_value": alert.get("threshold_value"),
                        "alert_context": alert.get("alert_context", {})
                    }
                }
            }

            # Send to PagerDuty Events API v2
            pagerduty_url = "https://events.pagerduty.com/v2/enqueue"

            async with aiohttp.ClientSession() as session:
                async with session.post(pagerduty_url, json=payload) as response:
                    response_data = await response.json()

                    if response.status in [200, 202]:
                        logger.info(f"PagerDuty incident created: {response_data.get('dedup_key')}")
                        return True, None, response_data
                    else:
                        logger.error(f"PagerDuty notification failed: {response_data}")
                        return False, str(response_data), None

        except Exception as e:
            logger.error(f"Failed to send PagerDuty notification: {str(e)}")
            return False, str(e), None

    def _map_severity_to_pagerduty(self, severity: str) -> str:
        """Map alert severity to PagerDuty severity."""
        mapping = {
            "info": "info",
            "warning": "warning",
            "critical": "error",
            "emergency": "critical"
        }
        return mapping.get(severity, "warning")


class AlertChannelService:
    """Service for managing alert notification channels."""

    def __init__(self, db: AsyncSession, config: Optional[Dict[str, Any]] = None):
        self.db = db
        self.config = config or {}

        # Initialize channels
        self.channels = {
            "email": EmailChannel(self.config.get("email", {})),
            "slack": SlackChannel(self.config.get("slack", {})),
            "webhook": WebhookChannel(self.config.get("webhook", {})),
            "sms": SMSChannel(self.config.get("sms", {})),
            "pagerduty": PagerDutyChannel(self.config.get("pagerduty", {}))
        }

    async def send_alert(
        self,
        alert: Dict[str, Any],
        channels_config: List[Dict[str, Any]],
        alert_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send alert through specified channels.

        Args:
            alert: Alert data
            channels_config: List of channel configurations
            alert_id: Alert ID for history tracking

        Returns:
            Dictionary with delivery results
        """
        results = {
            "total_channels": len(channels_config),
            "successful": 0,
            "failed": 0,
            "details": []
        }

        # Send to each channel
        tasks = []
        for channel_config in channels_config:
            channel_type = channel_config.get("type")
            recipients = channel_config.get("recipients", [])

            # Handle single recipient string
            if isinstance(recipients, str):
                recipients = [recipients]

            for recipient in recipients:
                task = self._send_to_channel(
                    channel_type,
                    alert,
                    recipient,
                    alert_id,
                    channel_config
                )
                tasks.append(task)

        # Execute all sends concurrently
        send_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in send_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["details"].append({
                    "success": False,
                    "error": str(result)
                })
            elif result["success"]:
                results["successful"] += 1
                results["details"].append(result)
            else:
                results["failed"] += 1
                results["details"].append(result)

        return results

    async def _send_to_channel(
        self,
        channel_type: str,
        alert: Dict[str, Any],
        recipient: str,
        alert_id: Optional[str],
        channel_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send alert to a single channel/recipient."""
        try:
            channel = self.channels.get(channel_type)
            if not channel:
                return {
                    "success": False,
                    "channel": channel_type,
                    "recipient": recipient,
                    "error": f"Unknown channel type: {channel_type}"
                }

            # Send notification
            success, error_msg, response_data = await channel.send(
                alert,
                recipient,
                **channel_config
            )

            # Record in notification history
            if alert_id:
                await self._record_notification(
                    alert_id,
                    channel_type,
                    recipient,
                    "sent" if success else "failed",
                    error_msg,
                    response_data
                )

            return {
                "success": success,
                "channel": channel_type,
                "recipient": recipient,
                "error": error_msg,
                "response": response_data
            }

        except Exception as e:
            logger.error(f"Error sending to {channel_type}/{recipient}: {str(e)}")
            return {
                "success": False,
                "channel": channel_type,
                "recipient": recipient,
                "error": str(e)
            }

    async def _record_notification(
        self,
        alert_id: str,
        channel: str,
        recipient: str,
        status: str,
        error_message: Optional[str],
        response_data: Optional[Dict[str, Any]]
    ):
        """Record notification in history table."""
        try:
            from uuid import UUID

            notification = NotificationHistory(
                alert_id=UUID(alert_id),
                channel=channel,
                recipient=recipient,
                sent_at=datetime.now(),
                delivery_status=status,
                error_message=error_message,
                retry_count=0,
                response_data=response_data
            )

            self.db.add(notification)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to record notification history: {str(e)}")
            await self.db.rollback()
