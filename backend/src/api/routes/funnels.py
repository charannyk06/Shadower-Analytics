"""Funnel analysis routes for conversion tracking."""

from typing import Dict, Any, Optional, List, Literal
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Body
from datetime import datetime
import logging

from ...core.database import get_db
from ...services.analytics.funnel_analysis import FunnelAnalysisService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...utils.validators import validate_workspace_id
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/funnels", tags=["funnels"])
logger = logging.getLogger(__name__)

# Note: Rate limiting is handled globally by RateLimitMiddleware in main.py


# ===================================================================
# REQUEST/RESPONSE MODELS
# ===================================================================

class FunnelStepCreate(BaseModel):
    """Funnel step creation model."""
    stepId: str = Field(..., description="Unique step identifier")
    stepName: str = Field(..., description="Human-readable step name")
    event: str = Field(..., description="Event name to track")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters for this step")


class FunnelDefinitionCreate(BaseModel):
    """Funnel definition creation model."""
    name: str = Field(..., min_length=1, max_length=255, description="Funnel name")
    description: Optional[str] = Field(None, description="Funnel description")
    steps: List[FunnelStepCreate] = Field(..., min_items=2, description="Funnel steps (minimum 2)")
    timeframe: Literal["24h", "7d", "30d", "90d"] = Field("30d", description="Default analysis timeframe")
    segmentBy: Optional[str] = Field(None, description="Optional segmentation field")


