"""General metrics and analytics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ...core.database import get_db
from ...services.metrics.execution_metrics import ExecutionMetricsService
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

# Rate limiter specifically for realtime metrics (higher frequency endpoint)
metrics_realtime_limiter = RateLimiter(
    requests_per_minute=20,  # Allow 20 requests per minute (every 3 seconds)
    requests_per_hour=300,
)


@router.get("/summary")
async def get_metrics_summary(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db=Depends(get_db),
):
    """Get summary of all metrics."""
    # Implementation will be added
    return {
        "users": {},
        "agents": {},
        "executions": {},
        "revenue": {},
    }


@router.get("/trends")
async def get_metrics_trends(
    metric_type: str = Query(..., regex="^(users|agents|executions|revenue)$"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db=Depends(get_db),
):
    """Get trend data for a specific metric."""
    # Implementation will be added
    return {"trend": [], "summary": {}}


@router.get("/comparison")
async def compare_metrics(
    metric_type: str = Query(...),
    current_start: date = Query(...),
    current_end: date = Query(...),
    previous_start: date = Query(...),
    previous_end: date = Query(...),
    db=Depends(get_db),
):
    """Compare metrics between two time periods."""
    # Implementation will be added
    return {
        "current": {},
        "previous": {},
        "change": {},
        "change_percentage": {},
    }


@router.get("/realtime")
async def get_realtime_metrics(
    db=Depends(get_db),
):
    """Get real-time metrics (last 5 minutes)."""
    # Implementation will be added
    return {
        "active_users": 0,
        "active_executions": 0,
        "requests_per_second": 0,
    }


@router.get("/execution")
async def get_execution_metrics(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("1h", regex="^(1h|6h|24h|7d|30d|90d)$", description="Time window"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive execution metrics.

    Returns real-time and historical execution metrics including:
    - Real-time execution status (currently running, queue depth)
    - Throughput metrics (executions per minute/hour/day)
    - Latency percentiles (p50, p75, p90, p95, p99)
    - Performance metrics (success rates, failures)
    - Execution patterns and anomalies
    - Resource utilization

    Args:
        workspace_id: Workspace to query metrics for
        timeframe: Time window (1h, 6h, 24h, 7d, 30d, 90d)

    Returns:
        Comprehensive execution metrics object
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get execution metrics
        service = ExecutionMetricsService(db)
        metrics = await service.get_execution_metrics(workspace_id, timeframe)

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch execution metrics for workspace '{workspace_id}' and timeframe '{timeframe}'"
        )


@router.get("/execution/realtime")
async def get_execution_realtime(
    request: Request,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time execution status only.

    Lightweight endpoint for frequent polling of real-time execution status.
    Returns only currently running executions and queue status.

    Rate limited to 20 requests per minute to prevent database overload.

    Args:
        workspace_id: Workspace to query

    Returns:
        Real-time execution status including running executions and queue depth
    """
    try:
        # Apply rate limiting
        client_ip = request.client.host if request.client else "unknown"
        user_id = current_user.get("sub")
        identifier = user_id or client_ip

        allowed, error_msg = await metrics_realtime_limiter.check_rate_limit(
            identifier, f"/metrics/execution/realtime/{workspace_id}"
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier} on realtime metrics")
            raise HTTPException(
                status_code=429,
                detail=error_msg,
                headers={"Retry-After": "60"}
            )

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get only realtime metrics
        service = ExecutionMetricsService(db)
        realtime = await service.get_realtime_metrics(workspace_id)

        return {
            "workspaceId": workspace_id,
            "realtime": realtime
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching realtime execution metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch realtime execution metrics for workspace '{workspace_id}'"
        )


@router.get("/execution/throughput")
async def get_execution_throughput(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution throughput metrics and trends.

    Args:
        workspace_id: Workspace to query
        timeframe: Time window

    Returns:
        Throughput metrics including executions per time unit and trends
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get throughput metrics
        service = ExecutionMetricsService(db)
        metrics = await service.get_execution_metrics(workspace_id, timeframe)

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "throughput": metrics['throughput']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching throughput metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch throughput metrics for workspace '{workspace_id}' and timeframe '{timeframe}'"
        )


@router.get("/execution/latency")
async def get_execution_latency(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution latency metrics and distribution.

    Args:
        workspace_id: Workspace to query
        timeframe: Time window

    Returns:
        Latency percentiles and distribution
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get latency metrics
        service = ExecutionMetricsService(db)
        metrics = await service.get_execution_metrics(workspace_id, timeframe)

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "latency": metrics['latency']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latency metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latency metrics for workspace '{workspace_id}' and timeframe '{timeframe}'"
        )
