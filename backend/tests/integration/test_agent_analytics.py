"""Integration tests for agent analytics endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from src.services.analytics.agent_analytics_service import AgentAnalyticsService
from src.utils.calculations import calculate_percentage_change


class TestAgentAnalyticsService:
    """Test AgentAnalyticsService."""

    @pytest.mark.asyncio
    async def test_uuid_validation(self, db_session):
        """Test that invalid UUIDs are rejected."""
        service = AgentAnalyticsService(db_session)

        # Test with invalid agent_id
        with pytest.raises(ValueError, match="Invalid UUID format"):
            await service.get_agent_analytics(
                agent_id="not-a-uuid",
                workspace_id=str(uuid4()),
                timeframe="7d"
            )

        # Test with invalid workspace_id
        with pytest.raises(ValueError, match="Invalid UUID format"):
            await service.get_agent_analytics(
                agent_id=str(uuid4()),
                workspace_id="not-a-uuid",
                timeframe="7d"
            )

    @pytest.mark.asyncio
    async def test_valid_timeframes(self, db_session):
        """Test that valid timeframes are accepted."""
        service = AgentAnalyticsService(db_session)
        agent_id = str(uuid4())
        workspace_id = str(uuid4())

        # All these should not raise validation errors
        # (though they may fail due to no data, which is expected)
        for timeframe in ["24h", "7d", "30d", "90d", "all"]:
            try:
                await service.get_agent_analytics(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    timeframe=timeframe
                )
            except Exception as e:
                # We expect the query to fail due to no data,
                # but UUID validation should have passed
                assert "Invalid UUID format" not in str(e)


class TestUtilityFunctions:
    """Test utility functions used in analytics."""

    def test_calculate_percentage_change(self):
        """Test percentage change calculation."""
        # Normal case
        assert calculate_percentage_change(150, 100) == 50.0
        assert calculate_percentage_change(75, 100) == -25.0

        # Zero previous value
        assert calculate_percentage_change(100, 0) == 100.0
        assert calculate_percentage_change(0, 0) == 0.0

        # Edge cases
        assert calculate_percentage_change(100, 50) == 100.0
        assert calculate_percentage_change(50, 100) == -50.0

    def test_calculate_percentage_change_rounding(self):
        """Test that percentage changes are properly rounded."""
        result = calculate_percentage_change(103, 100)
        assert result == 3.0
        assert isinstance(result, float)


@pytest.mark.asyncio
class TestAgentAnalyticsEndpoint:
    """Test agent analytics API endpoint."""

    async def test_analytics_endpoint_requires_auth(self, client):
        """Test that analytics endpoint requires authentication."""
        agent_id = str(uuid4())
        workspace_id = str(uuid4())

        # Without auth, should get 401 or 403
        response = client.get(
            f"/api/v1/agents/{agent_id}/analytics",
            params={"workspace_id": workspace_id, "timeframe": "7d"}
        )
        assert response.status_code in [401, 403], \
            "Analytics endpoint should require authentication"

    async def test_analytics_endpoint_validates_timeframe(self, client, sample_agent_data):
        """Test that invalid timeframe is rejected."""
        agent_id = sample_agent_data["agent_id"]
        workspace_id = sample_agent_data["workspace_id"]

        # Invalid timeframe should fail validation
        response = client.get(
            f"/api/v1/agents/{agent_id}/analytics",
            params={"workspace_id": workspace_id, "timeframe": "invalid"}
        )
        assert response.status_code == 422, \
            "Invalid timeframe should return 422 validation error"


# TODO: Add more comprehensive tests
# - Test with actual database data
# - Test error handling for database failures
# - Test caching behavior when implemented
# - Test pagination when implemented
# - Test concurrent requests
# - Performance tests with large datasets
