"""Unit tests for metrics calculations."""

import pytest
from datetime import date, timedelta
from src.services.metrics import user_metrics, agent_metrics


@pytest.mark.asyncio
async def test_calculate_dau(db_session):
    """Test DAU calculation."""
    result = await user_metrics.calculate_dau(db_session)
    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_calculate_wau(db_session):
    """Test WAU calculation."""
    result = await user_metrics.calculate_wau(db_session)
    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_calculate_mau(db_session):
    """Test MAU calculation."""
    result = await user_metrics.calculate_mau(db_session)
    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_agent_success_rate(db_session):
    """Test agent success rate calculation."""
    agent_id = "test-agent-123"
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    result = await agent_metrics.calculate_agent_success_rate(
        db_session, agent_id, start_date, end_date
    )

    assert isinstance(result, float)
    assert 0 <= result <= 100
