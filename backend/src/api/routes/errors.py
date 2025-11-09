"""Error tracking routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Body
import logging

from ...core.database import get_db
from ...models.schemas.error_tracking import (
    ErrorTrackingResponse,
    TrackErrorRequest,
    ResolveErrorRequest
)
from ...services.analytics.error_tracking_service import ErrorTrackingService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access

router = APIRouter(prefix="/api/v1/errors", tags=["errors"])
logger = logging.getLogger(__name__)


@router.get("/{workspace_id}", response_model=ErrorTrackingResponse)
async def get_error_tracking(
    workspace_id: str = Path(..., description="Workspace ID"),
    timeframe: str = Query(
        "7d",
        description="Time range: 24h, 7d, 30d, 90d",
        pattern="^(24h|7d|30d|90d)$",
    ),
    severity_filter: Optional[str] = Query(
        None,
        description="Filter by severity: all, low, medium, high, critical"
    ),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive error tracking data for a workspace.

    This endpoint provides detailed error analytics including:
    - Error overview and metrics
    - Error categorization and patterns
    - Timeline and spike detection
    - Top errors by various metrics
    - Error correlations
    - Recovery analysis

    **Parameters:**
    - **workspace_id**: Workspace identifier
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d)
    - **severity_filter**: Optional severity filter

    **Returns:**
    - Comprehensive error tracking data
    """
    try:
        logger.info(
            f"Fetching error tracking for workspace {workspace_id} "
            f"for timeframe {timeframe}"
        )

        service = ErrorTrackingService(db)
        tracking_data = await service.get_error_tracking(
            workspace_id=workspace_id,
            timeframe=timeframe,
            severity_filter=severity_filter
        )

        return tracking_data

    except Exception as e:
        logger.error(f"Error fetching error tracking: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch error tracking: {str(e)}",
        )


@router.post("/{workspace_id}/track")
async def track_error(
    workspace_id: str = Path(..., description="Workspace ID"),
    error_data: TrackErrorRequest = Body(...),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Track a new error occurrence.

    **Parameters:**
    - **workspace_id**: Workspace identifier
    - **error_data**: Error details

    **Returns:**
    - Error ID
    """
    try:
        logger.info(f"Tracking error for workspace {workspace_id}")

        service = ErrorTrackingService(db)
        error_id = await service.track_error(
            workspace_id=workspace_id,
            error_data=error_data.model_dump()
        )

        return {"errorId": error_id, "status": "tracked"}

    except Exception as e:
        logger.error(f"Error tracking error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track error: {str(e)}",
        )


@router.post("/{error_id}/resolve")
async def resolve_error(
    error_id: str = Path(..., description="Error ID"),
    resolution_data: ResolveErrorRequest = Body(...),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mark an error as resolved.

    **Parameters:**
    - **error_id**: Error identifier
    - **resolution_data**: Resolution details

    **Returns:**
    - Status confirmation
    """
    try:
        logger.info(f"Resolving error {error_id}")

        service = ErrorTrackingService(db)
        await service.resolve_error(
            error_id=error_id,
            resolution_data=resolution_data.model_dump()
        )

        return {"status": "resolved", "errorId": error_id}

    except Exception as e:
        logger.error(f"Error resolving error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve error: {str(e)}",
        )


@router.post("/{error_id}/ignore")
async def ignore_error(
    error_id: str = Path(..., description="Error ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mark an error as ignored.

    **Parameters:**
    - **error_id**: Error identifier

    **Returns:**
    - Status confirmation
    """
    try:
        logger.info(f"Ignoring error {error_id}")

        service = ErrorTrackingService(db)
        await service.ignore_error(error_id=error_id)

        return {"status": "ignored", "errorId": error_id}

    except Exception as e:
        logger.error(f"Error ignoring error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ignore error: {str(e)}",
        )
