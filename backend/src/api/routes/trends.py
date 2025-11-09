"""Trend analysis API routes."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ...core.database import get_db
from ...services.analytics.trend_analysis import TrendAnalysisService
from ..dependencies.auth import get_current_user
from ..middleware.rate_limit import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trends", tags=["trends"])

# Rate limiter for trend analysis (computationally expensive)
trends_limiter = RateLimiter(
    requests_per_minute=10,
    requests_per_hour=100,
)


@router.get("/{workspace_id}/{metric}")
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
        # Verify user has access to workspace
        # TODO: Add proper workspace access check
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        service = TrendAnalysisService(db)
        analysis = await service.analyze_trend(workspace_id, metric, timeframe)

        return analysis

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform trend analysis: {str(e)}"
        )


@router.get("/{workspace_id}/overview")
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
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        service = TrendAnalysisService(db)

        # Get trend overview for all key metrics
        metrics = ['executions', 'users', 'credits', 'success_rate']
        overviews = {}

        for metric in metrics:
            try:
                analysis = await service.analyze_trend(workspace_id, metric, timeframe)
                overviews[metric] = analysis.get('overview', {})
            except Exception as e:
                logger.warning(f"Failed to get trend for {metric}: {e}")
                overviews[metric] = {
                    "error": str(e),
                    "trend": "unknown"
                }

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "metrics": overviews
        }

    except Exception as e:
        logger.error(f"Trends overview failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trends overview: {str(e)}"
        )


@router.get("/{workspace_id}/{metric}/forecast")
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
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

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

    except Exception as e:
        logger.error(f"Forecast failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forecast: {str(e)}"
        )


@router.get("/{workspace_id}/{metric}/patterns")
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
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

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

    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze patterns: {str(e)}"
        )


@router.get("/{workspace_id}/{metric}/insights")
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
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        service = TrendAnalysisService(db)
        analysis = await service.analyze_trend(workspace_id, metric, timeframe)

        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "insights": analysis.get('insights', []),
            "overview": analysis.get('overview', {})
        }

    except Exception as e:
        logger.error(f"Insights generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.delete("/{workspace_id}/cache")
async def clear_trend_cache(
    workspace_id: str,
    metric: str = Query(None),
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
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        from sqlalchemy import text

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

    except Exception as e:
        logger.error(f"Cache clear failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )
