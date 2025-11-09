"""
Integration tests for Materialized Views API

Tests cover:
- Refresh endpoints
- Status endpoints
- Statistics endpoints
- Health check endpoints
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.materialized_views import MaterializedViewRefreshService


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Create a mock MaterializedViewRefreshService"""
    with patch('src.api.routes.materialized_views.MaterializedViewRefreshService') as mock:
        service_instance = AsyncMock()
        mock.return_value = service_instance
        yield service_instance


class TestMaterializedViewsAPI:
    """Test cases for Materialized Views API endpoints"""

    def test_list_available_views(self, client):
        """Test listing available views"""
        # Execute
        response = client.get("/materialized-views/views/list")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "total" in data
        assert isinstance(data["views"], list)
        assert data["total"] == len(data["views"])
        assert "mv_active_users" in data["views"]

    @pytest.mark.asyncio
    async def test_refresh_all_views(self, client, mock_service):
        """Test refreshing all materialized views"""
        # Setup
        mock_service.refresh_all.return_value = [
            {
                "view_name": "mv_active_users",
                "success": True,
                "started_at": "2025-11-09T12:00:00+00:00",
                "completed_at": "2025-11-09T12:00:01+00:00",
                "duration_seconds": 1.0,
                "error": None,
            },
            {
                "view_name": "mv_agent_performance",
                "success": True,
                "started_at": "2025-11-09T12:00:01+00:00",
                "completed_at": "2025-11-09T12:00:02+00:00",
                "duration_seconds": 1.0,
                "error": None,
            }
        ]

        # Execute
        response = client.post("/materialized-views/refresh", json={
            "views": None,
            "concurrent": True,
            "use_db_function": False
        })

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_views"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert data["total_duration_seconds"] == 2.0

    @pytest.mark.asyncio
    async def test_refresh_specific_views(self, client, mock_service):
        """Test refreshing specific views"""
        # Setup
        views_to_refresh = ["mv_active_users", "mv_agent_performance"]
        mock_service.refresh_all.return_value = [
            {
                "view_name": view,
                "success": True,
                "started_at": "2025-11-09T12:00:00+00:00",
                "completed_at": "2025-11-09T12:00:01+00:00",
                "duration_seconds": 1.0,
                "error": None,
            }
            for view in views_to_refresh
        ]

        # Execute
        response = client.post("/materialized-views/refresh", json={
            "views": views_to_refresh,
            "concurrent": True,
            "use_db_function": False
        })

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_views"] == len(views_to_refresh)
        assert all(r["view_name"] in views_to_refresh for r in data["results"])

    @pytest.mark.asyncio
    async def test_refresh_with_failures(self, client, mock_service):
        """Test refresh with some failures"""
        # Setup
        mock_service.refresh_all.return_value = [
            {
                "view_name": "mv_active_users",
                "success": True,
                "started_at": "2025-11-09T12:00:00+00:00",
                "completed_at": "2025-11-09T12:00:01+00:00",
                "duration_seconds": 1.0,
                "error": None,
            },
            {
                "view_name": "mv_agent_performance",
                "success": False,
                "started_at": "2025-11-09T12:00:01+00:00",
                "completed_at": "2025-11-09T12:00:02+00:00",
                "duration_seconds": 1.0,
                "error": "Refresh failed",
            }
        ]

        # Execute
        response = client.post("/materialized-views/refresh", json={
            "concurrent": True,
        })

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        failed_result = next(r for r in data["results"] if not r["success"])
        assert failed_result["error"] == "Refresh failed"

    @pytest.mark.asyncio
    async def test_refresh_using_db_function(self, client, mock_service):
        """Test refresh using database function"""
        # Setup
        mock_service.refresh_using_function.return_value = [
            {
                "view_name": "mv_active_users",
                "success": True,
                "started_at": "2025-11-09T12:00:00+00:00",
                "completed_at": "2025-11-09T12:00:01+00:00",
                "duration_seconds": 1.0,
                "error": None,
            }
        ]

        # Execute
        response = client.post("/materialized-views/refresh", json={
            "use_db_function": True,
            "concurrent": True,
        })

        # Assert
        assert response.status_code == 200
        mock_service.refresh_using_function.assert_called_once_with(
            concurrent_mode=True
        )

    @pytest.mark.asyncio
    async def test_refresh_single_view(self, client, mock_service):
        """Test refreshing a single view"""
        # Setup
        view_name = "mv_active_users"
        mock_service.refresh_view.return_value = {
            "view_name": view_name,
            "success": True,
            "started_at": "2025-11-09T12:00:00+00:00",
            "completed_at": "2025-11-09T12:00:01+00:00",
            "duration_seconds": 1.0,
            "error": None,
        }

        # Execute
        response = client.post(f"/materialized-views/refresh/{view_name}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["view_name"] == view_name
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_refresh_single_view_not_found(self, client, mock_service):
        """Test refreshing non-existent view"""
        # Setup
        mock_service.refresh_view.side_effect = ValueError("Unknown materialized view")

        # Execute
        response = client.post("/materialized-views/refresh/invalid_view")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_views_status(self, client, mock_service):
        """Test getting status for all views"""
        # Setup
        mock_service.get_refresh_status.return_value = [
            {
                "view_name": "mv_active_users",
                "owner": "postgres",
                "is_populated": True,
                "has_indexes": True,
                "total_size": "1024 kB",
                "data_size": "512 kB",
                "index_size": "512 kB",
                "description": "Active users summary",
            }
        ]

        # Execute
        response = client.get("/materialized-views/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["view_name"] == "mv_active_users"
        assert data[0]["is_populated"] is True

    @pytest.mark.asyncio
    async def test_get_view_statistics(self, client, mock_service):
        """Test getting statistics for a view"""
        # Setup
        view_name = "mv_active_users"
        mock_service.get_view_statistics.return_value = {
            "schema": "analytics",
            "view_name": view_name,
            "rows_inserted": 1000,
            "rows_updated": 50,
            "rows_deleted": 10,
            "live_rows": 990,
            "dead_rows": 10,
            "last_vacuum": "2025-11-09T12:00:00+00:00",
            "last_autovacuum": None,
            "last_analyze": "2025-11-09T12:00:00+00:00",
            "last_autoanalyze": None,
            "vacuum_count": 5,
            "autovacuum_count": 10,
            "analyze_count": 5,
            "autoanalyze_count": 10,
        }

        # Execute
        response = client.get(f"/materialized-views/statistics/{view_name}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["view_name"] == view_name
        assert data["live_rows"] == 990

    @pytest.mark.asyncio
    async def test_get_view_statistics_not_found(self, client, mock_service):
        """Test getting statistics for non-existent view"""
        # Setup
        mock_service.get_view_statistics.return_value = None

        # Execute
        response = client.get("/materialized-views/statistics/invalid_view")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_check_views_health(self, client, mock_service):
        """Test health check for all views"""
        # Setup
        mock_service.check_view_health.return_value = [
            {
                "view_name": "mv_active_users",
                "healthy": True,
                "issues": [],
            },
            {
                "view_name": "mv_agent_performance",
                "healthy": False,
                "issues": ["View is not populated"],
            }
        ]

        # Execute
        response = client.get("/materialized-views/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_views"] == 2
        assert data["healthy_views"] == 1
        assert data["unhealthy_views"] == 1

    @pytest.mark.asyncio
    async def test_get_view_row_count(self, client, mock_service):
        """Test getting row count for a view"""
        # Setup
        view_name = "mv_active_users"
        mock_service.get_row_count.return_value = 1500

        # Execute
        response = client.get(f"/materialized-views/{view_name}/row-count")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["view_name"] == view_name
        assert data["row_count"] == 1500

    @pytest.mark.asyncio
    async def test_get_view_row_count_invalid_view(self, client, mock_service):
        """Test getting row count for invalid view"""
        # Setup
        mock_service.get_row_count.side_effect = ValueError("Unknown materialized view")

        # Execute
        response = client.get("/materialized-views/invalid_view/row-count")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_refresh_error_handling(self, client, mock_service):
        """Test error handling during refresh"""
        # Setup
        mock_service.refresh_all.side_effect = Exception("Database error")

        # Execute
        response = client.post("/materialized-views/refresh", json={})

        # Assert
        assert response.status_code == 500
        assert "Failed to refresh materialized views" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_status_error_handling(self, client, mock_service):
        """Test error handling when getting status"""
        # Setup
        mock_service.get_refresh_status.side_effect = Exception("Database error")

        # Execute
        response = client.get("/materialized-views/status")

        # Assert
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, client, mock_service):
        """Test error handling during health check"""
        # Setup
        mock_service.check_view_health.side_effect = Exception("Database error")

        # Execute
        response = client.get("/materialized-views/health")

        # Assert
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_refresh_non_concurrent(self, client, mock_service):
        """Test refresh with concurrent mode disabled"""
        # Setup
        mock_service.refresh_all.return_value = []

        # Execute
        response = client.post("/materialized-views/refresh", json={
            "concurrent": False,
        })

        # Assert
        assert response.status_code == 200
        mock_service.refresh_all.assert_called_once()
        call_args = mock_service.refresh_all.call_args
        assert call_args.kwargs["concurrent"] is False
