"""Mathematical calculation utilities."""

from typing import List
import statistics


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0

    return ((new_value - old_value) / old_value) * 100


def calculate_average(values: List[float]) -> float:
    """Calculate average of a list of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> float:
    """Calculate median of a list of values."""
    if not values:
        return 0.0
    return statistics.median(values)


def calculate_percentile(values: List[float], percentile: int) -> float:
    """Calculate percentile of a list of values.

    Args:
        values: List of values
        percentile: Percentile to calculate (0-100)

    Returns:
        Value at the specified percentile
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = (percentile / 100) * (len(sorted_values) - 1)

    if index.is_integer():
        return sorted_values[int(index)]

    lower = sorted_values[int(index)]
    upper = sorted_values[int(index) + 1]
    return lower + (upper - lower) * (index - int(index))


def calculate_growth_rate(values: List[float]) -> float:
    """Calculate compound growth rate for a series of values."""
    if len(values) < 2 or values[0] == 0:
        return 0.0

    periods = len(values) - 1
    final_value = values[-1]
    initial_value = values[0]

    growth_rate = ((final_value / initial_value) ** (1 / periods)) - 1
    return growth_rate * 100
