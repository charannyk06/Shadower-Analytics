"""Unit tests for request validation utilities."""

import pytest
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from unittest.mock import Mock

from backend.src.api.validation import (
    RequestValidator,
    require_workspace_access,
    require_admin,
    validate_date_range
)


class TestWorkspaceAccessValidation:
    """Test workspace access validation."""

    @pytest.mark.asyncio
    async def test_validates_workspace_access_success(self):
        """Test successful workspace access validation."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "user123",
            "workspace_id": "ws123",
            "workspace_ids": ["ws123", "ws456"]
        }

        # Should not raise exception for primary workspace
        await RequestValidator.validate_workspace_access(request, "ws123")

        # Should not raise exception for workspace in list
        await RequestValidator.validate_workspace_access(request, "ws456")

    @pytest.mark.asyncio
    async def test_validates_workspace_access_denied(self):
        """Test workspace access is denied for unauthorized workspace."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "user123",
            "workspace_id": "ws123",
            "workspace_ids": ["ws123"]
        }

        # Should raise exception for unauthorized workspace
        with pytest.raises(HTTPException) as exc_info:
            await RequestValidator.validate_workspace_access(request, "ws999")

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validates_workspace_access_no_user(self):
        """Test workspace access validation without authenticated user."""
        request = Mock(spec=Request)
        request.state.user = None

        with pytest.raises(HTTPException) as exc_info:
            await RequestValidator.validate_workspace_access(request, "ws123")

        assert exc_info.value.status_code == 401


class TestDateRangeValidation:
    """Test date range validation."""

    def test_validates_valid_date_range(self):
        """Test valid date range passes validation."""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow() - timedelta(days=1)

        # Should not raise exception
        RequestValidator.validate_date_range(start, end, max_days=365)

    def test_rejects_end_before_start(self):
        """Test end date before start date is rejected."""
        start = datetime.utcnow()
        end = datetime.utcnow() - timedelta(days=7)

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_date_range(start, end)

        assert exc_info.value.status_code == 400
        assert "before" in exc_info.value.detail.lower()

    def test_rejects_range_exceeding_max(self):
        """Test date range exceeding maximum is rejected."""
        start = datetime.utcnow() - timedelta(days=400)
        end = datetime.utcnow()

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_date_range(start, end, max_days=365)

        assert exc_info.value.status_code == 400
        assert "exceeds maximum" in exc_info.value.detail

    def test_rejects_future_dates(self):
        """Test future dates are rejected."""
        start = datetime.utcnow()
        end = datetime.utcnow() + timedelta(days=7)

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_date_range(start, end)

        assert exc_info.value.status_code == 400
        assert "future" in exc_info.value.detail.lower()

    def test_validates_minimum_range(self):
        """Test minimum date range validation."""
        start = datetime.utcnow() - timedelta(hours=12)
        end = datetime.utcnow()

        # Should fail with min_days=1
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_date_range(start, end, min_days=1)

        assert exc_info.value.status_code == 400
        assert "at least" in exc_info.value.detail.lower()


class TestPaginationValidation:
    """Test pagination validation."""

    def test_validates_valid_pagination(self):
        """Test valid pagination passes validation."""
        RequestValidator.validate_pagination(page=1, per_page=50, max_per_page=100)
        RequestValidator.validate_pagination(page=5, per_page=25, max_per_page=100)

    def test_rejects_invalid_page(self):
        """Test invalid page number is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_pagination(page=0, per_page=50)

        assert exc_info.value.status_code == 400
        assert "page must be >= 1" in exc_info.value.detail

    def test_rejects_invalid_per_page(self):
        """Test invalid per_page is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_pagination(page=1, per_page=0)

        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_pagination(page=1, per_page=200, max_per_page=100)

        assert exc_info.value.status_code == 400
        assert "cannot exceed" in exc_info.value.detail


