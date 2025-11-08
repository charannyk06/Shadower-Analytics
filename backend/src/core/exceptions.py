"""Custom exceptions for the application."""


class ShadowAnalyticsException(Exception):
    """Base exception for Shadow Analytics."""

    pass


class DatabaseException(ShadowAnalyticsException):
    """Database-related exceptions."""

    pass


class CacheException(ShadowAnalyticsException):
    """Cache-related exceptions."""

    pass


class AuthenticationException(ShadowAnalyticsException):
    """Authentication-related exceptions."""

    pass


class AuthorizationException(ShadowAnalyticsException):
    """Authorization-related exceptions."""

    pass


class ValidationException(ShadowAnalyticsException):
    """Validation-related exceptions."""

    pass


class MetricNotFoundException(ShadowAnalyticsException):
    """Metric not found exception."""

    pass


class AgentNotFoundException(ShadowAnalyticsException):
    """Agent not found exception."""

    pass


class UserNotFoundException(ShadowAnalyticsException):
    """User not found exception."""

    pass


class WorkspaceNotFoundException(ShadowAnalyticsException):
    """Workspace not found exception."""

    pass
