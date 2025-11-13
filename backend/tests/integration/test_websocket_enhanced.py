"""Integration tests for enhanced WebSocket functionality."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from src.api.websocket.manager import ConnectionManager
from src.api.websocket.events import EventBroadcaster
from src.api.websocket.errors import WebSocketErrorCode, handle_ws_error
from src.api.websocket.rate_limit import WebSocketRateLimiter
from src.api.websocket.realtime_metrics import RealtimeMetricsService


class TestConnectionManager:
    """Test WebSocket connection manager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_creates_workspace_group(self, manager):
        """Test that connecting creates workspace group."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await manager.connect(
            mock_ws,
            "conn_1",
            "workspace_1",
            {"user_id": "user_1", "email": "test@example.com"},
        )

        assert "workspace_1" in manager.active_connections
        assert "conn_1" in manager.active_connections["workspace_1"]
        assert "conn_1" in manager.connection_users
        assert "conn_1" in manager.subscriptions
        assert "conn_1" in manager.active_streams
        assert "conn_1" in manager.heartbeat_tasks

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self, manager):
        """Test that disconnect cleans up all resources."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Connect first
        await manager.connect(
            mock_ws,
            "conn_1",
            "workspace_1",
            {"user_id": "user_1"},
        )

        # Then disconnect
        manager.disconnect("conn_1", "workspace_1")

        assert "conn_1" not in manager.connection_users
        assert "conn_1" not in manager.subscriptions
        assert "conn_1" not in manager.active_streams

    @pytest.mark.asyncio
    async def test_subscribe_adds_event_types(self, manager):
        """Test subscribing to event types."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await manager.connect(mock_ws, "conn_1", "workspace_1", {"user_id": "user_1"})
        await manager.subscribe("conn_1", ["dashboard_updates", "alerts"])

        assert "dashboard_updates" in manager.subscriptions["conn_1"]
        assert "alerts" in manager.subscriptions["conn_1"]

    @pytest.mark.asyncio
    async def test_join_room_adds_to_room(self, manager):
        """Test joining a room."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await manager.connect(mock_ws, "conn_1", "workspace_1", {"user_id": "user_1"})
        await manager.join_room("conn_1", "dashboard", "workspace_1")

        room_key = "workspace_1:dashboard"
        assert room_key in manager.room_subscriptions
        assert "conn_1" in manager.room_subscriptions[room_key]


class TestEventBroadcaster:
    """Test WebSocket event broadcaster."""

    @pytest.mark.asyncio
    async def test_broadcast_alert_notification(self):
        """Test broadcasting alert notification."""
        mock_manager = AsyncMock()

        with patch("src.api.websocket.events.manager", mock_manager):
            broadcaster = EventBroadcaster()

            await broadcaster.broadcast_alert_notification(
                workspace_id="workspace_1",
                severity="critical",
                title="High Error Rate",
                message="Error rate exceeded threshold",
                metric="error_rate",
                value=0.15,
                threshold=0.05,
                alert_id="alert_123",
            )

            mock_manager.broadcast_to_workspace.assert_called_once()
            call_args = mock_manager.broadcast_to_workspace.call_args

            assert call_args[0][0] == "workspace_1"
            message = call_args[0][1]
            assert message["type"] == "alert"
            assert message["severity"] == "critical"
            assert message["metric"] == "error_rate"

    @pytest.mark.asyncio
    async def test_broadcast_dashboard_update(self):
        """Test broadcasting dashboard update."""
        mock_manager = AsyncMock()

        with patch("src.api.websocket.events.manager", mock_manager):
            broadcaster = EventBroadcaster()

            await broadcaster.broadcast_dashboard_update(
                workspace_id="workspace_1",
                section="executive_summary",
                data={"active_users": 100, "credits_consumed": 5000},
            )

            mock_manager.broadcast_to_workspace.assert_called_once()
            call_args = mock_manager.broadcast_to_workspace.call_args

            assert call_args[0][0] == "workspace_1"
            message = call_args[0][1]
            assert message["type"] == "dashboard_update"
            assert message["section"] == "executive_summary"


