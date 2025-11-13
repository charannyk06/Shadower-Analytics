"""Template engine for rendering notifications."""

import logging
import json
from typing import Dict, Any, Optional
from jinja2 import Template, Environment, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.database.tables import NotificationTemplate

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Engine for rendering notification templates across different channels."""

    def __init__(self, db: AsyncSession):
        """
        Initialize template engine.

        Args:
            db: Database session
        """
        self.db = db
        self.jinja_env = Environment(
            autoescape=select_autoescape(
                enabled_extensions=('html', 'xml'),
                default_for_string=True,
            )
        )
        logger.info("TemplateEngine initialized")

    async def render(
        self,
        notification_type: str,
        channel: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Render notification template for specific channel.

        Args:
            notification_type: Type of notification
            channel: Target channel
            data: Data to populate template

        Returns:
            Rendered content dict or None if template not found
        """
        try:
            # Get template from database
            template = await self._get_template(notification_type, channel)

            if not template:
                logger.warning(
                    f"Template not found for type={notification_type} channel={channel}"
                )
                return None

            # Render subject if present
            subject = None
            if template.subject_template:
                subject_tmpl = self.jinja_env.from_string(template.subject_template)
                subject = subject_tmpl.render(**data)

            # Render body
            body_tmpl = self.jinja_env.from_string(template.body_template)
            body = body_tmpl.render(**data)

            # Parse body for structured channels (Slack, Teams, Discord)
            if channel in ["slack", "teams", "discord", "webhook"]:
                try:
                    # Try to parse as JSON
                    body = json.loads(body)
                except json.JSONDecodeError:
                    # If not JSON, keep as string
                    pass

            # Extract preview text (first 200 chars)
            preview = self._extract_preview(body)

            result = {
                "subject": subject,
                "body": body,
                "preview": preview,
                "template_name": template.template_name,
                "notification_type": notification_type,
                "channel": channel,
            }

            # For email, handle HTML and text formats
            if channel == "email":
                result["html_body"] = body if isinstance(body, str) else str(body)
                result["text_body"] = self._html_to_text(result["html_body"])

            # For in-app, extract structured fields
            if channel == "in_app":
                if isinstance(body, dict):
                    result["title"] = body.get("title", subject)
                    result["message"] = body.get("message", "")
                    result["severity"] = body.get("severity", "info")
                    result["action_url"] = body.get("action_url")
                else:
                    result["title"] = subject
                    result["message"] = body
                    result["severity"] = "info"

            logger.debug(
                f"Rendered template for type={notification_type} channel={channel}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to render template type={notification_type} channel={channel}: {e}"
            )
            return None

    async def _get_template(
        self, notification_type: str, channel: str
    ) -> Optional[NotificationTemplate]:
        """
        Get template from database.

        Args:
            notification_type: Notification type
            channel: Channel

        Returns:
            Template object or None
        """
        result = await self.db.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.notification_type == notification_type,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.is_active == True,
                )
            )
        )
        template = result.scalar_one_or_none()
        return template

    def _extract_preview(self, body: Any) -> str:
        """
        Extract preview text from body.

        Args:
            body: Notification body

        Returns:
            Preview text (max 200 chars)
        """
        if isinstance(body, dict):
            # For structured content, try to extract meaningful text
            text = body.get("message") or body.get("text") or str(body)
        else:
            text = str(body)

        # Remove HTML tags
        text = self._html_to_text(text)

        # Truncate to 200 chars
        if len(text) > 200:
            text = text[:197] + "..."

        return text

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text.

        Args:
            html: HTML string

        Returns:
            Plain text
        """
        # Simple HTML tag removal (for production, use a proper library like html2text)
        import re
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    async def validate_template(
        self, template_name: str, sample_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate template with sample data.

        Args:
            template_name: Template name
            sample_data: Sample data to test rendering

        Returns:
            Validation results
        """
        try:
            # Get template by name
            result = await self.db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.template_name == template_name
                )
            )
            template = result.scalar_one_or_none()

            if not template:
                return {
                    "valid": False,
                    "error": f"Template '{template_name}' not found",
                }

            # Check required variables
            required_vars = template.variables or []
            missing_vars = [
                var for var in required_vars if var not in sample_data
            ]

            if missing_vars:
                return {
                    "valid": False,
                    "error": f"Missing required variables: {', '.join(missing_vars)}",
                    "missing_variables": missing_vars,
                }

            # Try rendering
            rendered = await self.render(
                notification_type=template.notification_type,
                channel=template.channel,
                data=sample_data,
            )

            if not rendered:
                return {
                    "valid": False,
                    "error": "Failed to render template",
                }

            return {
                "valid": True,
                "message": "Template is valid",
                "preview": rendered,
            }

        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
            }

    async def preview_template(
        self, notification_type: str, channel: str, sample_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Preview template rendering with sample data.

        Args:
            notification_type: Notification type
            channel: Channel
            sample_data: Sample data

        Returns:
            Rendered preview or None
        """
        return await self.render(notification_type, channel, sample_data)

    async def get_template_variables(
        self, notification_type: str, channel: str
    ) -> Optional[list[str]]:
        """
        Get required variables for a template.

        Args:
            notification_type: Notification type
            channel: Channel

        Returns:
            List of required variables or None
        """
        template = await self._get_template(notification_type, channel)
        if template:
            return template.variables or []
        return None

    async def list_templates(
        self, notification_type: Optional[str] = None, channel: Optional[str] = None
    ) -> list[NotificationTemplate]:
        """
        List available templates.

        Args:
            notification_type: Optional filter by notification type
            channel: Optional filter by channel

        Returns:
            List of templates
        """
        filters = [NotificationTemplate.is_active == True]

        if notification_type:
            filters.append(NotificationTemplate.notification_type == notification_type)
        if channel:
            filters.append(NotificationTemplate.channel == channel)

        result = await self.db.execute(
            select(NotificationTemplate).where(and_(*filters))
        )
        templates = result.scalars().all()
        return list(templates)
