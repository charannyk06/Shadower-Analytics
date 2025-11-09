"""Integration tests for authentication endpoints and middleware."""

import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from datetime import timedelta
from unittest.mock import patch, AsyncMock

from src.core.security import create_access_token
from src.api.middleware.permissions import (
    get_current_user,
    PermissionChecker,
    WorkspacePermissionChecker,
    require_roles,
    require_workspace_permissions,
)


# Test app setup
@pytest.fixture
def app():
    """Create a test FastAPI app."""
    test_app = FastAPI()

    @test_app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    @test_app.get("/protected")
    async def protected_endpoint(current_user: dict = Depends(get_current_user)):
        return {"message": "protected", "user": current_user}

    @test_app.get("/admin")
    async def admin_endpoint(current_user: dict = Depends(require_roles(["admin"]))):
        return {"message": "admin", "user": current_user}

    @test_app.get("/workspaces/{workspace_id}/data")
    async def workspace_endpoint(
        workspace_id: str,
        current_user: dict = Depends(require_workspace_permissions(["read"])),
    ):
        return {"message": "workspace data", "workspace_id": workspace_id}

    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_public_endpoint_no_auth(self, client):
        """Test accessing public endpoint without authentication."""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}

    def test_protected_endpoint_no_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/protected")
        assert response.status_code == 403  # No credentials provided

    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token."""
        # Create a valid token
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        # Mock Redis calls
        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/protected",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["message"] == "protected"
                    assert data["user"]["sub"] == "user123"

    def test_protected_endpoint_with_expired_token(self, client):
        """Test accessing protected endpoint with expired token."""
        # Create an expired token
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                response = client.get(
                    "/protected",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert response.status_code == 401
                assert "Could not validate credentials" in response.json()["detail"]

    def test_protected_endpoint_with_blacklisted_token(self, client):
        """Test accessing protected endpoint with blacklisted token."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=True):
            response = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 401
            assert "revoked" in response.json()["detail"].lower()

    def test_protected_endpoint_with_invalid_token_format(self, client):
        """Test accessing protected endpoint with invalid token format."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-token-format"},
        )

        assert response.status_code == 401


class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_admin_endpoint_with_admin_role(self, client):
        """Test accessing admin endpoint with admin role."""
        data = {
            "sub": "admin123",
            "email": "admin@example.com",
            "roles": ["admin"],
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/admin",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 200
                    assert response.json()["message"] == "admin"

    def test_admin_endpoint_without_admin_role(self, client):
        """Test accessing admin endpoint without admin role."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
            "roles": ["viewer"],
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/admin",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 403
                    assert "Insufficient permissions" in response.json()["detail"]

    def test_admin_endpoint_with_no_roles(self, client):
        """Test accessing admin endpoint with no roles."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/admin",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 403

    def test_admin_endpoint_with_multiple_roles(self, client):
        """Test accessing admin endpoint with multiple roles including admin."""
        data = {
            "sub": "user123",
            "email": "manager@example.com",
            "roles": ["manager", "admin", "viewer"],
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/admin",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 200


class TestWorkspacePermissions:
    """Test workspace-level permissions."""

    def test_workspace_endpoint_with_valid_workspace_access(self, client):
        """Test accessing workspace endpoint with valid workspace access."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
            "workspaces": {
                "ws-1": {"permissions": ["read", "write"]},
            },
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/workspaces/ws-1/data",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 200
                    assert response.json()["workspace_id"] == "ws-1"

    def test_workspace_endpoint_without_workspace_access(self, client):
        """Test accessing workspace endpoint without workspace access."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
            "workspaces": {
                "ws-2": {"permissions": ["read"]},
            },
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/workspaces/ws-1/data",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 403
                    assert "Access denied" in response.json()["detail"]

    def test_workspace_endpoint_with_insufficient_permissions(self, client):
        """Test accessing workspace endpoint with insufficient permissions."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
            "workspaces": {
                "ws-1": {"permissions": ["write"]},  # Has write but not read
            },
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/workspaces/ws-1/data",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    # Should fail because read permission is required
                    assert response.status_code == 403

    def test_workspace_endpoint_with_no_workspaces(self, client):
        """Test accessing workspace endpoint with no workspaces in token."""
        data = {
            "sub": "user123",
            "email": "user@example.com",
        }
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    response = client.get(
                        "/workspaces/ws-1/data",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    assert response.status_code == 403


class TestTokenCaching:
    """Test token caching behavior."""

    def test_cached_token_used_on_subsequent_requests(self, client):
        """Test that cached tokens are used on subsequent requests."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        # First request - should cache the token
        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None) as mock_get_cache:
                with patch("src.core.security.cache_decoded_token", return_value=True) as mock_set_cache:
                    response1 = client.get(
                        "/protected",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert response1.status_code == 200
                    mock_get_cache.assert_called_once()
                    mock_set_cache.assert_called_once()

        # Second request - should use cached token
        cached_payload = {"sub": "user123", "email": "test@example.com", "exp": 99999999999}
        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=cached_payload):
                with patch("src.core.security.cache_decoded_token") as mock_set_cache:
                    response2 = client.get(
                        "/protected",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert response2.status_code == 200
                    # Should not try to cache again
                    mock_set_cache.assert_not_called()


class TestPermissionCheckerClass:
    """Test PermissionChecker class directly."""

    @pytest.mark.asyncio
    async def test_permission_checker_with_matching_role(self):
        """Test PermissionChecker with matching role."""
        checker = PermissionChecker(required_roles=["admin"])
        user = {"sub": "user123", "roles": ["admin"]}

        result = await checker(current_user=user)
        assert result == user

    @pytest.mark.asyncio
    async def test_permission_checker_with_non_matching_role(self):
        """Test PermissionChecker with non-matching role."""
        checker = PermissionChecker(required_roles=["admin"])
        user = {"sub": "user123", "roles": ["viewer"]}

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_permission_checker_with_no_required_roles(self):
        """Test PermissionChecker with no required roles."""
        checker = PermissionChecker(required_roles=[])
        user = {"sub": "user123", "roles": ["viewer"]}

        result = await checker(current_user=user)
        assert result == user

    @pytest.mark.asyncio
    async def test_permission_checker_with_string_role(self):
        """Test PermissionChecker when user has role as string instead of list."""
        checker = PermissionChecker(required_roles=["admin"])
        user = {"sub": "user123", "roles": "admin"}

        result = await checker(current_user=user)
        assert result == user
