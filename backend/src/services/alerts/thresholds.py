"""Threshold checking for alerts."""

from typing import Dict


def check_threshold(
    value: float,
    threshold: float,
    comparison: str = "greater_than",
) -> bool:
    """Check if value meets threshold condition."""
    if comparison == "greater_than":
        return value > threshold
    elif comparison == "less_than":
        return value < threshold
    elif comparison == "equal_to":
        return value == threshold
    elif comparison == "greater_or_equal":
        return value >= threshold
    elif comparison == "less_or_equal":
        return value <= threshold
    return False


def calculate_dynamic_threshold(
    historical_values: list,
    method: str = "stddev",
    sensitivity: float = 2.0,
) -> Dict:
    """Calculate dynamic threshold based on historical data."""
    import numpy as np

    if not historical_values:
        return {"upper": 0, "lower": 0}

    values = np.array(historical_values)
    mean = np.mean(values)
    std = np.std(values)

    if method == "stddev":
        return {
            "upper": mean + (sensitivity * std),
            "lower": mean - (sensitivity * std),
        }
    elif method == "percentile":
        return {
            "upper": np.percentile(values, 95),
            "lower": np.percentile(values, 5),
        }

    return {"upper": mean, "lower": mean}
