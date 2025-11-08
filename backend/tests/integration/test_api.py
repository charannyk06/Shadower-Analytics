"""Integration tests for API endpoints."""

import pytest
from fastapi import status


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["service"] == "Shadow Analytics API"


def test_executive_overview(client):
    """Test executive overview endpoint."""
    response = client.get("/api/v1/executive/overview")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "mrr" in data
    assert "dau" in data
    assert "mau" in data


def test_metrics_summary(client):
    """Test metrics summary endpoint."""
    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
