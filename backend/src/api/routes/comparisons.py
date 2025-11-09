"""
Comparison Views API Routes
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.comparison_views import (
    ComparisonRequest,
    ComparisonResponse,
    ComparisonType,
    ComparisonFilters,
    ComparisonOptions,
    ExportFormat,
)
from src.services.comparison_service import ComparisonService

router = APIRouter(prefix="/api/v1/comparisons", tags=["comparisons"])


@router.post("/", response_model=ComparisonResponse)
async def create_comparison(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Generate a comparison based on the specified type and filters

    Args:
        request: Comparison request with type, filters, and options
        db: Database session

    Returns:
        ComparisonResponse with comparison data

    Raises:
        HTTPException: If comparison generation fails
    """
    try:
        service = ComparisonService(db)
        response = await service.generate_comparison(
            comparison_type=request.type,
            filters=request.filters,
            options=request.options,
        )

        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.error.message if response.error else "Comparison failed",
            )

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate comparison: {str(e)}",
        )


@router.post("/agents", response_model=ComparisonResponse)
async def compare_agents(
    agent_ids: list[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_recommendations: bool = True,
    include_visual_diff: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Compare multiple agents

    Args:
        agent_ids: List of agent IDs to compare (2-10 agents)
        start_date: Start date for metrics (optional)
        end_date: End date for metrics (optional)
        include_recommendations: Include optimization recommendations
        include_visual_diff: Include visual diff highlighting
        db: Database session

    Returns:
        ComparisonResponse with agent comparison data

    Raises:
        HTTPException: If agent comparison fails or invalid parameters
    """
    if len(agent_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 agents required for comparison",
        )

    if len(agent_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 agents allowed for comparison",
        )

    filters = ComparisonFilters(
        agent_ids=agent_ids,
        start_date=start_date,
        end_date=end_date,
    )

    options = ComparisonOptions(
        include_recommendations=include_recommendations,
        include_visual_diff=include_visual_diff,
    )

    service = ComparisonService(db)
    return await service.generate_comparison(
        comparison_type=ComparisonType.AGENTS,
        filters=filters,
        options=options,
    )


@router.post("/periods", response_model=ComparisonResponse)
async def compare_periods(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_time_series: bool = True,
    workspace_ids: Optional[list[str]] = None,
    agent_ids: Optional[list[str]] = None,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Compare current period with previous period

    Args:
        start_date: Start date of current period (optional, defaults to 7 days ago)
        end_date: End date of current period (optional, defaults to now)
        include_time_series: Include time series comparison data
        workspace_ids: Filter by workspace IDs (optional)
        agent_ids: Filter by agent IDs (optional)
        db: Database session

    Returns:
        ComparisonResponse with period comparison data
    """
    filters = ComparisonFilters(
        start_date=start_date,
        end_date=end_date,
        workspace_ids=workspace_ids,
        agent_ids=agent_ids,
    )

    options = ComparisonOptions(
        include_time_series=include_time_series,
    )

    service = ComparisonService(db)
    return await service.generate_comparison(
        comparison_type=ComparisonType.PERIODS,
        filters=filters,
        options=options,
    )


@router.post("/workspaces", response_model=ComparisonResponse)
async def compare_workspaces(
    workspace_ids: list[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_statistics: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Compare multiple workspaces

    Args:
        workspace_ids: List of workspace IDs to compare (2-20 workspaces)
        start_date: Start date for metrics (optional)
        end_date: End date for metrics (optional)
        include_statistics: Include statistical analysis
        db: Database session

    Returns:
        ComparisonResponse with workspace comparison data

    Raises:
        HTTPException: If workspace comparison fails or invalid parameters
    """
    if len(workspace_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 workspaces required for comparison",
        )

    if len(workspace_ids) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 workspaces allowed for comparison",
        )

    filters = ComparisonFilters(
        workspace_ids=workspace_ids,
        start_date=start_date,
        end_date=end_date,
    )

    options = ComparisonOptions(
        include_statistics=include_statistics,
    )

    service = ComparisonService(db)
    return await service.generate_comparison(
        comparison_type=ComparisonType.WORKSPACES,
        filters=filters,
        options=options,
    )


@router.post("/metrics", response_model=ComparisonResponse)
async def compare_metrics(
    metric_name: str,
    workspace_ids: Optional[list[str]] = None,
    agent_ids: Optional[list[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_correlations: bool = False,
    include_statistics: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Compare a specific metric across entities

    Args:
        metric_name: Name of the metric to compare
        workspace_ids: Filter by workspace IDs (optional)
        agent_ids: Filter by agent IDs (optional)
        start_date: Start date for metrics (optional)
        end_date: End date for metrics (optional)
        include_correlations: Include correlation analysis with other metrics
        include_statistics: Include statistical analysis
        db: Database session

    Returns:
        ComparisonResponse with metric comparison data
    """
    filters = ComparisonFilters(
        metric_names=[metric_name],
        workspace_ids=workspace_ids,
        agent_ids=agent_ids,
        start_date=start_date,
        end_date=end_date,
    )

    options = ComparisonOptions(
        include_correlations=include_correlations,
        include_statistics=include_statistics,
    )

    service = ComparisonService(db)
    return await service.generate_comparison(
        comparison_type=ComparisonType.METRICS,
        filters=filters,
        options=options,
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for comparison service

    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "comparison-views",
        "timestamp": datetime.utcnow().isoformat(),
    }