class TestWebSocketRateLimiter:
    """Test WebSocket rate limiter."""

    def test_check_rate_limit_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = WebSocketRateLimiter()

        # Should allow first request
        assert limiter.check_rate_limit("user_1", "subscribe") is True

        # Should allow second request
        assert limiter.check_rate_limit("user_1", "subscribe") is True

    def test_check_rate_limit_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = WebSocketRateLimiter()

        # Make requests up to limit
        for _ in range(10):
            limiter.check_rate_limit("user_1", "subscribe")

        # Next request should be blocked
        assert limiter.check_rate_limit("user_1", "subscribe") is False

    def test_get_remaining_quota(self):
        """Test getting remaining quota."""
        limiter = WebSocketRateLimiter()

        # Initial quota should be max
        quota = limiter.get_remaining_quota("user_1", "subscribe")
        assert quota == 10  # Default for subscribe action

        # Use one
        limiter.check_rate_limit("user_1", "subscribe")

        # Quota should decrease
        quota = limiter.get_remaining_quota("user_1", "subscribe")
        assert quota == 9

    def test_reset_user_limits(self):
        """Test resetting user limits."""
        limiter = WebSocketRateLimiter()

        # Make some requests
        for _ in range(5):
            limiter.check_rate_limit("user_1", "subscribe")

        # Reset limits
        limiter.reset_user_limits("user_1")

        # Quota should be back to max
        quota = limiter.get_remaining_quota("user_1", "subscribe")
        assert quota == 10


class TestRealtimeMetricsService:
    """Test realtime metrics service."""

    @pytest.mark.asyncio
    async def test_get_active_users_count(self):
        """Test getting active users count."""
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (42,)
        mock_db.execute.return_value = mock_result

        service = RealtimeMetricsService()
        result = await service.get_active_users_count(mock_db, "workspace_1")

        assert result["active_users"] == 42
        assert result["timeframe"] == "5m"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_credits_consumed(self):
        """Test getting credits consumed."""
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (1500.5, 25)
        mock_db.execute.return_value = mock_result

        service = RealtimeMetricsService()
        result = await service.get_credits_consumed(mock_db, "workspace_1")

        assert result["credits_consumed"] == 1500.5
        assert result["execution_count"] == 25
        assert result["timeframe"] == "1h"

    @pytest.mark.asyncio
    async def test_get_error_rate(self):
        """Test getting error rate."""
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (100, 5)  # 100 total, 5 failed
        mock_db.execute.return_value = mock_result

        service = RealtimeMetricsService()
        result = await service.get_error_rate(mock_db, "workspace_1")

        assert result["error_rate"] == 5.0
        assert result["total_executions"] == 100
        assert result["failed_executions"] == 5

    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self):
        """Test getting dashboard summary."""
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        # active_users, credits, total_execs, successful, avg_runtime
        mock_result.fetchone.return_value = (25, 2500.0, 100, 95, 1.5)
        mock_db.execute.return_value = mock_result

        service = RealtimeMetricsService()
        result = await service.get_dashboard_summary(mock_db, "workspace_1")

        assert result["active_users"] == 25
        assert result["credits_consumed"] == 2500.0
        assert result["total_executions"] == 100
        assert result["success_rate"] == 95.0
        assert result["avg_runtime"] == 1.5


class TestWebSocketErrorCodes:
    """Test WebSocket error codes."""

    def test_error_codes_defined(self):
        """Test that all error codes are properly defined."""
        assert WebSocketErrorCode.INVALID_TOKEN == (4001, "Invalid authentication token")
        assert WebSocketErrorCode.TOKEN_EXPIRED == (4002, "Authentication token expired")
        assert WebSocketErrorCode.ACCESS_DENIED == (4003, "Access denied to resource")
        assert WebSocketErrorCode.RATE_LIMITED == (4004, "Rate limit exceeded")
        assert WebSocketErrorCode.INVALID_MESSAGE == (4005, "Invalid message format")

    @pytest.mark.asyncio
    async def test_handle_ws_error_sends_message(self):
        """Test that error handler sends proper message."""
        mock_ws = AsyncMock()

        await handle_ws_error(
            mock_ws,
            WebSocketErrorCode.RATE_LIMITED,
            details="Too many requests",
            close_connection=False,
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args["type"] == "error"
        assert call_args["code"] == 4004
        assert call_args["message"] == "Rate limit exceeded"
        assert call_args["details"] == "Too many requests"


# Note: Full WebSocket integration tests would require a running server
# and WebSocket test client, which is more complex to set up in pytest.
# The above tests focus on unit testing the individual components.
