"""Executive dashboard routes - CEO metrics and KPIs with caching."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import re
import logging

from ...core.database import get_db
from ...core.constants import TIMEFRAME_REGEX
from ...models.schemas.metrics import (
    ExecutiveMetrics,
    ExecutiveDashboardResponse,
    TimeRange,
)
from ...services.metrics.executive_service import (
    executive_metrics_service,
    get_executive_dashboard_data,
)
from ..dependencies.auth import get_current_user, require_owner_or_admin
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/executive", tags=["executive"])

# Rate limiter for executive dashboard endpoints
# More generous limits than auth, but still protected
executive_rate_limiter = RateLimiter(
    requests_per_minute=30,  # 30 requests per minute
    requests_per_hour=500,   # 500 requests per hour
)

# UUID validation pattern (supports both UUID and other ID formats)
WORKSPACE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


async def apply_rate_limit(request: Request):
    """Apply rate limiting to executive dashboard endpoints."""
    # Get client identifier (IP address or user ID if authenticated)
    client_ip = request.client.host if request.client else "unknown"
    user_id = getattr(request.state, "user", {}).get("sub")
    identifier = user_id or client_ip
    endpoint = request.url.path

    # Check rate limit
    allowed, error_msg = await executive_rate_limiter.check_rate_limit(identifier, endpoint)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=error_msg or "Rate limit exceeded",
            headers={"Retry-After": "60"},
        )


def validate_workspace_id(workspace_id: str) -> str:
    """
    Validate workspace ID format.

    Args:
        workspace_id: The workspace ID to validate

    Returns:
        The validated workspace ID

    Raises:
        HTTPException: If workspace ID is invalid
    """
    if not workspace_id or len(workspace_id) > 255:
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace ID: must be between 1 and 255 characters"
        )

    if not WORKSPACE_ID_PATTERN.match(workspace_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace ID format: only alphanumeric, hyphens, and underscores allowed"
        )

    return workspace_id


@router.get("/dashboard", response_model=ExecutiveDashboardResponse)
async def get_executive_dashboard(
    request: Request,
    workspace_id: str = Query(None, description="Workspace ID to query"),
    timeframe: str = Query("7d", regex="^(24h|7d|30d|90d|all)$"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive executive dashboard with all metrics, trends, and KPIs.

    Requires: owner or admin role

    Args:
        workspace_id: Target workspace (defaults to user's workspace)
        timeframe: Time period - 24h, 7d, 30d, 90d, or all

    Returns:
        Complete dashboard data including:
        - User metrics (DAU/WAU/MAU)
        - Execution metrics (runs, success rate, credits)
        - Business metrics (MRR, ARR, LTV, CAC, churn)
        - Agent metrics (top agents, performance)
        - Trend data (time-series for charts)
        - Active alerts
        - Top users
    """
    try:
        # Apply rate limiting
        await apply_rate_limit(request)

        # Use current workspace if not specified
        if not workspace_id:
            workspace_id = current_user.get("workspace_id")

        if not workspace_id:
            raise HTTPException(status_code=400, detail="Workspace ID required")

        # Validate workspace ID format
        workspace_id = validate_workspace_id(workspace_id)

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get comprehensive dashboard data
        dashboard_data = await get_executive_dashboard_data(
            db=db,
            workspace_id=workspace_id,
            timeframe=timeframe,
        )

        return dashboard_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching executive dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch executive dashboard data"
        )


@router.get("/overview", response_model=ExecutiveMetrics, dependencies=[Depends(apply_rate_limit)])
async def get_executive_overview(
    request: Request,
    workspace_id: str = Query(None, description="Workspace ID to query"),
    timeframe: str = Query(
        "30d", regex="^(24h|7d|30d|90d)$", description="Time period"
    ),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get executive dashboard overview with key business metrics (cached).

    Requires: owner or admin role

    Includes:
    - MRR (Monthly Recurring Revenue)
    - Churn rate
    - LTV (Lifetime Value)
    - DAU/WAU/MAU (Daily/Weekly/Monthly Active Users)
    - Agent performance metrics
    - Revenue trends

    Cache TTL: 30 minutes (can be bypassed with skip_cache=true)
    """
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get("workspace_id")

    # Validate workspace ID format
    if not workspace_id:
        raise HTTPException(status_code=400, detail="Workspace ID is required")

    workspace_id = validate_workspace_id(workspace_id)

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get metrics from cached service
    metrics = await executive_metrics_service.get_executive_overview(
        workspace_id=workspace_id, timeframe=timeframe, skip_cache=skip_cache, db=db
    )

    # Add metadata about cache status with timezone-aware timestamp
    metrics["_meta"] = {
        "cached": not skip_cache,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return metrics


@router.get("/revenue", dependencies=[Depends(apply_rate_limit)])
async def get_revenue_metrics(
    request: Request,
    workspace_id: str = Query(None, description="Workspace ID to query"),
    timeframe: str = Query("30d", regex=TIMEFRAME_REGEX),
    skip_cache: bool = Query(False, description="Skip cache"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get revenue metrics and trends (cached).

    Requires: owner or admin role

    Cache TTL: 30 minutes
    """
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get("workspace_id")

    # Validate workspace ID format
    if not workspace_id:
        raise HTTPException(status_code=400, detail="Workspace ID is required")

    workspace_id = validate_workspace_id(workspace_id)

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get metrics from cached service
    metrics = await executive_metrics_service.get_revenue_metrics(
        workspace_id=workspace_id, timeframe=timeframe, skip_cache=skip_cache, db=db
    )

    return metrics


@router.get("/kpis", dependencies=[Depends(apply_rate_limit)])
async def get_key_performance_indicators(
    request: Request,
    workspace_id: str = Query(None, description="Workspace ID to query"),
    skip_cache: bool = Query(False, description="Skip cache"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get key performance indicators for executive dashboard (cached).

    Requires: owner or admin role

    Cache TTL: 5 minutes
    """
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get("workspace_id")

    # Validate workspace ID format
    if not workspace_id:
        raise HTTPException(status_code=400, detail="Workspace ID is required")

    workspace_id = validate_workspace_id(workspace_id)

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get KPIs from cached service
    kpis = await executive_metrics_service.get_key_performance_indicators(
        workspace_id=workspace_id, skip_cache=skip_cache, db=db
    )

    return kpis
