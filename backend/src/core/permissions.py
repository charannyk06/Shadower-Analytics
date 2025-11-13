"""Permission and role constants."""

from typing import Dict, List, Set
from enum import Enum


# Permission constants
class Permissions:
    """Permission constants for role-based access control."""

    # Dashboard permissions
    VIEW_EXECUTIVE_DASHBOARD = "view_executive_dashboard"
    VIEW_FINANCIAL_METRICS = "view_financial_metrics"
    VIEW_AGENT_ANALYTICS = "view_agent_analytics"
    VIEW_USER_ANALYTICS = "view_user_analytics"

    # Analytics
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_ANALYTICS = "export_analytics"
    CREATE_REPORTS = "create_reports"

    # Data permissions
    EXPORT_DATA = "export_data"
    VIEW_SENSITIVE_DATA = "view_sensitive_data"
    DELETE_DATA = "delete_data"

    # Alerts
    VIEW_ALERTS = "view_alerts"
    CREATE_ALERTS = "create_alerts"
    MANAGE_ALERTS = "manage_alerts"

    # Configuration permissions
    MANAGE_REPORTS = "manage_reports"
    MANAGE_INTEGRATIONS = "manage_integrations"

    # Admin permissions
    MANAGE_WORKSPACE = "manage_workspace"
    VIEW_ALL_WORKSPACES = "view_all_workspaces"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"

    # Agents
    VIEW_AGENTS = "view_agents"
    MANAGE_AGENTS = "manage_agents"

    # Metrics
    VIEW_METRICS = "view_metrics"
    EXPORT_METRICS = "export_metrics"


# Role definitions
class Roles:
    """Role constants."""

    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    MEMBER = "member"
    VIEWER = "viewer"
    API_USER = "api_user"


# Get all permissions dynamically
def get_all_permissions() -> List[str]:
    """Get all available permissions."""
    return [
        getattr(Permissions, attr)
        for attr in dir(Permissions)
        if not attr.startswith("_") and isinstance(getattr(Permissions, attr), str)
    ]


# Permission matrix - maps roles to their permissions
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    # Super Admin has all permissions
    Roles.SUPER_ADMIN: get_all_permissions(),

    # Owner - Full workspace control
    Roles.OWNER: [
        # Dashboard permissions
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_FINANCIAL_METRICS,
        Permissions.VIEW_AGENT_ANALYTICS,
        Permissions.VIEW_USER_ANALYTICS,
        # Analytics
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.CREATE_REPORTS,
        # Data permissions
        Permissions.EXPORT_DATA,
        Permissions.VIEW_SENSITIVE_DATA,
        Permissions.DELETE_DATA,
        # Alerts
        Permissions.VIEW_ALERTS,
        Permissions.CREATE_ALERTS,
        Permissions.MANAGE_ALERTS,
        # Configuration
        Permissions.MANAGE_REPORTS,
        Permissions.MANAGE_INTEGRATIONS,
        # Admin
        Permissions.MANAGE_WORKSPACE,
        Permissions.VIEW_ALL_WORKSPACES,
        Permissions.MANAGE_USERS,
        Permissions.VIEW_AUDIT_LOGS,
        # Agents
        Permissions.VIEW_AGENTS,
        Permissions.MANAGE_AGENTS,
        # Metrics
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],

    # Admin - Can manage workspace but not all workspaces
    Roles.ADMIN: [
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_AGENT_ANALYTICS,
        Permissions.VIEW_USER_ANALYTICS,
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.CREATE_REPORTS,
        Permissions.EXPORT_DATA,
        Permissions.VIEW_SENSITIVE_DATA,
        Permissions.VIEW_ALERTS,
        Permissions.CREATE_ALERTS,
        Permissions.MANAGE_ALERTS,
        Permissions.MANAGE_REPORTS,
        Permissions.MANAGE_INTEGRATIONS,
        Permissions.MANAGE_USERS,
        Permissions.VIEW_AUDIT_LOGS,
        Permissions.VIEW_AGENTS,
        Permissions.MANAGE_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],

    # Analyst - Can view and analyze data
    Roles.ANALYST: [
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_AGENT_ANALYTICS,
        Permissions.VIEW_USER_ANALYTICS,
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.EXPORT_DATA,
        Permissions.CREATE_REPORTS,
        Permissions.MANAGE_REPORTS,
        Permissions.VIEW_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],

    # Member - Basic access
    Roles.MEMBER: [
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.VIEW_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],

    # Viewer - Read-only access
    Roles.VIEWER: [
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_AGENT_ANALYTICS,
        Permissions.VIEW_ANALYTICS,
        Permissions.VIEW_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.VIEW_METRICS,
    ],

    # API User - Programmatic access
    Roles.API_USER: [
        Permissions.VIEW_AGENT_ANALYTICS,
        Permissions.EXPORT_DATA,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],
}


def get_permissions_for_role(role: str) -> List[str]:
    """Get list of permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: str, permission: str, custom_permissions: Set[str] = None) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: The user's role
        permission: The permission to check
        custom_permissions: Optional set of custom permissions granted to the user

    Returns:
        True if the user has the permission, False otherwise
    """
    # Get base permissions for role
    base_permissions = set(ROLE_PERMISSIONS.get(role, []))

    # Add custom permissions if provided
    if custom_permissions:
        base_permissions = base_permissions.union(custom_permissions)

    return permission in base_permissions


class PermissionChecker:
    """Utility class for permission checking with custom permissions support."""

    @staticmethod
    def has_permission(
        user_role: str,
        required_permission: str,
        custom_permissions: Set[str] = None,
    ) -> bool:
        """
        Check if user has required permission.

        Args:
            user_role: The user's role
            required_permission: The permission to check
            custom_permissions: Optional set of custom permissions

        Returns:
            True if user has permission, False otherwise
        """
        return has_permission(user_role, required_permission, custom_permissions)

    @staticmethod
    def has_any_permission(
        user_role: str,
        required_permissions: List[str],
        custom_permissions: Set[str] = None,
    ) -> bool:
        """
        Check if user has any of the required permissions.

        Args:
            user_role: The user's role
            required_permissions: List of permissions to check
            custom_permissions: Optional set of custom permissions

        Returns:
            True if user has at least one permission, False otherwise
        """
        return any(
            has_permission(user_role, perm, custom_permissions)
            for perm in required_permissions
        )

    @staticmethod
    def has_all_permissions(
        user_role: str,
        required_permissions: List[str],
        custom_permissions: Set[str] = None,
    ) -> bool:
        """
        Check if user has all required permissions.

        Args:
            user_role: The user's role
            required_permissions: List of permissions to check
            custom_permissions: Optional set of custom permissions

        Returns:
            True if user has all permissions, False otherwise
        """
        return all(
            has_permission(user_role, perm, custom_permissions)
            for perm in required_permissions
        )
