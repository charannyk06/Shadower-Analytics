"""Unit tests for utility functions."""

import pytest
from datetime import datetime, timedelta
from src.utils.calculations import calculate_percentage_change
from src.utils.datetime import calculate_start_date


class TestCalculations:
    """Test calculation utilities."""

    def test_calculate_percentage_change_positive(self):
        """Test percentage change with positive growth."""
        assert calculate_percentage_change(150, 100) == 50.0
        assert calculate_percentage_change(200, 100) == 100.0
        assert calculate_percentage_change(110, 100) == 10.0

    def test_calculate_percentage_change_negative(self):
        """Test percentage change with negative growth."""
        assert calculate_percentage_change(50, 100) == -50.0
        assert calculate_percentage_change(75, 100) == -25.0
        assert calculate_percentage_change(90, 100) == -10.0

    def test_calculate_percentage_change_zero_previous(self):
        """Test percentage change when previous value is zero."""
        # Previous is 0, current is positive
        assert calculate_percentage_change(100, 0) == 100.0

        # Both are 0
        assert calculate_percentage_change(0, 0) == 0.0

    def test_calculate_percentage_change_precision(self):
        """Test that results are rounded to 2 decimal places."""
        result = calculate_percentage_change(103.456, 100)
        assert result == 3.46

        result = calculate_percentage_change(100.123, 100)
        assert result == 0.12

    def test_calculate_percentage_change_custom_rounding(self):
        """Test custom rounding precision."""
        # Round to 0 decimals
        result = calculate_percentage_change(103.456, 100, round_to=0)
        assert result == 3.0

        # Round to 4 decimals
        result = calculate_percentage_change(103.456789, 100, round_to=4)
        assert result == 3.4568


class TestDatetime:
    """Test datetime utilities."""

    def test_calculate_start_date_24h(self):
        """Test 24 hour timeframe calculation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("24h", from_date=now)
        expected = now - timedelta(hours=24)
        assert start == expected

    def test_calculate_start_date_7d(self):
        """Test 7 day timeframe calculation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("7d", from_date=now)
        expected = now - timedelta(days=7)
        assert start == expected

    def test_calculate_start_date_30d(self):
        """Test 30 day timeframe calculation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("30d", from_date=now)
        expected = now - timedelta(days=30)
        assert start == expected

    def test_calculate_start_date_90d(self):
        """Test 90 day timeframe calculation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("90d", from_date=now)
        expected = now - timedelta(days=90)
        assert start == expected

    def test_calculate_start_date_all(self):
        """Test 'all' timeframe calculation."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("all", from_date=now)
        expected = now - timedelta(days=365 * 10)
        assert start == expected

    def test_calculate_start_date_invalid_defaults_to_7d(self):
        """Test that invalid timeframe defaults to 7 days."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        start = calculate_start_date("invalid", from_date=now)
        expected = now - timedelta(days=7)
        assert start == expected

    def test_calculate_start_date_uses_current_time_by_default(self):
        """Test that function uses current time when from_date is None."""
        before = datetime.utcnow()
        start = calculate_start_date("7d")
        after = datetime.utcnow()

        # Start should be approximately 7 days before now
        expected_min = before - timedelta(days=7, seconds=1)
        expected_max = after - timedelta(days=7, seconds=-1)

        assert expected_min <= start <= expected_max
