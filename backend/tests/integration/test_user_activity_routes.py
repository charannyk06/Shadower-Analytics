"""Integration tests for user activity tracking routes."""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app


class TestUserActivityEndpoints:
    """Test suite for user activity tracking endpoints."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch("src.api.dependencies.auth.require_owner_or_admin") as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "role": "owner",
            }
            yield mock

    @pytest.fixture
    def mock_current_user(self):
        """Mock current user for tracking endpoint."""
        with patch("src.api.dependencies.auth.get_current_user") as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "role": "user",
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

    def test_get_user_activity_requires_auth(self, client):
        """Test that user activity endpoint requires authentication."""
        response = client.get("/api/v1/user-activity/test-workspace")
        assert response.status_code in [401, 403]

    @patch("src.services.analytics.user_activity.UserActivityService")
    def test_get_user_activity_success(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test successful user activity retrieval."""
        # Mock service response
        mock_instance = MagicMock()
        mock_instance.get_user_activity.return_value = {
            "workspaceId": "test-workspace",
            "timeframe": "30d",
            "activityMetrics": {
                "dau": 100,
                "wau": 500,
                "mau": 1500,
                "engagementScore": 75.5,
            },
        }
        mock_service.return_value = mock_instance

        response = client.get(
            "/api/v1/user-activity/test-workspace",
            params={"timeframe": "30d"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workspaceId"] == "test-workspace"
        assert data["activityMetrics"]["dau"] == 100

    def test_get_user_activity_validates_timeframe(
        self, client, mock_auth, mock_workspace_access
    ):
        """Test that invalid timeframe is rejected."""
        response = client.get(
            "/api/v1/user-activity/test-workspace",
            params={"timeframe": "invalid"},
        )
        assert response.status_code == 422

    @patch("src.services.analytics.retention_analysis.RetentionAnalysisService")
    def test_get_retention_curve_success(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test successful retention curve retrieval."""
        mock_instance = MagicMock()
        mock_instance.calculate_retention_curve.return_value = [
            {"day": 0, "retentionRate": 100.0, "activeUsers": 100},
            {"day": 1, "retentionRate": 80.0, "activeUsers": 80},
            {"day": 7, "retentionRate": 60.0, "activeUsers": 60},
        ]
        mock_service.return_value = mock_instance

        response = client.get(
            "/api/v1/user-activity/test-workspace/retention/curve",
            params={"cohort_date": "2024-01-01", "days": 90},
        )

        assert response.status_code == 200
        data = response.json()
        assert "retentionCurve" in data
        assert len(data["retentionCurve"]) == 3

    def test_get_retention_curve_invalid_date(
        self, client, mock_auth, mock_workspace_access
    ):
        """Test retention curve with invalid date format."""
        response = client.get(
            "/api/v1/user-activity/test-workspace/retention/curve",
            params={"cohort_date": "invalid-date"},
        )
        assert response.status_code == 400

    @patch("src.services.analytics.retention_analysis.RetentionAnalysisService")
    def test_get_cohort_analysis_success(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test successful cohort analysis retrieval."""
        mock_instance = MagicMock()
        mock_instance.generate_cohort_analysis.return_value = [
            {
                "cohortDate": "2024-01-01",
                "cohortSize": 100,
                "retention": {
                    "day1": 80.0,
                    "day7": 60.0,
                    "day30": 40.0,
                },
            }
        ]
        mock_service.return_value = mock_instance

        response = client.get(
            "/api/v1/user-activity/test-workspace/retention/cohorts",
            params={"cohort_type": "monthly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "cohorts" in data
        assert len(data["cohorts"]) == 1

    def test_get_cohort_analysis_validates_type(
        self, client, mock_auth, mock_workspace_access
    ):
        """Test that invalid cohort type is rejected."""
        response = client.get(
            "/api/v1/user-activity/test-workspace/retention/cohorts",
            params={"cohort_type": "invalid"},
        )
        assert response.status_code == 422

    @patch("src.services.analytics.retention_analysis.RetentionAnalysisService")
    def test_get_churn_analysis_success(
        self,
        mock_service,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test successful churn analysis retrieval."""
        mock_instance = MagicMock()
        mock_instance.analyze_churn.return_value = {
            "churnRate": 5.5,
            "avgLifetime": 180.0,
            "riskSegments": [],
        }
        mock_service.return_value = mock_instance

        response = client.get(
            "/api/v1/user-activity/test-workspace/churn",
            params={"timeframe": "30d"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["churnRate"] == 5.5

    @patch("src.core.privacy.anonymize_ip")
    @patch("src.models.database.tables.UserActivity")
    def test_track_activity_success(
        self,
        mock_activity_model,
        mock_anonymize_ip,
        client,
        mock_current_user,
        mock_workspace_access,
    ):
        """Test successful activity tracking."""
        mock_anonymize_ip.return_value = "192.168.1.0"

        event_data = {
            "user_id": "test-user",
            "event_type": "page_view",
            "event_name": "dashboard_view",
            "page_path": "/dashboard",
            "ip_address": "192.168.1.100",
        }

        response = client.post(
            "/api/v1/user-activity/test-workspace/track",
            json=event_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "activity_id" in data

    def test_track_activity_validates_event_type(
        self, client, mock_current_user, mock_workspace_access
    ):
        """Test that invalid event type is rejected."""
        event_data = {
            "user_id": "test-user",
            "event_type": "invalid_type",
        }

        response = client.post(
            "/api/v1/user-activity/test-workspace/track",
            json=event_data,
        )

        assert response.status_code == 422

    def test_track_activity_requires_auth(self, client):
        """Test that track activity requires authentication."""
        event_data = {
            "user_id": "test-user",
            "event_type": "page_view",
        }

        response = client.post(
            "/api/v1/user-activity/test-workspace/track",
            json=event_data,
        )

        assert response.status_code in [401, 403]


class TestUserActivityCaching:
    """Test suite for user activity caching."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch("src.api.dependencies.auth.require_owner_or_admin") as mock:
            mock.return_value = {
                "sub": "test-user-id",
                "workspace_id": "test-workspace-id",
                "role": "owner",
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

    @patch("src.services.cache.decorator.get_redis_client")
    @patch("src.services.analytics.user_activity.UserActivityService")
    def test_user_activity_uses_cache(
        self,
        mock_service,
        mock_redis,
        client,
        mock_auth,
        mock_workspace_access,
    ):
        """Test that user activity endpoint uses caching."""
        # Mock Redis client
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = None
        mock_redis.return_value = mock_redis_instance

        # Mock service
        mock_instance = MagicMock()
        mock_instance.get_user_activity.return_value = {
            "workspaceId": "test-workspace",
            "timeframe": "30d",
        }
        mock_service.return_value = mock_instance

        response = client.get(
            "/api/v1/user-activity/test-workspace",
            params={"timeframe": "30d"},
        )

        assert response.status_code == 200


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
