"""Preference manager for user notification settings."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete

from src.models.database.tables import (
    NotificationPreference,
    NotificationSubscription,
)
from src.models.schemas.notifications import (
    NotificationChannelEnum,
    NotificationFrequencyEnum,
)

logger = logging.getLogger(__name__)


class PreferenceManager:
    """Manager for user notification preferences and subscriptions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize preference manager.

        Args:
            db: Database session
        """
        self.db = db
        logger.info("PreferenceManager initialized")

    async def get_user_preferences(
        self, user_id: str, workspace_id: str
    ) -> List[NotificationPreference]:
        """
        Get user's notification preferences.

        Args:
            user_id: User ID
            workspace_id: Workspace ID

        Returns:
            List of notification preferences
        """
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.workspace_id == workspace_id,
                )
            )
        )
        preferences = result.scalars().all()
        return list(preferences)

    async def get_enabled_channels(
        self, user_id: str, workspace_id: str, notification_type: str
    ) -> List[str]:
        """
        Get enabled channels for a notification type.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            notification_type: Notification type

        Returns:
            List of enabled channel names
        """
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.workspace_id == workspace_id,
                    NotificationPreference.notification_type == notification_type,
                    NotificationPreference.is_enabled == True,
                )
            )
        )
        preferences = result.scalars().all()

        # If no preferences found, return default channels
        if not preferences:
            return self._get_default_channels(notification_type)

        return [pref.channel for pref in preferences]

    def _get_default_channels(self, notification_type: str) -> List[str]:
        """
        Get default channels for a notification type.

        Args:
            notification_type: Notification type

        Returns:
            List of default channels
        """
        # Default channel configuration based on notification type
        if notification_type.startswith("alert_"):
            return ["in_app", "email"]  # Alerts go to in-app and email by default
        elif notification_type.startswith("digest_"):
            return ["email"]  # Digests go to email only
        elif notification_type.startswith("milestone_"):
            return ["in_app"]  # Milestones go to in-app only
        else:
            return ["in_app"]  # Default to in-app only

    async def update_preference(
        self,
        user_id: str,
        workspace_id: str,
        notification_type: str,
        channel: str,
        is_enabled: Optional[bool] = None,
        frequency: Optional[str] = None,
        filter_rules: Optional[Dict[str, Any]] = None,
    ) -> NotificationPreference:
        """
        Update or create notification preference.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            notification_type: Notification type
            channel: Channel
            is_enabled: Enable/disable flag
            frequency: Frequency setting
            filter_rules: Filter rules

        Returns:
            Updated preference
        """
        # Check if preference exists
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.workspace_id == workspace_id,
                    NotificationPreference.notification_type == notification_type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        preference = result.scalar_one_or_none()

        if preference:
            # Update existing
            if is_enabled is not None:
                preference.is_enabled = is_enabled
            if frequency is not None:
                preference.frequency = frequency
            if filter_rules is not None:
                preference.filter_rules = filter_rules
            preference.updated_at = datetime.utcnow()
        else:
            # Create new
            preference = NotificationPreference(
                id=str(uuid4()),
                user_id=user_id,
                workspace_id=workspace_id,
                notification_type=notification_type,
                channel=channel,
                is_enabled=is_enabled if is_enabled is not None else True,
                frequency=frequency or NotificationFrequencyEnum.IMMEDIATE.value,
                filter_rules=filter_rules or {},
            )
            self.db.add(preference)

        await self.db.commit()
        await self.db.refresh(preference)

        logger.info(
            f"Updated preference for user {user_id} type={notification_type} channel={channel}"
        )
        return preference

    async def bulk_update_preferences(
        self,
        user_id: str,
        workspace_id: str,
        preferences: List[Dict[str, Any]],
    ) -> List[NotificationPreference]:
        """
        Bulk update notification preferences.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            preferences: List of preference updates

        Returns:
            List of updated preferences
        """
        updated = []

        for pref_data in preferences:
            preference = await self.update_preference(
                user_id=user_id,
                workspace_id=workspace_id,
                notification_type=pref_data.get("notification_type"),
                channel=pref_data.get("channel"),
                is_enabled=pref_data.get("is_enabled"),
                frequency=pref_data.get("frequency"),
                filter_rules=pref_data.get("filter_rules"),
            )
            updated.append(preference)

        logger.info(
            f"Bulk updated {len(updated)} preferences for user {user_id}"
        )
        return updated

    async def set_global_preference(
        self, user_id: str, workspace_id: str, channel: str, is_enabled: bool
    ) -> int:
        """
        Enable/disable a channel globally for all notification types.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            channel: Channel to enable/disable
            is_enabled: Enable/disable flag

        Returns:
            Number of preferences updated
        """
        # Get all preferences for this user/workspace/channel
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.workspace_id == workspace_id,
                    NotificationPreference.channel == channel,
                )
            )
        )
        preferences = result.scalars().all()

        # Update all
        count = 0
        for preference in preferences:
            preference.is_enabled = is_enabled
            preference.updated_at = datetime.utcnow()
            count += 1

        await self.db.commit()

        logger.info(
            f"Set global preference for user {user_id} channel={channel} enabled={is_enabled} ({count} updated)"
        )
        return count

    async def subscribe(
        self,
        user_id: str,
        workspace_id: str,
        subscription_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationSubscription:
        """
        Subscribe user to notification type.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            subscription_type: Subscription type
            metadata: Optional metadata

        Returns:
            Subscription object
        """
        # Check if subscription exists
        result = await self.db.execute(
            select(NotificationSubscription).where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.workspace_id == workspace_id,
                    NotificationSubscription.subscription_type == subscription_type,
                )
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Update existing
            subscription.is_subscribed = True
            subscription.metadata = metadata or subscription.metadata
            subscription.updated_at = datetime.utcnow()
        else:
            # Create new
            subscription = NotificationSubscription(
                id=str(uuid4()),
                user_id=user_id,
                workspace_id=workspace_id,
                subscription_type=subscription_type,
                is_subscribed=True,
                metadata=metadata or {},
            )
            self.db.add(subscription)

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(
            f"User {user_id} subscribed to {subscription_type}"
        )
        return subscription

    async def unsubscribe(
        self, user_id: str, workspace_id: str, subscription_type: str
    ) -> bool:
        """
        Unsubscribe user from notification type.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            subscription_type: Subscription type

        Returns:
            True if unsubscribed
        """
        result = await self.db.execute(
            select(NotificationSubscription).where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.workspace_id == workspace_id,
                    NotificationSubscription.subscription_type == subscription_type,
                )
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.is_subscribed = False
            subscription.updated_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                f"User {user_id} unsubscribed from {subscription_type}"
            )
            return True

        return False

    async def is_subscribed(
        self, user_id: str, workspace_id: str, subscription_type: str
    ) -> bool:
        """
        Check if user is subscribed to notification type.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            subscription_type: Subscription type

        Returns:
            True if subscribed
        """
        result = await self.db.execute(
            select(NotificationSubscription).where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.workspace_id == workspace_id,
                    NotificationSubscription.subscription_type == subscription_type,
                    NotificationSubscription.is_subscribed == True,
                )
            )
        )
        subscription = result.scalar_one_or_none()
        return subscription is not None

    async def get_subscriptions(
        self, user_id: str, workspace_id: str
    ) -> List[NotificationSubscription]:
        """
        Get all subscriptions for a user.

        Args:
            user_id: User ID
            workspace_id: Workspace ID

        Returns:
            List of subscriptions
        """
        result = await self.db.execute(
            select(NotificationSubscription).where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.workspace_id == workspace_id,
                )
            )
        )
        subscriptions = result.scalars().all()
        return list(subscriptions)

    async def delete_preference(
        self,
        user_id: str,
        workspace_id: str,
        notification_type: str,
        channel: str,
    ) -> bool:
        """
        Delete a notification preference.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            notification_type: Notification type
            channel: Channel

        Returns:
            True if deleted
        """
        await self.db.execute(
            delete(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.workspace_id == workspace_id,
                    NotificationPreference.notification_type == notification_type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        await self.db.commit()

        logger.info(
            f"Deleted preference for user {user_id} type={notification_type} channel={channel}"
        )
        return True
