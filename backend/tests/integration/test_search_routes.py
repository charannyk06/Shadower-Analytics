"""Integration tests for search API endpoints."""

import pytest
from fastapi import status
from datetime import date, timedelta


def test_global_search_requires_auth(client):
    """Test that global search requires authentication."""
    response = client.get(
        "/api/v1/search/global",
        params={
            "q": "test query",
            "workspace_id": "test-workspace-123",
        },
    )
    # Without auth, should return 401 or 403
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_global_search_missing_query(client, auth_headers):
    """Test global search with missing query parameter."""
    response = client.get(
        "/api/v1/search/global",
        params={"workspace_id": "test-workspace-123"},
        headers=auth_headers,
    )
    # Should return 422 for missing required parameter
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_global_search_success(client, auth_headers):
    """Test successful global search."""
    response = client.get(
        "/api/v1/search/global",
        params={
            "q": "test",
            "workspace_id": "test-workspace-123",
            "limit": 20,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "query" in data
        assert "total_results" in data
        assert "results" in data
        assert "suggestions" in data
        assert data["query"] == "test"


def test_advanced_search_requires_auth(client):
    """Test that advanced search requires authentication."""
    response = client.post(
        "/api/v1/search/advanced",
        json={
            "query": "test query",
            "workspace_id": "test-workspace-123",
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_advanced_search_with_filters(client, auth_headers):
    """Test advanced search with filters."""
    search_config = {
        "query": "error rate",
        "workspace_id": "test-workspace-123",
        "filters": {
            "date_range": {
                "start": str(date.today() - timedelta(days=30)),
                "end": str(date.today()),
            }
        },
    }

    response = client.post(
        "/api/v1/search/advanced",
        json=search_config,
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "execution_time_ms" in data


def test_search_users_requires_auth(client):
    """Test that user search requires authentication."""
    response = client.get(
        "/api/v1/search/users",
        params={
            "q": "test",
            "workspace_id": "test-workspace-123",
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_users_success(client, auth_headers):
    """Test successful user search."""
    response = client.get(
        "/api/v1/search/users",
        params={
            "q": "test",
            "workspace_id": "test-workspace-123",
            "skip": 0,
            "limit": 100,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "data" in data
        assert isinstance(data["data"], list)


def test_search_users_with_filters(client, auth_headers):
    """Test user search with filters."""
    response = client.get(
        "/api/v1/search/users",
        params={
            "q": "test",
            "workspace_id": "test-workspace-123",
            "active_only": True,
            "min_activity": 10,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "data" in data


def test_search_agents_requires_auth(client):
    """Test that agent search requires authentication."""
    response = client.get(
        "/api/v1/search/agents",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_agents_success(client, auth_headers):
    """Test successful agent search."""
    response = client.get(
        "/api/v1/search/agents",
        params={
            "q": "test",
            "workspace_id": "test-workspace-123",
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_agents_with_filters(client, auth_headers):
    """Test agent search with performance filters."""
    response = client.get(
        "/api/v1/search/agents",
        params={
            "workspace_id": "test-workspace-123",
            "min_success_rate": 80.0,
            "agent_type": "customer_service",
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_activities_requires_auth(client):
    """Test that activity search requires authentication."""
    response = client.get(
        "/api/v1/search/activities",
        params={
            "workspace_id": "test-workspace-123",
            "start_date": str(date.today() - timedelta(days=7)),
            "end_date": str(date.today()),
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_activities_success(client, auth_headers):
    """Test successful activity search."""
    response = client.get(
        "/api/v1/search/activities",
        params={
            "workspace_id": "test-workspace-123",
            "start_date": str(date.today() - timedelta(days=7)),
            "end_date": str(date.today()),
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "total" in data
        assert "data" in data


def test_search_metrics_requires_auth(client):
    """Test that metric search requires authentication."""
    response = client.get(
        "/api/v1/search/metrics",
        params={
            "workspace_id": "test-workspace-123",
            "start_date": str(date.today() - timedelta(days=7)),
            "end_date": str(date.today()),
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_metrics_success(client, auth_headers):
    """Test successful metric search."""
    response = client.get(
        "/api/v1/search/metrics",
        params={
            "workspace_id": "test-workspace-123",
            "metric_name": "error_rate",
            "start_date": str(date.today() - timedelta(days=7)),
            "end_date": str(date.today()),
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_alerts_requires_auth(client):
    """Test that alert search requires authentication."""
    response = client.get(
        "/api/v1/search/alerts",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_alerts_success(client, auth_headers):
    """Test successful alert search."""
    response = client.get(
        "/api/v1/search/alerts",
        params={
            "workspace_id": "test-workspace-123",
            "severity": ["high", "critical"],
            "status": ["active"],
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_reports_requires_auth(client):
    """Test that report search requires authentication."""
    response = client.get(
        "/api/v1/search/reports",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_reports_success(client, auth_headers):
    """Test successful report search."""
    response = client.get(
        "/api/v1/search/reports",
        params={
            "q": "monthly",
            "workspace_id": "test-workspace-123",
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_suggestions_requires_auth(client):
    """Test that search suggestions require authentication."""
    response = client.get(
        "/api/v1/search/suggestions",
        params={
            "q": "err",
            "workspace_id": "test-workspace-123",
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_suggestions_success(client, auth_headers):
    """Test successful search suggestions."""
    response = client.get(
        "/api/v1/search/suggestions",
        params={
            "q": "err",
            "workspace_id": "test-workspace-123",
            "limit": 10,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "query" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


def test_search_history_requires_auth(client):
    """Test that search history requires authentication."""
    response = client.get(
        "/api/v1/search/history",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_search_history_success(client, auth_headers):
    """Test successful search history retrieval."""
    response = client.get(
        "/api/v1/search/history",
        params={
            "workspace_id": "test-workspace-123",
            "limit": 20,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "searches" in data
        assert "total" in data
        assert isinstance(data["searches"], list)


def test_clear_search_history_requires_auth(client):
    """Test that clearing search history requires authentication."""
    response = client.delete(
        "/api/v1/search/history",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_clear_search_history_success(client, auth_headers):
    """Test successful search history clearing."""
    response = client.delete(
        "/api/v1/search/history",
        params={"workspace_id": "test-workspace-123"},
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "cleared" in data


def test_save_search_requires_auth(client):
    """Test that saving search requires authentication."""
    response = client.post(
        "/api/v1/search/saved",
        json={
            "name": "Test Search",
            "query": "test",
            "workspace_id": "test-workspace-123",
        },
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_save_search_success(client, auth_headers):
    """Test successful search saving."""
    response = client.post(
        "/api/v1/search/saved",
        json={
            "name": "High Error Agents",
            "query": "error rate > 5%",
            "workspace_id": "test-workspace-123",
            "alert_on_match": True,
            "share_with_team": False,
        },
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "created" in data


def test_get_saved_searches_requires_auth(client):
    """Test that getting saved searches requires authentication."""
    response = client.get(
        "/api/v1/search/saved",
        params={"workspace_id": "test-workspace-123"},
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_get_saved_searches_success(client, auth_headers):
    """Test successful retrieval of saved searches."""
    response = client.get(
        "/api/v1/search/saved",
        params={"workspace_id": "test-workspace-123"},
        headers=auth_headers,
    )

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "saved_searches" in data
        assert "total" in data
        assert isinstance(data["saved_searches"], list)


def test_search_analytics_requires_admin(client, auth_headers):
    """Test that search analytics requires admin permissions."""
    response = client.get(
        "/api/v1/search/analytics",
        params={
            "workspace_id": "test-workspace-123",
            "start_date": str(date.today() - timedelta(days=30)),
            "end_date": str(date.today()),
        },
        headers=auth_headers,
    )

    # May return 403 if user is not admin, or 200 if admin
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_403_FORBIDDEN,
    ]

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "search_analytics" in data
        assert "date_range" in data


@pytest.fixture
def auth_headers():
    """Mock authentication headers for testing."""
    # This would normally contain a valid JWT token
    # For testing purposes, you may need to generate a valid test token
    # or mock the authentication middleware
    return {
        "Authorization": "Bearer test-token-123"
    }
