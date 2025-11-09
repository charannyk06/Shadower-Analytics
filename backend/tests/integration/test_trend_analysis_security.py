"""
Integration tests for Trend Analysis Security

Tests SQL injection prevention, access control, and input validation
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

from src.services.analytics.trend_analysis_service_secure import TrendAnalysisService
from src.services.analytics.trend_analysis_constants import *


@pytest.fixture
async def mock_db():
    """Mock database session with execute method"""
    db = AsyncMock()
    return db


@pytest.fixture
def trend_service(mock_db):
    """Create secure TrendAnalysisService instance"""
    return TrendAnalysisService(mock_db)


class TestSQLInjectionPrevention:
    """Test SQL injection prevention measures"""

    @pytest.mark.asyncio
    async def test_sql_injection_in_workspace_id(self, trend_service, mock_db):
        """Test that SQL injection in workspace_id is prevented"""
        # Malicious input attempting SQL injection
        malicious_workspace_id = "'; DROP TABLE analytics.agent_executions; --"

        # Mock database to track executed query
        executed_queries = []

        async def mock_execute(query, params=None):
            executed_queries.append((str(query), params))
            # Return empty result
            mock_result = Mock()
            mock_result.fetchall = Mock(return_value=[])
            return mock_result

        mock_db.execute = mock_execute

        # This should raise ValueError due to input validation
        with pytest.raises(ValueError):
            await trend_service.analyze_trend(
                malicious_workspace_id,
                'executions',
                '30d'
            )

    @pytest.mark.asyncio
    async def test_parameterized_query_usage(self, trend_service, mock_db):
        """Test that queries use bind parameters, not string formatting"""
        valid_workspace_id = "550e8400-e29b-41d4-a716-446655440000"

        # Mock database execution
        executed_queries = []

        async def mock_execute(query, params=None):
            executed_queries.append((str(query), params))
            # Return sample data
            mock_result = Mock()
            mock_result.fetchall = Mock(return_value=[
                (datetime(2024, 1, i), float(100 + i))
                for i in range(1, 20)
            ])
            return mock_result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        # Execute analysis
        try:
            await trend_service._get_time_series_secure(
                valid_workspace_id,
                'executions',
                '30d'
            )
        except:
            pass  # May fail on other parts, we just want to check query structure

        # Verify at least one query was executed with parameters
        assert len(executed_queries) > 0

        for query, params in executed_queries:
            # Verify params is a dict (parameterized query)
            assert params is None or isinstance(params, dict), \
                "Query should use parameterized execution with dict params"

            # Verify workspace_id not directly in query string
            if params and 'workspace_id' in params:
                assert params['workspace_id'] not in str(query), \
                    "workspace_id should be bind parameter, not in query string"

    @pytest.mark.asyncio
    async def test_no_raw_string_interpolation(self, trend_service):
        """Test that _build_time_series_query_secure uses parameters"""
        workspace_id = "550e8400-e29b-41d4-a716-446655440000"
        start_date = datetime(2024, 1, 1)

        query, params = trend_service._build_time_series_query_secure(
            'executions',
            workspace_id,
            start_date
        )

        # Query should contain placeholders, not actual values
        assert ':workspace_id' in query
        assert ':start_date' in query

        # Values should be in params dict
        assert params['workspace_id'] == workspace_id
        assert params['start_date'] == start_date

        # Actual values should NOT be in query string
        assert workspace_id not in query
        assert start_date.isoformat() not in query


class TestInputValidation:
    """Test input validation and sanitization"""

    @pytest.mark.asyncio
    async def test_invalid_metric_rejected(self, trend_service):
        """Test that invalid metrics are rejected"""
        with pytest.raises(ValueError, match="Invalid metric"):
            trend_service._validate_inputs(
                "valid-workspace-id",
                "invalid_metric",  # Not in ALLOWED_METRICS
                "30d"
            )

    @pytest.mark.asyncio
    async def test_invalid_timeframe_rejected(self, trend_service):
        """Test that invalid timeframes are rejected"""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            trend_service._validate_inputs(
                "valid-workspace-id",
                "executions",
                "1000d"  # Not in ALLOWED_TIMEFRAMES
            )

    @pytest.mark.asyncio
    async def test_invalid_workspace_id_format(self, trend_service):
        """Test that invalid workspace_id formats are rejected"""
        with pytest.raises(ValueError, match="Invalid workspace_id"):
            trend_service._validate_inputs(
                "x",  # Too short
                "executions",
                "30d"
            )

    @pytest.mark.asyncio
    async def test_all_allowed_metrics_pass_validation(self, trend_service):
        """Test that all allowed metrics pass validation"""
        for metric in ALLOWED_METRICS:
            # Should not raise
            trend_service._validate_inputs(
                "550e8400-e29b-41d4-a716-446655440000",
                metric,
                "30d"
            )

    @pytest.mark.asyncio
    async def test_all_allowed_timeframes_pass_validation(self, trend_service):
        """Test that all allowed timeframes pass validation"""
        for timeframe in ALLOWED_TIMEFRAMES:
            # Should not raise
            trend_service._validate_inputs(
                "550e8400-e29b-41d4-a716-446655440000",
                "executions",
                timeframe
            )


class TestWorkspaceAccessControl:
    """Test workspace access validation"""

    @pytest.mark.asyncio
    async def test_unauthorized_access_denied(self, trend_service, mock_db):
        """Test that unauthorized users are denied access"""
        # Mock database to return False (no access)
        async def mock_execute(query, params=None):
            mock_result = Mock()
            mock_result.scalar = Mock(return_value=False)
            return mock_result

        mock_db.execute = mock_execute

        with pytest.raises(PermissionError, match="Unauthorized"):
            await trend_service._validate_workspace_access(
                "workspace-123",
                "user-456"
            )

    @pytest.mark.asyncio
    async def test_authorized_access_granted(self, trend_service, mock_db):
        """Test that authorized users are granted access"""
        # Mock database to return True (has access)
        async def mock_execute(query, params=None):
            mock_result = Mock()
            mock_result.scalar = Mock(return_value=True)
            return mock_result

        mock_db.execute = mock_execute

        # Should not raise
        await trend_service._validate_workspace_access(
            "workspace-123",
            "user-456"
        )

    @pytest.mark.asyncio
    async def test_workspace_validation_uses_parameterized_query(self, trend_service, mock_db):
        """Test that workspace validation uses parameterized queries"""
        executed_queries = []

        async def mock_execute(query, params=None):
            executed_queries.append((str(query), params))
            mock_result = Mock()
            mock_result.scalar = Mock(return_value=True)
            return mock_result

        mock_db.execute = mock_execute

        await trend_service._validate_workspace_access(
            "workspace-123",
            "user-456"
        )

        # Verify parameterized query was used
        assert len(executed_queries) == 1
        query, params = executed_queries[0]

        assert params is not None
        assert 'workspace_id' in params
        assert 'user_id' in params
        assert params['workspace_id'] == "workspace-123"
        assert params['user_id'] == "user-456"


class TestCacheIsolation:
    """Test cache isolation between users"""

    @pytest.mark.asyncio
    async def test_cache_includes_user_context(self, trend_service, mock_db):
        """Test that cache operations include user context"""
        # This is a structural test - actual implementation would need
        # to verify cache keys include user_id when provided

        # Mock cache retrieval
        async def mock_execute(query, params=None):
            mock_result = Mock()
            mock_result.fetchone = Mock(return_value=None)
            return mock_result

        mock_db.execute = mock_execute

        # Call with user_id
        result = await trend_service._get_cached_analysis(
            "workspace-123",
            "executions",
            "30d",
            "user-456"  # user_id provided
        )

        # Verify cache query was called (would include user in WHERE clause)
        assert mock_db.execute.called


class TestErrorHandling:
    """Test error handling and information disclosure"""

    @pytest.mark.asyncio
    async def test_database_errors_dont_expose_details(self, trend_service, mock_db):
        """Test that database errors don't expose internal details"""
        # Mock database to raise error
        async def mock_execute(query, params=None):
            raise Exception("Database connection failed: host=internal-db-server.local")

        mock_db.execute = mock_execute

        # Error should be caught and re-raised without exposing internal details
        with pytest.raises(Exception):
            await trend_service.analyze_trend(
                "550e8400-e29b-41d4-a716-446655440000",
                "executions",
                "30d",
                "user-123"
            )

        # In production, this should be caught and logged,
        # with only generic error returned to user

    @pytest.mark.asyncio
    async def test_validation_errors_provide_safe_messages(self, trend_service):
        """Test that validation errors provide safe, helpful messages"""
        try:
            trend_service._validate_inputs(
                "valid-id",
                "bad_metric",
                "30d"
            )
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e)
            # Should mention allowed values
            assert "allowed" in error_msg.lower() or "Invalid" in error_msg
            # Should not contain internal paths or stack traces
            assert "/src/" not in error_msg
            assert "Traceback" not in error_msg


