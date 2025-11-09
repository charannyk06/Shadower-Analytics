"""Agent analytics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from datetime import date, timedelta
import logging

from ...core.database import get_db
from ...models.schemas.agents import AgentMetrics, AgentPerformance, AgentStats
from ...models.schemas.agent_analytics import AgentAnalyticsResponse
from ...services.analytics.agent_analytics_service import AgentAnalyticsService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...utils.validators import validate_agent_id, validate_workspace_id

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[AgentMetrics])
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    workspace_id: Optional[str] = None,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List all agents with basic metrics.

    Requires authentication.
    """
    # Validate workspace_id if provided
    if workspace_id:
        validate_workspace_id(workspace_id)

    # TODO: Implement agent listing with pagination and filtering
    # Should query agent_analytics_summary for basic metrics
    # Filter by user's accessible workspaces
    return []


@router.get("/{agent_id}/analytics", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    agent_id: str = Path(..., description="Agent ID", min_length=1, max_length=255),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "7d",
        description="Time range: 24h, 7d, 30d, 90d, all",
        pattern="^(24h|7d|30d|90d|all)$",
    ),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive analytics for a specific agent.

    This endpoint provides detailed performance metrics, resource usage,
    error analysis, user satisfaction, and optimization suggestions.

    **Parameters:**
    - **agent_id**: Unique identifier for the agent
    - **workspace_id**: Workspace context for the analytics
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d, all)
    - **skip_cache**: Force fresh data calculation

    **Returns:**
    - Comprehensive analytics including:
        - Performance metrics (success rate, runtime statistics)
        - Resource usage (credits, tokens, costs)
        - Error analysis (patterns, recovery metrics)
        - User metrics (ratings, feedback, usage patterns)
        - Comparative analysis (vs workspace, previous period)
        - Optimization suggestions
        - Trend data (daily and hourly)
    """
    # Validate inputs
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching analytics for agent {validated_agent_id} in workspace {validated_workspace_id} "
            f"for timeframe {timeframe} (user: {current_user.get('user_id')})"
        )

        service = AgentAnalyticsService(db)
        analytics = await service.get_agent_analytics(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
            skip_cache=skip_cache,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching agent analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent analytics: {str(e)}",
        )


@router.get("/{agent_id}", response_model=AgentPerformance)
async def get_agent_details(
    agent_id: str = Path(..., min_length=1, max_length=255),
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get detailed metrics for a specific agent.

    Requires authentication.
    """
    # Validate agent_id
    validated_agent_id = validate_agent_id(agent_id)

    # TODO: Implement detailed agent metrics for date range
    # This endpoint differs from /analytics by focusing on time-series data
    # TODO: Verify user has access to this agent
    return {
        "agent_id": validated_agent_id,
        "total_executions": 0,
        "success_rate": 0,
        "avg_duration": 0,
    }


@router.get("/{agent_id}/stats", response_model=AgentStats)
async def get_agent_statistics(
    agent_id: str = Path(..., min_length=1, max_length=255),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get statistical analysis for an agent.

    Requires authentication.
    """
    # Validate agent_id
    validated_agent_id = validate_agent_id(agent_id)

    # TODO: Implement statistical analysis (distributions, correlations, outliers)
    # TODO: Verify user has access to this agent
    return {
        "agent_id": validated_agent_id,
        "stats": {},
    }


@router.get("/{agent_id}/executions")
async def get_agent_executions(
    agent_id: str = Path(..., min_length=1, max_length=255),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get execution history for an agent.

    Requires authentication.
    """
    # Validate agent_id
    validated_agent_id = validate_agent_id(agent_id)

    # TODO: Implement execution history with pagination
    # Should query agent_runs table with filters and sorting
    # TODO: Verify user has access to this agent
    return {"executions": [], "total": 0}
