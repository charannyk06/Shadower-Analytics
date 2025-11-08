/**
 * Permission constants and role definitions
 */

export const PERMISSIONS = {
  // Executive
  VIEW_EXECUTIVE_DASHBOARD: "view_executive_dashboard",
  VIEW_FINANCIAL_METRICS: "view_financial_metrics",

  // Analytics
  VIEW_ANALYTICS: "view_analytics",
  EXPORT_ANALYTICS: "export_analytics",
  CREATE_REPORTS: "create_reports",

  // Alerts
  VIEW_ALERTS: "view_alerts",
  CREATE_ALERTS: "create_alerts",
  MANAGE_ALERTS: "manage_alerts",

  // Admin
  MANAGE_WORKSPACE: "manage_workspace",
  VIEW_ALL_WORKSPACES: "view_all_workspaces",
  MANAGE_USERS: "manage_users",

  // Agents
  VIEW_AGENTS: "view_agents",
  MANAGE_AGENTS: "manage_agents",

  // Metrics
  VIEW_METRICS: "view_metrics",
  EXPORT_METRICS: "export_metrics",
} as const;

export const ROLES = {
  OWNER: "owner",
  ADMIN: "admin",
  MEMBER: "member",
  VIEWER: "viewer",
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
export type Role = (typeof ROLES)[keyof typeof ROLES];

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [ROLES.OWNER]: [
    PERMISSIONS.VIEW_EXECUTIVE_DASHBOARD,
    PERMISSIONS.VIEW_FINANCIAL_METRICS,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.EXPORT_ANALYTICS,
    PERMISSIONS.CREATE_REPORTS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.CREATE_ALERTS,
    PERMISSIONS.MANAGE_ALERTS,
    PERMISSIONS.MANAGE_WORKSPACE,
    PERMISSIONS.VIEW_ALL_WORKSPACES,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.VIEW_AGENTS,
    PERMISSIONS.MANAGE_AGENTS,
    PERMISSIONS.VIEW_METRICS,
    PERMISSIONS.EXPORT_METRICS,
  ],
  [ROLES.ADMIN]: [
    PERMISSIONS.VIEW_EXECUTIVE_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.EXPORT_ANALYTICS,
    PERMISSIONS.CREATE_REPORTS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.CREATE_ALERTS,
    PERMISSIONS.MANAGE_ALERTS,
    PERMISSIONS.VIEW_AGENTS,
    PERMISSIONS.MANAGE_AGENTS,
    PERMISSIONS.VIEW_METRICS,
    PERMISSIONS.EXPORT_METRICS,
  ],
  [ROLES.MEMBER]: [
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.EXPORT_ANALYTICS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.VIEW_AGENTS,
    PERMISSIONS.VIEW_METRICS,
    PERMISSIONS.EXPORT_METRICS,
  ],
  [ROLES.VIEWER]: [
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.VIEW_AGENTS,
    PERMISSIONS.VIEW_METRICS,
  ],
};

export function hasPermission(role: Role, permission: Permission): boolean {
  const rolePermissions = ROLE_PERMISSIONS[role] || [];
  return rolePermissions.includes(permission);
}

export function hasAnyPermission(
  role: Role,
  permissions: Permission[]
): boolean {
  return permissions.some((permission) => hasPermission(role, permission));
}