class TestMetricsValidation:
    """Test metrics validation."""

    def test_validates_valid_metrics(self):
        """Test valid metrics pass validation."""
        metrics = ["metric1", "metric2"]
        allowed = ["metric1", "metric2", "metric3"]

        RequestValidator.validate_metrics(metrics, allowed, max_metrics=10)

    def test_rejects_empty_metrics(self):
        """Test empty metrics list is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_metrics([], ["metric1"])

        assert exc_info.value.status_code == 400
        assert "At least one metric" in exc_info.value.detail

    def test_rejects_too_many_metrics(self):
        """Test too many metrics is rejected."""
        metrics = [f"metric{i}" for i in range(15)]
        allowed = metrics

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_metrics(metrics, allowed, max_metrics=10)

        assert exc_info.value.status_code == 400
        assert "Cannot request more than" in exc_info.value.detail

    def test_rejects_invalid_metrics(self):
        """Test invalid metric names are rejected."""
        metrics = ["metric1", "invalid_metric"]
        allowed = ["metric1", "metric2"]

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_metrics(metrics, allowed)

        assert exc_info.value.status_code == 400
        assert "Invalid metrics" in exc_info.value.detail
        assert "invalid_metric" in exc_info.value.detail


class TestAdminAccessValidation:
    """Test admin access validation."""

    @pytest.mark.asyncio
    async def test_validates_admin_role(self):
        """Test admin role grants access."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "admin123",
            "role": "admin",
            "permissions": []
        }

        # Should not raise exception
        await RequestValidator.validate_admin_access(request)

    @pytest.mark.asyncio
    async def test_validates_owner_role(self):
        """Test owner role grants access."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "owner123",
            "role": "owner",
            "permissions": []
        }

        # Should not raise exception
        await RequestValidator.validate_admin_access(request)

    @pytest.mark.asyncio
    async def test_validates_admin_permission(self):
        """Test admin permission grants access."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "user123",
            "role": "user",
            "permissions": ["admin"]
        }

        # Should not raise exception
        await RequestValidator.validate_admin_access(request)

    @pytest.mark.asyncio
    async def test_rejects_non_admin(self):
        """Test non-admin users are rejected."""
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "user123",
            "role": "user",
            "permissions": []
        }

        with pytest.raises(HTTPException) as exc_info:
            await RequestValidator.validate_admin_access(request)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail


class TestFilterValidation:
    """Test filter validation."""

    def test_validates_valid_filters(self):
        """Test valid filters pass validation."""
        filters = {"field1": "value1", "field2": "value2"}
        allowed = ["field1", "field2", "field3"]

        RequestValidator.validate_filters(filters, allowed)

    def test_rejects_invalid_filter_fields(self):
        """Test invalid filter fields are rejected."""
        filters = {"field1": "value1", "invalid_field": "value"}
        allowed = ["field1", "field2"]

        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_filters(filters, allowed)

        assert exc_info.value.status_code == 400
        assert "Invalid filter fields" in exc_info.value.detail


class TestSortValidation:
    """Test sort validation."""

    def test_validates_valid_sort_field(self):
        """Test valid sort field passes validation."""
        RequestValidator.validate_sort("field1", ["field1", "field2"])

    def test_validates_none_sort_field(self):
        """Test None sort field is allowed."""
        RequestValidator.validate_sort(None, ["field1", "field2"])

    def test_rejects_invalid_sort_field(self):
        """Test invalid sort field is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_sort("invalid_field", ["field1", "field2"])

        assert exc_info.value.status_code == 400
        assert "Invalid sort field" in exc_info.value.detail


class TestAggregationValidation:
    """Test aggregation validation."""

    def test_validates_valid_aggregations(self):
        """Test valid aggregations pass validation."""
        for agg in ["sum", "avg", "min", "max", "count", "p50", "p95", "p99"]:
            RequestValidator.validate_aggregation(agg)

    def test_rejects_invalid_aggregation(self):
        """Test invalid aggregation is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_aggregation("invalid")

        assert exc_info.value.status_code == 400
        assert "Invalid aggregation" in exc_info.value.detail


class TestIntervalValidation:
    """Test interval validation."""

    def test_validates_valid_intervals(self):
        """Test valid intervals pass validation."""
        for interval in ["hour", "day", "week", "month"]:
            RequestValidator.validate_interval(interval)

    def test_rejects_invalid_interval(self):
        """Test invalid interval is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            RequestValidator.validate_interval("invalid")

        assert exc_info.value.status_code == 400
        assert "Invalid interval" in exc_info.value.detail
