"""Date and time utility functions."""

from datetime import datetime, date, timedelta
from typing import Tuple


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
