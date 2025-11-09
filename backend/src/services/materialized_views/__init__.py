"""
Materialized Views Service Package

This package provides services for managing materialized views including:
- Refresh operations
- Status monitoring
- Performance tracking
"""

from .refresh_service import MaterializedViewRefreshService

__all__ = ["MaterializedViewRefreshService"]
