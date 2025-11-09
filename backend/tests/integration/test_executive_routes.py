"""Integration tests for executive dashboard routes."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.database.tables import ExecutionLog


class TestExecutiveOverviewEndpoint:
    """Test suite for /api/v1/executive/overview endpoint."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "src.api.dependencies.auth.require_owner_or_admin"
        ) as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "roles": ["owner"],
            }
            yield mock

    @pytest.fixture
    def mock_workspace_access(self):
        """Mock workspace access validation."""
        with patch(
            "src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access"
        ) as mock:
            mock.return_value = AsyncMock(return_value=True)
            yield mock

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter."""
        with patch("src.api.routes.executive.executive_rate_limiter") as mock:
            mock.check_rate_limit.return_value = AsyncMock(return_value=(True, None))
            yield mock

    def test_overview_endpoint_requires_authentication(self, client):
        """Test that overview endpoint requires authentication."""
        response = client.get("/api/v1/executive/overview")
        # Should return 401 or redirect to login
        assert response.status_code in [401, 403]

    @patch("src.api.routes.executive.executive_metrics_service")
    def test_overview_endpoint_with_auth(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
        mock_rate_limiter,
    ):
        """Test overview endpoint with authentication."""
        # Mock service response
        mock_service.get_executive_overview.return_value = {
            "workspace_id": "test-workspace-id",
            "timeframe": "30d",
            "period": {
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-31T00:00:00",
            },
            "mrr": 50000,
            "churn_rate": 2.5,
            "ltv": 10000,
            "dau": 100,
            "wau": 500,
            "mau": 1500,
            "total_executions": 5000,
            "success_rate": 95.5,
        }

        response = client.get(
            "/api/v1/executive/overview",
            params={"timeframe": "30d"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == "test-workspace-id"
        assert data["dau"] == 100
        assert data["success_rate"] == 95.5

    def test_overview_endpoint_validates_timeframe(
        self, client, mock_auth, mock_workspace_access, mock_rate_limiter
    ):
        """Test that invalid timeframe is rejected."""
        response = client.get(
            "/api/v1/executive/overview",
            params={"timeframe": "invalid"},
        )

        # FastAPI's regex validation should reject this
        assert response.status_code == 422

    def test_overview_endpoint_validates_workspace_id_format(
        self, client, mock_auth, mock_rate_limiter
    ):
        """Test workspace ID validation."""
        with patch("src.api.routes.executive.validate_workspace_id") as mock_validate:
            mock_validate.side_effect = Exception("Invalid workspace ID")

            response = client.get(
                "/api/v1/executive/overview",
                params={"workspace_id": "invalid@#$%"},
            )

            # Should return error from validation
            assert response.status_code in [400, 500]

    @patch("src.api.routes.executive.executive_metrics_service")
    def test_overview_endpoint_skip_cache_parameter(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
        mock_rate_limiter,
    ):
        """Test that skip_cache parameter is passed to service."""
        mock_service.get_executive_overview.return_value = {
            "workspace_id": "test-workspace-id",
            "timeframe": "30d",
            "period": {"start": "2024-01-01", "end": "2024-01-31"},
            "mrr": 0,
            "churn_rate": 0,
            "ltv": 0,
            "dau": 0,
            "wau": 0,
            "mau": 0,
            "total_executions": 0,
            "success_rate": 0,
        }

        response = client.get(
            "/api/v1/executive/overview",
            params={"skip_cache": True},
        )

        assert response.status_code == 200
        # Verify service was called with skip_cache=True
        mock_service.get_executive_overview.assert_called_once()
        call_args = mock_service.get_executive_overview.call_args
        assert call_args.kwargs.get("skip_cache") is True


class TestRevenueMetricsEndpoint:
    """Test suite for /api/v1/executive/revenue endpoint."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "src.api.dependencies.auth.require_owner_or_admin"
        ) as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "roles": ["owner"],
            }
            yield mock

    @pytest.fixture
    def mock_workspace_access(self):
        """Mock workspace access validation."""
        with patch(
            "src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access"
        ) as mock:
            mock.return_value = AsyncMock(return_value=True)
            yield mock

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter."""
        with patch("src.api.routes.executive.executive_rate_limiter") as mock:
            mock.check_rate_limit.return_value = AsyncMock(return_value=(True, None))
            yield mock

    @patch("src.api.routes.executive.executive_metrics_service")
    def test_revenue_endpoint(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
        mock_rate_limiter,
    ):
        """Test revenue metrics endpoint."""
        mock_service.get_revenue_metrics.return_value = {
            "workspace_id": "test-workspace-id",
            "timeframe": "30d",
            "total_revenue": 100000,
            "mrr": 50000,
            "arr": 600000,
            "trend": [],
            "growth_rate": 10.5,
        }

        response = client.get(
            "/api/v1/executive/revenue",
            params={"timeframe": "30d"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_revenue"] == 100000
        assert data["mrr"] == 50000

    def test_revenue_endpoint_validates_timeframe(
        self, client, mock_auth, mock_workspace_access, mock_rate_limiter
    ):
        """Test timeframe validation for revenue endpoint."""
        # Valid timeframes: 7d, 30d, 90d, 1y
        response = client.get(
            "/api/v1/executive/revenue",
            params={"timeframe": "24h"},  # Invalid for revenue endpoint
        )

        assert response.status_code == 422


class TestKPIsEndpoint:
    """Test suite for /api/v1/executive/kpis endpoint."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "src.api.dependencies.auth.require_owner_or_admin"
        ) as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "roles": ["admin"],
            }
            yield mock

    @pytest.fixture
    def mock_workspace_access(self):
        """Mock workspace access validation."""
        with patch(
            "src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access"
        ) as mock:
            mock.return_value = AsyncMock(return_value=True)
            yield mock

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter."""
        with patch("src.api.routes.executive.executive_rate_limiter") as mock:
            mock.check_rate_limit.return_value = AsyncMock(return_value=(True, None))
            yield mock

    @patch("src.api.routes.executive.executive_metrics_service")
    def test_kpis_endpoint(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
        mock_rate_limiter,
    ):
        """Test KPIs endpoint."""
        mock_service.get_key_performance_indicators.return_value = {
            "workspace_id": "test-workspace-id",
            "total_users": 500,
            "active_agents": 50,
            "total_executions": 10000,
            "success_rate": 98.5,
            "avg_execution_time": 2.5,
            "total_credits_used": 50000,
        }

        response = client.get("/api/v1/executive/kpis")

        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 500
        assert data["active_agents"] == 50
        assert data["success_rate"] == 98.5


class TestRateLimiting:
    """Test rate limiting for executive endpoints."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "src.api.dependencies.auth.require_owner_or_admin"
        ) as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "roles": ["owner"],
            }
            yield mock

    @pytest.fixture
    def mock_workspace_access(self):
        """Mock workspace access validation."""
        with patch(
            "src.api.middleware.workspace.WorkspaceAccess.validate_workspace_access"
        ) as mock:
            mock.return_value = AsyncMock(return_value=True)
            yield mock

    @patch("src.api.routes.executive.executive_rate_limiter")
    @patch("src.api.routes.executive.executive_metrics_service")
    def test_rate_limit_exceeded(
        self,
        mock_service,
        mock_limiter,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test that rate limit exceeded returns 429."""
        # Mock rate limiter to return exceeded
        mock_limiter.check_rate_limit.return_value = AsyncMock(
            return_value=(False, "Rate limit exceeded")
        )

        response = client.get("/api/v1/executive/overview")

        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()

    @patch("src.api.routes.executive.executive_rate_limiter")
    @patch("src.api.routes.executive.executive_metrics_service")
    def test_rate_limit_allows_request(
        self,
        mock_service,
        mock_limiter,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test that rate limiter allows valid requests."""
        # Mock rate limiter to allow request
        mock_limiter.check_rate_limit.return_value = AsyncMock(
            return_value=(True, None)
        )

        mock_service.get_executive_overview.return_value = {
            "workspace_id": "test-workspace-id",
            "timeframe": "30d",
            "period": {"start": "2024-01-01", "end": "2024-01-31"},
            "mrr": 0,
            "churn_rate": 0,
            "ltv": 0,
            "dau": 0,
            "wau": 0,
            "mau": 0,
            "total_executions": 0,
            "success_rate": 0,
        }

        response = client.get("/api/v1/executive/overview")

        assert response.status_code == 200


class TestWorkspaceValidation:
    """Test workspace ID validation."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "src.api.dependencies.auth.require_owner_or_admin"
        ) as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "roles": ["owner"],
            }
            yield mock

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter."""
        with patch("src.api.routes.executive.executive_rate_limiter") as mock:
            mock.check_rate_limit.return_value = AsyncMock(return_value=(True, None))
            yield mock

    def test_validate_workspace_id_valid_formats(self):
        """Test that valid workspace IDs are accepted."""
        from src.api.routes.executive import validate_workspace_id

        valid_ids = [
            "test-workspace-123",
            "workspace_456",
            "ABC123",
            "test-workspace-abc-123",
        ]

        for workspace_id in valid_ids:
            result = validate_workspace_id(workspace_id)
            assert result == workspace_id

    def test_validate_workspace_id_invalid_formats(self):
        """Test that invalid workspace IDs are rejected."""
        from src.api.routes.executive import validate_workspace_id
        from fastapi import HTTPException

        invalid_ids = [
            "test@workspace",
            "workspace#123",
            "test workspace",
            "workspace$",
            "",
            "a" * 256,  # Too long
        ]

        for workspace_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_workspace_id(workspace_id)
            assert exc_info.value.status_code == 400
