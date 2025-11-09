"""
Materialized Views API Routes

Provides endpoints for:
- Refreshing materialized views
- Checking view status and health
- Getting view statistics
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.materialized_views import MaterializedViewRefreshService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materialized-views", tags=["materialized-views"])


# =====================================================================
# Request/Response Models
# =====================================================================


class RefreshRequest(BaseModel):
    """Request model for refreshing materialized views"""

    views: Optional[List[str]] = Field(
        None,
        description="List of specific views to refresh. If None, refreshes all views."
    )
    concurrent: bool = Field(
        True,
        description="Use CONCURRENTLY option for non-blocking refresh"
    )
    use_db_function: bool = Field(
        False,
        description="Use database function for refresh with enhanced error handling"
    )


class RefreshResult(BaseModel):
    """Result of a materialized view refresh operation"""

    view_name: str
    success: bool
    started_at: str
    completed_at: str
    duration_seconds: float
    error: Optional[str] = None


class RefreshResponse(BaseModel):
    """Response containing refresh results"""

    results: List[RefreshResult]
    total_views: int
    successful: int
    failed: int
    total_duration_seconds: float


class ViewStatus(BaseModel):
    """Status information for a materialized view"""

    view_name: str
    owner: str
    is_populated: bool
    has_indexes: bool
    total_size: str
    data_size: str
    index_size: str
    description: Optional[str] = None


class ViewStatistics(BaseModel):
    """Detailed statistics for a materialized view"""

    schema: str
    view_name: str
    rows_inserted: int
    rows_updated: int
    rows_deleted: int
    live_rows: int
    dead_rows: int
    last_vacuum: Optional[str] = None
    last_autovacuum: Optional[str] = None
    last_analyze: Optional[str] = None
    last_autoanalyze: Optional[str] = None
    vacuum_count: int
    autovacuum_count: int
    analyze_count: int
    autoanalyze_count: int


class ViewHealth(BaseModel):
    """Health check result for a materialized view"""

    view_name: str
    healthy: bool
    issues: List[str]


class HealthCheckResponse(BaseModel):
    """Response containing health check results"""

    views: List[ViewHealth]
    total_views: int
    healthy_views: int
    unhealthy_views: int


# =====================================================================
# API Endpoints
# =====================================================================


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_materialized_views(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh materialized views.

    This endpoint refreshes one or more materialized views. By default, it refreshes
    all views, but you can specify a subset of views to refresh.

    Parameters:
    - **views**: Optional list of view names to refresh
    - **concurrent**: Use CONCURRENTLY option (default: true)
    - **use_db_function**: Use database function for refresh (default: false)

    Returns:
    - Refresh results including timing and success status for each view
    """
    service = MaterializedViewRefreshService(db)

    try:
        if request.use_db_function:
            results = await service.refresh_using_function(
                concurrent_mode=request.concurrent
            )
        else:
            results = await service.refresh_all(
                concurrent=request.concurrent,
                views=request.views
            )

        # Calculate summary statistics
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        total_duration = sum(r["duration_seconds"] for r in results)

        return RefreshResponse(
            results=[RefreshResult(**r) for r in results],
            total_views=len(results),
            successful=successful,
            failed=failed,
            total_duration_seconds=total_duration
        )

    except Exception as e:
        logger.error(f"Failed to refresh materialized views: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh materialized views: {str(e)}"
        )


@router.post("/refresh/{view_name}", response_model=RefreshResult)
async def refresh_single_view(
    view_name: str,
    concurrent: bool = Query(True, description="Use CONCURRENTLY option"),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh a single materialized view.

    Parameters:
    - **view_name**: Name of the materialized view to refresh
    - **concurrent**: Use CONCURRENTLY option (default: true)

    Returns:
    - Refresh result including timing and success status
    """
    service = MaterializedViewRefreshService(db)

    try:
        result = await service.refresh_view(view_name, concurrent=concurrent)
        return RefreshResult(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refresh view {view_name}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh view: {str(e)}"
        )


@router.get("/status", response_model=List[ViewStatus])
async def get_views_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get status information for all materialized views.

    Returns:
    - List of view status including size, population status, and description
    """
    service = MaterializedViewRefreshService(db)

    try:
        status = await service.get_refresh_status()
        return [ViewStatus(**s) for s in status]

    except Exception as e:
        logger.error(f"Failed to get view status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get view status: {str(e)}"
        )


@router.get("/statistics/{view_name}", response_model=ViewStatistics)
async def get_view_statistics(
    view_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed statistics for a specific materialized view.

    Parameters:
    - **view_name**: Name of the materialized view

    Returns:
    - Detailed statistics including row counts, vacuum/analyze info
    """
    service = MaterializedViewRefreshService(db)

    try:
        stats = await service.get_view_statistics(view_name)

        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Statistics not found for view: {view_name}"
            )

        return ViewStatistics(**stats)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get statistics for view {view_name}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get view statistics: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def check_views_health(
    db: AsyncSession = Depends(get_db)
):
    """
    Check the health of all materialized views.

    Performs health checks including:
    - View population status
    - Index existence
    - Row count validation

    Returns:
    - Health check results for all views
    """
    service = MaterializedViewRefreshService(db)

    try:
        health_results = await service.check_view_health()

        healthy_count = sum(1 for h in health_results if h["healthy"])
        unhealthy_count = len(health_results) - healthy_count

        return HealthCheckResponse(
            views=[ViewHealth(**h) for h in health_results],
            total_views=len(health_results),
            healthy_views=healthy_count,
            unhealthy_views=unhealthy_count
        )

    except Exception as e:
        logger.error(f"Failed to check view health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check view health: {str(e)}"
        )


@router.get("/{view_name}/row-count")
async def get_view_row_count(
    view_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the number of rows in a materialized view.

    Parameters:
    - **view_name**: Name of the materialized view

    Returns:
    - Row count for the specified view
    """
    service = MaterializedViewRefreshService(db)

    try:
        count = await service.get_row_count(view_name)
        return {
            "view_name": view_name,
            "row_count": count
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to get row count for view {view_name}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get row count: {str(e)}"
        )


@router.get("/views/list")
async def list_available_views():
    """
    List all available materialized views managed by this service.

    Returns:
    - List of view names
    """
    return {
        "views": MaterializedViewRefreshService.VIEWS,
        "total": len(MaterializedViewRefreshService.VIEWS)
    }
