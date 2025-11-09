"""Permission checking middleware and dependencies for FastAPI."""

from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
import logging

from ...core.security import verify_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user.

    Args:
        credentials: HTTP Bearer credentials from the request

    Returns:
        The decoded token payload containing user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        payload = await verify_token(token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) if str(e) else "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionChecker:
    """
    Dependency class for checking user permissions.

    Usage:
        @app.get("/admin/users")
        async def get_users(user: dict = Depends(PermissionChecker(["admin"]))):
            return {"users": [...]}
    """

    def __init__(self, required_roles: Optional[List[str]] = None):
        """
        Initialize the permission checker.

        Args:
            required_roles: List of roles required to access the endpoint
        """
        self.required_roles = required_roles or []

    async def __call__(
        self,
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        Check if the current user has the required permissions.

        Args:
            current_user: The current authenticated user

        Returns:
            The current user if authorized

        Raises:
            HTTPException: If user doesn't have required permissions
        """
        # If no specific roles required, just return the user
        if not self.required_roles:
            return current_user

        # Get user roles from the token payload
        user_roles = current_user.get("roles", [])
        if isinstance(user_roles, str):
            user_roles = [user_roles]

        # Check if user has any of the required roles
        has_permission = any(role in user_roles for role in self.required_roles)

        if not has_permission:
            logger.warning(
                f"User {current_user.get('sub')} attempted to access "
                f"resource requiring roles {self.required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(self.required_roles)}",
            )

        return current_user


class WorkspacePermissionChecker:
    """
    Dependency class for checking workspace-specific permissions.

    Usage:
        @app.get("/workspaces/{workspace_id}/data")
        async def get_workspace_data(
            workspace_id: str,
            user: dict = Depends(WorkspacePermissionChecker(["read", "write"]))
        ):
            return {"data": [...]}
    """

    def __init__(self, required_permissions: Optional[List[str]] = None):
        """
        Initialize the workspace permission checker.

        Args:
            required_permissions: List of permissions required (e.g., ["read", "write"])
        """
        self.required_permissions = required_permissions or []

    async def __call__(
        self,
        request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        Check if the current user has the required workspace permissions.

        Args:
            request: The FastAPI request object
            current_user: The current authenticated user

        Returns:
            The current user if authorized

        Raises:
            HTTPException: If user doesn't have required workspace permissions
        """
        # Extract workspace_id from path parameters
        workspace_id = request.path_params.get("workspace_id")

        if not workspace_id:
            # If no workspace_id in path, check if user has global permissions
            if "admin" in current_user.get("roles", []):
                return current_user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace ID required",
            )

        # Get user's workspaces from token
        user_workspaces = current_user.get("workspaces", {})

        # Check if user has access to this workspace
        if workspace_id not in user_workspaces:
            logger.warning(
                f"User {current_user.get('sub')} attempted to access "
                f"workspace {workspace_id} without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workspace",
            )

        # Check specific permissions if required
        if self.required_permissions:
            workspace_permissions = user_workspaces[workspace_id].get("permissions", [])
            has_permission = any(
                perm in workspace_permissions for perm in self.required_permissions
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient workspace permissions. Required: {', '.join(self.required_permissions)}",
                )

        return current_user


# Convenience function for requiring specific roles
def require_roles(roles: List[str]):
    """
    Convenience function to create a role-based permission dependency.

    Usage:
        @app.get("/admin/settings")
        async def admin_settings(user: dict = Depends(require_roles(["admin"]))):
            return {"settings": [...]}
    """
    return PermissionChecker(required_roles=roles)


# Convenience function for requiring workspace permissions
def require_workspace_permissions(permissions: List[str]):
    """
    Convenience function to create a workspace permission dependency.

    Usage:
        @app.post("/workspaces/{workspace_id}/data")
        async def create_data(
            workspace_id: str,
            user: dict = Depends(require_workspace_permissions(["write"]))
        ):
            return {"status": "created"}
    """
    return WorkspacePermissionChecker(required_permissions=permissions)
