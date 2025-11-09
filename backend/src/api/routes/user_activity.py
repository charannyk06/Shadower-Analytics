"""User activity tracking API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...services.analytics.user_activity import UserActivityService
from ...services.analytics.retention_analysis import RetentionAnalysisService
from ...models.schemas.user_activity import UserActivityData

router = APIRouter(prefix="/api/v1/user-activity", tags=["user-activity"])


@router.get("/{workspace_id}", response_model=UserActivityData)
async def get_user_activity(
    workspace_id: str,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    segment_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive user activity analytics for a workspace.

    Args:
        workspace_id: The workspace ID to analyze
        timeframe: Time period for analysis (7d, 30d, 90d, 1y)
        segment_id: Optional user segment to filter by

    Returns:
        Complete user activity analytics data
    """
    try:
        service = UserActivityService(db)
        data = await service.get_user_activity(workspace_id, timeframe, segment_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/retention/curve")
async def get_retention_curve(
    workspace_id: str,
    cohort_date: str = Query(..., description="Cohort date in YYYY-MM-DD format"),
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get retention curve for a specific cohort.

    Args:
        workspace_id: The workspace ID
        cohort_date: The cohort date
        days: Number of days to analyze

    Returns:
        Retention curve data
    """
    try:
        from datetime import datetime
        cohort_date_obj = datetime.strptime(cohort_date, "%Y-%m-%d").date()

        service = RetentionAnalysisService(db)
        curve = await service.calculate_retention_curve(workspace_id, cohort_date_obj, days)

        return {"retentionCurve": curve}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/retention/cohorts")
async def get_cohort_analysis(
    workspace_id: str,
    cohort_type: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get cohort analysis for user retention.

    Args:
        workspace_id: The workspace ID
        cohort_type: Type of cohort grouping (daily, weekly, monthly)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Cohort analysis data
    """
    try:
        from datetime import datetime, timedelta

        # Parse dates
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date_obj = (datetime.now() - timedelta(days=180)).date()

        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date_obj = datetime.now().date()

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/churn")
async def get_churn_analysis(
    workspace_id: str,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get churn analysis for the workspace.

    Args:
        workspace_id: The workspace ID
        timeframe: Time period for analysis

    Returns:
        Churn analysis data
    """
    try:
        from datetime import datetime, timedelta

        # Calculate date range
        end_date = datetime.utcnow()
        timeframe_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = timeframe_map.get(timeframe, 30)
        start_date = end_date - timedelta(days=days)

        service = RetentionAnalysisService(db)
        churn_data = await service.analyze_churn(workspace_id, start_date, end_date)

        return churn_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/track")
async def track_activity(
    workspace_id: str,
    event_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Track a user activity event.

    Args:
        workspace_id: The workspace ID
        event_data: Event data to track

    Returns:
        Success confirmation
    """
    try:
        from ...models.database.tables import UserActivity
        import uuid
        from datetime import datetime

        # Create activity record
        activity = UserActivity(
            id=str(uuid.uuid4()),
            user_id=event_data.get("userId"),
            workspace_id=workspace_id,
            session_id=event_data.get("sessionId"),
            event_type=event_data.get("eventType", "custom"),
            event_name=event_data.get("eventName"),
            page_path=event_data.get("pagePath"),
            ip_address=event_data.get("ipAddress"),
            user_agent=event_data.get("userAgent"),
            referrer=event_data.get("referrer"),
            device_type=event_data.get("deviceType"),
            browser=event_data.get("browser"),
            os=event_data.get("os"),
            country_code=event_data.get("countryCode"),
            metadata=event_data.get("metadata", {}),
            created_at=datetime.utcnow()
        )

        db.add(activity)
        await db.commit()

        return {"success": True, "activityId": activity.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
