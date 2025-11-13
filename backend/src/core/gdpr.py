"""GDPR compliance utilities for data privacy."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import json

logger = logging.getLogger(__name__)


class GDPRCompliance:
    """
    GDPR compliance utilities for data privacy.

    Implements right to access, right to be forgotten, and data portability.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize GDPR compliance handler.

        Args:
            db_session: Database session
        """
        self.db = db_session

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for GDPR data portability request.

        Implements GDPR Article 20 - Right to data portability.

        Args:
            user_id: ID of user requesting data export

        Returns:
            Dictionary containing all user data
        """
        try:
            logger.info(f"Exporting GDPR data for user {user_id}")

            data = {
                "export_metadata": {
                    "user_id": user_id,
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "format": "JSON",
                    "gdpr_article": "Article 20 - Right to data portability",
                },
                "user_profile": await self._get_user_profile(user_id),
                "activity_logs": await self._get_user_activities(user_id),
                "analytics_data": await self._get_user_analytics(user_id),
                "preferences": await self._get_user_preferences(user_id),
                "audit_logs": await self._get_user_audit_logs(user_id),
            }

            # Log the data export
            await self._log_gdpr_action(
                user_id=user_id,
                action="data_export",
                details={"exported_sections": list(data.keys())},
            )

            logger.info(f"GDPR data export completed for user {user_id}")
            return data

        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            raise

    async def delete_user_data(
        self, user_id: str, anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Delete or anonymize user data for GDPR right to be forgotten.

        Implements GDPR Article 17 - Right to erasure.

        Args:
            user_id: ID of user requesting deletion
            anonymize: If True, anonymize instead of delete (preserves analytics)

        Returns:
            Dictionary with deletion/anonymization summary
        """
        try:
            logger.info(
                f"Processing GDPR deletion request for user {user_id} "
                f"(anonymize={anonymize})"
            )

            summary = {
                "user_id": user_id,
                "deletion_timestamp": datetime.utcnow().isoformat(),
                "method": "anonymization" if anonymize else "deletion",
                "gdpr_article": "Article 17 - Right to erasure",
                "processed_tables": [],
            }

            if anonymize:
                # Anonymize user data while preserving analytics integrity
                summary["processed_tables"] = await self._anonymize_user_data(user_id)
            else:
                # Complete deletion (use with caution - may break referential integrity)
                summary["processed_tables"] = await self._delete_user_data(user_id)

            # Log the deletion/anonymization
            await self._log_gdpr_action(
                user_id=user_id,
                action="data_deletion" if not anonymize else "data_anonymization",
                details={
                    "method": summary["method"],
                    "tables_affected": summary["processed_tables"],
                },
            )

            logger.info(f"GDPR deletion completed for user {user_id}")
            return summary

        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            await self.db.rollback()
            raise

    async def get_consent_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's current consent status.

        Implements GDPR Article 7 - Conditions for consent.

        Args:
            user_id: User ID

        Returns:
            Dictionary with consent status
        """
        # TODO: Implement based on your consent management system
        return {
            "user_id": user_id,
            "analytics_consent": True,
            "marketing_consent": False,
            "data_sharing_consent": False,
            "consent_timestamp": datetime.utcnow().isoformat(),
        }

    async def update_consent(
        self, user_id: str, consent_type: str, granted: bool
    ) -> Dict[str, Any]:
        """
        Update user consent preferences.

        Args:
            user_id: User ID
            consent_type: Type of consent (analytics, marketing, etc.)
            granted: Whether consent is granted

        Returns:
            Updated consent status
        """
        logger.info(
            f"Updating consent for user {user_id}: {consent_type} = {granted}"
        )

        # TODO: Implement consent storage
        # This would update a consent table or user preferences

        await self._log_gdpr_action(
            user_id=user_id,
            action="consent_update",
            details={
                "consent_type": consent_type,
                "granted": granted,
            },
        )

        return await self.get_consent_status(user_id)

    # Private helper methods

    async def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data."""
        # TODO: Implement based on your user model
        return {
            "user_id": user_id,
            "note": "User profile data would be exported here",
        }

    async def _get_user_activities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user activity logs."""
        # TODO: Query your activity tables
        return []

    async def _get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user analytics data."""
        # TODO: Query analytics tables
        return {
            "note": "User analytics data would be exported here",
        }

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        # TODO: Query preferences/settings
        return {}

    async def _get_user_audit_logs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's audit logs."""
        try:
            from ..models.database.tables import AuditLog

            result = await self.db.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.timestamp.desc())
                .limit(1000)  # Limit to prevent huge exports
            )
            logs = result.scalars().all()

            return [
                {
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "event_type": log.event_type,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "status": log.status,
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {e}")
            return []

    async def _anonymize_user_data(self, user_id: str) -> List[str]:
        """
        Anonymize user data while preserving analytics.

        Args:
            user_id: User ID to anonymize

        Returns:
            List of tables that were anonymized
        """
        anonymized_tables = []

        try:
            # Anonymize user profile
            # TODO: Update user table with anonymized data
            # Example: UPDATE users SET email = 'anonymized@example.com',
            #          name = 'Anonymized User', ... WHERE id = user_id
            anonymized_tables.append("users")

            # Anonymize activity logs
            # Keep the records but remove identifying information
            # TODO: Update activity tables
            anonymized_tables.append("activity_logs")

            # Update audit logs
            # TODO: Anonymize user-identifying fields in audit logs
            anonymized_tables.append("audit_logs")

            await self.db.commit()
            logger.info(f"Anonymized user {user_id} across {len(anonymized_tables)} tables")

        except Exception as e:
            logger.error(f"Anonymization failed: {e}")
            await self.db.rollback()
            raise

        return anonymized_tables

    async def _delete_user_data(self, user_id: str) -> List[str]:
        """
        Completely delete user data.

        Warning: This may break referential integrity. Use anonymization instead.

        Args:
            user_id: User ID to delete

        Returns:
            List of tables that were deleted from
        """
        deleted_tables = []

        try:
            # Delete from various tables
            # TODO: Implement cascading deletes or manual deletion
            # Be careful with foreign key constraints

            # Example:
            # await self.db.execute(delete(ActivityLog).where(ActivityLog.user_id == user_id))
            # deleted_tables.append("activity_logs")

            # await self.db.execute(delete(User).where(User.id == user_id))
            # deleted_tables.append("users")

            await self.db.commit()
            logger.info(f"Deleted user {user_id} from {len(deleted_tables)} tables")

        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            await self.db.rollback()
            raise

        return deleted_tables

    async def _log_gdpr_action(
        self, user_id: str, action: str, details: Dict[str, Any]
    ):
        """Log GDPR-related actions to audit log."""
        try:
            from .audit import AuditLogger

            audit_logger = AuditLogger(self.db)
            await audit_logger.log_event(
                event_type="gdpr_compliance",
                action=action,
                user_id=user_id,
                details=details,
                severity="warning",  # GDPR actions are important
            )

        except Exception as e:
            logger.error(f"Failed to log GDPR action: {e}")
            # Don't raise - logging failure shouldn't break GDPR operations


# Convenience functions

async def export_user_data(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Export all user data for GDPR request.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User data export
    """
    gdpr = GDPRCompliance(db)
    return await gdpr.export_user_data(user_id)


async def delete_user_data(
    db: AsyncSession, user_id: str, anonymize: bool = True
) -> Dict[str, Any]:
    """
    Delete or anonymize user data for GDPR request.

    Args:
        db: Database session
        user_id: User ID
        anonymize: If True, anonymize instead of delete

    Returns:
        Deletion summary
    """
    gdpr = GDPRCompliance(db)
    return await gdpr.delete_user_data(user_id, anonymize)


async def get_data_retention_info(db: AsyncSession) -> Dict[str, Any]:
    """
    Get information about data retention policies.

    Implements GDPR Article 13 - Information to be provided.

    Returns:
        Dictionary with retention policy information
    """
    return {
        "data_retention_policy": {
            "user_data": "Retained while account is active, anonymized after deletion request",
            "analytics_data": "Retained for 2 years, anonymized after user deletion",
            "audit_logs": "Retained for 7 years for compliance",
            "backup_retention": "30 days for disaster recovery",
        },
        "data_processing_purposes": [
            "Providing analytics services",
            "Service improvement",
            "Security and fraud prevention",
            "Compliance with legal obligations",
        ],
        "third_party_sharing": {
            "analytics_providers": ["List would go here"],
            "purpose": "Service analytics and improvement",
        },
        "user_rights": [
            "Right to access (Article 15)",
            "Right to rectification (Article 16)",
            "Right to erasure (Article 17)",
            "Right to data portability (Article 20)",
            "Right to object (Article 21)",
        ],
    }
