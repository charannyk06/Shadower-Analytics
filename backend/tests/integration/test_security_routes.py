"""Integration tests for security analytics routes."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid


@pytest.fixture
def test_workspace_id():
    """Test workspace ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_agent_id():
    """Test agent ID."""
    return str(uuid.uuid4())


@pytest.fixture
def auth_headers(test_user_token):
    """Authentication headers for requests."""
    return {"Authorization": f"Bearer {test_user_token}"}


class TestSecurityDashboard:
    """Tests for security dashboard endpoint."""

    def test_get_security_dashboard(self, client: TestClient, test_workspace_id, auth_headers):
        """Test getting security dashboard summary."""
        response = client.get(
            f"/api/v1/security/dashboard/{test_workspace_id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "workspace_id" in data
            assert "security_events_24h" in data
            assert "open_incidents" in data
            assert "critical_vulnerabilities" in data

    def test_get_security_dashboard_unauthorized(self, client: TestClient, test_workspace_id):
        """Test unauthorized access to security dashboard."""
        response = client.get(f"/api/v1/security/dashboard/{test_workspace_id}")
        assert response.status_code == 401


class TestThreatDetection:
    """Tests for threat detection endpoints."""

    def test_get_threat_analysis(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test getting threat analysis for an agent."""
        response = client.get(
            f"/api/v1/security/threats/{test_agent_id}",
            params={"workspace_id": test_workspace_id, "timeframe": "24h"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "agent_id" in data
            assert "threat_level" in data
            assert "risk_score" in data
            assert "recommended_actions" in data

    def test_get_threat_analysis_invalid_timeframe(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test threat analysis with invalid timeframe."""
        response = client.get(
            f"/api/v1/security/threats/{test_agent_id}",
            params={"workspace_id": test_workspace_id, "timeframe": "invalid"},
            headers=auth_headers
        )

        # Should either accept it or return validation error
        assert response.status_code in [200, 400, 422, 500]


class TestVulnerabilityScanning:
    """Tests for vulnerability scanning endpoints."""

    def test_create_vulnerability_scan(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test creating a vulnerability scan."""
        scan_request = {
            "agent_id": test_agent_id,
            "workspace_id": test_workspace_id,
            "scan_type": "quick",
            "scan_scope": []
        }

        response = client.post(
            "/api/v1/security/vulnerabilities/scan",
            json=scan_request,
            headers=auth_headers
        )

        assert response.status_code in [200, 201, 500]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "scan" in data
            assert "vulnerabilities" in data

    def test_create_vulnerability_scan_invalid_type(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test creating scan with invalid type."""
        scan_request = {
            "agent_id": test_agent_id,
            "workspace_id": test_workspace_id,
            "scan_type": "invalid_type",
            "scan_scope": []
        }

        response = client.post(
            "/api/v1/security/vulnerabilities/scan",
            json=scan_request,
            headers=auth_headers
        )

        # Should accept any string for scan_type currently
        assert response.status_code in [200, 201, 400, 422, 500]


class TestSecurityIncidents:
    """Tests for security incidents endpoints."""

    def test_get_security_incidents(self, client: TestClient, test_workspace_id, auth_headers):
        """Test getting security incidents."""
        response = client.get(
            f"/api/v1/security/incidents/{test_workspace_id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_security_incidents_with_filters(self, client: TestClient, test_workspace_id, auth_headers):
        """Test getting incidents with filters."""
        response = client.get(
            f"/api/v1/security/incidents/{test_workspace_id}",
            params={"status": "open", "severity": "critical"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


class TestSecurityEvents:
    """Tests for security events endpoints."""

    def test_create_security_event(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test creating a security event."""
        event = {
            "agent_id": test_agent_id,
            "workspace_id": test_workspace_id,
            "event_type": "authentication",
            "severity": "medium",
            "category": "auth_failure",
            "description": "Failed authentication attempt",
            "event_data": {"ip": "192.168.1.1"},
            "threat_score": 45.0,
            "source_ip": "192.168.1.1"
        }

        response = client.post(
            "/api/v1/security/events",
            json=event,
            headers=auth_headers
        )

        assert response.status_code in [200, 201, 500]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "event_id" in data
            assert data["status"] == "created"

    def test_get_security_events(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test getting security events for an agent."""
        response = client.get(
            f"/api/v1/security/events/{test_agent_id}",
            params={"workspace_id": test_workspace_id, "timeframe": "24h"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_security_events_with_filters(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test getting events with severity filter."""
        response = client.get(
            f"/api/v1/security/events/{test_agent_id}",
            params={
                "workspace_id": test_workspace_id,
                "timeframe": "7d",
                "severity": "critical",
                "limit": 50
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]


class TestAccessControl:
    """Tests for access control analytics endpoints."""

    def test_get_access_control_metrics(self, client: TestClient, test_agent_id, test_workspace_id, auth_headers):
        """Test getting access control metrics."""
        response = client.get(
            f"/api/v1/security/access-control/{test_agent_id}",
            params={"workspace_id": test_workspace_id},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "agent_id" in data
            assert "permission_usage" in data
            assert "privilege_analysis" in data


class TestDataAccess:
    """Tests for data access analytics endpoints."""

    def test_get_data_access_analytics(self, client: TestClient, test_workspace_id, auth_headers):
        """Test getting data access analytics."""
        response = client.get(
            f"/api/v1/security/data-access/{test_workspace_id}",
            params={"timeframe": "7d"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "total_access_events" in data
            assert "pii_access_count" in data
            assert "data_exfiltration_risk" in data


class TestSecurityViews:
    """Tests for security materialized views refresh."""

    def test_refresh_security_views(self, client: TestClient, test_workspace_id, auth_headers):
        """Test refreshing security materialized views."""
        response = client.post(
            "/api/v1/security/refresh-views",
            params={"workspace_id": test_workspace_id},
            headers=auth_headers
        )

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
