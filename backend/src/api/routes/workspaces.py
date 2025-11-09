"""Workspace metrics routes with proper authentication and access control."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging

from ...core.database import get_db
from ...models.schemas.workspaces import WorkspaceMetrics, WorkspaceStats, WorkspaceAnalytics
from ...services.metrics.workspace_analytics_service import WorkspaceAnalyticsService
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


async def verify_workspace_access(
    workspace_id: str,
    user_id: str,
    db,
) -> bool:
    """
    Verify that a user has access to a specific workspace.

    Args:
        workspace_id: Workspace identifier
        user_id: User identifier
        db: Database session

    Returns:
        True if user has access, raises HTTPException otherwise

    Raises:
        HTTPException: 403 if access denied, 404 if workspace not found
    """
    try:
        # First check if workspace exists
        workspace_exists_query = text("""
            SELECT 1 FROM public.workspaces
            WHERE workspace_id = :workspace_id
        """)
        result = await db.execute(workspace_exists_query, {"workspace_id": workspace_id})
        if not result.fetchone():
            logger.warning(f"Workspace {workspace_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {workspace_id} not found"
            )

        # Check if user is a member of the workspace
        access_query = text("""
            SELECT 1 FROM public.workspace_members
            WHERE workspace_id = :workspace_id AND user_id = :user_id
        """)
        access_result = await db.execute(
            access_query,
            {"workspace_id": workspace_id, "user_id": user_id}
        )

        if not access_result.fetchone():
            logger.warning(
                f"Access denied for user {user_id} to workspace {workspace_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workspace"
            )

        return True

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error verifying workspace access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying workspace access"
        )


@router.get("/", response_model=List[WorkspaceMetrics])
async def list_workspaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
):
    """List all workspaces with basic metrics."""
    # Implementation will be added
    return []


@router.get("/{workspace_id}", response_model=WorkspaceStats)
async def get_workspace_details(
    workspace_id: str = Path(...),
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db=Depends(get_db),
):
    """Get detailed metrics for a specific workspace."""
    # Implementation will be added
    return {
        "workspace_id": workspace_id,
        "total_users": 0,
        "total_agents": 0,
        "total_executions": 0,
    }


@router.get("/{workspace_id}/agents")
async def get_workspace_agents(
    workspace_id: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
):
    """Get agents in a workspace."""
    # Implementation will be added
    return {"agents": [], "total": 0}


@router.get("/{workspace_id}/users")
async def get_workspace_users(
    workspace_id: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
):
    """Get users in a workspace."""
    # Implementation will be added
    return {"users": [], "total": 0}


