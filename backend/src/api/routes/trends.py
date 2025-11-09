"""Trend analysis API routes."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
import logging

from ...core.database import get_db
from ...services.analytics.trend_analysis import TrendAnalysisService
from ...utils.validators import validate_workspace_id
from ..dependencies.auth import get_current_user
from ..middleware.rate_limit import RateLimiter
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trends", tags=["trends"])

# Rate limiter for trend analysis (computationally expensive)
trends_limiter = RateLimiter(
    requests_per_minute=10,
    requests_per_hour=100,
)


@router.get("/{workspace_id}/{metric}", dependencies=[Depends(trends_limiter)])
async def get_trend_analysis(
    workspace_id: str,
    metric: str = Query(..., regex="^(executions|users|credits|errors|success_rate|revenue)$"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive trend analysis for a metric.

    Args:
        workspace_id: The workspace ID to analyze
        metric: The metric to analyze (executions, users, credits, etc.)
        timeframe: Time period for analysis (7d, 30d, 90d, 1y)

    Returns:
        Complete trend analysis including:
        - Overview with trend direction and statistics
        - Time series data with anomaly detection
        - Decomposition (trend, seasonal, residual)
        - Pattern detection (seasonality, growth, cycles)
        - Period comparisons
        - Correlations with other metrics
        - Forecast (short-term and long-term)
        - Actionable insights
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify user has access to workspace
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = TrendAnalysisService(db)
        analysis = await service.analyze_trend(workspace_id, metric, timeframe)

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trend analysis failed for workspace {workspace_id}, metric {metric}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to perform trend analysis"
        )


@router.get("/{workspace_id}/overview", dependencies=[Depends(trends_limiter)])
async def get_trends_overview(
    workspace_id: str,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trend overview for all key metrics.

    Returns a summary of trends across executions, users, credits, and success rate.
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = TrendAnalysisService(db)

        # Get trend overview for all key metrics in parallel (fixes N+1 query problem)
        metrics = ['executions', 'users', 'credits', 'success_rate']

        async def get_metric_overview(metric: str) -> tuple[str, Dict[str, Any]]:
            try:
                analysis = await service.analyze_trend(workspace_id, metric, timeframe)
                return metric, analysis.get('overview', {})
            except Exception as e:
                logger.warning(f"Failed to get trend for {metric} in workspace {workspace_id}: {e}")
                return metric, {"error": "Failed to analyze", "trend": "unknown"}

        results = await asyncio.gather(*[get_metric_overview(m) for m in metrics])
        overviews = dict(results)

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "metrics": overviews
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trends overview failed for workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get trends overview"
        )


@router.get("/{workspace_id}/{metric}/forecast", dependencies=[Depends(trends_limiter)])
async def get_metric_forecast(
    workspace_id: str,
    metric: str = Query(..., regex="^(executions|users|credits|errors|success_rate|revenue)$"),
    periods: int = Query(7, ge=1, le=90),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get forecast for a specific metric.

    Args:
        workspace_id: The workspace ID
        metric: The metric to forecast
        periods: Number of periods (days) to forecast

    Returns:
        Forecast data with predicted values and confidence intervals
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = TrendAnalysisService(db)

        # Use 90 days of historical data for forecasting
        analysis = await service.analyze_trend(workspace_id, metric, '90d')
        forecast = analysis.get('forecast', {})

        # Filter to requested number of periods
        short_term = forecast.get('shortTerm', [])[:periods]

        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "periods": periods,
            "forecast": short_term,
            "accuracy": forecast.get('accuracy', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast failed for workspace {workspace_id}, metric {metric}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate forecast"
        )


@router.get("/{workspace_id}/{metric}/patterns", dependencies=[Depends(trends_limiter)])
async def get_metric_patterns(
    workspace_id: str,
    metric: str = Query(..., regex="^(executions|users|credits|errors|success_rate|revenue)$"),
    timeframe: str = Query("90d", regex="^(30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pattern analysis for a specific metric.

    Returns:
        Detected patterns including seasonality, growth, and cycles
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = TrendAnalysisService(db)
        analysis = await service.analyze_trend(workspace_id, metric, timeframe)

        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "patterns": analysis.get('patterns', {}),
            "insights": [
                insight for insight in analysis.get('insights', [])
                if insight.get('type') in ['pattern', 'seasonality']
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pattern analysis failed for workspace {workspace_id}, metric {metric}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze patterns"
        )


@router.get("/{workspace_id}/{metric}/insights", dependencies=[Depends(trends_limiter)])
async def get_metric_insights(
    workspace_id: str,
    metric: str = Query(..., regex="^(executions|users|credits|errors|success_rate|revenue)$"),
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get actionable insights for a specific metric.

    Returns:
        AI-generated insights with recommendations
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = TrendAnalysisService(db)
        analysis = await service.analyze_trend(workspace_id, metric, timeframe)

        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "insights": analysis.get('insights', []),
            "overview": analysis.get('overview', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Insights generation failed for workspace {workspace_id}, metric {metric}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate insights"
        )


@router.delete("/{workspace_id}/cache", dependencies=[Depends(trends_limiter)])
async def clear_trend_cache(
    workspace_id: str,
    metric: str = Query(None, regex="^(executions|users|credits|errors|success_rate|revenue)?$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Clear cached trend analysis data.

    Args:
        workspace_id: The workspace ID
        metric: Optional specific metric to clear (clears all if not specified)

    Returns:
        Number of cache entries cleared
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        if metric:
            query = text("""
                DELETE FROM analytics.trend_analysis_cache
                WHERE workspace_id = :workspace_id
                AND metric = :metric
            """)
            result = await db.execute(
                query,
                {"workspace_id": workspace_id, "metric": metric}
            )
        else:
            query = text("""
                DELETE FROM analytics.trend_analysis_cache
                WHERE workspace_id = :workspace_id
            """)
            result = await db.execute(
                query,
                {"workspace_id": workspace_id}
            )

        await db.commit()
        rows_deleted = result.rowcount

        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "cacheEntriesCleared": rows_deleted
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache clear failed for workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cache"
        )
