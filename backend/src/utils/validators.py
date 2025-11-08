"""Input validation utilities."""

from datetime import date, datetime
from typing import Any


def validate_date_range(start_date: date, end_date: date) -> bool:
    """Validate that date range is valid."""
    if start_date > end_date:
        raise ValueError("Start date must be before end date")

    # Check that range is not too large (e.g., max 2 years)
    max_days = 730  # 2 years
    delta = (end_date - start_date).days

    if delta > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")

    return True


def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe parameter."""
    valid_timeframes = ["7d", "30d", "90d", "1y"]

    if timeframe not in valid_timeframes:
        raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")

    return True


def validate_pagination(skip: int, limit: int) -> bool:
    """Validate pagination parameters."""
    if skip < 0:
        raise ValueError("Skip must be non-negative")

    if limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000")

    return True


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        raise ValueError("Value must be a string")

    # Strip whitespace
    value = value.strip()

    # Check length
    if len(value) > max_length:
        value = value[:max_length]

    return value
