"""Unit tests for data aggregation."""

import pytest
from datetime import datetime, timedelta
from src.services.aggregation import aggregator


@pytest.mark.asyncio
async def test_aggregate_metrics(db_session):
    """Test metric aggregation."""
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()

    result = await aggregator.aggregate_metrics(
        db_session,
        metric_type="user_activity",
        start_time=start_time,
        end_time=end_time,
        granularity="hour",
    )

    assert isinstance(result, list)
