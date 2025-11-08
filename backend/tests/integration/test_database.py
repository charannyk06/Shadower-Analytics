"""Integration tests for database operations."""

import pytest
from src.models.database.tables import UserMetric, AgentMetric
from datetime import datetime


@pytest.mark.asyncio
async def test_create_user_metric(db_session):
    """Test creating user metric."""
    metric = UserMetric(
        user_id="test-user",
        metric_date=datetime.now(),
        sessions_count=5,
        executions_count=10,
    )

    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)

    assert metric.id is not None
    assert metric.user_id == "test-user"
    assert metric.sessions_count == 5


@pytest.mark.asyncio
async def test_create_agent_metric(db_session):
    """Test creating agent metric."""
    metric = AgentMetric(
        agent_id="test-agent",
        metric_date=datetime.now(),
        total_executions=20,
        successful_executions=18,
        failed_executions=2,
    )

    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)

    assert metric.id is not None
    assert metric.agent_id == "test-agent"
    assert metric.total_executions == 20
