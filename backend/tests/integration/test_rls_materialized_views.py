"""
Integration tests for RLS enforcement on materialized views.

CRITICAL: These tests verify multi-tenant data isolation using actual PostgreSQL
role switching. They MUST run in CI/CD and fail if RLS is not properly configured.

These tests verify that:
1. Users can only see data from their own workspaces via secure views
2. RLS policies properly filter data at the database level
3. Multi-tenant isolation is enforced even with SECURITY DEFINER functions
4. Admin users can access all data (if configured)

Prerequisites:
- Migration 014 (materialized views) applied
- Migration 015 (secure views and RLS) applied
- Test database with proper auth.uid() setup
- workspace_members table populated with test data
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from typing import AsyncGenerator

from src.services.materialized_views.refresh_service import MaterializedViewRefreshService


@pytest.fixture(scope="function")
async def test_workspaces_and_users(db_session):
    """
    Create test workspaces and users for RLS testing.
    
    Returns:
        dict with workspace_ids, user_ids, and workspace_memberships
    """
    workspace1_id = str(uuid.uuid4())
    workspace2_id = str(uuid.uuid4())
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    
    # Create workspace memberships in public.workspace_members
    # This is required for get_user_workspaces() to work
    try:
        await db_session.execute(
            text("""
                INSERT INTO public.workspace_members (workspace_id, user_id, role)
                VALUES 
                    (:workspace1_id, :user1_id, 'member'),
                    (:workspace2_id, :user2_id, 'member')
                ON CONFLICT DO NOTHING
            """),
            {
                "workspace1_id": workspace1_id,
                "workspace2_id": workspace2_id,
                "user1_id": user1_id,
                "user2_id": user2_id,
            }
        )
        await db_session.commit()
    except Exception as e:
        # If workspace_members table doesn't exist, mark test as failed
        pytest.fail(
            f"CRITICAL: workspace_members table not found. "
            f"RLS tests require proper database setup: {str(e)}"
        )
    
    return {
        "workspace1_id": workspace1_id,
        "workspace2_id": workspace2_id,
        "user1_id": user1_id,
        "user2_id": user2_id,
    }


@pytest.fixture(scope="function")
async def test_agent_runs_data(db_session, test_workspaces_and_users):
    """
    Create test agent_runs data in multiple workspaces.
    """
    data = test_workspaces_and_users
    workspace1_id = data["workspace1_id"]
    workspace2_id = data["workspace2_id"]
    user1_id = data["user1_id"]
    user2_id = data["user2_id"]
    
    # Insert test data into agent_runs
    try:
        # Workspace 1 data
        await db_session.execute(
            text("""
                INSERT INTO analytics.agent_runs 
                (workspace_id, user_id, agent_id, status, started_at, runtime_seconds, credits_consumed)
                VALUES 
                    (:workspace_id, :user_id, 1, 'completed', :started_at, 10.0, 100),
                    (:workspace_id, :user_id, 1, 'completed', :started_at, 15.0, 150)
            """),
            {
                "workspace_id": workspace1_id,
                "user_id": user1_id,
                "started_at": datetime.now(timezone.utc) - timedelta(days=1)
            }
        )
        
        # Workspace 2 data
        await db_session.execute(
            text("""
                INSERT INTO analytics.agent_runs 
                (workspace_id, user_id, agent_id, status, started_at, runtime_seconds, credits_consumed)
                VALUES 
                    (:workspace_id, :user_id, 2, 'completed', :started_at, 20.0, 200),
                    (:workspace_id, :user_id, 2, 'failed', :started_at, 5.0, 50)
            """),
            {
                "workspace_id": workspace2_id,
                "user_id": user2_id,
                "started_at": datetime.now(timezone.utc) - timedelta(days=1)
            }
        )
        await db_session.commit()
        
        # Refresh materialized views
        service = MaterializedViewRefreshService(db_session)
        await service.refresh_all(concurrent=False)
        
    except Exception as e:
        pytest.fail(
            f"CRITICAL: Failed to create test data. "
            f"RLS tests require agent_runs table and migrations: {str(e)}"
        )
    
    return data


@pytest.mark.integration
class TestRLSEnforcement:
    """
    CRITICAL: Tests for RLS enforcement on materialized views.
    
    These tests verify that workspace isolation is enforced at the database level.
    They use PostgreSQL role switching to simulate different users.
    """
    
    @pytest.mark.asyncio
    async def test_secure_view_filters_by_workspace_with_role_switching(
        self, db_session, test_agent_runs_data
    ):
        """
        CRITICAL TEST: Verify secure views filter by workspace using actual role switching.
        
        This test simulates user1 querying the secure view and verifies they only
        see data from workspace1, not workspace2.
        """
        data = test_agent_runs_data
        workspace1_id = data["workspace1_id"]
        workspace2_id = data["workspace2_id"]
        user1_id = data["user1_id"]
        
        # Set the current user context using PostgreSQL's role system
        # This simulates what happens when a user authenticates
        try:
            # Set role to authenticated user
            await db_session.execute(text("SET ROLE authenticated"))
            
            # Set the user ID in the JWT claim (Supabase/PostgREST pattern)
            # The auth.uid() function will read this value
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.sub\" = :user_id"),
                {"user_id": user1_id}
            )
            
            # Also set role claim
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.role\" = 'authenticated'")
            )
            
            # Query secure view - should only return workspace1 data
            result = await db_session.execute(
                text("""
                    SELECT workspace_id, COUNT(*) as count
                    FROM analytics.v_agent_performance_secure
                    GROUP BY workspace_id
                """)
            )
            rows = result.fetchall()
            workspace_ids = [str(row.workspace_id) for row in rows]
            
            # CRITICAL ASSERTION: User1 should ONLY see workspace1 data
            assert workspace1_id in workspace_ids, \
                f"User1 should see workspace1 data. Found workspaces: {workspace_ids}"
            assert workspace2_id not in workspace_ids, \
                f"SECURITY BREACH: User1 can see workspace2 data! Found workspaces: {workspace_ids}"
            
            # Verify row counts
            workspace1_count = sum(
                row.count for row in rows 
                if str(row.workspace_id) == workspace1_id
            )
            assert workspace1_count > 0, "User1 should see data from workspace1"
            
        except Exception as e:
            # If role switching fails, this indicates RLS is not properly configured
            pytest.fail(
                f"CRITICAL: RLS test failed. Role switching or get_user_workspaces() "
                f"not working correctly: {str(e)}. "
                f"This indicates a potential multi-tenant data leak."
            )
        finally:
            # Reset role
            await db_session.execute(text("RESET ROLE"))
            await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_rls_policy_prevents_cross_workspace_access(
        self, db_session, test_agent_runs_data
    ):
        """
        CRITICAL TEST: Verify RLS policies prevent direct access to other workspaces' data.
        
        This test queries the source table (agent_runs) directly to verify RLS
        policies are enforced at the table level.
        """
        data = test_agent_runs_data
        workspace1_id = data["workspace1_id"]
        workspace2_id = data["workspace2_id"]
        user1_id = data["user1_id"]
        
        try:
            # Set role to authenticated user
            await db_session.execute(text("SET ROLE authenticated"))
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.sub\" = :user_id"),
                {"user_id": user1_id}
            )
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.role\" = 'authenticated'")
            )
            
            # Query agent_runs directly - RLS should filter
            result = await db_session.execute(
                text("""
                    SELECT workspace_id, COUNT(*) as count
                    FROM analytics.agent_runs
                    GROUP BY workspace_id
                """)
            )
            rows = result.fetchall()
            workspace_ids = [str(row.workspace_id) for row in rows]
            
            # CRITICAL ASSERTION: User1 should ONLY see workspace1 data
            assert workspace1_id in workspace_ids, \
                f"User1 should see workspace1 data. Found workspaces: {workspace_ids}"
            assert workspace2_id not in workspace_ids, \
                f"SECURITY BREACH: RLS policy failed! User1 can see workspace2 data. "
                f"Found workspaces: {workspace_ids}"
            
        except Exception as e:
            pytest.fail(
                f"CRITICAL: RLS policy test failed: {str(e)}. "
                f"This indicates RLS is not properly enforced on agent_runs table."
            )
        finally:
            await db_session.execute(text("RESET ROLE"))
            await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_get_user_workspaces_function_returns_correct_workspaces(
        self, db_session, test_workspaces_and_users
    ):
        """
        CRITICAL TEST: Verify get_user_workspaces() function returns correct workspaces.
        
        This test verifies that the SECURITY DEFINER function correctly identifies
        which workspaces a user has access to.
        """
        data = test_workspaces_and_users
        workspace1_id = data["workspace1_id"]
        user1_id = data["user1_id"]
        
        try:
            # Set role to authenticated user
            await db_session.execute(text("SET ROLE authenticated"))
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.sub\" = :user_id"),
                {"user_id": user1_id}
            )
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.role\" = 'authenticated'")
            )
            
            # Call get_user_workspaces() function
            result = await db_session.execute(
                text("SELECT workspace_id FROM analytics.get_user_workspaces()")
            )
            rows = result.fetchall()
            workspace_ids = [str(row.workspace_id) for row in rows]
            
            # CRITICAL ASSERTION: Function should return workspace1_id
            assert workspace1_id in workspace_ids, \
                f"get_user_workspaces() should return workspace1_id. "
                f"Found: {workspace_ids}"
            
            # Verify it doesn't return workspace2_id
            workspace2_id = data["workspace2_id"]
            assert workspace2_id not in workspace_ids, \
                f"SECURITY BREACH: get_user_workspaces() returned workspace2_id "
                f"for user1. Found: {workspace_ids}"
            
        except Exception as e:
            pytest.fail(
                f"CRITICAL: get_user_workspaces() test failed: {str(e)}. "
                f"This function is critical for RLS enforcement."
            )
        finally:
            await db_session.execute(text("RESET ROLE"))
            await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_materialized_view_contains_all_workspaces(
        self, db_session, test_agent_runs_data
    ):
        """
        Test that materialized views contain data from all workspaces.
        
        This test verifies that materialized views themselves (not secure views)
        contain all data. This is expected behavior - RLS is enforced via secure views.
        """
        data = test_agent_runs_data
        workspace1_id = data["workspace1_id"]
        workspace2_id = data["workspace2_id"]
        
        # Query materialized view directly (bypassing secure view)
        # This should work with service_role or admin role
        try:
            result = await db_session.execute(
                text("""
                    SELECT workspace_id, COUNT(*) as count
                    FROM analytics.mv_agent_performance
                    GROUP BY workspace_id
                """)
            )
            rows = result.fetchall()
            workspace_ids = [str(row.workspace_id) for row in rows]
            
            # Materialized view should contain data from both workspaces
            assert workspace1_id in workspace_ids, \
                f"Materialized view should contain workspace1 data. Found: {workspace_ids}"
            assert workspace2_id in workspace_ids, \
                f"Materialized view should contain workspace2 data. Found: {workspace_ids}"
            
        except Exception as e:
            pytest.fail(
                f"Failed to query materialized view: {str(e)}. "
                f"This may indicate the view was not refreshed correctly."
            )
    
    @pytest.mark.asyncio
    async def test_secure_view_joins_correctly_with_get_user_workspaces(
        self, db_session, test_agent_runs_data
    ):
        """
        CRITICAL TEST: Verify secure view JOIN with get_user_workspaces() works correctly.
        
        This test verifies that the INNER JOIN in secure views properly filters
        data based on the current user's workspaces.
        """
        data = test_agent_runs_data
        workspace1_id = data["workspace1_id"]
        workspace2_id = data["workspace2_id"]
        user1_id = data["user1_id"]
        
        try:
            # Set role to authenticated user
            await db_session.execute(text("SET ROLE authenticated"))
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.sub\" = :user_id"),
                {"user_id": user1_id}
            )
            await db_session.execute(
                text("SET LOCAL \"request.jwt.claim.role\" = 'authenticated'")
            )
            
            # Query secure view with explicit workspace filter
            result = await db_session.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM analytics.v_agent_performance_secure
                    WHERE workspace_id = :workspace_id
                """),
                {"workspace_id": workspace1_id}
            )
            row = result.fetchone()
            workspace1_count = row.count if row else 0
            
            result = await db_session.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM analytics.v_agent_performance_secure
                    WHERE workspace_id = :workspace_id
                """),
                {"workspace_id": workspace2_id}
            )
            row = result.fetchone()
            workspace2_count = row.count if row else 0
            
            # CRITICAL ASSERTIONS
            assert workspace1_count > 0, \
                f"User1 should see workspace1 data. Count: {workspace1_count}"
            assert workspace2_count == 0, \
                f"SECURITY BREACH: User1 can see workspace2 data! Count: {workspace2_count}"
            
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Secure view JOIN test failed: {str(e)}. "
                f"This indicates the secure view is not properly filtering by workspace."
            )
        finally:
            await db_session.execute(text("RESET ROLE"))
            await db_session.rollback()


@pytest.mark.integration
class TestRLSConfiguration:
    """
    Tests to verify RLS is properly configured in the database.
    """
    
    @pytest.mark.asyncio
    async def test_rls_is_enabled_on_source_tables(self, db_session):
        """
        Verify RLS is enabled on agent_runs and agent_errors tables.
        """
        try:
            result = await db_session.execute(
                text("""
                    SELECT tablename, rowsecurity
                    FROM pg_tables
                    WHERE schemaname = 'analytics'
                        AND tablename IN ('agent_runs', 'agent_errors')
                """)
            )
            rows = result.fetchall()
            
            tables_with_rls = {row.tablename: row.rowsecurity for row in rows}
            
            assert 'agent_runs' in tables_with_rls, \
                "agent_runs table not found"
            assert tables_with_rls['agent_runs'] is True, \
                "CRITICAL: RLS is not enabled on agent_runs table"
            
            assert 'agent_errors' in tables_with_rls, \
                "agent_errors table not found"
            assert tables_with_rls['agent_errors'] is True, \
                "CRITICAL: RLS is not enabled on agent_errors table"
                
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Failed to verify RLS configuration: {str(e)}. "
                f"RLS must be enabled on source tables for security."
            )
    
    @pytest.mark.asyncio
    async def test_rls_policies_exist(self, db_session):
        """
        Verify RLS policies exist on agent_runs and agent_errors tables.
        """
        try:
            result = await db_session.execute(
                text("""
                    SELECT tablename, policyname
                    FROM pg_policies
                    WHERE schemaname = 'analytics'
                        AND tablename IN ('agent_runs', 'agent_errors')
                """)
            )
            rows = result.fetchall()
            
            policies_by_table = {}
            for row in rows:
                if row.tablename not in policies_by_table:
                    policies_by_table[row.tablename] = []
                policies_by_table[row.tablename].append(row.policyname)
            
            assert 'agent_runs' in policies_by_table, \
                "CRITICAL: No RLS policies found on agent_runs table"
            assert len(policies_by_table['agent_runs']) > 0, \
                "CRITICAL: No RLS policies found on agent_runs table"
            
            assert 'agent_errors' in policies_by_table, \
                "CRITICAL: No RLS policies found on agent_errors table"
            assert len(policies_by_table['agent_errors']) > 0, \
                "CRITICAL: No RLS policies found on agent_errors table"
                
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Failed to verify RLS policies: {str(e)}. "
                f"RLS policies must exist for workspace isolation."
            )
    
    @pytest.mark.asyncio
    async def test_secure_views_exist(self, db_session):
        """
        Verify secure views exist for all materialized views.
        """
        expected_secure_views = [
            'v_agent_performance_secure',
            'v_workspace_metrics_secure',
            'v_top_agents_enhanced_secure',
            'v_error_summary_secure',
        ]
        
        try:
            result = await db_session.execute(
                text("""
                    SELECT viewname
                    FROM pg_views
                    WHERE schemaname = 'analytics'
                        AND viewname = ANY(:view_names)
                """),
                {"view_names": expected_secure_views}
            )
            rows = result.fetchall()
            existing_views = [row.viewname for row in rows]
            
            for view_name in expected_secure_views:
                assert view_name in existing_views, \
                    f"CRITICAL: Secure view {view_name} does not exist. "
                    f"Found views: {existing_views}"
                    
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Failed to verify secure views: {str(e)}. "
                f"Secure views are required for workspace-filtered access."
            )

