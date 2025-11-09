"""Integration tests for leaderboard API routes."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.api.main import app
from src.models.schemas.leaderboards import TimeFrame, AgentCriteria, UserCriteria, WorkspaceCriteria


@pytest.fixture
def mock_leaderboard_service():
    """Create a mock leaderboard service."""
    with patch("src.api.routes.leaderboards.LeaderboardService") as mock:
        yield mock


@pytest.fixture
def mock_auth():
    """Mock authentication dependencies."""
    with patch("src.api.routes.leaderboards.get_current_user") as mock_user, \
         patch("src.api.routes.leaderboards.validate_workspace_access") as mock_workspace:
        mock_user.return_value = {"user_id": "user-123", "email": "test@example.com"}
        mock_workspace.return_value = True
        yield mock_user, mock_workspace


class TestAgentLeaderboardRoutes:
    """Test agent leaderboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_agent_leaderboard_success(self, mock_leaderboard_service, mock_auth):
        """Test successful agent leaderboard retrieval."""
        # Mock service response
        mock_service_instance = MagicMock()
        mock_service_instance.get_agent_leaderboard = AsyncMock(return_value={
            "criteria": "success_rate",
            "timeframe": "7d",
            "rankings": [
                {
                    "rank": 1,
                    "previousRank": None,
                    "change": "new",
                    "agent": {
                        "id": "agent-123",
                        "name": "Test Agent",
                        "type": "automation",
                        "workspace": "Test Workspace",
                    },
                    "metrics": {
                        "totalRuns": 100,
                        "successRate": 95.0,
                        "avgRuntime": 1000.0,
                        "creditsPerRun": 10.0,
                        "uniqueUsers": 5,
                    },
                    "score": 100.0,
                    "percentile": 100.0,
                    "badge": "gold",
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 100,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/agents",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                    "timeframe": "7d",
                    "criteria": "success_rate",
                    "limit": 100,
                    "offset": 0,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["criteria"] == "success_rate"
        assert data["timeframe"] == "7d"
        assert len(data["rankings"]) == 1
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["badge"] == "gold"

    @pytest.mark.asyncio
    async def test_get_agent_leaderboard_invalid_workspace_id(self, mock_auth):
        """Test agent leaderboard with invalid workspace ID."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/agents",
                params={
                    "workspace_id": "invalid-uuid",
                    "timeframe": "7d",
                    "criteria": "success_rate",
                }
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_agent_leaderboard_different_criteria(self, mock_leaderboard_service, mock_auth):
        """Test agent leaderboard with different criteria."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_agent_leaderboard = AsyncMock(return_value={
            "criteria": "runs",
            "timeframe": "30d",
            "rankings": [],
            "total": 0,
            "offset": 0,
            "limit": 100,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/agents",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                    "timeframe": "30d",
                    "criteria": "runs",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["criteria"] == "runs"
        assert data["timeframe"] == "30d"

    @pytest.mark.asyncio
    async def test_get_my_agent_rank_success(self, mock_leaderboard_service, mock_auth):
        """Test successful my agent rank retrieval."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_agent_leaderboard = AsyncMock(return_value={
            "rankings": [
                {
                    "rank": 5,
                    "agent": {"id": "agent-123"},
                    "percentile": 85.0,
                    "score": 75.5,
                    "badge": None,
                    "change": "up",
                }
            ],
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/my-rank/agent/agent-123",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                    "timeframe": "7d",
                    "criteria": "success_rate",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["agentId"] == "agent-123"
        assert data["rank"] == 5
        assert data["percentile"] == 85.0


class TestUserLeaderboardRoutes:
    """Test user leaderboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_leaderboard_success(self, mock_leaderboard_service, mock_auth):
        """Test successful user leaderboard retrieval."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_user_leaderboard = AsyncMock(return_value={
            "criteria": "activity",
            "timeframe": "7d",
            "rankings": [
                {
                    "rank": 1,
                    "previousRank": None,
                    "change": "new",
                    "user": {
                        "id": "user-123",
                        "name": "Test User",
                        "avatar": None,
                        "workspace": "Test Workspace",
                    },
                    "metrics": {
                        "totalActions": 200,
                        "successRate": 92.0,
                        "creditsUsed": 500.0,
                        "creditsSaved": 100.0,
                        "agentsUsed": 8,
                    },
                    "score": 150.0,
                    "percentile": 98.0,
                    "achievements": ["Century Club", "Top Performer"],
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 100,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/users",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                    "timeframe": "7d",
                    "criteria": "activity",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["criteria"] == "activity"
        assert len(data["rankings"]) == 1
        assert len(data["rankings"][0]["achievements"]) == 2

    @pytest.mark.asyncio
    async def test_get_user_leaderboard_empty(self, mock_leaderboard_service, mock_auth):
        """Test user leaderboard with no rankings."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_user_leaderboard = AsyncMock(return_value={
            "criteria": "activity",
            "timeframe": "7d",
            "rankings": [],
            "total": 0,
            "offset": 0,
            "limit": 100,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/users",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rankings"]) == 0
        assert data["total"] == 0


class TestWorkspaceLeaderboardRoutes:
    """Test workspace leaderboard API endpoints."""

    @pytest.mark.asyncio
    async def test_get_workspace_leaderboard_success(self, mock_leaderboard_service, mock_auth):
        """Test successful workspace leaderboard retrieval."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_workspace_leaderboard = AsyncMock(return_value={
            "criteria": "activity",
            "timeframe": "7d",
            "rankings": [
                {
                    "rank": 1,
                    "previousRank": None,
                    "change": "new",
                    "workspace": {
                        "id": "workspace-123",
                        "name": "Test Workspace",
                        "plan": "pro",
                        "memberCount": 25,
                    },
                    "metrics": {
                        "totalActivity": 1000,
                        "activeUsers": 20,
                        "agentCount": 15,
                        "successRate": 94.0,
                        "healthScore": 88.0,
                    },
                    "score": 500.0,
                    "tier": "platinum",
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 100,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/workspaces",
                params={
                    "timeframe": "7d",
                    "criteria": "activity",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["criteria"] == "activity"
        assert len(data["rankings"]) == 1
        assert data["rankings"][0]["tier"] == "platinum"


class TestLeaderboardRefreshRoute:
    """Test leaderboard refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_leaderboards_success(self, mock_leaderboard_service, mock_auth):
        """Test successful leaderboard refresh."""
        mock_service_instance = MagicMock()
        mock_service_instance.refresh_all_leaderboards = AsyncMock()
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leaderboards/refresh/00000000-0000-0000-0000-000000000000"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "workspace" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_refresh_leaderboards_invalid_workspace(self, mock_auth):
        """Test refresh with invalid workspace ID."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leaderboards/refresh/invalid-uuid"
            )

        assert response.status_code == 400


class TestLeaderboardPagination:
    """Test leaderboard pagination."""

    @pytest.mark.asyncio
    async def test_agent_leaderboard_pagination(self, mock_leaderboard_service, mock_auth):
        """Test agent leaderboard with pagination."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_agent_leaderboard = AsyncMock(return_value={
            "criteria": "success_rate",
            "timeframe": "7d",
            "rankings": [],
            "total": 250,
            "offset": 50,
            "limit": 50,
            "calculatedAt": datetime.utcnow().isoformat(),
        })
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/agents",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                    "limit": 50,
                    "offset": 50,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 250
        assert data["offset"] == 50
        assert data["limit"] == 50


class TestLeaderboardErrorHandling:
    """Test error handling in leaderboard routes."""

    @pytest.mark.asyncio
    async def test_service_exception_handling(self, mock_leaderboard_service, mock_auth):
        """Test handling of service exceptions."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_agent_leaderboard = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_leaderboard_service.return_value = mock_service_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/leaderboards/agents",
                params={
                    "workspace_id": "00000000-0000-0000-0000-000000000000",
                }
            )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()
