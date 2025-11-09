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
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List all workspaces with basic metrics.

    Requires authentication. Returns only workspaces the user has access to.
    """
    # Implementation will be added
    # TODO: Filter by workspaces user has access to
    return []


@router.get("/{workspace_id}", response_model=WorkspaceStats)
async def get_workspace_details(
    workspace_id: str = Path(..., min_length=1, max_length=64),
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get detailed metrics for a specific workspace.

    Requires authentication and workspace membership.
    """
    # TODO: Verify workspace access
    # Implementation will be added
    return {
        "workspace_id": workspace_id,
        "total_users": 0,
        "total_agents": 0,
        "total_executions": 0,
    }


@router.get("/{workspace_id}/agents")
async def get_workspace_agents(
    workspace_id: str = Path(..., min_length=1, max_length=64),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get agents in a workspace.

    Requires authentication and workspace membership.
    """
    # TODO: Verify workspace access
    # Implementation will be added
    return {"agents": [], "total": 0}


@router.get("/{workspace_id}/users")
async def get_workspace_users(
    workspace_id: str = Path(..., min_length=1, max_length=64),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get users in a workspace.

    Requires authentication and workspace membership.
    """
    # TODO: Verify workspace access
    # Implementation will be added
    return {"users": [], "total": 0}


@router.get("/{workspace_id}/analytics")
async def get_workspace_analytics(
    workspace_id: str = Path(
        ...,
        pattern="^[a-zA-Z0-9-_]{1,64}$",
        description="Workspace ID (alphanumeric, hyphens, underscores, max 64 chars)"
    ),
    timeframe: str = Query(
        "30d",
        pattern="^(24h|7d|30d|90d|all)$",
        description="Time period for analytics (24h, 7d, 30d, 90d, all)"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """
    Get comprehensive analytics for a workspace.

    This endpoint provides detailed analytics including:
    - Workspace overview metrics
    - Member activity and engagement
    - Agent usage statistics
    - Resource consumption
    - Activity trends over time
    - Overall workspace health score

    **Authentication Required**: User must be authenticated and a member of the workspace.

    **Parameters**:
    - `workspace_id`: Unique identifier for the workspace
    - `timeframe`: Time period for analytics (24h, 7d, 30d, 90d, all)

    **Returns**:
    - Comprehensive workspace analytics data

    **Raises**:
    - 401: Unauthorized - Missing or invalid authentication
    - 403: Forbidden - User is not a member of the workspace
    - 404: Not Found - Workspace does not exist
    - 500: Internal Server Error - Database or processing error
    """
    try:
        logger.info(
            f"Analytics request for workspace_id={workspace_id}, "
            f"timeframe={timeframe}, user_id={current_user.get('sub')}"
        )

        # Verify workspace access
        user_id = current_user.get("sub")
        if not user_id:
            logger.error("User ID not found in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        await verify_workspace_access(workspace_id, user_id, db)

        # Get analytics
        service = WorkspaceAnalyticsService(db)
        analytics = await service.get_workspace_analytics(
            workspace_id=workspace_id,
            timeframe=timeframe,
            user_id=user_id,
        )

        logger.info(f"Analytics successfully retrieved for workspace_id={workspace_id}")
        return analytics

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error in workspace analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching analytics"
        )
    except Exception as e:
        logger.error(f"Unexpected error in workspace analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
