"""Leaderboard routes for competitive rankings."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException
import logging

from ...core.database import get_db
from ...models.schemas.leaderboards import (
    AgentLeaderboardQuery,
    UserLeaderboardQuery,
    WorkspaceLeaderboardQuery,
    TimeFrame,
    AgentCriteria,
    UserCriteria,
    WorkspaceCriteria,
)
from ...services.analytics.leaderboard_service import LeaderboardService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...middleware.rate_limit import RateLimiter
from ...utils.validators import validate_workspace_id

router = APIRouter(prefix="/api/v1/leaderboards", tags=["leaderboards"])
logger = logging.getLogger(__name__)

# Rate limiters for leaderboard endpoints
# Leaderboards are computationally expensive, so we limit requests
rate_limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)


@router.get("/agents")
async def get_agent_leaderboard(
    workspace_id: str = Query(..., description="Workspace ID to filter by"),
    timeframe: TimeFrame = Query(
        TimeFrame.SEVEN_DAYS,
        description="Time range for rankings: 24h, 7d, 30d, 90d, all",
    ),
    criteria: AgentCriteria = Query(
        AgentCriteria.SUCCESS_RATE,
        description="Ranking criteria: runs, success_rate, speed, efficiency, popularity",
    ),
    limit: int = Query(100, ge=1, le=500, description="Number of rankings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get agent leaderboard rankings.

    This endpoint provides competitive rankings for agents based on various
    performance criteria such as total runs, success rate, speed, efficiency,
    and popularity.

    **Parameters:**
    - **workspace_id**: Workspace to get rankings for
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d, all)
    - **criteria**: Ranking criteria (runs, success_rate, speed, efficiency, popularity)
    - **limit**: Maximum number of rankings to return (1-500)
    - **offset**: Offset for pagination

    **Returns:**
    - Agent leaderboard with rankings including:
        - Rank and rank change
        - Agent information
        - Performance metrics
        - Score and percentile
        - Achievement badges
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching agent leaderboard for workspace {validated_workspace_id} "
            f"with criteria {criteria.value} and timeframe {timeframe.value} "
            f"(user: {current_user.get('user_id')})"
        )

        query = AgentLeaderboardQuery(
            timeframe=timeframe,
            criteria=criteria,
            limit=limit,
            offset=offset,
            workspaceId=validated_workspace_id,
        )

        service = LeaderboardService(db)
        leaderboard = await service.get_agent_leaderboard(
            workspace_id=validated_workspace_id,
            query=query,
        )

        return leaderboard

    except ValueError as e:
        logger.warning(f"Validation error in agent leaderboard: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching agent leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch agent leaderboard. Please try again later."
        )


@router.get("/users")
async def get_user_leaderboard(
    workspace_id: str = Query(..., description="Workspace ID to filter by"),
    timeframe: TimeFrame = Query(
        TimeFrame.SEVEN_DAYS,
        description="Time range for rankings: 24h, 7d, 30d, 90d, all",
    ),
    criteria: UserCriteria = Query(
        UserCriteria.ACTIVITY,
        description="Ranking criteria: activity, efficiency, contribution, savings",
    ),
    limit: int = Query(100, ge=1, le=500, description="Number of rankings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get user leaderboard rankings.

    This endpoint provides competitive rankings for users based on various
    criteria such as activity level, efficiency, contribution, and cost savings.

    **Parameters:**
    - **workspace_id**: Workspace to get rankings for
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d, all)
    - **criteria**: Ranking criteria (activity, efficiency, contribution, savings)
    - **limit**: Maximum number of rankings to return (1-500)
    - **offset**: Offset for pagination

    **Returns:**
    - User leaderboard with rankings including:
        - Rank and rank change
        - User information
        - Performance metrics
        - Score and percentile
        - Achievements
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching user leaderboard for workspace {validated_workspace_id} "
            f"with criteria {criteria.value} and timeframe {timeframe.value} "
            f"(user: {current_user.get('user_id')})"
        )

        query = UserLeaderboardQuery(
            timeframe=timeframe,
            criteria=criteria,
            limit=limit,
            offset=offset,
            workspaceId=validated_workspace_id,
        )

        service = LeaderboardService(db)
        leaderboard = await service.get_user_leaderboard(
            workspace_id=validated_workspace_id,
            query=query,
        )

        return leaderboard

    except ValueError as e:
        logger.warning(f"Validation error in user leaderboard: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching user leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch user leaderboard. Please try again later."
        )


@router.get("/workspaces")
async def get_workspace_leaderboard(
    timeframe: TimeFrame = Query(
        TimeFrame.SEVEN_DAYS,
        description="Time range for rankings: 24h, 7d, 30d, 90d, all",
    ),
    criteria: WorkspaceCriteria = Query(
        WorkspaceCriteria.ACTIVITY,
        description="Ranking criteria: activity, efficiency, growth, innovation",
    ),
    limit: int = Query(100, ge=1, le=500, description="Number of rankings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get workspace leaderboard rankings.

    This endpoint provides competitive rankings for workspaces based on various
    criteria such as overall activity, efficiency, growth rate, and innovation.

    **Parameters:**
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d, all)
    - **criteria**: Ranking criteria (activity, efficiency, growth, innovation)
    - **limit**: Maximum number of rankings to return (1-500)
    - **offset**: Offset for pagination

    **Returns:**
    - Workspace leaderboard with rankings including:
        - Rank and rank change
        - Workspace information
        - Performance metrics
        - Score and tier
    """
    try:
        logger.info(
            f"Fetching workspace leaderboard with criteria {criteria.value} "
            f"and timeframe {timeframe.value} (user: {current_user.get('user_id')})"
        )

        query = WorkspaceLeaderboardQuery(
            timeframe=timeframe,
            criteria=criteria,
            limit=limit,
            offset=offset,
        )

        service = LeaderboardService(db)
        leaderboard = await service.get_workspace_leaderboard(query=query)

        return leaderboard

    except ValueError as e:
        logger.warning(f"Validation error in workspace leaderboard: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching workspace leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch workspace leaderboard. Please try again later."
        )


