"""Resource utilization analytics routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from datetime import date
import logging

from ...core.database import get_db
from ...models.schemas.resource_analytics import (
    ResourceAnalyticsResponse,
    CostAnalysisResponse,
    OptimizationRecommendation,
    WasteSummary,
    ResourceForecast,
    TokenBudget,
    BudgetUsage,
)
from ...services.metrics.resource_metrics_service import ResourceMetricsService
from ...services.analytics.resource_analytics_service import (
    ResourceAnalyticsService,
    TokenEfficiencyAnalyzer,
    CostOptimizationEngine,
    ResourceWasteAnalyzer,
    ResourceDemandForecaster,
)
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...utils.validators import validate_agent_id, validate_workspace_id

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])
logger = logging.getLogger(__name__)


@router.get("/agents/{agent_id}/usage")
async def get_agent_resource_usage(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "7d",
        description="Time range: 24h, 7d, 30d, 90d",
        pattern="^(24h|7d|30d|90d)$",
    ),
    granularity: str = Query(
        "daily",
        description="Data granularity: hourly, daily, weekly",
        pattern="^(hourly|daily|weekly)$",
    ),
    resource_types: Optional[List[str]] = Query(
        None,
        description="Filter by resource types: compute, tokens, api, storage",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get detailed resource usage analytics for an agent.

    **Returns:**
    - Compute metrics (CPU, memory, GPU, network)
    - Token usage and efficiency
    - API call statistics
    - Storage utilization
    - Cost breakdown by category
    - Efficiency scoring
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching resource usage for agent {validated_agent_id} "
            f"in workspace {validated_workspace_id} for timeframe {timeframe}"
        )

        service = ResourceMetricsService(db)
        usage = await service.get_resource_usage(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return usage

    except Exception as e:
        logger.error(f"Error fetching resource usage: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch resource usage: {str(e)}")


@router.get("/agents/{agent_id}/analytics")
async def get_agent_resource_analytics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(
        "7d",
        description="Time range: 24h, 7d, 30d, 90d",
        pattern="^(24h|7d|30d|90d)$",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive resource analytics including:
    - Token efficiency analysis
    - Cost optimization recommendations
    - Waste detection
    - Resource forecasting
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching comprehensive resource analytics for agent {validated_agent_id}"
        )

        service = ResourceAnalyticsService(db)
        analytics = await service.get_comprehensive_analytics(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching resource analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch resource analytics: {str(e)}"
        )


@router.get("/agents/{agent_id}/token-analysis")
async def get_agent_token_analysis(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", pattern="^(24h|7d|30d|90d)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get detailed token usage analysis and optimization opportunities.

    **Returns:**
    - Token distribution (input/output/embedding)
    - Efficiency metrics
    - Optimization opportunities
    - Cost analysis
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        analyzer = TokenEfficiencyAnalyzer(db)
        analysis = await analyzer.analyze_token_usage(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing token usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze token usage: {str(e)}"
        )


@router.get("/agents/{agent_id}/cost-optimization")
async def get_cost_optimizations(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get cost optimization recommendations for an agent.

    **Returns:**
    - Current monthly cost
    - Potential savings
    - Optimization recommendations by category
    - Implementation effort estimates
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        optimizer = CostOptimizationEngine(db)
        optimizations = await optimizer.analyze_cost_optimizations(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return optimizations

    except Exception as e:
        logger.error(f"Error analyzing cost optimizations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze cost optimizations: {str(e)}"
        )


@router.get("/agents/{agent_id}/waste-detection")
async def get_resource_waste(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", pattern="^(24h|7d|30d|90d)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Identify resource waste for an agent.

    **Returns:**
    - Total waste cost
    - Waste breakdown by type
    - Unresolved waste events
    - Potential monthly savings
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        analyzer = ResourceWasteAnalyzer(db)
        waste = await analyzer.identify_resource_waste(
            workspace_id=validated_workspace_id,
            agent_id=validated_agent_id,
            timeframe=timeframe,
        )

        return waste

    except Exception as e:
        logger.error(f"Error detecting resource waste: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to detect resource waste: {str(e)}"
        )


@router.get("/agents/{agent_id}/forecast")
async def forecast_resource_usage(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    horizon_days: int = Query(30, ge=1, le=90, description="Forecast horizon in days"),
    include_cost_projection: bool = Query(True, description="Include cost projections"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Forecast future resource usage and costs.

    **Returns:**
    - Token usage predictions
    - Compute usage predictions
    - Cost projections
    - Budget alerts
    - Confidence intervals
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        forecaster = ResourceDemandForecaster(db)
        forecast = await forecaster.forecast_resource_usage(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            horizon_days=horizon_days,
        )

        return forecast

    except Exception as e:
        logger.error(f"Error forecasting resource usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to forecast resource usage: {str(e)}"
        )


@router.get("/workspace/{workspace_id}/cost-analysis")
async def get_workspace_cost_analysis(
    workspace_id: str = Path(..., description="Workspace ID"),
    period: str = Query(
        "month",
        description="Analysis period: day, week, month, quarter",
        pattern="^(day|week|month|quarter)$",
    ),
    breakdown_by: str = Query(
        "agent",
        description="Breakdown by: agent, category, model",
        pattern="^(agent|category|model)$",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get cost analysis and breakdown for entire workspace.

    **Returns:**
    - Total workspace cost
    - Cost breakdown by specified dimension
    - Cost trends
    - Projections
    - Optimization potential
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching workspace cost analysis for {validated_workspace_id} "
            f"by {breakdown_by}"
        )

        # Map period to timeframe
        timeframe_map = {
            "day": "24h",
            "week": "7d",
            "month": "30d",
            "quarter": "90d",
        }
        timeframe = timeframe_map.get(period, "30d")

        # Get aggregated workspace costs
        from sqlalchemy import text
        query = text("""
            SELECT
                agent_id,
                SUM(total_cost) as total_cost,
                SUM(total_compute_cost) as compute_cost,
                SUM(total_token_cost) as token_cost,
                SUM(total_api_cost) as api_cost
            FROM analytics.daily_resource_utilization
            WHERE workspace_id = :workspace_id
                AND usage_date >= CURRENT_DATE - INTERVAL ':days days'
            GROUP BY agent_id
            ORDER BY total_cost DESC
        """)

        days_map = {"day": 1, "week": 7, "month": 30, "quarter": 90}
        days = days_map.get(period, 30)

        result = await db.execute(
            query,
            {"workspace_id": validated_workspace_id, "days": days},
        )
        rows = result.fetchall()

        total_cost = sum(float(row.total_cost or 0) for row in rows)
        cost_by_agent = {
            str(row.agent_id): float(row.total_cost or 0) for row in rows
        }

        return {
            "workspaceId": validated_workspace_id,
            "period": period,
            "totalCost": total_cost,
            "costByAgent": cost_by_agent,
            "costBreakdown": {
                "computeCostUsd": sum(float(row.compute_cost or 0) for row in rows),
                "tokenCostUsd": sum(float(row.token_cost or 0) for row in rows),
                "apiCostUsd": sum(float(row.api_cost or 0) for row in rows),
                "storageCostUsd": 0,
                "networkCostUsd": 0,
                "totalCostUsd": total_cost,
            },
        }

    except Exception as e:
        logger.error(f"Error fetching workspace cost analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch workspace cost analysis: {str(e)}"
        )


@router.post("/agents/{agent_id}/optimize")
async def optimize_agent_resources(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    optimization_goals: List[str] = Query(
        ["cost", "performance"],
        description="Optimization goals: cost, performance, efficiency",
    ),
    constraints: Optional[Dict[str, Any]] = None,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Generate and optionally apply resource optimization recommendations.

    **Parameters:**
    - optimization_goals: What to optimize for (cost, performance, efficiency)
    - constraints: Optional constraints (max_cost, min_performance, etc.)

    **Returns:**
    - Optimization recommendations
    - Expected impact
    - Implementation steps
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Generating optimization recommendations for agent {validated_agent_id} "
            f"with goals: {optimization_goals}"
        )

        optimizer = CostOptimizationEngine(db)
        recommendations = await optimizer.analyze_cost_optimizations(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
        )

        return {
            "agentId": validated_agent_id,
            "optimizationGoals": optimization_goals,
            "recommendations": recommendations.get("optimizationRecommendations", []),
            "expectedSavings": recommendations.get("potentialSavings", 0),
            "status": "pending",  # Would track implementation status
        }

    except Exception as e:
        logger.error(f"Error generating optimizations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate optimizations: {str(e)}"
        )


@router.get("/workspace/{workspace_id}/efficiency-leaderboard")
async def get_efficiency_leaderboard(
    workspace_id: str = Path(..., description="Workspace ID"),
    metric: str = Query(
        "overall",
        description="Metric to rank by: overall, cost, tokens, performance",
        pattern="^(overall|cost|tokens|performance)$",
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of agents to return"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get efficiency leaderboard for agents in a workspace.

    **Returns:**
    - Ranked list of agents by efficiency
    - Efficiency scores and breakdown
    - Comparison metrics
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        from sqlalchemy import text

        # Query from efficiency scorecard
        query = text("""
            SELECT
                agent_id,
                overall_efficiency_score,
                tokens_per_dollar,
                executions_per_dollar,
                cost_efficiency_percent,
                total_30d_cost
            FROM analytics.agent_efficiency_scorecard
            WHERE workspace_id = :workspace_id
            ORDER BY overall_efficiency_score DESC
            LIMIT :limit
        """)

        result = await db.execute(
            query,
            {"workspace_id": validated_workspace_id, "limit": limit},
        )
        rows = result.fetchall()

        leaderboard = [
            {
                "agentId": str(row.agent_id),
                "rank": idx + 1,
                "efficiencyScore": float(row.overall_efficiency_score or 0),
                "tokensPerDollar": float(row.tokens_per_dollar or 0),
                "executionsPerDollar": float(row.executions_per_dollar or 0),
                "costEfficiencyPercent": float(row.cost_efficiency_percent or 0),
                "monthlyCost": float(row.total_30d_cost or 0),
            }
            for idx, row in enumerate(rows)
        ]

        return {
            "workspaceId": validated_workspace_id,
            "metric": metric,
            "leaderboard": leaderboard,
        }

    except Exception as e:
        logger.error(f"Error fetching efficiency leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch efficiency leaderboard: {str(e)}"
        )
