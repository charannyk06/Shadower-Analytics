"""User activity tracking API routes."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from ...core.database import get_db
from ...core.privacy import anonymize_ip
from ...services.analytics.user_activity import UserActivityService
from ...services.analytics.retention_analysis import RetentionAnalysisService
from ...models.schemas.user_activity import UserActivityData, TrackActivityRequest, TrackActivityResponse
from ..dependencies.auth import require_owner_or_admin, get_current_user
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user-activity", tags=["user-activity"])


@router.get("/{workspace_id}", response_model=UserActivityData)
async def get_user_activity(
    workspace_id: str,
    timeframe: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    segment_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive user activity analytics for a workspace.

    Requires: owner or admin role

    Args:
        workspace_id: The workspace ID to analyze
        timeframe: Time period for analysis (7d, 30d, 90d, 1y)
        segment_id: Optional user segment to filter by

    Returns:
        Complete user activity analytics data
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = UserActivityService(db)
        data = await service.get_user_activity(workspace_id, timeframe, segment_id)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user activity data")


@router.get("/{workspace_id}/retention/curve")
async def get_retention_curve(
    workspace_id: str,
    cohort_date: str = Query(..., description="Cohort date in YYYY-MM-DD format"),
    days: int = Query(90, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get retention curve for a specific cohort.

    Requires: owner or admin role

    Args:
        workspace_id: The workspace ID
        cohort_date: The cohort date
        days: Number of days to analyze

    Returns:
        Retention curve data
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        cohort_date_obj = datetime.strptime(cohort_date, "%Y-%m-%d").date()

        service = RetentionAnalysisService(db)
        curve = await service.calculate_retention_curve(workspace_id, cohort_date_obj, days)

        return {"retentionCurve": curve}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating retention curve: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate retention curve")


@router.get("/{workspace_id}/retention/cohorts")
async def get_cohort_analysis(
    workspace_id: str,
    cohort_type: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cohort analysis for user retention (basic version).

    Requires: owner or admin role

    Args:
        workspace_id: The workspace ID
        cohort_type: Type of cohort grouping (daily, weekly, monthly)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Cohort analysis data
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        from datetime import timedelta

        # Parse dates
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date_obj = (datetime.utcnow() - timedelta(days=180)).date()

        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date_obj = datetime.utcnow().date()

        service = RetentionAnalysisService(db)
        cohorts = await service.generate_cohort_analysis(
            workspace_id,
            cohort_type,
            start_date_obj,
            end_date_obj
        )

        return {"cohorts": cohorts}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating cohort analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate cohort analysis")


@router.get("/{workspace_id}/cohorts/advanced")
async def get_advanced_cohort_analysis(
    workspace_id: str,
    cohort_type: str = Query("signup", pattern="^(signup|activation|feature_adoption|custom)$"),
    cohort_period: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get advanced cohort analysis with LTV, segments, and comparison metrics.

    Requires: owner or admin role

    Args:
        workspace_id: The workspace ID
        cohort_type: Type of cohort (signup, activation, feature_adoption, custom)
        cohort_period: Period grouping (daily, weekly, monthly)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Advanced cohort analysis data with metrics and comparisons
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        from datetime import timedelta
        from ...services.analytics.cohort_analysis import CohortAnalysisService

        # Parse dates
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date_obj = (datetime.utcnow() - timedelta(days=180)).date()

        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date_obj = datetime.utcnow().date()

        service = CohortAnalysisService(db)
        analysis = await service.generate_cohort_analysis(
            workspace_id,
            cohort_type,
            cohort_period,
            start_date_obj,
            end_date_obj
        )

        return analysis
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating advanced cohort analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate advanced cohort analysis")


@router.get("/{workspace_id}/churn")
async def get_churn_analysis(
    workspace_id: str,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: Dict[str, Any] = Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get churn analysis for the workspace.

    Requires: owner or admin role

    Args:
        workspace_id: The workspace ID
        timeframe: Time period for analysis

    Returns:
        Churn analysis data
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        from datetime import timedelta

        # Calculate date range
        end_date = datetime.utcnow()
        timeframe_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = timeframe_map.get(timeframe, 30)
        start_date = end_date - timedelta(days=days)

        service = RetentionAnalysisService(db)
        churn_data = await service.analyze_churn(workspace_id, start_date, end_date)

        return churn_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing churn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze churn")


@router.post("/{workspace_id}/track", response_model=TrackActivityResponse)
async def track_activity(
    workspace_id: str,
    event_data: TrackActivityRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Track a user activity event.

    Requires: authenticated user

    Args:
        workspace_id: The workspace ID
        event_data: Event data to track (validated)

    Returns:
        Success confirmation with activity ID
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        from ...models.database.tables import UserActivity
        import uuid

        # Anonymize IP address for privacy compliance (GDPR)
        anonymized_ip = anonymize_ip(event_data.ip_address)

        # Create activity record
        activity = UserActivity(
            id=str(uuid.uuid4()),
            user_id=event_data.user_id,
            workspace_id=workspace_id,
            session_id=event_data.session_id,
            event_type=event_data.event_type,
            event_name=event_data.event_name,
            page_path=event_data.page_path,
            ip_address=anonymized_ip,  # Store anonymized IP
            user_agent=event_data.user_agent,
            referrer=event_data.referrer,
            device_type=event_data.device_type,
            browser=event_data.browser,
            os=event_data.os,
            country_code=event_data.country_code,
            metadata=event_data.metadata or {},
            created_at=datetime.utcnow()
        )

        db.add(activity)
        await db.commit()

        return TrackActivityResponse(success=True, activity_id=activity.id)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error tracking activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to track activity")
