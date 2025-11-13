"""Agent execution analytics API endpoints."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
import uuid

from ...core.database import get_db
from ...models.schemas.execution_analytics import (
    ExecutionAnalyticsResponse,
    ExecutionDetail,
    ExecutionStepsResponse,
    WorkspaceExecutionAnalytics,
    ExecutionComparison,
    ExecutionAnalyticsRequest,
    BatchExecutionAnalysisRequest,
    LiveExecution,
    ExecutionSummary,
)
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter
from ...services.analytics.agent_execution_analytics import AgentExecutionAnalyticsService
from ...services.analytics.execution_pattern_analyzer import ExecutionPatternAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent-executions", tags=["agent-executions"])

# Rate limiters
execution_analytics_limiter = RateLimiter(
    requests_per_minute=30,
    requests_per_hour=500,
)

expensive_analytics_limiter = RateLimiter(
    requests_per_minute=5,
    requests_per_hour=50,
)


# ============================================================================
# Agent Execution Analytics Endpoints
# ============================================================================

@router.get("/summary", response_model=ExecutionSummary)
async def get_execution_summary(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    timeframe: str = Query("7d", description="Time frame: 24h, 7d, 30d, 90d, all"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get execution summary statistics."""
    try:
        service = AgentExecutionAnalyticsService(db)

        if agent_id:
            analytics = await service.get_execution_analytics(
                agent_id=agent_id,
                workspace_id=workspace_id,
                timeframe=timeframe,
            )
            return analytics["summary"]
        else:
            workspace_analytics = await service.get_workspace_execution_analytics(
                workspace_id=workspace_id,
                timeframe=timeframe,
            )
            # Convert workspace analytics to summary format
            return {
                "totalExecutions": workspace_analytics["totalExecutions"],
                "successfulExecutions": int(
                    workspace_analytics["totalExecutions"]
                    * workspace_analytics["successRate"]
                    / 100
                ),
                "failedExecutions": workspace_analytics["totalExecutions"]
                - int(
                    workspace_analytics["totalExecutions"]
                    * workspace_analytics["successRate"]
                    / 100
                ),
                "timeoutExecutions": 0,
                "successRate": workspace_analytics["successRate"],
                "avgDurationMs": workspace_analytics["avgDurationMs"],
                "medianDurationMs": workspace_analytics["avgDurationMs"],
                "p95DurationMs": workspace_analytics["avgDurationMs"] * 1.5,
                "p99DurationMs": workspace_analytics["avgDurationMs"] * 2,
                "totalCreditsConsumed": workspace_analytics["totalCredits"],
                "avgCreditsPerExecution": (
                    workspace_analytics["totalCredits"]
                    / workspace_analytics["totalExecutions"]
                    if workspace_analytics["totalExecutions"] > 0
                    else 0
                ),
            }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching execution summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution summary")


