"""
Integration tests for Comparison API routes
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from fastapi import status


class TestComparisonRoutes:
    """Test suite for comparison API routes"""

    # ========================================================================
    # Agent Comparison Endpoint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_agents_endpoint(self, client: AsyncClient):
        """Test agent comparison endpoint"""
        response = await client.post(
            "/api/v1/comparisons/agents",
            params={
                "agent_ids": ["agent-1", "agent-2", "agent-3"],
                "include_recommendations": True,
                "include_visual_diff": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["type"] == "agents"
        assert data["data"]["agent_comparison"] is not None
        assert len(data["data"]["agent_comparison"]["agents"]) == 3

    @pytest.mark.asyncio
    async def test_compare_agents_too_few(self, client: AsyncClient):
        """Test agent comparison with too few agents"""
        response = await client.post(
            "/api/v1/comparisons/agents",
            params={
                "agent_ids": ["agent-1"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_compare_agents_too_many(self, client: AsyncClient):
        """Test agent comparison with too many agents"""
        agent_ids = [f"agent-{i}" for i in range(15)]

        response = await client.post(
            "/api/v1/comparisons/agents",
            params={"agent_ids": agent_ids},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ========================================================================
    # Period Comparison Endpoint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_periods_endpoint(self, client: AsyncClient):
        """Test period comparison endpoint"""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = await client.post(
            "/api/v1/comparisons/periods",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "include_time_series": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["type"] == "periods"
        assert data["data"]["period_comparison"] is not None

        period_comp = data["data"]["period_comparison"]
        assert "current" in period_comp
        assert "previous" in period_comp
        assert "change" in period_comp

    @pytest.mark.asyncio
    async def test_compare_periods_default_dates(self, client: AsyncClient):
        """Test period comparison with default dates"""
        response = await client.post("/api/v1/comparisons/periods")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True

    # ========================================================================
    # Workspace Comparison Endpoint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_workspaces_endpoint(self, client: AsyncClient):
        """Test workspace comparison endpoint"""
        response = await client.post(
            "/api/v1/comparisons/workspaces",
            params={
                "workspace_ids": ["ws-1", "ws-2", "ws-3"],
                "include_statistics": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["type"] == "workspaces"
        assert data["data"]["workspace_comparison"] is not None

        ws_comp = data["data"]["workspace_comparison"]
        assert "workspaces" in ws_comp
        assert "benchmarks" in ws_comp
        assert "rankings" in ws_comp

    @pytest.mark.asyncio
    async def test_compare_workspaces_too_few(self, client: AsyncClient):
        """Test workspace comparison with too few workspaces"""
        response = await client.post(
            "/api/v1/comparisons/workspaces",
            params={"workspace_ids": ["ws-1"]},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ========================================================================
    # Metric Comparison Endpoint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_metrics_endpoint(self, client: AsyncClient):
        """Test metric comparison endpoint"""
        response = await client.post(
            "/api/v1/comparisons/metrics",
            params={
                "metric_name": "success_rate",
                "include_statistics": True,
                "include_correlations": False,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["type"] == "metrics"
        assert data["data"]["metric_comparison"] is not None

        metric_comp = data["data"]["metric_comparison"]
        assert metric_comp["metric_name"] == "success_rate"
        assert "statistics" in metric_comp
        assert "distribution" in metric_comp

    @pytest.mark.asyncio
    async def test_compare_metrics_with_correlations(self, client: AsyncClient):
        """Test metric comparison with correlations"""
        response = await client.post(
            "/api/v1/comparisons/metrics",
            params={
                "metric_name": "success_rate",
                "include_correlations": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        metric_comp = data["data"]["metric_comparison"]
        assert "correlations" in metric_comp
        assert isinstance(metric_comp["correlations"], list)

    # ========================================================================
    # Generic Comparison Endpoint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generic_comparison_endpoint(self, client: AsyncClient):
        """Test generic comparison endpoint"""
        payload = {
            "type": "agents",
            "filters": {
                "agent_ids": ["agent-1", "agent-2"],
            },
            "options": {
                "include_recommendations": True,
            },
        }

        response = await client.post("/api/v1/comparisons/", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["type"] == "agents"

    # ========================================================================
    # Health Check Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test comparison service health check"""
        response = await client.get("/api/v1/comparisons/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "comparison-views"
        assert "timestamp" in data

    # ========================================================================
    # Performance Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_comparison_performance(self, client: AsyncClient):
        """Test that comparisons meet performance targets"""
        import time

        start = time.time()

        response = await client.post(
            "/api/v1/comparisons/agents",
            params={"agent_ids": ["agent-1", "agent-2", "agent-3"]},
        )

        end = time.time()
        elapsed = end - start

        assert response.status_code == status.HTTP_200_OK
        # Should complete in less than 1.5 seconds
        assert elapsed < 1.5

        data = response.json()
        assert data["metadata"]["processing_time"] < 0.5

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_invalid_request_body(self, client: AsyncClient):
        """Test handling of invalid request body"""
        response = await client.post(
            "/api/v1/comparisons/",
            json={"invalid": "data"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_required_params(self, client: AsyncClient):
        """Test handling of missing required parameters"""
        response = await client.post("/api/v1/comparisons/agents")

        # Should fail due to missing agent_ids
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
