"""Agent analytics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from datetime import date, timedelta
import logging

from ...core.database import get_db
from ...models.schemas.agents import AgentMetrics, AgentPerformance, AgentStats
from ...models.schemas.agent_analytics import AgentAnalyticsResponse
from ...models.schemas.agent_lifecycle import (
    AgentLifecycleAnalytics,
    LifecycleAnalyticsQuery,
    VersionComparisonRequest,
    VersionComparisonResponse,
    RetirementCandidatesQuery,
    LifecycleEventCreate,
    LifecycleEvent,
)
from ...services.analytics.agent_analytics_service import AgentAnalyticsService
from ...services.analytics.agent_lifecycle_service import AgentLifecycleService
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


# ============================================================================
# Lifecycle Analytics Endpoints
# ============================================================================


@router.get("/{agent_id}/lifecycle")
async def get_agent_lifecycle_analytics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "all",
        description="Time range: 24h, 7d, 30d, 90d, all",
        pattern="^(24h|7d|30d|90d|all)$",
    ),
    include_predictions: bool = Query(False, description="Include predictive analytics"),
    include_versions: bool = Query(True, description="Include version data"),
    include_deployments: bool = Query(True, description="Include deployment metrics"),
    include_health: bool = Query(True, description="Include health scores"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive lifecycle analytics for an agent.

    Tracks agent lifecycle including:
    - Current state and state history
    - State transitions and durations
    - Version history and performance comparison
    - Deployment metrics and patterns
    - Health scores and trends
    - Retirement risk assessment

    **Parameters:**
    - **agent_id**: Unique identifier for the agent
    - **workspace_id**: Workspace context
    - **timeframe**: Time range for analysis
    - **include_predictions**: Include predictive analytics
    - **include_versions**: Include version comparison data
    - **include_deployments**: Include deployment metrics
    - **include_health**: Include health score data

    **Returns:**
    - Comprehensive lifecycle analytics including state transitions, versions,
      deployments, health scores, and retirement risk assessment
    """
    # Validate inputs
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching lifecycle analytics for agent {validated_agent_id} "
            f"in workspace {validated_workspace_id} for timeframe {timeframe} "
            f"(user: {current_user.get('user_id')})"
        )

        service = AgentLifecycleService(db)
        analytics = await service.get_lifecycle_analytics(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
            include_predictions=include_predictions,
            include_versions=include_versions,
            include_deployments=include_deployments,
            include_health=include_health,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching lifecycle analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch lifecycle analytics: {str(e)}",
        )


@router.get("/{agent_id}/lifecycle/transitions")
async def get_lifecycle_transitions(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "30d",
        description="Time range: 24h, 7d, 30d, 90d, all",
        pattern="^(24h|7d|30d|90d|all)$",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get detailed state transition history for an agent.

    Returns all state transitions within the specified timeframe,
    including transition reasons, durations, and metadata.
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        from ...utils.datetime import calculate_start_date

        service = AgentLifecycleService(db)
        start_date = calculate_start_date(timeframe)
        transitions = await service._get_state_transitions(validated_agent_id, start_date)

        return {
            "agentId": validated_agent_id,
            "workspaceId": validated_workspace_id,
            "timeframe": timeframe,
            "transitions": transitions,
            "totalTransitions": len(transitions),
        }

    except Exception as e:
        logger.error(f"Error fetching state transitions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch state transitions: {str(e)}",
        )


@router.get("/{agent_id}/lifecycle/status")
async def get_lifecycle_status(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get current lifecycle status (lightweight endpoint for polling).

    Returns only the current state and basic information without
    historical data. Useful for frequent polling and status checks.
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        service = AgentLifecycleService(db)
        current_state = await service._get_current_state(validated_agent_id)

        return {
            "agentId": validated_agent_id,
            "workspaceId": validated_workspace_id,
            "currentState": current_state,
        }

    except Exception as e:
        logger.error(f"Error fetching lifecycle status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch lifecycle status: {str(e)}",
        )


@router.post("/{agent_id}/lifecycle/events", response_model=Dict[str, str])
async def record_lifecycle_event(
    agent_id: str = Path(..., description="Agent ID"),
    event: LifecycleEventCreate = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Record a lifecycle event for an agent.

    Use this endpoint to manually record state changes, deployments,
    or other lifecycle events.
    """
    validated_agent_id = validate_agent_id(agent_id)

    try:
        service = AgentLifecycleService(db)
        event_id = await service.record_lifecycle_event(
            agent_id=validated_agent_id,
            workspace_id=event.workspace_id,
            event_type=event.event_type,
            previous_state=event.previous_state,
            new_state=event.new_state,
            triggered_by=event.triggered_by,
            metadata=event.metadata,
        )

        return {
            "eventId": event_id,
            "message": "Lifecycle event recorded successfully",
        }

    except Exception as e:
        logger.error(f"Error recording lifecycle event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record lifecycle event: {str(e)}",
        )


@router.get("/{agent_id}/versions/compare")
async def compare_agent_versions(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    version_a: str = Query(..., description="First version to compare"),
    version_b: str = Query(..., description="Second version to compare"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Compare performance between two agent versions.

    Provides side-by-side comparison of performance metrics, costs,
    reliability, and other key indicators between specified versions.
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        service = AgentLifecycleService(db)
        version_performance = await service._get_version_performance(validated_agent_id)

        # Find the specified versions
        version_a_data = next((v for v in version_performance if v["version"] == version_a), None)
        version_b_data = next((v for v in version_performance if v["version"] == version_b), None)

        if not version_a_data:
            raise HTTPException(status_code=404, detail=f"Version {version_a} not found")
        if not version_b_data:
            raise HTTPException(status_code=404, detail=f"Version {version_b} not found")

        # Calculate comparison metrics
        comparison = {
            "executionsDelta": version_b_data["totalExecutions"] - version_a_data["totalExecutions"],
            "successRateDelta": version_b_data["successRate"] - version_a_data["successRate"],
            "avgDurationDelta": version_b_data["avgDuration"] - version_a_data["avgDuration"],
            "avgCreditsDelta": version_b_data["avgCredits"] - version_a_data["avgCredits"],
            "errorCountDelta": version_b_data["errorCount"] - version_a_data["errorCount"],
        }

        # Generate recommendation
        recommendation = "Version B shows improvement" if comparison["successRateDelta"] > 0 else "Consider rollback to Version A"

        return {
            "agentId": validated_agent_id,
            "versionA": version_a_data,
            "versionB": version_b_data,
            "comparison": comparison,
            "recommendation": recommendation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing versions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare versions: {str(e)}",
        )
