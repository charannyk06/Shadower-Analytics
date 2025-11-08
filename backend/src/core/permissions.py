"""Permission and role constants."""

from typing import Dict, List


# Permission constants
class Permissions:
    """Permission constants for role-based access control."""

    # Executive
    VIEW_EXECUTIVE_DASHBOARD = "view_executive_dashboard"
    VIEW_FINANCIAL_METRICS = "view_financial_metrics"

    # Analytics
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_ANALYTICS = "export_analytics"
    CREATE_REPORTS = "create_reports"

    # Alerts
    VIEW_ALERTS = "view_alerts"
    CREATE_ALERTS = "create_alerts"
    MANAGE_ALERTS = "manage_alerts"

    # Admin
    MANAGE_WORKSPACE = "manage_workspace"
    VIEW_ALL_WORKSPACES = "view_all_workspaces"
    MANAGE_USERS = "manage_users"

    # Agents
    VIEW_AGENTS = "view_agents"
    MANAGE_AGENTS = "manage_agents"

    # Metrics
    VIEW_METRICS = "view_metrics"
    EXPORT_METRICS = "export_metrics"


# Role definitions
class Roles:
    """Role constants."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Permission matrix - maps roles to their permissions
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Roles.OWNER: [
        # Has all permissions
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_FINANCIAL_METRICS,
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.CREATE_REPORTS,
        Permissions.VIEW_ALERTS,
        Permissions.CREATE_ALERTS,
        Permissions.MANAGE_ALERTS,
        Permissions.MANAGE_WORKSPACE,
        Permissions.VIEW_ALL_WORKSPACES,
        Permissions.MANAGE_USERS,
        Permissions.VIEW_AGENTS,
        Permissions.MANAGE_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],
    Roles.ADMIN: [
        Permissions.VIEW_EXECUTIVE_DASHBOARD,
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.CREATE_REPORTS,
        Permissions.VIEW_ALERTS,
        Permissions.CREATE_ALERTS,
        Permissions.MANAGE_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.MANAGE_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],
    Roles.MEMBER: [
        Permissions.VIEW_ANALYTICS,
        Permissions.EXPORT_ANALYTICS,
        Permissions.VIEW_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.VIEW_METRICS,
        Permissions.EXPORT_METRICS,
    ],
    Roles.VIEWER: [
        Permissions.VIEW_ANALYTICS,
        Permissions.VIEW_ALERTS,
        Permissions.VIEW_AGENTS,
        Permissions.VIEW_METRICS,
    ],
}


def get_permissions_for_role(role: str) -> List[str]:
    """Get list of permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in role_permissions
