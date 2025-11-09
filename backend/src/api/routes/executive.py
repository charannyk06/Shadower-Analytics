"""Executive dashboard routes - CEO metrics and KPIs with caching."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from datetime import datetime

from ...core.database import get_db
from ...models.schemas.metrics import ExecutiveMetrics, TimeRange
from ...services.metrics.executive_service import executive_metrics_service
from ..dependencies.auth import get_current_user, require_owner_or_admin
from ..middleware.workspace import WorkspaceAccess

router = APIRouter(prefix="/api/v1/executive", tags=["executive"])


@router.get("/overview")
async def get_executive_overview(
    workspace_id: str = Query(None, description="Workspace ID to query"),
    timeframe: str = Query(
        "30d", regex="^(24h|7d|30d|90d)$", description="Time period"
    ),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db=Depends(get_db),
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

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get metrics from cached service
    metrics = await executive_metrics_service.get_executive_overview(
        workspace_id=workspace_id, timeframe=timeframe, skip_cache=skip_cache
    )

    # Add metadata about cache status
    metrics["_meta"] = {
        "cached": not skip_cache,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return metrics


@router.get("/revenue")
async def get_revenue_metrics(
    workspace_id: str = Query(None, description="Workspace ID to query"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    skip_cache: bool = Query(False, description="Skip cache"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db=Depends(get_db),
):
    """Get revenue metrics and trends (cached).

    Requires: owner or admin role

    Cache TTL: 30 minutes
    """
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get("workspace_id")

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get metrics from cached service
    metrics = await executive_metrics_service.get_revenue_metrics(
        workspace_id=workspace_id, timeframe=timeframe, skip_cache=skip_cache
    )

    return metrics


@router.get("/kpis")
async def get_key_performance_indicators(
    workspace_id: str = Query(None, description="Workspace ID to query"),
    skip_cache: bool = Query(False, description="Skip cache"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db=Depends(get_db),
):
    """Get key performance indicators for executive dashboard (cached).

    Requires: owner or admin role

    Cache TTL: 5 minutes
    """
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get("workspace_id")

    # Validate workspace access
    await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

    # Get KPIs from cached service
    kpis = await executive_metrics_service.get_key_performance_indicators(
        workspace_id=workspace_id, skip_cache=skip_cache
    )

    return kpis
