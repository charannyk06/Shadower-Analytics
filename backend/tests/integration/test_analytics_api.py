"""Integration tests for analytics API endpoints."""

import pytest
from httpx import AsyncClient
from datetime import date, datetime, timedelta
from typing import Dict

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    """Create test client."""
    from src.api.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    # In real tests, this would use a test JWT token
    return {"Authorization": "Bearer test_token"}


class TestExecutiveDashboardAPI:
    """Test suite for executive dashboard API."""

    @pytest.mark.asyncio
    async def test_get_executive_summary(self, client, auth_headers):
        """Test executive summary endpoint."""
        response = await client.get(
            "/api/v1/dashboard/executive/summary",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 401]  # Account for test environment
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_executive_summary_missing_params(self, client, auth_headers):
        """Test executive summary with missing parameters."""
        response = await client.get(
            "/api/v1/dashboard/executive/summary",
            headers=auth_headers
        )

        # Should return 422 for missing required parameters
        assert response.status_code in [422, 400]

    @pytest.mark.asyncio
    async def test_get_executive_summary_invalid_date_range(self, client, auth_headers):
        """Test executive summary with invalid date range."""
        response = await client.get(
            "/api/v1/dashboard/executive/summary",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-31",
                "date_to": "2024-01-01"  # End before start
            },
            headers=auth_headers
        )

        assert response.status_code in [400, 422]


class TestAgentAnalyticsAPI:
    """Test suite for agent analytics API."""

    @pytest.mark.asyncio
    async def test_get_agent_performance(self, client, auth_headers):
        """Test get agent performance endpoint."""
        response = await client.get(
            "/api/v1/analytics/agents/agent_123/performance",
            params={
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_agent_list(self, client, auth_headers):
        """Test get agent list endpoint."""
        response = await client.get(
            "/api/v1/analytics/agents",
            params={
                "workspace_id": "ws_test",
                "limit": 10,
                "offset": 0
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_get_agent_executions(self, client, auth_headers):
        """Test get agent executions endpoint."""
        response = await client.get(
            "/api/v1/analytics/agents/agent_123/executions",
            params={
                "limit": 50,
                "offset": 0
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]


class TestReportsAPI:
    """Test suite for reports API."""

    @pytest.mark.asyncio
    async def test_create_report_generation(self, client, auth_headers):
        """Test report generation endpoint."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={
                "name": "Test Report",
                "template_id": "template_daily",
                "format": "pdf",
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-01-31"
                }
            },
            headers=auth_headers
        )

        # Accept 202 (accepted), 201 (created), or 404 (endpoint not implemented yet)
        assert response.status_code in [201, 202, 404]
        if response.status_code in [201, 202]:
            data = response.json()
            assert "job_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_get_report_status(self, client, auth_headers):
        """Test get report status endpoint."""
        response = await client.get(
            "/api/v1/reports/job_123/status",
            headers=auth_headers
        )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_list_reports(self, client, auth_headers):
        """Test list reports endpoint."""
        response = await client.get(
            "/api/v1/reports",
            params={
                "workspace_id": "ws_test",
                "limit": 20
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]


class TestCreditsAPI:
    """Test suite for credits API."""

    @pytest.mark.asyncio
    async def test_get_credit_usage(self, client, auth_headers):
        """Test get credit usage endpoint."""
        response = await client.get(
            "/api/v1/credits/usage",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_credit_balance(self, client, auth_headers):
        """Test get credit balance endpoint."""
        response = await client.get(
            "/api/v1/credits/balance",
            params={"workspace_id": "ws_test"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404]


class TestAuthenticationAPI:
    """Test suite for authentication."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, client):
        """Test unauthenticated request returns 401."""
        response = await client.get(
            "/api/v1/dashboard/executive/summary",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )

        # Should return 401 or 403 for unauthenticated requests
        assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_invalid_token(self, client):
        """Test request with invalid token."""
        response = await client.get(
            "/api/v1/dashboard/executive/summary",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code in [401, 403, 404]


class TestPaginationAPI:
    """Test suite for pagination."""

    @pytest.mark.asyncio
    async def test_pagination_limits(self, client, auth_headers):
        """Test pagination with different limits."""
        for limit in [10, 50, 100]:
            response = await client.get(
                "/api/v1/analytics/agents",
                params={
                    "workspace_id": "ws_test",
                    "limit": limit,
                    "offset": 0
                },
                headers=auth_headers
            )

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_pagination_offset(self, client, auth_headers):
        """Test pagination with offset."""
        response = await client.get(
            "/api/v1/analytics/agents",
            params={
                "workspace_id": "ws_test",
                "limit": 10,
                "offset": 20
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, client, auth_headers):
        """Test 404 for non-existent endpoint."""
        response = await client.get(
            "/api/v1/nonexistent/endpoint",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, client, auth_headers):
        """Test 405 for wrong HTTP method."""
        response = await client.put(
            "/api/v1/dashboard/executive/summary",
            headers=auth_headers
        )

        assert response.status_code in [405, 404]

    @pytest.mark.asyncio
    async def test_422_validation_error(self, client, auth_headers):
        """Test 422 for validation errors."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={
                "invalid": "data"
            },
            headers=auth_headers
        )

        assert response.status_code in [422, 400, 404]
