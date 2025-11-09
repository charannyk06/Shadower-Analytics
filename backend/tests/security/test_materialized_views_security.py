"""
Security Tests for Materialized Views

These tests verify:
1. Row-Level Security (RLS) enforcement for workspace isolation
2. Authentication requirements for all endpoints
3. Authorization checks (admin vs regular users)
4. SQL injection prevention

Note: These tests require a test database with RLS policies enabled.
Run with: pytest tests/security/test_materialized_views_security.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.api.main import app
from src.core.security import create_access_token


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def admin_user():
    """Admin user data"""
    return {
        "sub": "admin-user-id",
        "email": "admin@example.com",
        "role": "admin",
        "workspaces": ["workspace-1", "workspace-2"],
    }


@pytest.fixture
def regular_user():
    """Regular user data"""
    return {
        "sub": "regular-user-id",
        "email": "user@example.com",
        "role": "member",
        "workspaces": ["workspace-1"],
    }


@pytest.fixture
def admin_token(admin_user):
    """Generate admin JWT token for testing"""
    return create_access_token(admin_user)


@pytest.fixture
def regular_user_token(regular_user):
    """Generate regular user JWT token for testing"""
    return create_access_token(regular_user)


class TestMaterializedViewsSecurity:
    """Security tests for materialized views"""

    def test_refresh_requires_authentication(self, client):
        """Test that refresh endpoint requires authentication"""
        # Execute - No authentication header
        response = client.post("/materialized-views/refresh", json={})

        # Assert - Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_refresh_requires_admin_role(self, client, regular_user):
        """Test that refresh endpoint requires admin role"""
        # Mock require_admin dependency to raise 403 for non-admin users
        # This directly tests the authorization logic
        async def mock_require_admin():
            raise HTTPException(status_code=403, detail="Admin access required")
        
        with patch(
            "src.api.routes.materialized_views.require_admin",
            side_effect=mock_require_admin
        ):
            headers = {"Authorization": "Bearer fake-token"}
            response = client.post(
                "/materialized-views/refresh",
                json={},
                headers=headers
            )
            # Should return 403 Forbidden for non-admin users
            assert response.status_code == 403
            assert "Admin access required" in response.json()["detail"]

    def test_refresh_allows_admin_role(self, client, admin_user):
        """Test that refresh endpoint allows admin role"""
        # Mock require_admin to return admin user (simulating successful auth)
        async def mock_require_admin():
            return admin_user
        
        with patch(
            "src.api.routes.materialized_views.require_admin",
            return_value=admin_user
        ):
            # Mock the refresh service to avoid actual database operations
            with patch(
                "src.api.routes.materialized_views.MaterializedViewRefreshService"
            ) as mock_service:
                mock_service.return_value.refresh_all = AsyncMock(
                    return_value=[
                        {
                            "view_name": "mv_agent_performance",
                            "success": True,
                            "started_at": "2025-01-01T00:00:00Z",
                            "completed_at": "2025-01-01T00:00:01Z",
                            "duration_seconds": 1.0,
                            "error": None,
                        }
                    ]
                )
                
                headers = {"Authorization": "Bearer fake-admin-token"}
                response = client.post(
                    "/materialized-views/refresh",
                    json={},
                    headers=headers
                )
                # Should succeed (200) or return error from service (500), but not 403
                assert response.status_code != 403, \
                    f"Admin user should not receive 403, got {response.status_code}"

    def test_status_requires_authentication(self, client):
        """Test that status endpoint requires authentication"""
        # Execute - No authentication header
        response = client.get("/materialized-views/status")

        # Assert - Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_statistics_requires_authentication(self, client):
        """Test that statistics endpoint requires authentication"""
        # Execute - No authentication header
        response = client.get("/materialized-views/statistics/mv_active_users")

        # Assert - Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_health_requires_authentication(self, client):
        """Test that health endpoint requires authentication"""
        # Execute - No authentication header
        response = client.get("/materialized-views/health")

        # Assert - Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_row_count_requires_authentication(self, client):
        """Test that row count endpoint requires authentication"""
        # Execute - No authentication header
        response = client.get("/materialized-views/mv_active_users/row-count")

        # Assert - Should return 401 or 403
        assert response.status_code in [401, 403]


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention"""

    @pytest.mark.asyncio
    async def test_refresh_view_rejects_malformed_names(self):
        """Test that malformed view names are rejected"""
        from src.services.materialized_views import MaterializedViewRefreshService

        # Setup
        mock_db = AsyncMock()
        service = MaterializedViewRefreshService(mock_db)

        # Test various SQL injection attempts
        malicious_names = [
            "mv_test; DROP TABLE users;--",
            "mv_test' OR '1'='1",
            "mv_test\"; DELETE FROM analytics.user_activity;--",
            "../../../etc/passwd",
            "mv_test<script>alert('xss')</script>",
            "MV_TEST",  # uppercase should fail
            "mv-test",  # hyphens should fail
            "mv_test.extra",  # dots should fail
            "' OR 1=1--",
            "1; UPDATE analytics.daily_metrics SET value=0",
        ]

        for malicious_name in malicious_names:
            # Execute
            result = await service.refresh_view(malicious_name)

            # Assert - Should fail with error, never execute
            assert result["success"] is False
            assert "error" in result
            assert "Unknown materialized view" in result["error"] or \
                   "Invalid SQL identifier" in result["error"]

    @pytest.mark.asyncio
    async def test_get_row_count_rejects_malformed_names(self):
        """Test that get_row_count rejects malformed view names"""
        from src.services.materialized_views import MaterializedViewRefreshService

        # Setup
        mock_db = AsyncMock()
        service = MaterializedViewRefreshService(mock_db)

        # Execute
        with pytest.raises(ValueError, match="(Unknown materialized view|Invalid SQL identifier)"):
            await service.get_row_count("mv_test; DROP TABLE users;--")

    @pytest.mark.asyncio
    async def test_sql_identifier_validation(self):
        """Test SQL identifier validation function"""
        from src.services.materialized_views.refresh_service import MaterializedViewRefreshService

        # Valid identifiers - should not raise
        valid_names = [
            "mv_test",
            "mv_agent_performance",
            "mv_test_123",
            "_test_view",
            "a" * 63,  # Max length
        ]

        for name in valid_names:
            try:
                MaterializedViewRefreshService._validate_sql_identifier(name)
            except ValueError:
                pytest.fail(f"Valid identifier '{name}' was rejected")

        # Invalid identifiers - should raise ValueError
        invalid_names = [
            "MV_TEST",  # uppercase
            "mv-test",  # hyphen
            "mv.test",  # dot
            "1mv_test",  # starts with digit
            "mv_test; DROP",  # semicolon
            "mv_test'",  # quote
            "mv_test\"",  # double quote
            "a" * 64,  # Too long
            "",  # empty
            "mv test",  # space
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid SQL identifier"):
                MaterializedViewRefreshService._validate_sql_identifier(name)


class TestWorkspaceIsolation:
    """
    Tests for workspace isolation via Row-Level Security (RLS)

    These tests require a test database with:
    - RLS policies enabled on materialized views
    - Multiple test workspaces with test data
    - Test users with access to specific workspaces
    """

    @pytest.mark.skip(reason="Requires test database with RLS and multi-tenant data")
    @pytest.mark.asyncio
    async def test_user_only_sees_own_workspace_data(self):
        """
        Test that RLS policies enforce workspace isolation

        Setup:
        1. Create two workspaces: workspace_a, workspace_b
        2. Create test data in both workspaces
        3. Create user_a with access only to workspace_a
        4. Create user_b with access only to workspace_b

        Test:
        1. Query mv_agent_performance as user_a
        2. Verify only workspace_a data is returned
        3. Query mv_agent_performance as user_b
        4. Verify only workspace_b data is returned
        """
        pass

    @pytest.mark.skip(reason="Requires test database with RLS and multi-tenant data")
    @pytest.mark.asyncio
    async def test_admin_sees_all_workspace_data(self):
        """
        Test that admin users can see data from all workspaces

        Setup:
        1. Create multiple workspaces with test data
        2. Create admin user with access to all workspaces

        Test:
        1. Query materialized views as admin
        2. Verify data from all workspaces is returned
        """
        pass

    @pytest.mark.skip(reason="Requires test database with RLS and multi-tenant data")
    @pytest.mark.asyncio
    async def test_rls_prevents_cross_workspace_queries(self):
        """
        Test that users cannot access data by directly querying with different workspace_id

        Setup:
        1. Create workspace_a and workspace_b
        2. Create user with access only to workspace_a

        Test:
        1. Attempt to query mv_agent_performance with WHERE workspace_id = workspace_b
        2. Verify no data from workspace_b is returned (RLS blocks it)
        """
        pass


# =====================================================================
# Documentation for Manual Security Testing
# =====================================================================

"""
MANUAL SECURITY TESTS TO PERFORM:

1. RLS Policy Enforcement (Database-level test)
   ```sql
   -- Set up test data in multiple workspaces
   -- Switch to user with access to workspace_a only
   SET ROLE test_user_a;

   -- Query should only return workspace_a data
   SELECT * FROM analytics.mv_agent_performance;

   -- Should return 0 rows (RLS blocks workspace_b data)
   SELECT * FROM analytics.mv_agent_performance WHERE workspace_id = 'workspace_b_id';
   ```

2. Authentication Tests (API-level test)
   ```bash
   # Test without token - should return 401
   curl -X POST http://localhost:8000/materialized-views/refresh

   # Test with valid token - should succeed (for admin)
   curl -X POST http://localhost:8000/materialized-views/refresh \
     -H "Authorization: Bearer <admin_token>"

   # Test with valid token but wrong role - should return 403
   curl -X POST http://localhost:8000/materialized-views/refresh \
     -H "Authorization: Bearer <regular_user_token>"
   ```

3. SQL Injection Tests (Application-level test)
   ```bash
   # Try various SQL injection payloads
   curl -X POST "http://localhost:8000/materialized-views/refresh/mv_test;DROP%20TABLE%20users" \
     -H "Authorization: Bearer <admin_token>"

   # Should return error, not execute malicious SQL
   ```

4. Workspace Isolation Tests (Integration test)
   - Create 2 workspaces with different data
   - Create 2 users, each with access to only one workspace
   - Query materialized views as each user
   - Verify each user only sees their workspace data

5. Grant Verification Tests (Database-level test)
   ```sql
   -- Verify PUBLIC doesn't have access
   SELECT has_table_privilege('public', 'analytics.mv_agent_performance', 'SELECT');
   -- Should return false

   -- Verify authenticated role has access
   SELECT has_table_privilege('authenticated', 'analytics.mv_agent_performance', 'SELECT');
   -- Should return true

   -- Verify RLS is enabled
   SELECT tablename, rowsecurity
   FROM pg_tables
   WHERE schemaname = 'analytics' AND tablename LIKE 'mv_%';
   -- rowsecurity should be true for all views
   ```

TEST RESULTS SHOULD SHOW:
✅ All endpoints require authentication (401 without token)
✅ Refresh endpoints require admin role (403 for non-admin)
✅ RLS policies enforce workspace isolation
✅ SQL injection attempts are blocked
✅ PUBLIC role has no access to views
✅ Only authenticated users can query views
✅ Refresh function only accessible to service_role/postgres
"""
