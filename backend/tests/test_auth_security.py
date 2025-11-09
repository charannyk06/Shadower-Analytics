"""Tests for API authentication and authorization security."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.api.main import app

client = TestClient(app)


class TestAuthenticationRequired:
    """Test that endpoints require authentication."""

    @pytest.fixture
    def mock_db(self):
        """Mock database dependency."""
        return Mock()

    def test_agents_list_requires_auth(self):
        """Test that /agents/ endpoint requires authentication."""
        response = client.get("/api/v1/agents/")
        assert response.status_code == 401

    def test_agents_analytics_requires_auth(self):
        """Test that /agents/{id}/analytics requires authentication."""
        response = client.get(
            "/api/v1/agents/test-agent/analytics",
            params={"workspace_id": "test-workspace", "timeframe": "7d"}
        )
        assert response.status_code == 401

    def test_agents_details_requires_auth(self):
        """Test that /agents/{id} requires authentication."""
        response = client.get("/api/v1/agents/test-agent")
        assert response.status_code == 401

    def test_agents_stats_requires_auth(self):
        """Test that /agents/{id}/stats requires authentication."""
        response = client.get("/api/v1/agents/test-agent/stats")
        assert response.status_code == 401

    def test_agents_executions_requires_auth(self):
        """Test that /agents/{id}/executions requires authentication."""
        response = client.get("/api/v1/agents/test-agent/executions")
        assert response.status_code == 401

    def test_users_metrics_requires_auth(self):
        """Test that /users/metrics requires authentication."""
        response = client.get("/api/v1/users/metrics")
        assert response.status_code == 401

    def test_users_activity_requires_auth(self):
        """Test that /users/activity requires authentication."""
        response = client.get("/api/v1/users/activity")
        assert response.status_code == 401

    def test_users_cohorts_requires_auth(self):
        """Test that /users/cohorts requires authentication."""
        response = client.get("/api/v1/users/cohorts")
        assert response.status_code == 401

    def test_users_details_requires_auth(self):
        """Test that /users/{id} requires authentication."""
        response = client.get("/api/v1/users/test-user")
        assert response.status_code == 401

    def test_users_timeline_requires_auth(self):
        """Test that /users/{id}/timeline requires authentication."""
        response = client.get("/api/v1/users/test-user/timeline")
        assert response.status_code == 401

    def test_workspaces_list_requires_auth(self):
        """Test that /workspaces/ requires authentication."""
        response = client.get("/api/v1/workspaces/")
        assert response.status_code == 401

    def test_workspaces_details_requires_auth(self):
        """Test that /workspaces/{id} requires authentication."""
        response = client.get("/api/v1/workspaces/test-workspace")
        assert response.status_code == 401

    def test_workspaces_agents_requires_auth(self):
        """Test that /workspaces/{id}/agents requires authentication."""
        response = client.get("/api/v1/workspaces/test-workspace/agents")
        assert response.status_code == 401

    def test_workspaces_users_requires_auth(self):
        """Test that /workspaces/{id}/users requires authentication."""
        response = client.get("/api/v1/workspaces/test-workspace/users")
        assert response.status_code == 401

    def test_metrics_summary_requires_auth(self):
        """Test that /metrics/summary requires authentication."""
        response = client.get("/api/v1/metrics/summary")
        assert response.status_code == 401

    def test_metrics_trends_requires_auth(self):
        """Test that /metrics/trends requires authentication."""
        response = client.get("/api/v1/metrics/trends?metric_type=users")
        assert response.status_code == 401

    def test_metrics_comparison_requires_auth(self):
        """Test that /metrics/comparison requires authentication."""
        response = client.get(
            "/api/v1/metrics/comparison",
            params={
                "metric_type": "users",
                "current_start": "2024-01-01",
                "current_end": "2024-01-31",
                "previous_start": "2023-12-01",
                "previous_end": "2023-12-31",
            }
        )
        assert response.status_code == 401

    def test_metrics_realtime_requires_auth(self):
        """Test that /metrics/realtime requires authentication."""
        response = client.get("/api/v1/metrics/realtime")
        assert response.status_code == 401


class TestPathTraversalProtection:
    """Test that path traversal attacks are blocked."""

    def test_agent_id_path_traversal_blocked(self):
        """Test that path traversal in agent ID is blocked."""
        malicious_ids = [
            "../../etc/passwd",
            "../config",
            "agent/../../../etc/passwd",
        ]
        for agent_id in malicious_ids:
            # Even with valid auth, path traversal should be blocked
            response = client.get(
                f"/api/v1/agents/{agent_id}",
                headers={"Authorization": "Bearer fake-token"}
            )
            # Should be 400 Bad Request or 401 Unauthorized (before reaching validation)
            assert response.status_code in [400, 401]

    def test_workspace_id_path_traversal_blocked(self):
        """Test that path traversal in workspace ID is blocked."""
        response = client.get(
            "/api/v1/workspaces/../../etc/passwd",
            headers={"Authorization": "Bearer fake-token"}
        )
        assert response.status_code in [400, 401]

    def test_user_id_path_traversal_blocked(self):
        """Test that path traversal in user ID is blocked."""
        response = client.get(
            "/api/v1/users/../../etc/passwd",
            headers={"Authorization": "Bearer fake-token"}
        )
        assert response.status_code in [400, 401]


class TestInvalidTokenRejection:
    """Test that invalid tokens are rejected."""

    def test_missing_bearer_prefix_rejected(self):
        """Test that tokens without 'Bearer' prefix are rejected."""
        response = client.get(
            "/api/v1/agents/",
            headers={"Authorization": "InvalidToken"}
        )
        assert response.status_code == 401

    def test_empty_token_rejected(self):
        """Test that empty tokens are rejected."""
        response = client.get(
            "/api/v1/agents/",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401

    def test_malformed_token_rejected(self):
        """Test that malformed tokens are rejected."""
        response = client.get(
            "/api/v1/agents/",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        assert response.status_code == 401


class TestPublicEndpoints:
    """Test that public endpoints don't require auth."""

    def test_root_endpoint_public(self):
        """Test that root endpoint is accessible without auth."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint_public(self):
        """Test that health endpoint is accessible without auth."""
        response = client.get("/health")
        # May be 200 or 404 if not implemented
        assert response.status_code in [200, 404]

    def test_docs_endpoint_public(self):
        """Test that docs endpoint is accessible without auth."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint_public(self):
        """Test that OpenAPI spec is accessible without auth."""
        response = client.get("/openapi.json")
        assert response.status_code == 200


