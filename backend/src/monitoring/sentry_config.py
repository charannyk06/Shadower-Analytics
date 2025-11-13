"""Sentry error tracking and performance monitoring configuration."""

import os
import logging
from typing import Optional, Any, Dict
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def setup_sentry() -> bool:
    """Configure Sentry error tracking and performance monitoring.

    Returns:
        True if Sentry was configured successfully, False otherwise
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        logger.warning("SENTRY_DSN not configured, error tracking disabled")
        return False

    try:
        environment = os.getenv("APP_ENV", "development")
        release = os.getenv("APP_VERSION", "unknown")

        # Configure Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=release,

            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint"  # Group transactions by endpoint
                ),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR  # Send errors as events
                ),
            ],

            # Performance monitoring
            traces_sample_rate=_get_traces_sample_rate(environment),
            profiles_sample_rate=_get_profiles_sample_rate(environment),

            # Error filtering
            before_send=filter_errors,
            before_breadcrumb=filter_breadcrumbs,

            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send PII by default
            max_breadcrumbs=50,
            max_value_length=1024,

            # Enable performance monitoring for specific operations
            enable_tracing=True,
        )

        logger.info(
            f"Sentry initialized successfully",
            extra={
                "environment": environment,
                "release": release,
                "traces_sample_rate": _get_traces_sample_rate(environment)
            }
        )

        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
        return False


def _get_traces_sample_rate(environment: str) -> float:
    """Get traces sample rate based on environment.

    Args:
        environment: Application environment

    Returns:
        Sample rate (0.0 to 1.0)
    """
    # Allow override via environment variable
    env_rate = os.getenv("SENTRY_TRACES_SAMPLE_RATE")
    if env_rate:
        try:
            return float(env_rate)
        except ValueError:
            logger.warning(f"Invalid SENTRY_TRACES_SAMPLE_RATE: {env_rate}")

    # Default rates by environment
    rates = {
        "production": 0.1,   # 10% in production
        "staging": 0.5,      # 50% in staging
        "development": 1.0,  # 100% in development
    }

    return rates.get(environment, 0.1)


def _get_profiles_sample_rate(environment: str) -> float:
    """Get profiling sample rate based on environment.

    Args:
        environment: Application environment

    Returns:
        Sample rate (0.0 to 1.0)
    """
    # Allow override via environment variable
    env_rate = os.getenv("SENTRY_PROFILES_SAMPLE_RATE")
    if env_rate:
        try:
            return float(env_rate)
        except ValueError:
            logger.warning(f"Invalid SENTRY_PROFILES_SAMPLE_RATE: {env_rate}")

    # Default rates by environment
    rates = {
        "production": 0.1,   # 10% in production
        "staging": 0.3,      # 30% in staging
        "development": 0.5,  # 50% in development
    }

    return rates.get(environment, 0.1)


def filter_errors(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter errors before sending to Sentry.

    Args:
        event: Sentry event
        hint: Error hint with exception info

    Returns:
        Modified event or None to drop the event
    """
    # Don't send 404 errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']

        # Filter out HTTPException with 404 status
        if isinstance(exc_value, HTTPException):
            if exc_value.status_code == 404:
                return None  # Drop event

            # Don't send 400-level errors except important ones
            if 400 <= exc_value.status_code < 500:
                # Only send auth errors and rate limits
                if exc_value.status_code not in [401, 403, 429]:
                    return None

    # Add custom context from request state
    if 'request' in event:
        request_data = event['request']

        # Add workspace context if available
        if hasattr(hint.get('request'), 'state'):
            state = hint['request'].state

            if hasattr(state, 'workspace_id'):
                event.setdefault('tags', {})['workspace_id'] = state.workspace_id

            if hasattr(state, 'user_id'):
                event.setdefault('user', {})['id'] = state.user_id

            if hasattr(state, 'request_id'):
                event.setdefault('tags', {})['request_id'] = state.request_id

    # Add additional context
    event.setdefault('tags', {}).update({
        'service': 'analytics-backend',
    })

    return event


def filter_breadcrumbs(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter breadcrumbs before adding to Sentry.

    Args:
        crumb: Breadcrumb data
        hint: Additional context

    Returns:
        Modified breadcrumb or None to drop it
    """
    # Filter out noisy breadcrumbs
    if crumb.get('category') == 'query':
        # Don't log simple SELECT 1 health checks
        message = crumb.get('message', '')
        if 'SELECT 1' in message or 'SELECT version()' in message:
            return None

    # Filter Redis ping commands
    if crumb.get('category') == 'redis':
        if crumb.get('data', {}).get('command') == 'PING':
            return None

    return crumb


def capture_exception(error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
    """Manually capture an exception to Sentry.

    Args:
        error: Exception to capture
        context: Additional context to attach

    Returns:
        Event ID from Sentry

    Example:
        try:
            risky_operation()
        except Exception as e:
            event_id = capture_exception(e, {
                "workspace_id": workspace_id,
                "operation": "data_export"
            })
    """
    with sentry_sdk.push_scope() as scope:
        # Add context
        if context:
            for key, value in context.items():
                if key in ['user_id', 'workspace_id', 'request_id']:
                    scope.set_tag(key, value)
                else:
                    scope.set_context(key, value)

        # Capture exception
        event_id = sentry_sdk.capture_exception(error)

    return event_id


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> str:
    """Manually capture a message to Sentry.

    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context to attach

    Returns:
        Event ID from Sentry

    Example:
        event_id = capture_message(
            "Unusual credit consumption detected",
            level="warning",
            context={"workspace_id": workspace_id, "credits": credits}
        )
    """
    with sentry_sdk.push_scope() as scope:
        # Add context
        if context:
            for key, value in context.items():
                if key in ['user_id', 'workspace_id', 'request_id']:
                    scope.set_tag(key, value)
                else:
                    scope.set_context(key, value)

        # Capture message
        event_id = sentry_sdk.capture_message(message, level=level)

    return event_id


def set_user_context(user_id: str, workspace_id: Optional[str] = None, **kwargs) -> None:
    """Set user context for Sentry events.

    Args:
        user_id: User identifier
        workspace_id: Workspace identifier
        **kwargs: Additional user attributes

    Example:
        set_user_context(
            user_id="user-123",
            workspace_id="ws-456",
            email="user@example.com"
        )
    """
    sentry_sdk.set_user({
        "id": user_id,
        "workspace_id": workspace_id,
        **kwargs
    })


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", data: Optional[Dict[str, Any]] = None) -> None:
    """Add a breadcrumb for debugging.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Breadcrumb level
        data: Additional data

    Example:
        add_breadcrumb(
            "Cache miss for analytics query",
            category="cache",
            data={"query_type": "user_activity"}
        )
    """
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=data or {}
    )