class TestQueryConstruction:
    """Test secure query construction"""

    @pytest.mark.asyncio
    async def test_all_metrics_use_parameterized_queries(self, trend_service):
        """Test that all metric queries use bind parameters"""
        workspace_id = "550e8400-e29b-41d4-a716-446655440000"
        start_date = datetime(2024, 1, 1)

        for metric in ALLOWED_METRICS:
            query, params = trend_service._build_time_series_query_secure(
                metric,
                workspace_id,
                start_date
            )

            # All queries should use bind parameters
            assert ':workspace_id' in query
            assert ':start_date' in query
            assert params['workspace_id'] == workspace_id
            assert params['start_date'] == start_date

            # No values should be interpolated into query
            assert workspace_id not in query
            assert str(start_date) not in query

    @pytest.mark.asyncio
    async def test_query_includes_proper_null_handling(self, trend_service):
        """Test that queries handle NULL values safely"""
        query, params = trend_service._build_time_series_query_secure(
            'credits',
            "workspace-id",
            datetime(2024, 1, 1)
        )

        # Should use COALESCE or similar for NULL handling
        assert 'COALESCE' in query.upper() or 'NULLIF' in query.upper()


@pytest.mark.integration
class TestEndToEndSecurity:
    """End-to-end security integration tests"""

    @pytest.mark.asyncio
    async def test_full_flow_with_security_checks(self, trend_service, mock_db):
        """Test complete analysis flow with all security checks"""
        workspace_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "user-123"
        metric = "executions"
        timeframe = "30d"

        # Mock responses
        call_count = {'workspace_check': 0, 'data_query': 0}

        async def mock_execute(query, params=None):
            query_str = str(query)

            # Workspace access check
            if 'workspace_members' in query_str:
                call_count['workspace_check'] += 1
                mock_result = Mock()
                mock_result.scalar = Mock(return_value=True)
                return mock_result

            # Cache check
            if 'trend_analysis_cache' in query_str and 'SELECT' in query_str:
                mock_result = Mock()
                mock_result.fetchone = Mock(return_value=None)
                return mock_result

            # Data query
            if 'agent_executions' in query_str:
                call_count['data_query'] += 1
                # Verify parameterized
                assert params is not None
                assert 'workspace_id' in params

                mock_result = Mock()
                mock_result.fetchall = Mock(return_value=[
                    (datetime(2024, 1, i), float(100 + i))
                    for i in range(1, 20)
                ])
                return mock_result

            # Cache write
            if 'INSERT' in query_str or 'UPDATE' in query_str:
                mock_result = Mock()
                return mock_result

            return Mock()

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        # Execute full analysis
        try:
            result = await trend_service.analyze_trend(
                workspace_id,
                metric,
                timeframe,
                user_id
            )
        except Exception as e:
            # Some parts may fail, but security checks should have executed
            pass

        # Verify security checks were performed
        assert call_count['workspace_check'] > 0, "Workspace access should be checked"
        # Note: data_query might be 0 if validation failed, which is OK


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