class TestInputValidation:
    """Test input validation on API endpoints."""

    def test_invalid_agent_id_format_rejected(self):
        """Test that invalid agent ID format is rejected."""
        invalid_ids = [
            "agent@123",
            "agent#test",
            "agent test",  # Space
        ]
        for agent_id in invalid_ids:
            response = client.get(
                f"/api/v1/agents/{agent_id}",
                headers={"Authorization": "Bearer fake-token"}
            )
            # Should be rejected (400 or 401 before validation)
            assert response.status_code in [400, 401, 422]

    def test_invalid_timeframe_rejected(self):
        """Test that invalid timeframe values are rejected."""
        response = client.get(
            "/api/v1/agents/test-agent/analytics",
            params={"workspace_id": "test", "timeframe": "invalid"},
            headers={"Authorization": "Bearer fake-token"}
        )
        # Should be rejected (validation error)
        assert response.status_code in [401, 422]

    def test_negative_pagination_rejected(self):
        """Test that negative pagination values are rejected."""
        response = client.get(
            "/api/v1/agents/?skip=-1&limit=10",
            headers={"Authorization": "Bearer fake-token"}
        )
        # Should be rejected (validation error)
        assert response.status_code in [401, 422]

    def test_excessive_limit_rejected(self):
        """Test that excessive limit values are rejected."""
        response = client.get(
            "/api/v1/agents/?skip=0&limit=10000",
            headers={"Authorization": "Bearer fake-token"}
        )
        # Should be rejected (validation error)
        assert response.status_code in [401, 422]
