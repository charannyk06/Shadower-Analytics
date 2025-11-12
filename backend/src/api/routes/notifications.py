"""Notification API endpoints."""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.schemas.notifications import (
    SendNotificationRequest,
    SendNotificationResponse,
    BulkNotificationRequest,
    BulkNotificationResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    MarkAsReadRequest,
    MarkAsReadResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    DigestPreviewRequest,
    DigestPreviewResponse,
    NotificationMetricsResponse,
    UnreadCountResponse,
    NotificationLog,
    NotificationPreference,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
)
from src.services.notifications import (
    NotificationSystem,
    NotificationChannelManager,
    TemplateEngine,
    PreferenceManager,
    DeliveryTracker,
    DigestBuilder,
)
from src.api.websocket.manager import get_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics/notifications", tags=["notifications"])


# Dependency to get notification system
async def get_notification_system(
    db: AsyncSession = Depends(get_db),
) -> NotificationSystem:
    """Get notification system instance."""
    websocket_manager = get_connection_manager()
    channel_manager = NotificationChannelManager(websocket_manager)
    template_engine = TemplateEngine(db)
    preference_manager = PreferenceManager(db)
    delivery_tracker = DeliveryTracker(db)

    return NotificationSystem(
        db=db,
        channel_manager=channel_manager,
        template_engine=template_engine,
        preference_manager=preference_manager,
        delivery_tracker=delivery_tracker,
    )


# Dependency to get preference manager
async def get_preference_manager(
    db: AsyncSession = Depends(get_db),
) -> PreferenceManager:
    """Get preference manager instance."""
    return PreferenceManager(db)


# Dependency to get delivery tracker
async def get_delivery_tracker(
    db: AsyncSession = Depends(get_db),
) -> DeliveryTracker:
    """Get delivery tracker instance."""
    return DeliveryTracker(db)


# Dependency to get digest builder
async def get_digest_builder(
    db: AsyncSession = Depends(get_db),
) -> DigestBuilder:
    """Get digest builder instance."""
    return DigestBuilder(db)


