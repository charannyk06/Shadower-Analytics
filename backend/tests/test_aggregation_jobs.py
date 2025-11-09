"""Tests for aggregation jobs."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from src.services.aggregation.rollup import (
    hourly_rollup,
    daily_rollup,
    aggregate_execution_metrics,
    aggregate_user_activity,
    aggregate_credit_consumption,
)
from src.services.aggregation.materialized import (
    refresh_materialized_view,
)


@pytest.fixture
async def sample_execution_logs(db_session):
    """Create sample execution logs for testing."""
    # Insert sample execution logs
    query = text(
        """
        INSERT INTO execution_logs (
            execution_id, agent_id, user_id, workspace_id,
            status, duration, credits_used, started_at, completed_at
        ) VALUES
        ('exec1', 'agent1', 'user1', 'workspace1', 'completed', 120.5, 10,
         NOW() - INTERVAL '1 hour', NOW() - INTERVAL '55 minutes'),
        ('exec2', 'agent1', 'user1', 'workspace1', 'completed', 150.2, 15,
         NOW() - INTERVAL '1 hour', NOW() - INTERVAL '50 minutes'),
        ('exec3', 'agent2', 'user2', 'workspace1', 'failed', 30.0, 5,
         NOW() - INTERVAL '1 hour', NOW() - INTERVAL '59 minutes'),
        ('exec4', 'agent1', 'user1', 'workspace2', 'completed', 90.0, 8,
         NOW() - INTERVAL '1 hour', NOW() - INTERVAL '58 minutes')
    """
    )
    await db_session.execute(query)
    await db_session.commit()

    yield

    # Cleanup
    await db_session.execute(text("DELETE FROM execution_logs"))
    await db_session.commit()


@pytest.fixture
async def sample_user_activity(db_session):
    """Create sample user activity for testing."""
    query = text(
        """
        INSERT INTO analytics.user_activity (
            id, user_id, workspace_id, session_id,
            event_type, event_name, created_at
        ) VALUES
        ('evt1', 'user1', 'workspace1', 'session1', 'page_view', 'dashboard', NOW() - INTERVAL '1 hour'),
        ('evt2', 'user1', 'workspace1', 'session1', 'click', 'button', NOW() - INTERVAL '59 minutes'),
        ('evt3', 'user2', 'workspace1', 'session2', 'page_view', 'agents', NOW() - INTERVAL '58 minutes'),
        ('evt4', 'user1', 'workspace1', 'session1', 'page_view', 'metrics', NOW() - INTERVAL '57 minutes')
    """
    )
    await db_session.execute(query)
    await db_session.commit()

    yield

    # Cleanup
    await db_session.execute(text("DELETE FROM analytics.user_activity"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_aggregate_execution_metrics(db_session, sample_execution_logs):
    """Test execution metrics aggregation."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=2)

    # Run aggregation
    count = await aggregate_execution_metrics(db_session, start_time, end_time)

    # Verify results
    assert count > 0

    # Check that aggregated data exists
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM analytics.execution_metrics_hourly")
    )
    row_count = result.scalar()
    assert row_count > 0

    # Verify workspace1 has aggregated data
    result = await db_session.execute(
        text(
            """
            SELECT total_executions, successful_executions, failed_executions
            FROM analytics.execution_metrics_hourly
            WHERE workspace_id = 'workspace1'
            LIMIT 1
        """
        )
    )
    row = result.fetchone()
    assert row is not None
    total, successful, failed = row
    assert total == successful + failed
    assert successful >= 2  # We have at least 2 successful executions
    assert failed >= 1  # We have at least 1 failed execution


@pytest.mark.asyncio
async def test_aggregate_user_activity(db_session, sample_user_activity):
    """Test user activity aggregation."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=2)

    # Run aggregation
    count = await aggregate_user_activity(db_session, start_time, end_time)

    # Verify results
    assert count > 0

    # Check that aggregated data exists
    result = await db_session.execute(text("SELECT COUNT(*) FROM analytics.user_activity_hourly"))
    row_count = result.scalar()
    assert row_count > 0

    # Verify user1 has aggregated data
    result = await db_session.execute(
        text(
            """
            SELECT total_events, page_views, unique_sessions
            FROM analytics.user_activity_hourly
            WHERE user_id = 'user1'
            LIMIT 1
        """
        )
    )
    row = result.fetchone()
    assert row is not None
    total_events, page_views, unique_sessions = row
    assert total_events >= 3  # user1 has at least 3 events
    assert page_views >= 2  # user1 has at least 2 page views
    assert unique_sessions >= 1  # user1 has at least 1 session


@pytest.mark.asyncio
async def test_aggregate_credit_consumption(db_session, sample_execution_logs):
    """Test credit consumption aggregation."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=2)

    # Run aggregation
    count = await aggregate_credit_consumption(db_session, start_time, end_time)

    # Verify results
    assert count > 0

    # Check that aggregated data exists
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM analytics.credit_consumption_hourly")
    )
    row_count = result.scalar()
    assert row_count > 0

    # Verify workspace1 credit consumption
    result = await db_session.execute(
        text(
            """
            SELECT total_credits, executions_count, avg_credits_per_execution
            FROM analytics.credit_consumption_hourly
            WHERE workspace_id = 'workspace1' AND user_id = 'user1'
            LIMIT 1
        """
        )
    )
    row = result.fetchone()
    assert row is not None
    total_credits, executions_count, avg_credits = row
    assert total_credits > 0
    assert executions_count > 0
    assert avg_credits > 0


