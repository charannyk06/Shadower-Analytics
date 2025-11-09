"""Credit consumption API routes."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from ...core.database import get_db
from ...services.analytics.credit_consumption import CreditConsumptionService
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


@router.get("/consumption")
async def get_credit_consumption(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$", description="Time window"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive credit consumption analytics.

    Returns:
    - Current credit status and burn rate
    - Consumption breakdown by model, agent, and user
    - Usage trends and patterns
    - Budget status and alerts
    - Cost analysis and efficiency metrics
    - Optimization recommendations
    - Usage forecasts

    Args:
        workspace_id: Workspace to query
        timeframe: Time window (7d, 30d, 90d, 1y)

    Returns:
        Complete credit consumption analytics
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get credit consumption analytics
        service = CreditConsumptionService(db)
        consumption = await service.get_credit_consumption(workspace_id, timeframe)

        return consumption

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching credit consumption: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch credit consumption for workspace '{workspace_id}'"
        )


@router.get("/consumption/status")
async def get_credit_status(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current credit status only (lightweight endpoint).

    Returns only the current credit balance, burn rate, and projections
    for quick status checks without full analytics.

    Args:
        workspace_id: Workspace to query

    Returns:
        Current credit status
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get only current status
        service = CreditConsumptionService(db)
        status = await service.get_current_status(workspace_id)

        return {
            "workspaceId": workspace_id,
            "currentStatus": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching credit status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch credit status for workspace '{workspace_id}'"
        )


@router.get("/consumption/breakdown")
async def get_consumption_breakdown(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$", description="Time window"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get consumption breakdown by model, agent, and user.

    Args:
        workspace_id: Workspace to query
        timeframe: Time window

    Returns:
        Consumption breakdown analytics
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = CreditConsumptionService(db)
        start_date = service._calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        breakdown = await service.get_consumption_breakdown(
            workspace_id, start_date, end_date
        )

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "breakdown": breakdown
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching consumption breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch consumption breakdown for workspace '{workspace_id}'"
        )


@router.get("/consumption/trends")
async def get_consumption_trends(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$", description="Time window"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get consumption trends and patterns over time.

    Args:
        workspace_id: Workspace to query
        timeframe: Time window

    Returns:
        Consumption trends including daily, hourly, and weekly patterns
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = CreditConsumptionService(db)
        start_date = service._calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        trends = await service.get_consumption_trends(
            workspace_id, start_date, end_date
        )

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "trends": trends
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching consumption trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch consumption trends for workspace '{workspace_id}'"
        )


@router.get("/budget")
async def get_budget_status(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get budget status and alerts.

    Args:
        workspace_id: Workspace to query

    Returns:
        Budget configuration, utilization, and active alerts
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = CreditConsumptionService(db)
        budget = await service.get_budget_status(workspace_id)

        return {
            "workspaceId": workspace_id,
            "budget": budget
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching budget status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch budget status for workspace '{workspace_id}'"
        )


@router.get("/optimization")
async def get_optimization_recommendations(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get credit optimization recommendations.

    Analyzes usage patterns and provides actionable recommendations
    for reducing credit consumption.

    Args:
        workspace_id: Workspace to query

    Returns:
        List of optimization recommendations with potential savings
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = CreditConsumptionService(db)
        optimizations = await service.get_optimization_recommendations(workspace_id)

        return {
            "workspaceId": workspace_id,
            "optimizations": optimizations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching optimization recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch optimization recommendations for workspace '{workspace_id}'"
        )


@router.get("/forecast")
async def get_usage_forecast(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get credit usage forecast.

    Predicts future credit consumption based on historical patterns.

    Args:
        workspace_id: Workspace to query

    Returns:
        Usage forecasts for next day, week, and month with confidence intervals
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = CreditConsumptionService(db)
        forecast = await service.forecast_usage(workspace_id)

        return {
            "workspaceId": workspace_id,
            "forecast": forecast
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage forecast: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch usage forecast for workspace '{workspace_id}'"
        )
