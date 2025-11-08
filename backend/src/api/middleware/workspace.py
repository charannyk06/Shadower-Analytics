"""Workspace access validation."""

from fastapi import HTTPException, status
from typing import Dict, Any, List


class WorkspaceAccess:
    """Workspace access validation utilities."""

    @staticmethod
    async def validate_workspace_access(user: Dict[str, Any], workspace_id: str) -> bool:
        """Check if user has access to workspace."""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_workspaces = user.get("workspaces", [])

        if workspace_id not in user_workspaces:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to workspace {workspace_id}",
            )

        return True

    @staticmethod
    async def get_accessible_workspaces(user: Dict[str, Any]) -> List[str]:
        """Get list of workspaces user can access."""
        if not user:
            return []

        return user.get("workspaces", [])

    @staticmethod
    def has_workspace_access(user: Dict[str, Any], workspace_id: str) -> bool:
        """Check if user has access to workspace (non-async)."""
        if not user:
            return False

        user_workspaces = user.get("workspaces", [])
        return workspace_id in user_workspaces
