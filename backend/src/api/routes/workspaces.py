"""Workspace metrics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.schemas.workspaces import WorkspaceMetrics, WorkspaceStats, WorkspaceAnalytics
from ...services.metrics.workspace_analytics_service import get_workspace_analytics
from ..dependencies.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


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


@router.get("/{workspace_id}/analytics", response_model=WorkspaceAnalytics)
async def get_workspace_analytics_endpoint(
    workspace_id: str = Path(..., description="Workspace ID"),
    timeframe: str = Query(
        "30d",
        regex="^(24h|7d|30d|90d|all)$",
        description="Time period for analytics"
    ),
    include_comparison: bool = Query(
        False,
        description="Include cross-workspace comparison (admin only)"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive workspace analytics.

    Returns detailed analytics for a workspace including:
    - Overview metrics (members, activity, health score)
    - Member analytics (roles, activity distribution, top contributors)
    - Agent usage (performance, efficiency)
    - Resource utilization (credits, storage, API)
    - Billing information
    - Workspace comparison (admin only)

    Args:
        workspace_id: The workspace ID
        timeframe: Time period (24h, 7d, 30d, 90d, all)
        include_comparison: Include comparison data (requires admin role)
        current_user: Current authenticated user
        db: Database session

    Returns:
        WorkspaceAnalytics: Complete workspace analytics data

    Raises:
        HTTPException: If workspace not found or access denied
    """

    # Check workspace access
    # TODO: Implement proper workspace access validation
    # For now, allow any authenticated user

    # If comparison is requested, verify admin role
    if include_comparison:
        user_role = current_user.get("role", "").lower()
        if user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Workspace comparison data is only available to admins"
            )

    try:
        analytics = await get_workspace_analytics(
            db=db,
            workspace_id=workspace_id,
            timeframe=timeframe,
            include_comparison=include_comparison
        )
        return analytics

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log the error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching workspace analytics for {workspace_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch workspace analytics"
        )
