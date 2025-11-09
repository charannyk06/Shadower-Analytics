"""Date and time utility functions."""

from datetime import datetime, date, timedelta, timezone
from typing import Tuple, Optional


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible).

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(timezone.utc)


def get_date_range(timeframe: str) -> Tuple[date, date]:
    """Get date range for a timeframe.

    Args:
        timeframe: '7d', '30d', '90d', '1y'

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = date.today()

    if timeframe == "7d":
        start_date = end_date - timedelta(days=7)
    elif timeframe == "30d":
        start_date = end_date - timedelta(days=30)
    elif timeframe == "90d":
        start_date = end_date - timedelta(days=90)
    elif timeframe == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    return start_date, end_date


def get_period_start(dt: datetime, period: str) -> datetime:
    """Get start of period for a datetime.

    Args:
        dt: Datetime to get period start for
        period: 'hour', 'day', 'week', 'month'

    Returns:
        Datetime at start of period
    """
    if period == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    elif period == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return start - timedelta(days=start.weekday())
    elif period == "month":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return dt


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def calculate_start_date(timeframe: str, from_date: Optional[datetime] = None) -> datetime:
    """Calculate start date based on timeframe.

    Args:
        timeframe: Time range - '24h', '7d', '30d', '90d', or 'all'
        from_date: Reference date to calculate from (default: current UTC time)

    Returns:
        Datetime representing the start of the timeframe
    """
    now = from_date or utc_now()

    timeframe_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "all": timedelta(days=365 * 10),
    }

    return now - timeframe_map.get(timeframe, timedelta(days=7))
