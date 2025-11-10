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


def normalize_timeframe_to_interval(timeframe: str) -> str:
    """Normalize timeframe string to PostgreSQL interval format.

    Args:
        timeframe: Time range string (e.g., '1h', '24h', '7d', '30d', '1y')

    Returns:
        PostgreSQL interval string (e.g., '1 hour', '24 hours', '7 days', '30 days', '1 year')

    Raises:
        ValueError: If timeframe format is invalid or value is out of range

    Examples:
        >>> normalize_timeframe_to_interval('7d')
        '7 days'
        >>> normalize_timeframe_to_interval('24h')
        '24 hours'
        >>> normalize_timeframe_to_interval('1h')
        '1 hour'
    """
    import re
    
    # Validate input
    if not timeframe:
        return "7 days"
    
    # Validate format: digits followed by single letter, or PostgreSQL format
    if ' ' in timeframe and any(keyword in timeframe.lower() for keyword in ['hour', 'day', 'week', 'month', 'year']):
        # Already in PostgreSQL format, return as-is
        return timeframe
    
    # Validate format: must be digits followed by single letter (h, d, w, m, y)
    if not re.match(r'^\d+[hdwmy]$', timeframe):
        raise ValueError(
            f"Invalid timeframe format: '{timeframe}'. "
            "Expected format: <number><unit> (e.g., '7d', '24h', '1y') "
            "where unit is one of: h (hours), d (days), w (weeks), m (months), y (years)"
        )
    
    # Extract number and unit
    unit = timeframe[-1]
    try:
        number = int(timeframe[:-1])
    except ValueError:
        raise ValueError(f"Invalid timeframe number: '{timeframe[:-1]}'. Must be a positive integer.")
    
    # Validate reasonable ranges
    max_values = {'h': 8760, 'd': 365, 'w': 52, 'm': 12, 'y': 10}
    
    if number <= 0:
        raise ValueError(f"Timeframe value must be positive, got: {number}")
    
    if number > max_values.get(unit, 365):
        raise ValueError(
            f"Timeframe value too large: {number}{unit}. "
            f"Maximum for '{unit}' is {max_values[unit]}"
        )
    
    # Handle hours
    if unit == 'h':
        return f"{number} hour{'s' if number != 1 else ''}"
    
    # Handle days
    elif unit == 'd':
        return f"{number} day{'s' if number != 1 else ''}"
    
    # Handle weeks
    elif unit == 'w':
        days = number * 7
        return f"{days} day{'s' if days != 1 else ''}"
    
    # Handle months - use PostgreSQL native month intervals for accuracy
    elif unit == 'm':
        return f"{number} month{'s' if number != 1 else ''}"
    
    # Handle years
    elif unit == 'y':
        return f"{number} year{'s' if number != 1 else ''}"
    
    # Should never reach here due to regex validation above
    raise ValueError(f"Unsupported timeframe unit: '{unit}'")


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