@router.get("/{agent_id}/analytics", response_model=ExecutionAnalyticsResponse)
async def get_agent_execution_analytics(
    agent_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", description="Time frame: 24h, 7d, 30d, 90d, all"),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get comprehensive execution analytics for a specific agent."""
    try:
        service = AgentExecutionAnalyticsService(db)
        analytics = await service.get_execution_analytics(
            agent_id=agent_id,
            workspace_id=workspace_id,
            timeframe=timeframe,
            skip_cache=skip_cache,
        )

        return analytics

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching agent execution analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution analytics")


@router.get("/{agent_id}/performance")
async def get_agent_execution_performance(
    agent_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", description="Time frame: 24h, 7d, 30d, 90d, all"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get performance metrics and trends for a specific agent."""
    try:
        service = AgentExecutionAnalyticsService(db)
        analytics = await service.get_execution_analytics(
            agent_id=agent_id,
            workspace_id=workspace_id,
            timeframe=timeframe,
        )

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "performance": analytics["performance"],
            "trends": analytics["trends"],
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch performance metrics")


@router.get("/{agent_id}/failures")
async def get_agent_execution_failures(
    agent_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", description="Time frame: 24h, 7d, 30d, 90d, all"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get failure analysis for a specific agent."""
    try:
        service = AgentExecutionAnalyticsService(db)
        analytics = await service.get_execution_analytics(
            agent_id=agent_id,
            workspace_id=workspace_id,
            timeframe=timeframe,
        )

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "failureAnalysis": analytics["failureAnalysis"],
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching failure analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch failure analysis")


@router.get("/{agent_id}/patterns")
async def get_execution_patterns(
    agent_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    lookback_days: int = Query(30, ge=1, le=90, description="Days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(expensive_analytics_limiter),
):
    """Analyze execution patterns for optimization opportunities."""
    try:
        analyzer = ExecutionPatternAnalyzer(db)
        patterns = await analyzer.analyze_patterns(
            agent_id=agent_id,
            workspace_id=workspace_id,
            lookback_days=lookback_days,
        )

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "lookbackDays": lookback_days,
            "analyzedAt": datetime.utcnow().isoformat(),
            **patterns,
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing execution patterns: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze execution patterns")


@router.post("/batch-analysis")
async def batch_execution_analysis(
    request: BatchExecutionAnalysisRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(expensive_analytics_limiter),
):
    """Get execution analytics for multiple agents in batch."""
    try:
        if len(request.agentIds) > 10:
            raise HTTPException(
                status_code=400, detail="Maximum 10 agents allowed per batch request"
            )

        service = AgentExecutionAnalyticsService(db)
        results = []

        for agent_id in request.agentIds:
            try:
                analytics = await service.get_execution_analytics(
                    agent_id=agent_id,
                    workspace_id=request.workspaceId,
                    timeframe=request.timeframe,
                )
                results.append(analytics)
            except Exception as e:
                logger.error(
                    f"Error fetching analytics for agent {agent_id}: {str(e)}"
                )
                results.append(
                    {
                        "agentId": agent_id,
                        "error": str(e),
                        "workspaceId": request.workspaceId,
                    }
                )

        return {"results": results, "count": len(results)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform batch analysis")


@router.get("/workspace/{workspace_id}/trends", response_model=WorkspaceExecutionAnalytics)
async def get_workspace_execution_trends(
    workspace_id: str,
    timeframe: str = Query("7d", description="Time frame: 24h, 7d, 30d, 90d, all"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get workspace-level execution trends and analytics."""
    try:
        service = AgentExecutionAnalyticsService(db)
        analytics = await service.get_workspace_execution_analytics(
            workspace_id=workspace_id,
            timeframe=timeframe,
        )

        return analytics

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching workspace trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch workspace trends")


@router.get("/{agent_id}/executions/{execution_id}")
async def get_execution_detail(
    agent_id: str,
    execution_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get detailed information about a specific execution."""
    try:
        from sqlalchemy import text

        query = text("""
            SELECT
                execution_id,
                agent_id,
                workspace_id,
                user_id,
                trigger_type,
                trigger_source,
                input_data,
                output_data,
                start_time,
                end_time,
                duration_ms,
                status,
                error_message,
                error_type,
                credits_consumed,
                tokens_used,
                api_calls_count,
                memory_usage_mb,
                steps_total,
                steps_completed,
                execution_graph,
                environment,
                runtime_mode,
                version,
                created_at,
                updated_at
            FROM analytics.agent_executions
            WHERE execution_id = :execution_id
                AND agent_id = :agent_id
                AND workspace_id = :workspace_id
        """)

        result = await db.execute(
            query,
            {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "workspace_id": workspace_id,
            },
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "executionId": row.execution_id,
            "agentId": row.agent_id,
            "workspaceId": row.workspace_id,
            "userId": row.user_id,
            "triggerType": row.trigger_type,
            "triggerSource": row.trigger_source,
            "inputData": row.input_data,
            "outputData": row.output_data,
            "startTime": row.start_time.isoformat() if row.start_time else None,
            "endTime": row.end_time.isoformat() if row.end_time else None,
            "durationMs": row.duration_ms,
            "status": row.status,
            "errorMessage": row.error_message,
            "errorType": row.error_type,
            "creditsConsumed": row.credits_consumed,
            "tokensUsed": row.tokens_used,
            "apiCallsCount": row.api_calls_count,
            "memoryUsageMb": float(row.memory_usage_mb) if row.memory_usage_mb else None,
            "stepsTotal": row.steps_total,
            "stepsCompleted": row.steps_completed,
            "executionGraph": row.execution_graph,
            "environment": row.environment,
            "runtimeMode": row.runtime_mode,
            "version": row.version,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution detail")


@router.get("/{agent_id}/executions/{execution_id}/steps", response_model=ExecutionStepsResponse)
async def get_execution_steps(
    agent_id: str,
    execution_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access: Any = Depends(WorkspaceAccess),
    db: AsyncSession = Depends(get_db),
    rate_limit: Any = Depends(execution_analytics_limiter),
):
    """Get detailed steps for a specific execution."""
    try:
        from sqlalchemy import text

        # Verify execution belongs to agent and workspace
        verify_query = text("""
            SELECT 1 FROM analytics.agent_executions
            WHERE execution_id = :execution_id
                AND agent_id = :agent_id
                AND workspace_id = :workspace_id
        """)

        verify_result = await db.execute(
            verify_query,
            {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "workspace_id": workspace_id,
            },
        )
        if not verify_result.fetchone():
            raise HTTPException(status_code=404, detail="Execution not found")

        # Get steps
        steps_query = text("""
            SELECT
                step_index,
                step_name,
                step_type,
                start_time,
                end_time,
                duration_ms,
                status,
                input,
                output,
                error,
                tokens_used
            FROM analytics.execution_steps
            WHERE execution_id = :execution_id
            ORDER BY step_index
        """)

        steps_result = await db.execute(steps_query, {"execution_id": execution_id})

        steps = []
        for row in steps_result:
            steps.append({
                "stepIndex": row.step_index,
                "stepName": row.step_name,
                "stepType": row.step_type,
                "startTime": row.start_time.isoformat() if row.start_time else None,
                "endTime": row.end_time.isoformat() if row.end_time else None,
                "durationMs": row.duration_ms,
                "status": row.status,
                "input": row.input,
                "output": row.output,
                "error": row.error,
                "tokensUsed": row.tokens_used,
            })

        completed_steps = sum(1 for s in steps if s["status"] == "completed")

        return {
            "executionId": execution_id,
            "steps": steps,
            "totalSteps": len(steps),
            "completedSteps": completed_steps,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution steps: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution steps")
