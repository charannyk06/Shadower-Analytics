"""Unit tests for ExecutionMetricsService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics.execution_metrics import ExecutionMetricsService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def execution_metrics_service(mock_db_session):
    """Create ExecutionMetricsService instance with mock session."""
    return ExecutionMetricsService(db=mock_db_session)


@pytest.mark.asyncio
async def test_get_execution_metrics_basic(execution_metrics_service, mock_db_session):
    """Test basic execution metrics retrieval."""
    workspace_id = "test-workspace-123"
    timeframe = "1h"

    # Mock the individual metric methods
    with patch.object(
        execution_metrics_service, '_get_realtime_metrics',
        new_callable=AsyncMock
    ) as mock_realtime, \
    patch.object(
        execution_metrics_service, '_get_throughput_metrics',
        new_callable=AsyncMock
    ) as mock_throughput, \
    patch.object(
        execution_metrics_service, '_get_latency_metrics',
        new_callable=AsyncMock
    ) as mock_latency, \
    patch.object(
        execution_metrics_service, '_get_performance_metrics',
        new_callable=AsyncMock
    ) as mock_performance, \
    patch.object(
        execution_metrics_service, '_get_execution_patterns',
        new_callable=AsyncMock
    ) as mock_patterns, \
    patch.object(
        execution_metrics_service, '_get_resource_utilization',
        new_callable=AsyncMock
    ) as mock_resources:

        # Set return values
        mock_realtime.return_value = {"currentlyRunning": 5, "queueDepth": 3}
        mock_throughput.return_value = {"executionsPerMinute": 10}
        mock_latency.return_value = {"executionLatency": {"p50": 100}}
        mock_performance.return_value = {"totalExecutions": 100, "successRate": 95.5}
        mock_patterns.return_value = {"timeline": []}
        mock_resources.return_value = {"compute": {}}

        # Execute
        result = await execution_metrics_service.get_execution_metrics(workspace_id, timeframe)

        # Assert
        assert result is not None
        assert result["workspaceId"] == workspace_id
        assert result["timeframe"] == timeframe
        assert "realtime" in result
        assert "throughput" in result
        assert "latency" in result
        assert "performance" in result
        assert "patterns" in result
        assert "resources" in result


@pytest.mark.asyncio
async def test_get_execution_metrics_handles_partial_failures(execution_metrics_service):
    """Test that get_execution_metrics handles partial failures gracefully."""
    workspace_id = "test-workspace-123"
    timeframe = "1h"

    # Mock methods with one raising an exception
    with patch.object(
        execution_metrics_service, '_get_realtime_metrics',
        new_callable=AsyncMock
    ) as mock_realtime, \
    patch.object(
        execution_metrics_service, '_get_throughput_metrics',
        side_effect=Exception("Database error")
    ), \
    patch.object(
        execution_metrics_service, '_get_latency_metrics',
        new_callable=AsyncMock
    ) as mock_latency, \
    patch.object(
        execution_metrics_service, '_get_performance_metrics',
        new_callable=AsyncMock
    ) as mock_performance, \
    patch.object(
        execution_metrics_service, '_get_execution_patterns',
        new_callable=AsyncMock
    ) as mock_patterns, \
    patch.object(
        execution_metrics_service, '_get_resource_utilization',
        new_callable=AsyncMock
    ) as mock_resources:

        mock_realtime.return_value = {"currentlyRunning": 5}
        mock_latency.return_value = {"executionLatency": {"p50": 100}}
        mock_performance.return_value = {"totalExecutions": 100}
        mock_patterns.return_value = {"timeline": []}
        mock_resources.return_value = {"compute": {}}

        # Execute - should not raise exception
        result = await execution_metrics_service.get_execution_metrics(workspace_id, timeframe)

        # Assert - should have default values for failed metric
        assert result is not None
        assert "throughput" in result
        # Should have default throughput values since the call failed
        assert result["throughput"]["executionsPerMinute"] == 0


@pytest.mark.asyncio
async def test_calculate_start_time(execution_metrics_service):
    """Test start time calculation from timeframe."""
    end_time = datetime(2025, 11, 9, 12, 0, 0)

    # Test various timeframes
    assert execution_metrics_service._calculate_start_time("1h", end_time) == end_time - timedelta(hours=1)
    assert execution_metrics_service._calculate_start_time("6h", end_time) == end_time - timedelta(hours=6)
    assert execution_metrics_service._calculate_start_time("24h", end_time) == end_time - timedelta(hours=24)
    assert execution_metrics_service._calculate_start_time("7d", end_time) == end_time - timedelta(days=7)
    assert execution_metrics_service._calculate_start_time("30d", end_time) == end_time - timedelta(days=30)

    # Test invalid timeframe defaults to 1h
    assert execution_metrics_service._calculate_start_time("invalid", end_time) == end_time - timedelta(hours=1)


@pytest.mark.asyncio
async def test_get_realtime_metrics_structure(execution_metrics_service, mock_db_session):
    """Test that realtime metrics returns proper structure."""
    workspace_id = "test-workspace-123"

    # Mock database execute to return empty results
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with patch.object(
        execution_metrics_service, '_get_system_load',
        new_callable=AsyncMock,
        return_value={"cpu": 50.0, "memory": 60.0}
    ):
        result = await execution_metrics_service._get_realtime_metrics(workspace_id)

        # Assert structure
        assert "currentlyRunning" in result
        assert "queueDepth" in result
        assert "avgQueueWaitTime" in result
        assert "executionsInProgress" in result
        assert "queuedExecutions" in result
        assert "systemLoad" in result

        # Assert types
        assert isinstance(result["currentlyRunning"], int)
        assert isinstance(result["queueDepth"], int)
        assert isinstance(result["avgQueueWaitTime"], (int, float))
        assert isinstance(result["executionsInProgress"], list)
        assert isinstance(result["queuedExecutions"], list)


@pytest.mark.asyncio
async def test_get_throughput_metrics_with_data(execution_metrics_service, mock_db_session):
    """Test throughput metrics calculation with data."""
    workspace_id = "test-workspace-123"
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()

    # Mock database responses
    stats_result = MagicMock()
    stats_result.mappings.return_value.first.return_value = {
        'total_minutes': 1440,
        'total_executions': 1000,
        'avg_per_minute': 0.694,
        'peak_executions': 5
    }

    trend_result = MagicMock()
    trend_result.mappings.return_value.all.return_value = [
        {'timestamp': datetime.now() - timedelta(hours=1), 'value': 10}
    ]

    mock_db_session.execute = AsyncMock(side_effect=[stats_result, trend_result])

    result = await execution_metrics_service._get_throughput_metrics(
        workspace_id, start_time, end_time
    )

    # Assert structure and values
    assert "executionsPerMinute" in result
    assert "executionsPerHour" in result
    assert "executionsPerDay" in result
    assert "throughputTrend" in result
    assert "peakThroughput" in result

    # Check calculations
    assert result["executionsPerMinute"] > 0
    assert result["executionsPerHour"] > result["executionsPerMinute"]
    assert isinstance(result["throughputTrend"], list)


@pytest.mark.asyncio
async def test_get_latency_metrics_structure(execution_metrics_service, mock_db_session):
    """Test latency metrics returns proper percentile structure."""
    workspace_id = "test-workspace-123"
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()

    # Mock database responses
    stats_result = MagicMock()
    stats_result.mappings.return_value.first.return_value = {
        'exec_avg': 150.5, 'exec_p50': 120, 'exec_p75': 180,
        'exec_p90': 250, 'exec_p95': 300, 'exec_p99': 450,
        'queue_avg': 0, 'queue_p50': 0, 'queue_p75': 0,
        'queue_p90': 0, 'queue_p95': 0, 'queue_p99': 0
    }

    distribution_result = MagicMock()
    distribution_result.mappings.return_value.all.return_value = [
        {'bucket': '0-1s', 'count': 50},
        {'bucket': '1-5s', 'count': 100}
    ]

    mock_db_session.execute = AsyncMock(side_effect=[stats_result, distribution_result])

    result = await execution_metrics_service._get_latency_metrics(
        workspace_id, start_time, end_time
    )

    # Assert all percentile fields exist
    for latency_type in ["queueLatency", "executionLatency", "endToEndLatency"]:
        assert latency_type in result
        assert "p50" in result[latency_type]
        assert "p75" in result[latency_type]
        assert "p90" in result[latency_type]
        assert "p95" in result[latency_type]
        assert "p99" in result[latency_type]
        assert "avg" in result[latency_type]

    # Assert distribution exists
    assert "latencyDistribution" in result
    assert isinstance(result["latencyDistribution"], list)


@pytest.mark.asyncio
async def test_get_performance_metrics_success_rate(execution_metrics_service, mock_db_session):
    """Test performance metrics calculates success rate correctly."""
    workspace_id = "test-workspace-123"
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()

    # Mock overall stats
    overall_result = MagicMock()
    overall_result.mappings.return_value.first.return_value = {
        'total_executions': 100,
        'successful': 95,
        'failed': 3,
        'cancelled': 2
    }

    # Mock by_agent stats
    agent_result = MagicMock()
    agent_result.mappings.return_value.all.return_value = []

    # Mock by_hour stats
    hour_result = MagicMock()
    hour_result.mappings.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[
        overall_result, agent_result, hour_result
    ])

    result = await execution_metrics_service._get_performance_metrics(
        workspace_id, start_time, end_time
    )

    # Assert success rate calculation
    assert result["totalExecutions"] == 100
    assert result["successfulExecutions"] == 95
    assert result["failedExecutions"] == 3
    assert result["cancelledExecutions"] == 2
    assert result["successRate"] == 95.0
    assert result["failureRate"] == 3.0
    assert result["cancellationRate"] == 2.0


@pytest.mark.asyncio
async def test_get_performance_metrics_zero_executions(execution_metrics_service, mock_db_session):
    """Test performance metrics handles zero executions gracefully."""
    workspace_id = "test-workspace-123"
    start_time = datetime.now() - timedelta(hours=24)
    end_time = datetime.now()

    # Mock empty results
    empty_result = MagicMock()
    empty_result.mappings.return_value.first.return_value = {
        'total_executions': 0,
        'successful': 0,
        'failed': 0,
        'cancelled': 0
    }

    empty_list = MagicMock()
    empty_list.mappings.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[
        empty_result, empty_list, empty_list
    ])

    result = await execution_metrics_service._get_performance_metrics(
        workspace_id, start_time, end_time
    )

    # Should not divide by zero
    assert result["successRate"] == 0
    assert result["failureRate"] == 0


@pytest.mark.asyncio
async def test_legacy_function_deprecation_warnings():
    """Test that legacy functions emit deprecation warnings."""
    from src.services.metrics.execution_metrics import (
        get_execution_stats,
        get_execution_trends,
        get_execution_distribution
    )

    mock_db = MagicMock(spec=AsyncSession)
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock,
        return_value={
            'performance': {
                'totalExecutions': 100,
                'successfulExecutions': 95,
                'failedExecutions': 5,
                'cancelledExecutions': 0
            },
            'latency': {
                'executionLatency': {'avg': 150, 'p95': 300, 'p99': 450}
            },
            'patterns': {'timeline': []}
        }
    ):
        # Test each legacy function emits deprecation warning
        with pytest.warns(DeprecationWarning):
            await get_execution_stats(mock_db, start_date, end_date)

        with pytest.warns(DeprecationWarning):
            await get_execution_trends(mock_db, start_date, end_date)

        with pytest.warns(DeprecationWarning):
            await get_execution_distribution(mock_db, start_date, end_date)


@pytest.mark.asyncio
async def test_legacy_functions_accept_workspace_id():
    """Test that legacy functions accept workspace_id parameter."""
    from src.services.metrics.execution_metrics import get_execution_stats

    mock_db = MagicMock(spec=AsyncSession)
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    workspace_id = "custom-workspace"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock,
        return_value={
            'performance': {
                'totalExecutions': 100,
                'successfulExecutions': 95,
                'failedExecutions': 5,
                'cancelledExecutions': 0
            },
            'latency': {
                'executionLatency': {'avg': 150, 'p95': 300, 'p99': 450}
            }
        }
    ) as mock_metrics:
        with pytest.warns(DeprecationWarning):
            await get_execution_stats(mock_db, start_date, end_date, workspace_id)

        # Verify the workspace_id was passed through
        mock_metrics.assert_called_once()
        call_args = mock_metrics.call_args
        assert call_args[0][0] == workspace_id
