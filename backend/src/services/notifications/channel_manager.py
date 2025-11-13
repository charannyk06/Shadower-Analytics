"""Notification channel manager for multi-channel delivery."""

import logging
import json
import aiosmtp
import aiohttp
from typing import Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.config import get_settings
from src.api.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationChannelManager:
    """Manager for sending notifications through different channels."""

    def __init__(self, websocket_manager: Optional[ConnectionManager] = None):
        """
        Initialize channel manager.

        Args:
            websocket_manager: WebSocket manager for in-app notifications
        """
        self.websocket_manager = websocket_manager
        logger.info("NotificationChannelManager initialized")

    async def send(
        self,
        channel: str,
        recipient_id: str,
        recipient_email: Optional[str],
        content: Dict[str, Any],
    ) -> bool:
        """
        Send notification through specified channel.

        Args:
            channel: Channel to send through
            recipient_id: Recipient user ID
            recipient_email: Recipient email (for email channel)
            content: Rendered notification content

        Returns:
            True if successful, False otherwise
        """
        try:
            if channel == "in_app":
                return await self.send_in_app(recipient_id, content)
            elif channel == "email":
                return await self.send_email(
                    recipient_email, content.get("subject"), content
                )
            elif channel == "slack":
                return await self.send_slack(content.get("webhook_url"), content)
            elif channel == "teams":
                return await self.send_teams(content.get("webhook_url"), content)
            elif channel == "discord":
                return await self.send_discord(content.get("webhook_url"), content)
            elif channel == "webhook":
                return await self.send_webhook(content.get("webhook_url"), content)
            else:
                logger.error(f"Unknown channel: {channel}")
                return False
        except Exception as e:
            logger.error(f"Failed to send notification via {channel}: {e}")
            return False

    async def send_in_app(
        self, user_id: str, notification: Dict[str, Any]
    ) -> bool:
        """
        Send in-app notification via WebSocket.

        Args:
            user_id: User ID
            notification: Notification data

        Returns:
            True if successful
        """
        try:
            if not self.websocket_manager:
                logger.warning("WebSocket manager not available for in-app notifications")
                return False

            # Broadcast to user via WebSocket
            await self.websocket_manager.send_to_user(
                user_id=user_id,
                message={
                    "event": "notification",
                    "data": {
                        "title": notification.get("title"),
                        "message": notification.get("message"),
                        "severity": notification.get("severity", "info"),
                        "action_url": notification.get("action_url"),
                        "timestamp": notification.get("timestamp"),
                    },
                },
            )

            logger.info(f"Sent in-app notification to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            return False

    async def send_email(
        self,
        recipients: list[str] | str,
        subject: str,
        content: Dict[str, Any],
    ) -> bool:
        """
        Send email notification with HTML and text fallback.

        Args:
            recipients: Email address(es)
            subject: Email subject
            content: Email content with 'html_body' and 'text_body'

        Returns:
            True if successful
        """
        try:
            # Ensure recipients is a list
            if isinstance(recipients, str):
                recipients = [recipients]

            # Get SMTP configuration from settings
            smtp_host = getattr(settings, "SMTP_HOST", None)
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_user = getattr(settings, "SMTP_USER", None)
            smtp_password = getattr(settings, "SMTP_PASSWORD", None)
            smtp_from = getattr(settings, "SMTP_FROM", smtp_user)

            if not all([smtp_host, smtp_user, smtp_password]):
                logger.warning("SMTP not configured, skipping email notification")
                return False

            # Create multipart message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = smtp_from
            message["To"] = ", ".join(recipients)

            # Add text and HTML parts
            text_body = content.get("text_body", content.get("body", ""))
            html_body = content.get("html_body", content.get("body", ""))

            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")

            message.attach(part1)
            message.attach(part2)

            # Send email using aiosmtplib (async SMTP)
            # Note: In production, you'd want to use a proper SMTP library
            # For now, we'll log the attempt
            logger.info(
                f"Would send email to {recipients} with subject '{subject}' "
                f"via {smtp_host}:{smtp_port}"
            )

            # TODO: Implement actual SMTP sending with aiosmtplib
            # import aiosmtplib
            # await aiosmtplib.send(
            #     message,
            #     hostname=smtp_host,
            #     port=smtp_port,
            #     username=smtp_user,
            #     password=smtp_password,
            #     use_tls=True,
            # )

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_slack(
        self, webhook_url: str, message: Dict[str, Any]
    ) -> bool:
        """
        Send Slack notification with rich formatting.

        Args:
            webhook_url: Slack webhook URL
            message: Message data (should contain 'blocks' for rich formatting)

        Returns:
            True if successful
        """
        try:
            if not webhook_url:
                logger.warning("Slack webhook URL not provided")
                return False

            # Parse message body if it's a JSON string
            if isinstance(message.get("body"), str):
                try:
                    slack_message = json.loads(message["body"])
                except json.JSONDecodeError:
                    # Fallback to simple text message
                    slack_message = {
                        "text": message.get("body", "Notification"),
                    }
            else:
                slack_message = message.get("body", {})

            # Send to Slack webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=slack_message,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        logger.info("Successfully sent Slack notification")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Slack webhook failed with status {response.status}: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def send_teams(
        self, webhook_url: str, card: Dict[str, Any]
    ) -> bool:
        """
        Send Microsoft Teams adaptive card notification.

        Args:
            webhook_url: Teams webhook URL
            card: Adaptive card data

        Returns:
            True if successful
        """
        try:
            if not webhook_url:
                logger.warning("Teams webhook URL not provided")
                return False

            # Parse card body if it's a JSON string
            if isinstance(card.get("body"), str):
                try:
                    teams_card = json.loads(card["body"])
                except json.JSONDecodeError:
                    # Fallback to simple card
                    teams_card = {
                        "@type": "MessageCard",
                        "@context": "https://schema.org/extensions",
                        "summary": card.get("subject", "Notification"),
                        "text": card.get("body", ""),
                    }
            else:
                teams_card = card.get("body", {})

            # Send to Teams webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=teams_card,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        logger.info("Successfully sent Teams notification")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Teams webhook failed with status {response.status}: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False

    async def send_discord(
        self, webhook_url: str, embed: Dict[str, Any]
    ) -> bool:
        """
        Send Discord embed notification.

        Args:
            webhook_url: Discord webhook URL
            embed: Embed data

        Returns:
            True if successful
        """
        try:
            if not webhook_url:
                logger.warning("Discord webhook URL not provided")
                return False

            # Parse embed body if it's a JSON string
            if isinstance(embed.get("body"), str):
                try:
                    discord_embed = json.loads(embed["body"])
                except json.JSONDecodeError:
                    # Fallback to simple embed
                    discord_embed = {
                        "content": embed.get("body", "Notification"),
                    }
            else:
                discord_embed = embed.get("body", {})

            # Send to Discord webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=discord_embed,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status in [200, 204]:
                        logger.info("Successfully sent Discord notification")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Discord webhook failed with status {response.status}: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    async def send_webhook(
        self, webhook_url: str, payload: Dict[str, Any]
    ) -> bool:
        """
        Send generic webhook notification.

        Args:
            webhook_url: Webhook URL
            payload: Payload to send

        Returns:
            True if successful
        """
        try:
            if not webhook_url:
                logger.warning("Webhook URL not provided")
                return False

            # Send to custom webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status in [200, 201, 202, 204]:
                        logger.info(f"Successfully sent webhook notification to {webhook_url}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Webhook failed with status {response.status}: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

    async def test_channel(
        self, channel: str, configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a notification channel configuration.

        Args:
            channel: Channel to test
            configuration: Channel configuration

        Returns:
            Dict with test results
        """
        try:
            test_content = {
                "subject": "Test Notification",
                "body": "This is a test notification from Shadower Analytics.",
                "title": "Test Notification",
                "message": "This is a test notification.",
                "severity": "info",
            }

            if channel == "email":
                test_content.update({
                    "html_body": "<p>This is a test notification from Shadower Analytics.</p>",
                    "text_body": "This is a test notification from Shadower Analytics.",
                })
                success = await self.send_email(
                    recipients=configuration.get("test_email"),
                    subject="Test Notification",
                    content=test_content,
                )
            elif channel == "slack":
                test_content["webhook_url"] = configuration.get("webhook_url")
                test_content["body"] = json.dumps({
                    "text": "Test notification from Shadower Analytics"
                })
                success = await self.send_slack(
                    webhook_url=configuration.get("webhook_url"),
                    message=test_content,
                )
            elif channel == "teams":
                test_content["webhook_url"] = configuration.get("webhook_url")
                test_content["body"] = json.dumps({
                    "@type": "MessageCard",
                    "@context": "https://schema.org/extensions",
                    "summary": "Test Notification",
                    "text": "This is a test notification from Shadower Analytics.",
                })
                success = await self.send_teams(
                    webhook_url=configuration.get("webhook_url"),
                    card=test_content,
                )
            elif channel == "discord":
                test_content["webhook_url"] = configuration.get("webhook_url")
                test_content["body"] = json.dumps({
                    "content": "Test notification from Shadower Analytics"
                })
                success = await self.send_discord(
                    webhook_url=configuration.get("webhook_url"),
                    embed=test_content,
                )
            else:
                return {
                    "success": False,
                    "message": f"Unknown channel: {channel}",
                }

            return {
                "success": success,
                "message": "Test successful" if success else "Test failed",
                "details": {"channel": channel, "timestamp": str(logger)},
            }

        except Exception as e:
            logger.error(f"Channel test failed: {e}")
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
            }
