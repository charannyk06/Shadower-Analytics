"""
Materialized View Refresh Service

Handles refresh operations for materialized views including:
- Individual view refresh
- Batch refresh operations
- Refresh status monitoring
- Performance tracking
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MaterializedViewRefreshService:
    """
    Service for managing materialized view refresh operations.

    Provides automatic refresh scheduling, incremental updates,
    dependency management, and refresh monitoring.
    """

    # Materialized views managed by this service
    # These views are created in migration 014_create_enhanced_materialized_views.sql
    # Other views (mv_active_users, mv_top_agents, mv_workspace_summary, etc.)
    # may exist from migration 004 but are not managed by this service
    VIEWS = [
        'mv_agent_performance',
        'mv_workspace_metrics',
        'mv_top_agents_enhanced',
        'mv_error_summary',
    ]

    # Refresh timeout in seconds
    REFRESH_TIMEOUT = 30

    # View refresh dependencies (views that depend on other views)
    DEPENDENCIES = {
        'mv_top_agents_enhanced': ['mv_agent_performance'],
    }

    def __init__(self, db: AsyncSession):
        """
        Initialize the refresh service.

        Args:
            db: Async database session
        """
        self.db = db

    async def refresh_all(
        self,
        concurrent: bool = True,
        views: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Refresh all or specified materialized views.

        Args:
            concurrent: Use CONCURRENTLY option for non-blocking refresh
            views: Optional list of specific views to refresh. If None, refreshes all.

        Returns:
            List of refresh results with status and timing
        """
        views_to_refresh = views or self.VIEWS
        results = []

        # Resolve dependencies to determine refresh order
        ordered_views = self._resolve_dependencies(views_to_refresh)

        logger.info(f"Starting refresh of {len(ordered_views)} materialized views")

        for view_name in ordered_views:
            result = await self.refresh_view(view_name, concurrent=concurrent)
            results.append(result)

        logger.info(f"Completed refresh of {len(ordered_views)} materialized views")

        return results

    @staticmethod
    def _validate_sql_identifier(identifier: str) -> None:
        """
        Validate SQL identifier to prevent SQL injection.

        Ensures identifier matches PostgreSQL naming rules:
        - Starts with letter or underscore
        - Contains only letters, digits, and underscores
        - Maximum length 63 characters

        Args:
            identifier: SQL identifier to validate

        Raises:
            ValueError: If identifier format is invalid
        """
        if not re.match(r'^[a-z_][a-z0-9_]{0,62}$', identifier):
            raise ValueError(
                f"Invalid SQL identifier format: {identifier}. "
                "Must start with letter or underscore and contain only "
                "lowercase letters, digits, and underscores."
            )

    async def refresh_view(
        self,
        view_name: str,
        concurrent: bool = True
    ) -> Dict[str, Any]:
        """
        Refresh a single materialized view.

        Args:
            view_name: Name of the materialized view to refresh
            concurrent: Use CONCURRENTLY option for non-blocking refresh

        Returns:
            Dictionary containing refresh status and metrics
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate view name against whitelist
            if view_name not in self.VIEWS:
                raise ValueError(f"Unknown materialized view: {view_name}")

            # Additional SQL identifier validation
            self._validate_sql_identifier(view_name)

            # Build refresh command
            concurrent_keyword = "CONCURRENTLY" if concurrent else ""
            query = text(
                f"REFRESH MATERIALIZED VIEW {concurrent_keyword} "
                f"analytics.{view_name}"
            )

            # Set statement timeout
            await self.db.execute(
                text(f"SET LOCAL statement_timeout = '{self.REFRESH_TIMEOUT}s'")
            )

            # Execute refresh
            logger.info(f"Refreshing materialized view: {view_name}")
            await self.db.execute(query)
            await self.db.commit()

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Successfully refreshed {view_name} in {duration:.2f} seconds"
            )

            return {
                "view_name": view_name,
                "success": True,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "error": None,
            }

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error(
                f"Failed to refresh {view_name}: {str(e)}",
                exc_info=True
            )

            # Rollback on error
            await self.db.rollback()

            return {
                "view_name": view_name,
                "success": False,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e),
            }

    async def get_refresh_status(self) -> List[Dict[str, Any]]:
        """
        Get refresh status for all materialized views.

        Returns view metadata (size, population status) for all managed views.
        This endpoint returns administrative metadata only and is restricted to
        admin users to prevent information leakage.

        Note: Materialized views do not support RLS directly. Applications should
        use the secure views (v_*_secure) created in migration 015 to access
        workspace-filtered data. This endpoint returns metadata about the 
        materialized views themselves (storage size, indexes, etc.), not the
        aggregated data they contain.

        Returns:
            List of view status information including size and population status
        """
        query = text("""
            SELECT
                matviewname as view_name,
                matviewowner as owner,
                ispopulated,
                hasindexes,
                pg_size_pretty(pg_total_relation_size('analytics.' || matviewname)) as total_size,
                pg_size_pretty(pg_relation_size('analytics.' || matviewname)) as data_size,
                pg_size_pretty(
                    pg_total_relation_size('analytics.' || matviewname) -
                    pg_relation_size('analytics.' || matviewname)
                ) as index_size,
                obj_description(('analytics.' || matviewname)::regclass, 'pg_class') as description
            FROM pg_matviews
            WHERE schemaname = 'analytics'
                AND matviewname = ANY(:view_names)
            ORDER BY matviewname
        """)

        result = await self.db.execute(query, {"view_names": self.VIEWS})
        rows = result.fetchall()

        return [
            {
                "view_name": row.view_name,
                "owner": row.owner,
                "is_populated": row.ispopulated,
                "has_indexes": row.hasindexes,
                "total_size": row.total_size,
                "data_size": row.data_size,
                "index_size": row.index_size,
                "description": row.description,
            }
            for row in rows
        ]

    async def get_view_statistics(
        self,
        view_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a specific materialized view.

        Args:
            view_name: Name of the materialized view

        Returns:
            Dictionary containing view statistics or None if not found
        """
        if view_name not in self.VIEWS:
            raise ValueError(f"Unknown materialized view: {view_name}")

        query = text("""
            SELECT
                schemaname,
                tablename as view_name,
                n_tup_ins as rows_inserted,
                n_tup_upd as rows_updated,
                n_tup_del as rows_deleted,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze,
                vacuum_count,
                autovacuum_count,
                analyze_count,
                autoanalyze_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'analytics'
                AND tablename = :view_name
        """)

        result = await self.db.execute(query, {"view_name": view_name})
        row = result.fetchone()

        if not row:
            return None

        return {
            "schema": row.schemaname,
            "view_name": row.view_name,
            "rows_inserted": row.rows_inserted,
            "rows_updated": row.rows_updated,
            "rows_deleted": row.rows_deleted,
            "live_rows": row.live_rows,
            "dead_rows": row.dead_rows,
            "last_vacuum": row.last_vacuum.isoformat() if row.last_vacuum else None,
            "last_autovacuum": row.last_autovacuum.isoformat() if row.last_autovacuum else None,
            "last_analyze": row.last_analyze.isoformat() if row.last_analyze else None,
            "last_autoanalyze": row.last_autoanalyze.isoformat() if row.last_autoanalyze else None,
            "vacuum_count": row.vacuum_count,
            "autovacuum_count": row.autovacuum_count,
            "analyze_count": row.analyze_count,
            "autoanalyze_count": row.autoanalyze_count,
        }

    async def get_row_count(self, view_name: str) -> int:
        """
        Get the number of rows in a materialized view.

        Args:
            view_name: Name of the materialized view

        Returns:
            Number of rows in the view
        """
        # Validate view name against whitelist
        if view_name not in self.VIEWS:
            raise ValueError(f"Unknown materialized view: {view_name}")

        # Additional SQL identifier validation
        self._validate_sql_identifier(view_name)

        # Use SQLAlchemy's table() constructor for safe identifier handling
        # This ensures proper quoting and prevents SQL injection
        from sqlalchemy import select, func, table
        
        # Build table reference safely using SQLAlchemy's table constructor
        # The table() function properly quotes identifiers
        view_table = table(
            view_name,
            schema='analytics'
        )
        
        # Use SQLAlchemy's select with func.count() for safe query construction
        query = select(func.count()).select_from(view_table)
        
        result = await self.db.execute(query)
        row = result.fetchone()

        return row[0] if row else 0

    async def check_view_health(self) -> List[Dict[str, Any]]:
        """
        Check the health of all materialized views.

        Returns:
            List of health check results for each view
        """
        health_results = []

        for view_name in self.VIEWS:
            try:
                # Get view status
                status_query = text("""
                    SELECT ispopulated, hasindexes
                    FROM pg_matviews
                    WHERE schemaname = 'analytics'
                        AND matviewname = :view_name
                """)

                result = await self.db.execute(
                    status_query,
                    {"view_name": view_name}
                )
                row = result.fetchone()

                if not row:
                    health_results.append({
                        "view_name": view_name,
                        "healthy": False,
                        "issues": ["View not found"],
                    })
                    continue

                issues = []

                # Check if populated
                if not row.ispopulated:
                    issues.append("View is not populated")

                # Check if indexes exist
                if not row.hasindexes:
                    issues.append("View has no indexes")

                # Get row count
                try:
                    row_count = await self.get_row_count(view_name)
                    if row_count == 0:
                        issues.append("View has no rows")
                except Exception as e:
                    issues.append(f"Failed to get row count: {str(e)}")

                health_results.append({
                    "view_name": view_name,
                    "healthy": len(issues) == 0,
                    "issues": issues,
                })

            except Exception as e:
                health_results.append({
                    "view_name": view_name,
                    "healthy": False,
                    "issues": [f"Health check failed: {str(e)}"],
                })

        return health_results

    def _resolve_dependencies(self, views: List[str]) -> List[str]:
        """
        Resolve view dependencies to determine refresh order.

        Views with no dependencies are refreshed first, followed by
        views that depend on them.

        Args:
            views: List of view names to refresh

        Returns:
            Ordered list of views respecting dependencies
        """
        ordered = []
        remaining = set(views)

        while remaining:
            # Find views with no unresolved dependencies
            ready = [
                view for view in remaining
                if view not in self.DEPENDENCIES or
                all(
                    dep not in remaining
                    for dep in self.DEPENDENCIES.get(view, [])
                )
            ]

            if not ready:
                # Circular dependency or missing dependency
                logger.warning(
                    f"Cannot resolve dependencies for: {remaining}. "
                    "Refreshing in arbitrary order."
                )
                ready = list(remaining)

            ordered.extend(ready)
            remaining -= set(ready)

        return ordered

    async def refresh_using_function(
        self,
        concurrent_mode: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Refresh all views using the database function.

        This uses the analytics.refresh_all_materialized_views() function
        which handles error recovery and provides detailed timing.

        Args:
            concurrent_mode: Use concurrent refresh mode

        Returns:
            List of refresh results from the database function
        """
        query = text("""
            SELECT *
            FROM analytics.refresh_all_materialized_views(:concurrent_mode)
        """)

        result = await self.db.execute(
            query,
            {"concurrent_mode": concurrent_mode}
        )
        rows = result.fetchall()

        return [
            {
                "view_name": row.view_name,
                "started_at": row.refresh_started_at.isoformat(),
                "completed_at": row.refresh_completed_at.isoformat(),
                "duration_seconds": float(row.duration_seconds),
                "success": row.success,
                "error": row.error_message,
            }
            for row in rows
        ]
