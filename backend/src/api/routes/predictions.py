"""
Predictive Analytics API Routes

Endpoints for machine learning predictions including credit consumption,
user churn, growth metrics, peak usage, and error rates.

Author: Claude Code
Date: 2025-11-12
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
import logging

# Request timeout for prediction operations (60 seconds)
PREDICTION_TIMEOUT_SECONDS = 60

from ...core.database import get_db
from ...services.analytics.predictive_analytics import PredictiveAnalytics
from ...utils.validators import validate_workspace_id
from ..dependencies.auth import get_current_user
from ..middleware.rate_limit import RateLimiter
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

# Rate limiter for predictions (ML operations are expensive)
predictions_limiter = RateLimiter(
    requests_per_minute=5,
    requests_per_hour=50,
)


# Pydantic models
class GeneratePredictionRequest(BaseModel):
    """Request model for generating predictions."""
    prediction_type: str = Field(..., description="Type of prediction to generate")
    target_metric: str = Field(..., description="Target metric")
    horizon: int = Field(..., description="Prediction horizon")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


@router.get("/consumption/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def predict_credit_consumption(
    workspace_id: str,
    days_ahead: int = Query(30, ge=1, le=180, description="Number of days to predict ahead"),
    granularity: str = Query("daily", regex="^(daily|weekly)$", description="Prediction granularity"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict future credit consumption using Prophet/ARIMA ensemble.

    Returns daily or weekly predictions with confidence intervals,
    including insights about trends, peaks, and recommendations.

    Args:
        workspace_id: Workspace identifier
        days_ahead: Number of days to predict (1-180)
        granularity: Prediction granularity (daily, weekly)

    Returns:
        - predictions: List of predictions with confidence intervals
        - insights: Analysis of consumption patterns
        - recommendations: Actionable recommendations
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Generate predictions
        service = PredictiveAnalytics(db)

        try:
            result = await asyncio.wait_for(
                service.predict_credit_consumption(
                    workspace_id=workspace_id,
                    days_ahead=days_ahead,
                    granularity=granularity
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Credit consumption prediction timed out for workspace {workspace_id}")
            raise HTTPException(
                status_code=504,
                detail=f"Prediction request timed out after {PREDICTION_TIMEOUT_SECONDS} seconds. Try again later."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credit consumption prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to predict credit consumption"
        )


@router.get("/churn/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def predict_user_churn(
    workspace_id: str,
    risk_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Risk threshold for high-risk classification"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict user churn probability for the next 30 days.

    Uses gradient boosting with behavioral features to identify users
    at risk of churning.

    Args:
        workspace_id: Workspace identifier
        risk_threshold: Threshold for high-risk classification (0-1)
        limit: Maximum number of users to return

    Returns:
        - predictions: User-level churn predictions with risk scores
        - risk_analysis: Distribution of risk levels
        - high_risk_users: Count of high-risk users
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Generate predictions
        service = PredictiveAnalytics(db)

        try:
            result = await asyncio.wait_for(
                service.predict_user_churn(
                    workspace_id=workspace_id,
                    users=None,  # Predict for all users
                    risk_threshold=risk_threshold
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS
            )

            # Limit results
            if 'predictions' in result and len(result['predictions']) > limit:
                # Sort by risk score descending and take top N
                result['predictions'] = sorted(
                    result['predictions'],
                    key=lambda x: x['risk_score'],
                    reverse=True
                )[:limit]

            return result
        except asyncio.TimeoutError:
            logger.warning(f"Churn prediction timed out for workspace {workspace_id}")
            raise HTTPException(
                status_code=504,
                detail=f"Prediction request timed out after {PREDICTION_TIMEOUT_SECONDS} seconds. Try again later."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Churn prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to predict user churn"
        )


@router.get("/growth/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def predict_growth_metrics(
    workspace_id: str,
    metric: str = Query(..., regex="^(dau|wau|mau|mrr|active_users)$", description="Metric to predict"),
    horizon_days: int = Query(90, ge=7, le=365, description="Prediction horizon in days"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict growth trajectory for DAU/WAU/MAU/MRR.

    Uses ensemble of time-series models with multiple growth scenarios
    (optimistic, base, pessimistic).

    Args:
        workspace_id: Workspace identifier
        metric: Metric to predict (dau, wau, mau, mrr, active_users)
        horizon_days: Prediction horizon (7-365 days)

    Returns:
        - base_predictions: Primary growth predictions
        - scenarios: Optimistic, base, and pessimistic scenarios
        - milestones: When key growth milestones will be reached
        - insights: Growth analysis and recommendations
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Generate predictions
        service = PredictiveAnalytics(db)

        try:
            result = await asyncio.wait_for(
                service.predict_growth_metrics(
                    workspace_id=workspace_id,
                    metric=metric,
                    horizon_days=horizon_days
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Growth prediction timed out for workspace {workspace_id}")
            raise HTTPException(
                status_code=504,
                detail=f"Prediction request timed out after {PREDICTION_TIMEOUT_SECONDS} seconds. Try again later."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Growth prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to predict growth metrics"
        )


@router.get("/peak-usage/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def predict_peak_usage(
    workspace_id: str,
    granularity: str = Query("hourly", regex="^(hourly|daily)$", description="Time granularity"),
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days to predict"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict peak usage times and capacity needs.

    Helps with resource planning by identifying when peak loads
    will occur and what capacity is needed.

    Args:
        workspace_id: Workspace identifier
        granularity: Time granularity (hourly, daily)
        days_ahead: Number of days to predict (1-30)

    Returns:
        - predictions: Usage predictions
        - peak_times: Identified peak usage periods
        - capacity_recommendations: Resource planning recommendations
        - insights: Capacity planning insights
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Generate predictions
        service = PredictiveAnalytics(db)

        try:
            result = await asyncio.wait_for(
                service.predict_peak_usage(
                    workspace_id=workspace_id,
                    granularity=granularity,
                    days_ahead=days_ahead
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Peak usage prediction timed out for workspace {workspace_id}")
            raise HTTPException(
                status_code=504,
                detail=f"Prediction request timed out after {PREDICTION_TIMEOUT_SECONDS} seconds. Try again later."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Peak usage prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to predict peak usage"
        )


@router.get("/error-rates/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def predict_error_rates(
    workspace_id: str,
    agent_id: Optional[str] = Query(None, description="Optional specific agent ID"),
    days_ahead: int = Query(14, ge=1, le=90, description="Number of days to predict"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict future error rates based on patterns.

    Identifies potential issues before they escalate with
    anomaly detection and early warning alerts.

    Args:
        workspace_id: Workspace identifier
        agent_id: Optional specific agent ID to analyze
        days_ahead: Number of days to predict (1-90)

    Returns:
        - predictions: Error rate predictions
        - anomalies: Detected anomalies in predictions
        - alerts: Critical alerts requiring action
        - patterns: Error pattern analysis
        - recommendations: Recommendations to reduce errors
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Generate predictions
        service = PredictiveAnalytics(db)

        try:
            result = await asyncio.wait_for(
                service.predict_error_rates(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    days_ahead=days_ahead
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Error rate prediction timed out for workspace {workspace_id}")
            raise HTTPException(
                status_code=504,
                detail=f"Prediction request timed out after {PREDICTION_TIMEOUT_SECONDS} seconds. Try again later."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rate prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to predict error rates"
        )


@router.post("/generate/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def generate_prediction(
    workspace_id: str,
    request: GeneratePredictionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate predictions on-demand.

    Flexible endpoint for generating any type of prediction with
    custom parameters.

    Args:
        workspace_id: Workspace identifier
        prediction_type: Type of prediction (consumption, churn, growth, etc.)
        target_metric: Target metric to predict
        horizon: Prediction horizon
        parameters: Additional prediction parameters

    Returns:
        Prediction ID for async tracking and results when available
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Route to appropriate prediction service
        service = PredictiveAnalytics(db)

        if request.prediction_type == "consumption":
            result = await service.predict_credit_consumption(
                workspace_id,
                days_ahead=request.horizon,
                granularity=request.parameters.get('granularity', 'daily')
            )
        elif request.prediction_type == "churn":
            result = await service.predict_user_churn(
                workspace_id,
                users=request.parameters.get('users'),
                risk_threshold=request.parameters.get('risk_threshold', 0.7)
            )
        elif request.prediction_type == "growth":
            result = await service.predict_growth_metrics(
                workspace_id,
                metric=request.target_metric,
                horizon_days=request.horizon
            )
        elif request.prediction_type == "peak_usage":
            result = await service.predict_peak_usage(
                workspace_id,
                granularity=request.parameters.get('granularity', 'hourly'),
                days_ahead=request.horizon
            )
        elif request.prediction_type == "error_rate":
            result = await service.predict_error_rates(
                workspace_id,
                agent_id=request.parameters.get('agent_id'),
                days_ahead=request.horizon
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown prediction type: {request.prediction_type}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate prediction"
        )


@router.get("/history/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def get_prediction_history(
    workspace_id: str,
    prediction_type: Optional[str] = Query(None, description="Filter by prediction type"),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve historical predictions for a workspace.

    Args:
        workspace_id: Workspace identifier
        prediction_type: Optional filter by prediction type
        days_back: Number of days of history to retrieve

    Returns:
        Historical predictions with accuracy metrics
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Build query
        type_filter = ""
        if prediction_type:
            type_filter = "AND prediction_type = :prediction_type"

        query = text(f"""
            SELECT
                id,
                prediction_type,
                target_metric,
                prediction_date,
                predicted_value,
                confidence_lower,
                confidence_upper,
                confidence_level,
                model_version,
                created_at
            FROM analytics.predictions
            WHERE workspace_id = :workspace_id
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '{days_back} days'
                {type_filter}
            ORDER BY created_at DESC
            LIMIT 1000
        """)

        params = {"workspace_id": workspace_id}
        if prediction_type:
            params["prediction_type"] = prediction_type

        result = await db.execute(query, params)
        rows = result.fetchall()

        predictions = []
        for row in rows:
            predictions.append({
                "id": str(row[0]),
                "prediction_type": row[1],
                "target_metric": row[2],
                "prediction_date": row[3].isoformat(),
                "predicted_value": float(row[4]) if row[4] else None,
                "confidence_lower": float(row[5]) if row[5] else None,
                "confidence_upper": float(row[6]) if row[6] else None,
                "confidence_level": float(row[7]) if row[7] else None,
                "model_version": row[8],
                "created_at": row[9].isoformat()
            })

        return {
            "workspace_id": workspace_id,
            "predictions": predictions,
            "total": len(predictions)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve prediction history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve prediction history"
        )


@router.get("/accuracy/{workspace_id}", dependencies=[Depends(predictions_limiter)])
async def get_prediction_accuracy(
    workspace_id: str,
    prediction_type: str = Query(..., description="Type of prediction to analyze"),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get prediction accuracy metrics.

    Analyzes how accurate past predictions were by comparing
    predicted vs actual values.

    Args:
        workspace_id: Workspace identifier
        prediction_type: Type of prediction to analyze
        days_back: Days of history to analyze

    Returns:
        Accuracy metrics including MAPE, accuracy rate, etc.
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Use database function to calculate accuracy
        query = text("""
            SELECT * FROM analytics.calculate_prediction_accuracy(
                :workspace_id,
                :prediction_type,
                :days_back
            )
        """)

        result = await db.execute(query, {
            "workspace_id": workspace_id,
            "prediction_type": prediction_type,
            "days_back": days_back
        })

        row = result.fetchone()

        if not row:
            return {
                "workspace_id": workspace_id,
                "prediction_type": prediction_type,
                "message": "No accuracy data available yet"
            }

        return {
            "workspace_id": workspace_id,
            "prediction_type": prediction_type,
            "target_metric": row[1],
            "total_predictions": row[2],
            "accurate_predictions": row[3],
            "accuracy_rate": float(row[4]),
            "avg_error": float(row[5]),
            "avg_percentage_error": float(row[6])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve prediction accuracy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve prediction accuracy"
        )