@router.post("/refresh/{workspace_id}")
async def refresh_leaderboards(
    workspace_id: str = Path(..., description="Workspace ID to refresh"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Manually refresh all leaderboards for a workspace.

    This endpoint triggers a recalculation of all leaderboard rankings
    for the specified workspace. Use this sparingly as it's computationally expensive.

    **Parameters:**
    - **workspace_id**: Workspace to refresh leaderboards for

    **Returns:**
    - Success message
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Refreshing all leaderboards for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = LeaderboardService(db)
        await service.refresh_all_leaderboards(workspace_id=validated_workspace_id)

        return {
            "status": "success",
            "message": f"Leaderboards refreshed for workspace {validated_workspace_id}",
        }

    except ValueError as e:
        logger.warning(f"Validation error in refresh leaderboards: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing leaderboards: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh leaderboards. Please try again later."
        )


@router.get("/my-rank/agent/{agent_id}")
async def get_my_agent_rank(
    agent_id: str = Path(..., description="Agent ID to check rank for"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: TimeFrame = Query(
        TimeFrame.SEVEN_DAYS,
        description="Time range for rankings",
    ),
    criteria: AgentCriteria = Query(
        AgentCriteria.SUCCESS_RATE,
        description="Ranking criteria",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get current rank for a specific agent.

    **Parameters:**
    - **agent_id**: Agent ID to check rank for
    - **workspace_id**: Workspace context
    - **timeframe**: Time range for rankings
    - **criteria**: Ranking criteria

    **Returns:**
    - Agent's current rank and percentile
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        # Get full leaderboard and find the agent
        query = AgentLeaderboardQuery(
            timeframe=timeframe,
            criteria=criteria,
            limit=500,  # Get enough to find the agent
            offset=0,
            workspaceId=validated_workspace_id,
        )

        service = LeaderboardService(db)
        leaderboard = await service.get_agent_leaderboard(
            workspace_id=validated_workspace_id,
            query=query,
        )

        # Find agent in rankings
        for ranking in leaderboard.get("rankings", []):
            if ranking["agent"]["id"] == agent_id:
                return {
                    "agentId": agent_id,
                    "rank": ranking["rank"],
                    "percentile": ranking["percentile"],
                    "score": ranking["score"],
                    "badge": ranking.get("badge"),
                    "change": ranking["change"],
                }

        # Agent not found in rankings (doesn't meet minimum criteria)
        return {
            "agentId": agent_id,
            "rank": None,
            "message": "Agent does not qualify for rankings (minimum activity not met)",
        }

    except Exception as e:
        logger.error(f"Error fetching agent rank: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch agent rank. Please try again later."
        )