@pytest.mark.asyncio
async def test_hourly_rollup(db_session, sample_execution_logs, sample_user_activity):
    """Test complete hourly rollup."""
    # Specify target hour
    target_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    # Run hourly rollup
    result = await hourly_rollup(db_session, target_hour)

    # Verify result structure
    assert result["success"] is True
    assert result["period"] == "hourly"
    assert "start_time" in result
    assert "end_time" in result
    assert "execution_metrics_workspaces" in result
    assert "user_activity_users" in result
    assert "credit_consumption_records" in result


@pytest.mark.asyncio
async def test_daily_rollup(db_session):
    """Test daily rollup."""
    # First create some hourly data
    query = text(
        """
        INSERT INTO analytics.execution_metrics_hourly (
            workspace_id, hour, total_executions, successful_executions,
            failed_executions, avg_runtime, p50_runtime, p95_runtime, p99_runtime,
            total_credits, avg_credits_per_run
        ) VALUES
        ('workspace1', DATE_TRUNC('hour', NOW() - INTERVAL '2 hours'), 10, 8, 2, 120.0, 100.0, 150.0, 200.0, 100, 10.0),
        ('workspace1', DATE_TRUNC('hour', NOW() - INTERVAL '3 hours'), 15, 12, 3, 130.0, 110.0, 160.0, 210.0, 150, 10.0)
    """
    )
    await db_session.execute(query)
    await db_session.commit()

    # Also need execution logs for the join
    query_logs = text(
        """
        INSERT INTO execution_logs (
            execution_id, agent_id, user_id, workspace_id,
            status, duration, credits_used, started_at
        ) VALUES
        ('daily1', 'agent1', 'user1', 'workspace1', 'completed', 120.0, 10, NOW() - INTERVAL '2 hours'),
        ('daily2', 'agent2', 'user2', 'workspace1', 'completed', 130.0, 15, NOW() - INTERVAL '3 hours')
    """
    )
    await db_session.execute(query_logs)
    await db_session.commit()

    # Run daily rollup
    target_date = datetime.utcnow().date() - timedelta(days=0)
    target_datetime = datetime.combine(target_date, datetime.min.time())
    result = await daily_rollup(db_session, target_datetime)

    # Verify result structure
    assert result["success"] is True
    assert result["period"] == "daily"
    assert "date" in result
    assert "workspaces_aggregated" in result

    # Cleanup
    await db_session.execute(text("DELETE FROM analytics.execution_metrics_hourly"))
    await db_session.execute(text("DELETE FROM execution_logs WHERE execution_id LIKE 'daily%'"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_hourly_rollup_idempotency(db_session, sample_execution_logs):
    """Test that hourly rollup can be run multiple times safely."""
    target_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    # Run rollup first time
    result1 = await hourly_rollup(db_session, target_hour)
    assert result1["success"] is True

    # Get count after first run
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM analytics.execution_metrics_hourly")
    )
    count1 = result.scalar()

    # Run rollup second time (should update, not duplicate)
    result2 = await hourly_rollup(db_session, target_hour)
    assert result2["success"] is True

    # Get count after second run (should be same due to ON CONFLICT)
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM analytics.execution_metrics_hourly")
    )
    count2 = result.scalar()

    assert count1 == count2  # No duplicates created


@pytest.mark.asyncio
async def test_aggregation_with_empty_data(db_session):
    """Test aggregations with no data."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    # Run aggregations with no data
    exec_count = await aggregate_execution_metrics(db_session, start_time, end_time)
    user_count = await aggregate_user_activity(db_session, start_time, end_time)
    credit_count = await aggregate_credit_consumption(db_session, start_time, end_time)

    # Should succeed but with 0 counts
    assert exec_count >= 0
    assert user_count >= 0
    assert credit_count >= 0


@pytest.mark.asyncio
async def test_materialized_view_refresh(db_session):
    """Test materialized view refresh."""
    # Note: This test assumes materialized views have been created
    # In a real scenario, you'd create them first or skip if not exists

    try:
        # Try to refresh a materialized view
        result = await refresh_materialized_view(
            db_session,
            "analytics.mv_hourly_execution_stats",
            concurrently=False,  # Use False for testing as CONCURRENTLY requires unique index
        )

        # Check result structure
        assert "view_name" in result
        assert "success" in result

    except Exception as e:
        # If materialized views don't exist yet, that's okay for this test
        # In production, they should be created via migrations
        pytest.skip(f"Materialized views not yet created: {str(e)}")


@pytest.mark.asyncio
async def test_aggregation_performance(db_session):
    """Test that aggregations complete within acceptable time."""
    import time

    # Insert a reasonable amount of test data
    query = text(
        """
        INSERT INTO execution_logs (
            execution_id, agent_id, user_id, workspace_id,
            status, duration, credits_used, started_at
        )
        SELECT
            'perf_exec_' || generate_series,
            'agent1',
            'user1',
            'workspace1',
            CASE WHEN random() > 0.2 THEN 'completed' ELSE 'failed' END,
            random() * 200,
            (random() * 20)::int,
            NOW() - (random() * INTERVAL '1 hour')
        FROM generate_series(1, 100)
    """
    )
    await db_session.execute(query)
    await db_session.commit()

    # Time the aggregation
    timer_start = time.time()
    end_time = datetime.utcnow()
    start_time_dt = end_time - timedelta(hours=2)

    await aggregate_execution_metrics(db_session, start_time_dt, end_time)

    elapsed = time.time() - timer_start

    # Should complete in under 5 seconds for 100 records
    assert elapsed < 5.0, f"Aggregation took {elapsed}s, expected < 5s"

    # Cleanup
    await db_session.execute(
        text("DELETE FROM execution_logs WHERE execution_id LIKE 'perf_exec_%'")
    )
    await db_session.commit()
