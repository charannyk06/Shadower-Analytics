"""Request validation utilities.

Provides reusable validation functions for API requests.
"""

from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class RequestValidator:
    """Collection of request validation methods."""

    @staticmethod
    async def validate_workspace_access(
        request: Request,
        workspace_id: str
    ):
        """Validate user has access to workspace.

        Args:
            request: FastAPI request object
            workspace_id: Workspace ID to check access for

        Raises:
            HTTPException: If user doesn't have access
        """
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Check if user has access to this workspace
        user_workspace_id = user.get("workspace_id")
        user_workspace_ids = user.get("workspace_ids", [])

        # User can access if it's their primary workspace or in their workspace list
        has_access = (
            workspace_id == user_workspace_id or
            workspace_id in user_workspace_ids
        )

        if not has_access:
            logger.warning(
                f"Access denied: user {user.get('user_id')} "
                f"attempted to access workspace {workspace_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to workspace {workspace_id}"
            )

    @staticmethod
    def validate_date_range(
        start_date: datetime,
        end_date: datetime,
        max_days: int = 365,
        min_days: int = 1
    ):
        """Validate date range constraints.

        Args:
            start_date: Start date
            end_date: End date
            max_days: Maximum allowed days in range
            min_days: Minimum allowed days in range

        Raises:
            HTTPException: If date range is invalid
        """
        # Check if start is before end
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )

        # Calculate range in days
        date_range = (end_date - start_date).days

        # Check minimum range
        if date_range < min_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range must be at least {min_days} day(s)"
            )

        # Check maximum range
        if date_range > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range exceeds maximum of {max_days} days"
            )

        # Check if dates are not in the future
        now = datetime.utcnow()
        if end_date > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date cannot be in the future"
            )

    @staticmethod
    def validate_pagination(
        page: int,
        per_page: int,
        max_per_page: int = 100
    ):
        """Validate pagination parameters.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            max_per_page: Maximum items per page

        Raises:
            HTTPException: If pagination params are invalid
        """
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page must be >= 1"
            )

        if per_page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="per_page must be >= 1"
            )

        if per_page > max_per_page:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"per_page cannot exceed {max_per_page}"
            )

    @staticmethod
    def validate_metrics(
        metrics: List[str],
        allowed_metrics: List[str],
        max_metrics: int = 10
    ):
        """Validate metric selection.

        Args:
            metrics: List of requested metrics
            allowed_metrics: List of allowed metric names
            max_metrics: Maximum number of metrics allowed

        Raises:
            HTTPException: If metrics are invalid
        """
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one metric must be specified"
            )

        if len(metrics) > max_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request more than {max_metrics} metrics at once"
            )

        # Check for invalid metrics
        invalid_metrics = set(metrics) - set(allowed_metrics)
        if invalid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metrics: {', '.join(invalid_metrics)}"
            )

    @staticmethod
    def validate_filters(
        filters: dict,
        allowed_fields: List[str]
    ):
        """Validate filter parameters.

        Args:
            filters: Dictionary of filter field -> value
            allowed_fields: List of fields that can be filtered

        Raises:
            HTTPException: If filters contain invalid fields
        """
        invalid_fields = set(filters.keys()) - set(allowed_fields)
        if invalid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filter fields: {', '.join(invalid_fields)}"
            )

    @staticmethod
    def validate_sort(
        sort_by: Optional[str],
        allowed_fields: List[str]
    ):
        """Validate sort parameter.

        Args:
            sort_by: Field to sort by
            allowed_fields: List of fields that can be sorted

        Raises:
            HTTPException: If sort field is invalid
        """
        if sort_by and sort_by not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort field: {sort_by}. Allowed: {', '.join(allowed_fields)}"
            )

    @staticmethod
    async def validate_admin_access(request: Request):
        """Validate user has admin access.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If user is not an admin
        """
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        role = user.get("role")
        permissions = user.get("permissions", [])

        is_admin = (
            role == "admin" or
            role == "owner" or
            "admin" in permissions
        )

        if not is_admin:
            logger.warning(
                f"Admin access denied for user {user.get('user_id')}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

    @staticmethod
    def validate_export_format(format: str):
        """Validate export format.

        Args:
            format: Export format (csv, json, pdf, excel)

        Raises:
            HTTPException: If format is invalid
        """
        allowed_formats = ["csv", "json", "pdf", "excel"]

        if format.lower() not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export format. Allowed: {', '.join(allowed_formats)}"
            )

    @staticmethod
    def validate_timezone(timezone: str):
        """Validate timezone string.

        Args:
            timezone: Timezone identifier (e.g., "UTC", "America/New_York")

        Raises:
            HTTPException: If timezone is invalid
        """
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(timezone)
        except Exception:
            # Fallback to pytz if zoneinfo not available
            try:
                import pytz
                pytz.timezone(timezone)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid timezone: {timezone}"
                )

    @staticmethod
    def validate_aggregation(aggregation: str):
        """Validate aggregation method.

        Args:
            aggregation: Aggregation method (sum, avg, min, max, count, p50, p95, p99)

        Raises:
            HTTPException: If aggregation is invalid
        """
        allowed = ["sum", "avg", "min", "max", "count", "p50", "p95", "p99"]

        if aggregation.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid aggregation. Allowed: {', '.join(allowed)}"
            )

    @staticmethod
    def validate_interval(interval: str):
        """Validate time interval.

        Args:
            interval: Time interval (hour, day, week, month)

        Raises:
            HTTPException: If interval is invalid
        """
        allowed = ["hour", "day", "week", "month"]

        if interval.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interval. Allowed: {', '.join(allowed)}"
            )

    @staticmethod
    async def validate_resource_exists(
        resource_id: str,
        check_func,
        resource_type: str = "Resource"
    ):
        """Validate that a resource exists.

        Args:
            resource_id: ID of resource to check
            check_func: Async function to check if resource exists
            resource_type: Type of resource for error message

        Raises:
            HTTPException: If resource doesn't exist
        """
        exists = await check_func(resource_id)

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_type} not found: {resource_id}"
            )


# Convenience functions for common validations

async def require_workspace_access(request: Request, workspace_id: str):
    """Shorthand for workspace access validation."""
    await RequestValidator.validate_workspace_access(request, workspace_id)


async def require_admin(request: Request):
    """Shorthand for admin access validation."""
    await RequestValidator.validate_admin_access(request)


def validate_date_range(
    start_date: datetime,
    end_date: datetime,
    max_days: int = 365
):
    """Shorthand for date range validation."""
    RequestValidator.validate_date_range(start_date, end_date, max_days)
