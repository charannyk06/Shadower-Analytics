"""Moving averages API routes."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

from ...core.database import get_db
from ...services.analytics.moving_averages import MovingAverageService
from ...utils.validators import validate_workspace_id
from ..dependencies.auth import get_current_user
from ..middleware.rate_limit import RateLimiter
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/moving-averages", tags=["moving-averages"])

# Request timeout for moving average calculations (30 seconds)
CALCULATION_TIMEOUT_SECONDS = 30

# Rate limiter for moving average calculations
ma_limiter = RateLimiter(
    requests_per_minute=20,
    requests_per_hour=200,
)


@router.get("/{workspace_id}/analyze", dependencies=[Depends(ma_limiter)])
async def get_moving_average_analysis(
    workspace_id: str,
    metric: str = Query(..., regex="^(runtime_seconds|credits_consumed|tokens_used|executions)$"),
    ma_type: str = Query("sma", regex="^(sma|ema|wma)$"),
    window: int = Query(7, ge=1, le=365),
    timeframe: str = Query("90d", regex="^(7d|30d|90d|1y)$"),
    weights: Optional[str] = Query(None, description="Comma-separated weights for WMA (e.g., '1,2,3,4,5')"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate moving average for a metric.

    Args:
        workspace_id: The workspace ID to analyze
        metric: The metric to analyze (runtime_seconds, credits_consumed, tokens_used, executions)
        ma_type: Moving average type (sma, ema, wma)
        window: Window size for moving average (1-365 days)
        timeframe: Time period for analysis (7d, 30d, 90d, 1y)
        weights: Comma-separated weights for WMA (required if ma_type=wma)

    Returns:
        Moving average analysis including:
        - Time series data with moving average values
        - Trend direction (upward, downward, neutral)
        - Statistical summary
        - Current values
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify user has access to workspace
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Parse weights if WMA is selected
        parsed_weights = None
        if ma_type == 'wma':
            if not weights:
                raise HTTPException(
                    status_code=400,
                    detail="Weights required for weighted moving average (WMA)"
                )
            try:
                parsed_weights = [float(w.strip()) for w in weights.split(',')]
                if len(parsed_weights) != window:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Number of weights ({len(parsed_weights)}) must match window size ({window})"
                    )
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid weights format: {e}. Use comma-separated numbers (e.g., '1,2,3,4,5')"
                )

        # Create service and calculate moving average
        service = MovingAverageService(db)

        try:
            result = await asyncio.wait_for(
                service.get_metric_with_ma(
                    workspace_id=workspace_id,
                    metric=metric,
                    ma_type=ma_type,
                    window=window,
                    timeframe=timeframe,
                    weights=parsed_weights
                ),
                timeout=CALCULATION_TIMEOUT_SECONDS
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"Moving average calculation timed out after {CALCULATION_TIMEOUT_SECONDS}s",
                extra={
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "ma_type": ma_type,
                    "window": window
                }
            )
            raise HTTPException(
                status_code=504,
                detail=f"Calculation timed out after {CALCULATION_TIMEOUT_SECONDS} seconds. Try a shorter timeframe."
            ) from None  # Intentionally suppress traceback for timeout

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid input for moving average calculation: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Moving average calculation failed",
            extra={
                "workspace_id": workspace_id,
                "metric": metric,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate moving average"
        ) from e


@router.get("/{workspace_id}/compare", dependencies=[Depends(ma_limiter)])
async def compare_moving_averages(
    workspace_id: str,
    metric: str = Query(..., regex="^(runtime_seconds|credits_consumed|tokens_used|executions)$"),
    windows: str = Query(..., description="Comma-separated window sizes (e.g., '7,14,30')"),
    timeframe: str = Query("90d", regex="^(7d|30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple moving averages with different window sizes.

    Useful for identifying short-term vs long-term trends and crossover signals.

    Args:
        workspace_id: The workspace ID to analyze
        metric: The metric to analyze
        windows: Comma-separated window sizes (e.g., '7,14,30')
        timeframe: Time period for analysis

    Returns:
        Comparative analysis with:
        - Multiple moving averages
        - Crossover analysis
        - Signal detection (bullish/bearish)
        - Trend convergence/divergence
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify user has access to workspace
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Parse windows
        try:
            parsed_windows = [int(w.strip()) for w in windows.split(',')]
            if not parsed_windows:
                raise ValueError("At least one window size required")
            if len(parsed_windows) > 5:
                raise ValueError("Maximum 5 window sizes allowed")
            if any(w <= 0 or w > 365 for w in parsed_windows):
                raise ValueError("Window sizes must be between 1 and 365")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid windows format: {e}. Use comma-separated integers (e.g., '7,14,30')"
            )

        # Create service and compare moving averages
        service = MovingAverageService(db)

        try:
            result = await asyncio.wait_for(
                service.compare_moving_averages(
                    workspace_id=workspace_id,
                    metric=metric,
                    windows=parsed_windows,
                    timeframe=timeframe
                ),
                timeout=CALCULATION_TIMEOUT_SECONDS * 2  # Allow more time for multiple calculations
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"Moving average comparison timed out",
                extra={
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "windows": parsed_windows
                }
            )
            raise HTTPException(
                status_code=504,
                detail="Comparison timed out. Try fewer window sizes or a shorter timeframe."
            ) from None  # Intentionally suppress traceback for timeout

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid input for moving average comparison: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Moving average comparison failed",
            extra={
                "workspace_id": workspace_id,
                "metric": metric,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to compare moving averages"
        ) from e


@router.post("/{workspace_id}/calculate-custom", dependencies=[Depends(ma_limiter)])
async def calculate_custom_moving_average(
    workspace_id: str,
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Calculate moving average on custom data (in-memory calculation).

    Useful for calculating moving averages on custom datasets without
    querying the database.

    Args:
        workspace_id: The workspace ID (for access validation)
        data: Dictionary containing:
            - values: List of numeric values
            - ma_type: Moving average type (sma, ema, wma)
            - window: Window size
            - weights: (optional) List of weights for WMA

    Returns:
        Calculated moving average values
    """
    try:
        # Validate input
        workspace_id = validate_workspace_id(workspace_id)

        # Verify user has access to workspace
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Extract and validate parameters
        values = data.get('values')
        ma_type = data.get('ma_type', 'sma')
        window = data.get('window', 7)
        weights = data.get('weights')

        if not values or not isinstance(values, list):
            raise HTTPException(
                status_code=400,
                detail="'values' must be a non-empty list of numbers"
            )

        if ma_type not in ['sma', 'ema', 'wma']:
            raise HTTPException(
                status_code=400,
                detail="'ma_type' must be one of: sma, ema, wma"
            )

        if not isinstance(window, int) or window <= 0:
            raise HTTPException(
                status_code=400,
                detail="'window' must be a positive integer"
            )

        if len(values) > 10000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10,000 data points allowed for custom calculation"
            )

        # Validate all values are numeric
        import pandas as pd
        try:
            numeric_values = [float(v) for v in values]
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"All values must be numeric: {e}"
            )

        # Convert to pandas Series
        series = pd.Series(numeric_values)

        # Calculate moving average
        service = MovingAverageService()
        if ma_type == 'sma':
            ma_values = service.calculate_sma(series, window)
        elif ma_type == 'ema':
            ma_values = service.calculate_ema(series, window)
        elif ma_type == 'wma':
            # Validate weights for WMA
            if not weights or not isinstance(weights, list):
                raise HTTPException(
                    status_code=400,
                    detail="'weights' must be a non-empty list for WMA"
                )
            if len(weights) != window:
                raise HTTPException(
                    status_code=400,
                    detail=f"Number of weights ({len(weights)}) must match window size ({window})"
                )
            ma_values = service.calculate_wma(series, weights)

        # Identify trend
        trend = service.identify_trend(series, ma_values)

        # Handle NaN values in output
        import math

        current_val = series.iloc[-1]
        current_ma_val = ma_values.iloc[-1]
        avg_val = series.mean()

        return {
            "ma_type": ma_type,
            "window": window,
            "values": values,
            "moving_averages": [None if (isinstance(v, float) and math.isnan(v)) else v for v in ma_values.tolist()],
            "trend": trend,
            "summary": {
                "current_value": None if pd.isna(current_val) else float(current_val),
                "current_ma": None if pd.isna(current_ma_val) else float(current_ma_val),
                "avg_value": None if pd.isna(avg_val) else float(avg_val),
                "data_points": len(values)
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid input for custom moving average: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Custom moving average calculation failed",
            extra={"workspace_id": workspace_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate custom moving average"
        ) from e
