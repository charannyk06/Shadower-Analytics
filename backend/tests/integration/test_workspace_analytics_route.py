"""Integration tests for workspace analytics API routes."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status

from src.api.routes.workspaces import verify_workspace_access, get_workspace_analytics


class TestVerifyWorkspaceAccess:
    """Test suite for workspace access verification."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_verify_workspace_access_workspace_not_found(self, mock_db):
        """Test access verification when workspace doesn't exist."""
        # Mock workspace not found
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await verify_workspace_access("ws_nonexistent", "user_123", mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_workspace_access_user_not_member(self, mock_db):
        """Test access verification when user is not a member."""
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = Mock()
            if call_count[0] == 1:
                # Workspace exists
                mock_result.fetchone.return_value = Mock()
            else:
                # User is not a member
                mock_result.fetchone.return_value = None
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        with pytest.raises(HTTPException) as exc_info:
            await verify_workspace_access("ws_123", "user_unauthorized", mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "access denied" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_workspace_access_success(self, mock_db):
        """Test successful workspace access verification."""
        # Mock both workspace exists and user is member
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock()  # Non-None value
        mock_db.execute.return_value = mock_result

        result = await verify_workspace_access("ws_123", "user_123", mock_db)

        assert result is True


class TestGetWorkspaceAnalyticsRoute:
    """Test suite for get_workspace_analytics route."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        return {
            "sub": "user_123",
            "email": "test@example.com",
            "role": "member"
        }

    @pytest.mark.asyncio
    async def test_get_workspace_analytics_missing_user_id(self, mock_db):
        """Test analytics endpoint with missing user ID in token."""
        current_user = {}  # No 'sub' field

        with pytest.raises(HTTPException) as exc_info:
            await get_workspace_analytics(
                workspace_id="ws_123",
                timeframe="30d",
                current_user=current_user,
                db=mock_db
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid authentication" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_workspace_analytics_access_denied(self, mock_db, mock_current_user):
        """Test analytics endpoint with access denied."""
        # Mock workspace exists but user not a member
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = Mock()
            if call_count[0] == 1:
                # Workspace exists
                mock_result.fetchone.return_value = Mock()
            else:
                # User is not a member
                mock_result.fetchone.return_value = None
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        with pytest.raises(HTTPException) as exc_info:
            await get_workspace_analytics(
                workspace_id="ws_123",
                timeframe="30d",
                current_user=mock_current_user,
                db=mock_db
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_workspace_analytics_workspace_not_found(self, mock_db, mock_current_user):
        """Test analytics endpoint with non-existent workspace."""
        # Mock workspace not found
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_workspace_analytics(
                workspace_id="ws_nonexistent",
                timeframe="30d",
                current_user=mock_current_user,
                db=mock_db
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch('src.api.routes.workspaces.WorkspaceAnalyticsService')
    async def test_get_workspace_analytics_success(
        self,
        mock_service_class,
        mock_db,
        mock_current_user
    ):
        """Test successful analytics retrieval."""
        # Mock workspace access verification
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = Mock()
            # Both workspace exists and user is member
            mock_result.fetchone.return_value = Mock()
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        # Mock analytics service
        mock_analytics_data = {
            "workspaceId": "ws_123",
            "timeframe": "30d",
            "generatedAt": datetime.utcnow().isoformat(),
            "healthScore": {
                "overall": 75.5,
                "components": {
                    "successRate": 80.0,
                    "activity": 70.0,
                    "engagement": 65.0,
                    "efficiency": 85.0
                }
            },
            "overview": {
                "workspaceName": "Test Workspace",
                "totalMembers": 10,
                "activeMembers": 7
            },
            "memberAnalytics": {
                "topMembers": [],
                "engagementLevels": {"high": 2, "medium": 3, "low": 2},
                "totalAnalyzed": 7
            },
            "agentUsage": {
                "totalAgents": 5,
                "totalRuns": 100,
                "successRate": 85.0
            },
            "resourceConsumption": {
                "dailyConsumption": [],
                "totalCredits": 500.0,
                "avgDailyCredits": 16.67
            },
            "activityTrends": {
                "trends": []
            }
        }

        mock_service_instance = Mock()
        mock_service_instance.get_workspace_analytics = AsyncMock(
            return_value=mock_analytics_data
        )
        mock_service_class.return_value = mock_service_instance

        result = await get_workspace_analytics(
            workspace_id="ws_123",
            timeframe="30d",
            current_user=mock_current_user,
            db=mock_db
        )

        # Verify service was called correctly
        mock_service_instance.get_workspace_analytics.assert_called_once_with(
            workspace_id="ws_123",
            timeframe="30d",
            user_id="user_123"
        )

        # Verify response
        assert result["workspaceId"] == "ws_123"
        assert result["timeframe"] == "30d"
        assert result["healthScore"]["overall"] == 75.5

    @pytest.mark.asyncio
    async def test_get_workspace_analytics_invalid_timeframe(self, mock_db, mock_current_user):
        """Test analytics endpoint with invalid timeframe."""
        # Note: In actual implementation, FastAPI's regex validation would catch this
        # before the route handler is called, but we can test the validation logic

        # For this test, we assume the route is called with an invalid timeframe
        # that bypassed FastAPI's validation (shouldn't happen in practice)

        # Mock workspace access verification
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock()
        mock_db.execute.return_value = mock_result

        # The actual validation happens at the FastAPI level with regex
        # So this test verifies that the service handles unexpected values gracefully

        with patch('src.api.routes.workspaces.WorkspaceAnalyticsService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_instance.get_workspace_analytics = AsyncMock(
                return_value={"workspaceId": "ws_123", "timeframe": "invalid"}
            )
            mock_service_class.return_value = mock_service_instance

            # Should not raise an error as the service will handle it
            result = await get_workspace_analytics(
                workspace_id="ws_123",
                timeframe="invalid",  # Would normally be caught by FastAPI
                current_user=mock_current_user,
                db=mock_db
            )

            # Service should have been called
            assert mock_service_instance.get_workspace_analytics.called


class TestWorkspaceAnalyticsValidation:
    """Test suite for workspace analytics input validation."""

    def test_workspace_id_regex_valid(self):
        """Test valid workspace IDs match the regex pattern."""
        valid_ids = [
            "ws_123",
            "workspace-abc",
            "WORKSPACE_123",
            "ws123abc",
            "a" * 64,  # Max length
        ]

        import re
        pattern = r"^[a-zA-Z0-9-_]{1,64}$"

        for workspace_id in valid_ids:
            assert re.match(pattern, workspace_id), f"Valid ID {workspace_id} should match"

    def test_workspace_id_regex_invalid(self):
        """Test invalid workspace IDs don't match the regex pattern."""
        invalid_ids = [
            "",  # Empty
            "a" * 65,  # Too long
            "ws@123",  # Invalid character
            "ws 123",  # Space
            "ws/123",  # Slash
        ]

        import re
        pattern = r"^[a-zA-Z0-9-_]{1,64}$"

        for workspace_id in invalid_ids:
            assert not re.match(pattern, workspace_id), f"Invalid ID {workspace_id} should not match"

    def test_timeframe_regex_valid(self):
        """Test valid timeframes match the regex pattern."""
        valid_timeframes = ["24h", "7d", "30d", "90d", "all"]

        import re
        pattern = r"^(24h|7d|30d|90d|all)$"

        for timeframe in valid_timeframes:
            assert re.match(pattern, timeframe), f"Valid timeframe {timeframe} should match"

    def test_timeframe_regex_invalid(self):
        """Test invalid timeframes don't match the regex pattern."""
        invalid_timeframes = [
            "1d",
            "60d",
            "1y",
            "24",
            "h",
            "",
            "ALL",  # Case sensitive
        ]

        import re
        pattern = r"^(24h|7d|30d|90d|all)$"

        for timeframe in invalid_timeframes:
            assert not re.match(pattern, timeframe), f"Invalid timeframe {timeframe} should not match"