@router.get("")
async def get_notifications(
    user_id: str = Query(..., description="User ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID filter"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> NotificationListResponse:
    """
    Get user's notifications.

    Args:
        user_id: User ID
        workspace_id: Optional workspace ID filter
        unread_only: Only return unread notifications
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of notifications with metadata
    """
    try:
        result = await notification_system.get_notifications(
            user_id=user_id,
            workspace_id=workspace_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

        return NotificationListResponse(
            notifications=[
                NotificationLog.model_validate(n) for n in result["notifications"]
            ],
            total=result["total"],
            unread_count=result["unread_count"],
            has_more=result["has_more"],
        )

    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}",
        )


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(..., description="User ID"),
    notification_system: NotificationSystem = Depends(get_notification_system),
):
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID
        user_id: User ID (for security check)

    Returns:
        Success message
    """
    try:
        count = await notification_system.mark_as_read([notification_id], user_id)

        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or already read",
            )

        return {"message": "Notification marked as read", "updated": count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}",
        )


@router.post("/mark-read")
async def mark_notifications_read(
    request: MarkAsReadRequest,
    user_id: str = Query(..., description="User ID"),
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> MarkAsReadResponse:
    """
    Mark multiple notifications as read.

    Args:
        request: Request with notification IDs
        user_id: User ID

    Returns:
        Count of updated notifications
    """
    try:
        count = await notification_system.mark_as_read(
            request.notification_ids, user_id
        )

        return MarkAsReadResponse(
            updated_count=count,
            message=f"Marked {count} notifications as read",
        )

    except Exception as e:
        logger.error(f"Failed to mark notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notifications as read: {str(e)}",
        )


@router.get("/unread-count")
async def get_unread_count(
    user_id: str = Query(..., description="User ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID filter"),
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> UnreadCountResponse:
    """
    Get unread notification count.

    Args:
        user_id: User ID
        workspace_id: Optional workspace ID filter

    Returns:
        Unread count
    """
    try:
        count = await notification_system.get_unread_count(user_id, workspace_id)

        return UnreadCountResponse(
            user_id=user_id,
            workspace_id=workspace_id,
            unread_count=count,
        )

    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unread count: {str(e)}",
        )


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
    workspace_id: str = Query(..., description="Workspace ID"),
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> SendNotificationResponse:
    """
    Send notification to recipients.

    Args:
        request: Send notification request
        workspace_id: Workspace ID

    Returns:
        Send results
    """
    try:
        result = await notification_system.send_notification(
            notification_type=request.notification_type,
            recipients=request.recipients,
            data=request.data,
            workspace_id=workspace_id,
            priority=request.priority.value,
            channels=[c.value for c in request.channels] if request.channels else None,
            scheduled_for=request.scheduled_for,
        )

        return SendNotificationResponse(
            notification_ids=result["notification_ids"],
            queued_count=result["queued_count"],
            failed_count=result.get("failed_count", 0),
            message=result["message"],
        )

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post("/bulk")
async def send_bulk_notification(
    request: BulkNotificationRequest,
    workspace_id: str = Query(..., description="Workspace ID"),
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> BulkNotificationResponse:
    """
    Send bulk notifications.

    Args:
        request: Bulk notification request
        workspace_id: Workspace ID

    Returns:
        Job ID and status
    """
    try:
        result = await notification_system.send_notification(
            notification_type=request.notification_type,
            recipients=request.recipients,
            data=request.data,
            workspace_id=workspace_id,
            priority=request.priority.value,
            channels=[c.value for c in request.channels] if request.channels else None,
        )

        return BulkNotificationResponse(
            job_id=result["notification_ids"][0] if result["notification_ids"] else "unknown",
            total_recipients=len(request.recipients),
            queued_count=result["queued_count"],
            status="queued",
        )

    except Exception as e:
        logger.error(f"Failed to send bulk notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send bulk notification: {str(e)}",
        )


@router.post("/test")
async def test_notification(
    request: TestNotificationRequest,
    notification_system: NotificationSystem = Depends(get_notification_system),
) -> TestNotificationResponse:
    """
    Send test notification.

    Args:
        request: Test notification request

    Returns:
        Test results
    """
    try:
        # Test channel configuration
        result = await notification_system.channel_manager.test_channel(
            channel=request.channel.value,
            configuration=request.sample_data,
        )

        return TestNotificationResponse(
            success=result["success"],
            message=result["message"],
            details=result.get("details"),
        )

    except Exception as e:
        logger.error(f"Failed to test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test notification: {str(e)}",
        )


@router.get("/preferences")
async def get_preferences(
    user_id: str = Query(..., description="User ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    preference_manager: PreferenceManager = Depends(get_preference_manager),
) -> NotificationPreferencesResponse:
    """
    Get user's notification preferences.

    Args:
        user_id: User ID
        workspace_id: Workspace ID

    Returns:
        List of preferences
    """
    try:
        preferences = await preference_manager.get_user_preferences(
            user_id, workspace_id
        )

        return NotificationPreferencesResponse(
            preferences=[
                NotificationPreference.model_validate(p) for p in preferences
            ],
            total=len(preferences),
        )

    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}",
        )


@router.post("/preferences")
async def update_preference(
    request: NotificationPreferenceCreate,
    preference_manager: PreferenceManager = Depends(get_preference_manager),
) -> NotificationPreference:
    """
    Update or create notification preference.

    Args:
        request: Preference data

    Returns:
        Updated preference
    """
    try:
        preference = await preference_manager.update_preference(
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            notification_type=request.notification_type,
            channel=request.channel.value,
            is_enabled=request.is_enabled,
            frequency=request.frequency.value,
            filter_rules=request.filter_rules,
        )

        return NotificationPreference.model_validate(preference)

    except Exception as e:
        logger.error(f"Failed to update preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preference: {str(e)}",
        )


@router.get("/digest/preview")
async def preview_digest(
    workspace_id: str = Query(..., description="Workspace ID"),
    digest_type: str = Query(..., description="Digest type"),
    period_start: Optional[datetime] = Query(None, description="Period start"),
    period_end: Optional[datetime] = Query(None, description="Period end"),
    digest_builder: DigestBuilder = Depends(get_digest_builder),
) -> DigestPreviewResponse:
    """
    Preview digest content.

    Args:
        workspace_id: Workspace ID
        digest_type: Type of digest
        period_start: Optional period start
        period_end: Optional period end

    Returns:
        Digest preview
    """
    try:
        preview = await digest_builder.preview_digest(
            workspace_id=workspace_id,
            digest_type=digest_type,
            period_start=period_start,
            period_end=period_end,
        )

        return DigestPreviewResponse(**preview)

    except Exception as e:
        logger.error(f"Failed to preview digest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview digest: {str(e)}",
        )


@router.get("/metrics")
async def get_notification_metrics(
    workspace_id: str = Query(..., description="Workspace ID"),
    notification_type: Optional[str] = Query(None, description="Notification type filter"),
    channel: Optional[str] = Query(None, description="Channel filter"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    delivery_tracker: DeliveryTracker = Depends(get_delivery_tracker),
):
    """
    Get notification delivery metrics.

    Args:
        workspace_id: Workspace ID
        notification_type: Optional notification type filter
        channel: Optional channel filter
        days: Number of days to analyze

    Returns:
        Notification metrics
    """
    try:
        metrics = await delivery_tracker.get_delivery_metrics(
            workspace_id=workspace_id,
            notification_type=notification_type,
            channel=channel,
            start_date=datetime.utcnow() - timedelta(days=days),
        )

        return metrics

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "notifications",
        "timestamp": datetime.utcnow().isoformat(),
    }