class FunnelDefinitionUpdate(BaseModel):
    """Funnel definition update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    steps: Optional[List[FunnelStepCreate]] = Field(None, min_items=2)
    timeframe: Optional[Literal["24h", "7d", "30d", "90d"]] = None
    segmentBy: Optional[str] = None
    status: Optional[Literal["active", "paused", "archived"]] = None


# ===================================================================
# FUNNEL DEFINITION ENDPOINTS
# ===================================================================

@router.post("/definitions")
async def create_funnel_definition(
    workspace_id: str = Query(..., description="Workspace ID"),
    funnel_data: FunnelDefinitionCreate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Create a new funnel definition.

    This endpoint creates a new conversion funnel with specified steps
    and configuration.

    **Parameters:**
    - **workspace_id**: Workspace to create funnel in
    - **funnel_data**: Funnel configuration including steps

    **Returns:**
    - Created funnel definition with ID and metadata
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Creating funnel definition '{funnel_data.name}' for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)

        # Convert Pydantic models to dicts
        steps = [step.dict() for step in funnel_data.steps]

        funnel = await service.create_funnel_definition(
            workspace_id=validated_workspace_id,
            name=funnel_data.name,
            steps=steps,
            description=funnel_data.description,
            timeframe=funnel_data.timeframe,
            segment_by=funnel_data.segmentBy,
            created_by=current_user.get("user_id"),
        )

        return funnel

    except ValueError as e:
        logger.warning(f"Validation error creating funnel: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating funnel definition: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create funnel definition. Please try again later."
        )


@router.get("/definitions")
async def list_funnel_definitions(
    workspace_id: str = Query(..., description="Workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status: active, paused, archived"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    List all funnel definitions for a workspace.

    **Parameters:**
    - **workspace_id**: Workspace to list funnels for
    - **status**: Optional status filter

    **Returns:**
    - List of funnel definitions
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Listing funnel definitions for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)
        funnels = await service.list_funnel_definitions(
            workspace_id=validated_workspace_id,
            status=status,
        )

        return {
            "funnels": funnels,
            "total": len(funnels),
        }

    except ValueError as e:
        logger.warning(f"Validation error listing funnels: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing funnel definitions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to list funnel definitions. Please try again later."
        )


@router.get("/definitions/{funnel_id}")
async def get_funnel_definition(
    funnel_id: str = Path(..., description="Funnel ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get a specific funnel definition.

    **Parameters:**
    - **funnel_id**: Funnel ID to retrieve
    - **workspace_id**: Workspace ID for validation

    **Returns:**
    - Funnel definition with full configuration
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching funnel definition {funnel_id} for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)
        funnel = await service.get_funnel_definition(
            funnel_id=funnel_id,
            workspace_id=validated_workspace_id,
        )

        if not funnel:
            raise HTTPException(status_code=404, detail="Funnel not found")

        return funnel

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error getting funnel: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching funnel definition: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch funnel definition. Please try again later."
        )


@router.patch("/definitions/{funnel_id}")
async def update_funnel_definition(
    funnel_id: str = Path(..., description="Funnel ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    updates: FunnelDefinitionUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Update a funnel definition.

    **Parameters:**
    - **funnel_id**: Funnel ID to update
    - **workspace_id**: Workspace ID for validation
    - **updates**: Fields to update

    **Returns:**
    - Updated funnel definition
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Updating funnel definition {funnel_id} for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)

        # Convert Pydantic model to dict and filter None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}

        # Convert steps if present
        if "steps" in update_data and update_data["steps"]:
            update_data["steps"] = [step.dict() for step in updates.steps]

        funnel = await service.update_funnel_definition(
            funnel_id=funnel_id,
            workspace_id=validated_workspace_id,
            updates=update_data,
        )

        return funnel

    except ValueError as e:
        logger.warning(f"Validation error updating funnel: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating funnel definition: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update funnel definition. Please try again later."
        )


# ===================================================================
# FUNNEL ANALYSIS ENDPOINTS
# ===================================================================

@router.post("/definitions/{funnel_id}/analyze")
async def analyze_funnel(
    funnel_id: str = Path(..., description="Funnel ID to analyze"),
    workspace_id: str = Query(..., description="Workspace ID"),
    start_date: Optional[str] = Query(None, description="Analysis start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Analysis end date (ISO format)"),
    segment_name: Optional[str] = Query(None, description="Optional segment filter"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Analyze a conversion funnel.

    This endpoint runs funnel analysis to calculate conversion rates,
    drop-off points, and user flow metrics.

    **Parameters:**
    - **funnel_id**: Funnel to analyze
    - **workspace_id**: Workspace ID for validation
    - **start_date**: Optional start date for analysis
    - **end_date**: Optional end date for analysis
    - **segment_name**: Optional segment to analyze

    **Returns:**
    - Funnel analysis results including:
        - Step-by-step metrics
        - Conversion rates
        - Drop-off analysis
        - Overall metrics
        - Segment comparison (if applicable)
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Analyzing funnel {funnel_id} for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None

        service = FunnelAnalysisService(db)
        analysis = await service.analyze_funnel(
            funnel_id=funnel_id,
            workspace_id=validated_workspace_id,
            start_date=start_dt,
            end_date=end_dt,
            segment_name=segment_name,
        )

        return analysis

    except ValueError as e:
        logger.warning(f"Validation error analyzing funnel: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing funnel: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze funnel. Please try again later."
        )


@router.get("/definitions/{funnel_id}/journeys")
async def get_user_journeys(
    funnel_id: str = Path(..., description="Funnel ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status: in_progress, completed, abandoned"),
    limit: int = Query(100, ge=1, le=500, description="Number of journeys to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get user journeys through a funnel.

    This endpoint returns individual user paths through the funnel,
    useful for understanding specific user behaviors.

    **Parameters:**
    - **funnel_id**: Funnel ID
    - **workspace_id**: Workspace ID for validation
    - **status**: Optional status filter
    - **limit**: Maximum number of journeys to return
    - **offset**: Offset for pagination

    **Returns:**
    - List of user journeys with timestamps and path information
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching user journeys for funnel {funnel_id} in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)
        journeys = await service.get_user_journeys(
            funnel_id=funnel_id,
            workspace_id=validated_workspace_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        return journeys

    except ValueError as e:
        logger.warning(f"Validation error fetching journeys: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching user journeys: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch user journeys. Please try again later."
        )


# ===================================================================
# SUMMARY ENDPOINTS
# ===================================================================

@router.get("/performance-summary")
async def get_funnel_performance_summary(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", description="Analysis timeframe: 24h, 7d, 30d, 90d"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get performance summary for all funnels.

    This endpoint provides an overview of all funnel performance
    metrics for a workspace.

    **Parameters:**
    - **workspace_id**: Workspace ID
    - **timeframe**: Analysis timeframe

    **Returns:**
    - Summary of all funnels with health scores and conversion rates
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching funnel performance summary for workspace {validated_workspace_id} "
            f"with timeframe {timeframe} (user: {current_user.get('user_id')})"
        )

        service = FunnelAnalysisService(db)
        summary = await service.get_funnel_performance_summary(
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return summary

    except ValueError as e:
        logger.warning(f"Validation error fetching summary: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching funnel performance summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch funnel performance summary. Please try again later."
        )
