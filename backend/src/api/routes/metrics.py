"""General metrics and analytics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ...core.database import get_db
from ...services.metrics.execution_metrics import ExecutionMetricsService
from ...services.analytics.trend_analysis_service import TrendAnalysisService
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

# Rate limiter specifically for realtime metrics (higher frequency endpoint)
metrics_realtime_limiter = RateLimiter(
    requests_per_minute=20,  # Allow 20 requests per minute (every 3 seconds)
    requests_per_hour=300,
)

# Rate limiter for trend analysis (computationally expensive endpoint)
trend_analysis_limiter = RateLimiter(
    requests_per_minute=2,   # Allow 2 requests per minute
    requests_per_hour=50,    # Maximum 50 requests per hour
)


@router.get("/summary")
async def get_metrics_summary(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get summary of all metrics.

    Requires authentication.
    """
    # Implementation will be added
    return {
        "users": {},
        "agents": {},
        "executions": {},
        "revenue": {},
    }


@router.get("/trends")
async def get_metrics_trends(
    metric_type: str = Query(..., pattern="^(users|agents|executions|revenue)$"),
    timeframe: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get trend data for a specific metric.

    Requires authentication.
    """
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
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Compare metrics between two time periods.

    Requires authentication.
    """
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
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get real-time metrics (last 5 minutes).

    Requires authentication.
    """
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
            detail=f"Failed to fetch execution metrics for workspace '{workspace_id}' and timeframe '{timeframe}'",
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
            raise HTTPException(status_code=429, detail=error_msg, headers={"Retry-After": "60"})

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get only realtime metrics
        service = ExecutionMetricsService(db)
        realtime = await service.get_realtime_metrics(workspace_id)

        return {"workspaceId": workspace_id, "realtime": realtime}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching realtime execution metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch realtime execution metrics for workspace '{workspace_id}'",
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
            "throughput": metrics["throughput"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching throughput metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch throughput metrics for workspace '{workspace_id}' and timeframe '{timeframe}'",
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

        return {"workspaceId": workspace_id, "timeframe": timeframe, "latency": metrics["latency"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latency metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latency metrics for workspace '{workspace_id}' and timeframe '{timeframe}'",
        )


@router.get("/trends/analysis")
async def get_trend_analysis(
    request: Request,
    workspace_id: str = Query(..., description="Workspace ID"),
    metric: str = Query(
        ...,
        regex="^(executions|users|credits|errors|success_rate)$",
        description="Metric to analyze",
    ),
    timeframe: str = Query(
        "30d", regex="^(7d|30d|90d|1y)$", description="Time window for analysis"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive trend analysis for a metric.

    Performs advanced time-series analysis including:
    - Trend decomposition (trend, seasonal, residual)
    - Seasonality detection and pattern recognition
    - Growth rate calculations and projections
    - Anomaly detection in trends
    - Period-over-period comparisons
    - Predictive forecasting (short and long term)
    - Actionable insights and recommendations

    Rate Limited: 2 requests per minute, 50 per hour (computationally expensive)

    Args:
        workspace_id: Workspace to analyze
        metric: Metric to analyze (executions, users, credits, errors, success_rate, revenue)
        timeframe: Time window (7d, 30d, 90d, 1y)

    Returns:
        Comprehensive trend analysis with forecasts, patterns, and insights
    """
    try:
        # Apply rate limiting
        client_ip = request.client.host if request.client else "unknown"
        user_id = current_user.get("sub")
        identifier = user_id or client_ip

        allowed, error_msg = await trend_analysis_limiter.check_rate_limit(
            identifier, f"/metrics/trends/analysis/{workspace_id}"
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for trend analysis",
                extra={
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "ip": client_ip
                }
            )
            raise HTTPException(
                status_code=429,
                detail=error_msg,
                headers={"Retry-After": "60"}
            )

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get trend analysis with timeout protection
        service = TrendAnalysisService(db)

        try:
            # 30-second timeout for analysis (Prophet can be slow)
            async with asyncio.timeout(30):
                analysis = await service.analyze_trend(
                    workspace_id,
                    metric,
                    timeframe,
                    user_id=user_id  # Pass user_id for cache scoping
                )
        except asyncio.TimeoutError:
            logger.error(
                f"Trend analysis timeout",
                extra={
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "timeframe": timeframe
                }
            )
            raise HTTPException(
                status_code=504,
                detail="Analysis timeout - please try a shorter timeframe"
            )

        return analysis

    except HTTPException:
        raise
    except ValueError as e:
        # Input validation errors (safe to expose)
        logger.warning(f"Invalid input for trend analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        # Access control errors
        logger.warning(
            f"Unauthorized trend analysis access attempt",
            extra={"user_id": user_id}
        )
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        # Internal errors - don't expose details
        logger.error(
            f"Error in trend analysis",
            exc_info=True,
            extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to complete trend analysis"
        )
