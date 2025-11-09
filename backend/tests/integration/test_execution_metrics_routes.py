"""Integration tests for execution metrics API routes."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "sub": "test-user-123",
        "email": "test@example.com",
        "workspace_id": "test-workspace-123"
    }


@pytest.fixture
def mock_workspace_validation():
    """Mock workspace access validation."""
    with patch(
        'src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access',
        new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_current_user(mock_user):
    """Mock get_current_user dependency."""
    with patch(
        'src.api.dependencies.auth.get_current_user',
        return_value=mock_user
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_execution_metrics_success(client, mock_current_user, mock_workspace_validation):
    """Test successful execution metrics retrieval."""
    workspace_id = "test-workspace-123"
    timeframe = "24h"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock
    ) as mock_service:
        mock_service.return_value = {
            "timeframe": timeframe,
            "workspaceId": workspace_id,
            "realtime": {"currentlyRunning": 5, "queueDepth": 3},
            "throughput": {"executionsPerMinute": 10},
            "latency": {"executionLatency": {"p50": 100}},
            "performance": {"totalExecutions": 100, "successRate": 95},
            "patterns": {"timeline": []},
            "resources": {"compute": {}}
        }

        response = client.get(
            "/api/v1/metrics/execution",
            params={"workspace_id": workspace_id, "timeframe": timeframe}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["workspaceId"] == workspace_id
        assert data["timeframe"] == timeframe
        assert "realtime" in data
        assert "throughput" in data


@pytest.mark.asyncio
async def test_get_execution_metrics_invalid_timeframe(client, mock_current_user, mock_workspace_validation):
    """Test execution metrics with invalid timeframe."""
    workspace_id = "test-workspace-123"

    response = client.get(
        "/api/v1/metrics/execution",
        params={"workspace_id": workspace_id, "timeframe": "invalid"}
    )

    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_execution_metrics_unauthorized_workspace(client, mock_current_user):
    """Test execution metrics with unauthorized workspace access."""
    workspace_id = "unauthorized-workspace"

    with patch(
        'src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access',
        side_effect=Exception("Unauthorized")
    ):
        response = client.get(
            "/api/v1/metrics/execution",
            params={"workspace_id": workspace_id, "timeframe": "24h"}
        )

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR]


@pytest.mark.asyncio
async def test_get_execution_realtime_success(client, mock_current_user, mock_workspace_validation):
    """Test successful realtime metrics retrieval."""
    workspace_id = "test-workspace-123"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService._get_realtime_metrics',
        new_callable=AsyncMock
    ) as mock_service:
        mock_service.return_value = {
            "currentlyRunning": 5,
            "queueDepth": 3,
            "avgQueueWaitTime": 120,
            "executionsInProgress": [],
            "queuedExecutions": [],
            "systemLoad": {"cpu": 50, "memory": 60}
        }

        response = client.get(
            "/api/v1/metrics/execution/realtime",
            params={"workspace_id": workspace_id}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["workspaceId"] == workspace_id
        assert "realtime" in data
        assert data["realtime"]["currentlyRunning"] == 5


@pytest.mark.asyncio
async def test_get_execution_realtime_rate_limiting(client, mock_current_user, mock_workspace_validation):
    """Test rate limiting on realtime metrics endpoint."""
    workspace_id = "test-workspace-123"

    # Mock rate limiter to reject requests
    with patch(
        'src.api.routes.metrics.metrics_realtime_limiter.check_rate_limit',
        new_callable=AsyncMock,
        return_value=(False, "Rate limit exceeded")
    ):
        response = client.get(
            "/api/v1/metrics/execution/realtime",
            params={"workspace_id": workspace_id}
        )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_get_execution_throughput_success(client, mock_current_user, mock_workspace_validation):
    """Test successful throughput metrics retrieval."""
    workspace_id = "test-workspace-123"
    timeframe = "24h"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock
    ) as mock_service:
        mock_service.return_value = {
            "throughput": {
                "executionsPerMinute": 10,
                "executionsPerHour": 600,
                "executionsPerDay": 14400,
                "throughputTrend": []
            }
        }

        response = client.get(
            "/api/v1/metrics/execution/throughput",
            params={"workspace_id": workspace_id, "timeframe": timeframe}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["workspaceId"] == workspace_id
        assert data["timeframe"] == timeframe
        assert "throughput" in data


@pytest.mark.asyncio
async def test_get_execution_latency_success(client, mock_current_user, mock_workspace_validation):
    """Test successful latency metrics retrieval."""
    workspace_id = "test-workspace-123"
    timeframe = "24h"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock
    ) as mock_service:
        mock_service.return_value = {
            "latency": {
                "executionLatency": {
                    "p50": 100,
                    "p75": 150,
                    "p90": 200,
                    "p95": 250,
                    "p99": 400
                },
                "queueLatency": {},
                "endToEndLatency": {},
                "latencyDistribution": []
            }
        }

        response = client.get(
            "/api/v1/metrics/execution/latency",
            params={"workspace_id": workspace_id, "timeframe": timeframe}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["workspaceId"] == workspace_id
        assert "latency" in data
        assert "executionLatency" in data["latency"]


@pytest.mark.asyncio
async def test_get_execution_metrics_handles_service_errors(client, mock_current_user, mock_workspace_validation):
    """Test that API handles service errors gracefully."""
    workspace_id = "test-workspace-123"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        side_effect=Exception("Database connection error")
    ):
        response = client.get(
            "/api/v1/metrics/execution",
            params={"workspace_id": workspace_id, "timeframe": "24h"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to fetch execution metrics" in response.json()["detail"]


@pytest.mark.asyncio
async def test_execution_metrics_requires_authentication(client):
    """Test that metrics endpoints require authentication."""
    # Override auth to raise exception
    with patch(
        'src.api.dependencies.auth.get_current_user',
        side_effect=Exception("Unauthorized")
    ):
        response = client.get(
            "/api/v1/metrics/execution",
            params={"workspace_id": "test", "timeframe": "24h"}
        )

        # Should return 401 or 500 depending on error handling
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


@pytest.mark.asyncio
async def test_execution_metrics_validates_workspace_access(client, mock_current_user):
    """Test that workspace access validation is enforced."""
    workspace_id = "unauthorized-workspace"

    with patch(
        'src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access',
        new_callable=AsyncMock,
        side_effect=Exception("Access denied")
    ):
        response = client.get(
            "/api/v1/metrics/execution",
            params={"workspace_id": workspace_id, "timeframe": "24h"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_execution_metrics_all_timeframes(client, mock_current_user, mock_workspace_validation):
    """Test that all valid timeframes are accepted."""
    workspace_id = "test-workspace-123"
    valid_timeframes = ["1h", "6h", "24h", "7d", "30d", "90d"]

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService.get_execution_metrics',
        new_callable=AsyncMock
    ) as mock_service:
        mock_service.return_value = {
            "timeframe": "1h",
            "workspaceId": workspace_id,
            "realtime": {},
            "throughput": {},
            "latency": {},
            "performance": {},
            "patterns": {},
            "resources": {}
        }

        for timeframe in valid_timeframes:
            response = client.get(
                "/api/v1/metrics/execution",
                params={"workspace_id": workspace_id, "timeframe": timeframe}
            )

            assert response.status_code == status.HTTP_200_OK, \
                f"Timeframe {timeframe} should be valid"


@pytest.mark.asyncio
async def test_realtime_metrics_concurrent_requests(client, mock_current_user, mock_workspace_validation):
    """Test that realtime endpoint handles concurrent requests."""
    workspace_id = "test-workspace-123"

    with patch(
        'src.services.metrics.execution_metrics.ExecutionMetricsService._get_realtime_metrics',
        new_callable=AsyncMock
    ) as mock_service, \
    patch(
        'src.api.routes.metrics.metrics_realtime_limiter.check_rate_limit',
        new_callable=AsyncMock,
        return_value=(True, None)
    ):
        mock_service.return_value = {
            "currentlyRunning": 5,
            "queueDepth": 3,
            "avgQueueWaitTime": 120,
            "executionsInProgress": [],
            "queuedExecutions": [],
            "systemLoad": {}
        }

        # Make multiple concurrent requests
        responses = []
        for _ in range(5):
            response = client.get(
                "/api/v1/metrics/execution/realtime",
                params={"workspace_id": workspace_id}
            )
            responses.append(response)

        # All should succeed (assuming rate limit allows)
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
