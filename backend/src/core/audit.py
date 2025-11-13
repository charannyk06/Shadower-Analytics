"""Audit logging system for security and compliance."""

import json
import logging
from typing import Any, Dict, Optional, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Comprehensive audit logging system.

    Logs security-relevant events for compliance and monitoring.
    """

    # Sensitive field names that should be redacted from logs
    SENSITIVE_FIELDS: Set[str] = {
        "password",
        "token",
        "secret",
        "api_key",
        "credit_card",
        "ssn",
        "private_key",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "session",
    }

    # Event types that trigger security alerts
    CRITICAL_EVENTS: Set[str] = {
        "security_breach",
        "unauthorized_access",
        "data_export",
        "data_deletion",
        "admin_action",
        "authentication_failure",
        "authorization_failure",
    }

    def __init__(self, db_session: AsyncSession):
        """
        Initialize audit logger.

        Args:
            db_session: Database session for storing audit logs
        """
        self.db = db_session

    async def log_event(
        self,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        severity: str = "info",
    ):
        """
        Log a security-relevant event.

        Args:
            event_type: Type of event (authentication, data_export, etc.)
            action: Action performed (login, export, delete, etc.)
            user_id: ID of user performing action
            workspace_id: ID of workspace context
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
            ip_address: IP address of client
            user_agent: User agent string
            request_id: Request correlation ID
            status: Event status (success, failure, error)
            error_message: Error message if applicable
            severity: Event severity (debug, info, warning, error, critical)
        """
        try:
            # Import here to avoid circular dependency
            from ..models.database.tables import AuditLog

            # Sanitize details to remove sensitive information
            sanitized_details = self._sanitize_details(details or {})

            # Create audit log entry
            audit_log = AuditLog(
                event_type=event_type,
                action=action,
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=sanitized_details,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                status=status,
                error_message=error_message,
                severity=severity,
                timestamp=datetime.utcnow(),
            )

            self.db.add(audit_log)
            await self.db.commit()

            # Check if this is a critical event that needs alerting
            if event_type in self.CRITICAL_EVENTS or severity == "critical":
                await self._send_security_alert(audit_log)

            logger.info(
                f"Audit log created: {event_type}/{action} by user {user_id} - {status}"
            )

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't raise - audit logging failure shouldn't break the application
            await self.db.rollback()

    async def log_from_request(
        self,
        request: Request,
        event_type: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        severity: str = "info",
    ):
        """
        Log event from FastAPI request context.

        Automatically extracts user_id, workspace_id, IP address, etc. from request.

        Args:
            request: FastAPI request object
            event_type: Type of event
            action: Action performed
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
            status: Event status
            error_message: Error message if applicable
            severity: Event severity
        """
        # Extract user context from request
        user = getattr(request.state, "user", None)
        user_id = user.id if user and hasattr(user, "id") else None

        workspace_id = getattr(request.state, "workspace_id", None)

        # Extract client information
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_id = request.headers.get("x-request-id")

        await self.log_event(
            event_type=event_type,
            action=action,
            user_id=user_id,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            severity=severity,
        )

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from audit log details.

        Args:
            details: Event details dictionary

        Returns:
            Sanitized details with sensitive fields redacted
        """
        sanitized = {}

        for key, value in details.items():
            # Check if key contains sensitive field name
            key_lower = key.lower()
            is_sensitive = any(
                sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS
            )

            if is_sensitive:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                # Sanitize list items if they're dictionaries
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    async def _send_security_alert(self, audit_log):
        """
        Send security alert for critical events.

        Args:
            audit_log: AuditLog instance with event details
        """
        try:
            # TODO: Implement alerting mechanism
            # This could send notifications via:
            # - Email
            # - Slack
            # - PagerDuty
            # - SIEM system
            logger.critical(
                f"SECURITY ALERT: {audit_log.event_type} - "
                f"Action: {audit_log.action}, User: {audit_log.user_id}, "
                f"Status: {audit_log.status}"
            )

        except Exception as e:
            logger.error(f"Failed to send security alert: {e}")


# Convenience functions for common audit events

async def log_authentication(
    db: AsyncSession,
    user_id: str,
    action: str,
    status: str = "success",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Log authentication event."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="authentication",
        action=action,
        user_id=user_id,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
        error_message=error_message,
        severity="warning" if status != "success" else "info",
    )


async def log_data_access(
    db: AsyncSession,
    user_id: str,
    workspace_id: str,
    resource_type: str,
    resource_id: str,
    action: str = "read",
    details: Optional[Dict[str, Any]] = None,
):
    """Log data access event."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="data_access",
        action=action,
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )


async def log_data_export(
    db: AsyncSession,
    user_id: str,
    workspace_id: str,
    resource_type: str,
    export_format: str,
    record_count: int,
    ip_address: Optional[str] = None,
):
    """Log data export event."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="data_export",
        action="export",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        details={
            "export_format": export_format,
            "record_count": record_count,
        },
        ip_address=ip_address,
        severity="warning",  # Data exports are security-relevant
    )


async def log_data_modification(
    db: AsyncSession,
    user_id: str,
    workspace_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    changes: Optional[Dict[str, Any]] = None,
):
    """Log data modification event."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="data_modification",
        action=action,
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={"changes": changes} if changes else None,
    )


async def log_admin_action(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Log administrative action."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="admin_action",
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        severity="warning",  # Admin actions are security-relevant
    )


async def log_authorization_failure(
    db: AsyncSession,
    user_id: str,
    required_permission: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Log authorization failure."""
    logger_instance = AuditLogger(db)
    await logger_instance.log_event(
        event_type="authorization_failure",
        action="access_denied",
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={"required_permission": required_permission},
        ip_address=ip_address,
        status="failure",
        severity="warning",
    )
