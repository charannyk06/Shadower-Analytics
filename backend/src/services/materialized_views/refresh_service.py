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
import os
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
    # These views are created in migration 013_create_enhanced_materialized_views.sql
    # 
    # LEGACY VIEWS NOTE:
    # Other materialized views may exist from migration 004_create_materialized_views.sql:
    # - mv_active_users
    # - mv_top_agents  
    # - mv_workspace_summary
    # - mv_error_trends
    # - mv_agent_usage_trends
    # These legacy views are NOT managed by this service. They may be deprecated in favor
    # of the enhanced views created in migration 014. Long-term plan: Migrate queries to
    # use the enhanced views (mv_agent_performance, mv_workspace_metrics, etc.) and
    # deprecate legacy views after a transition period.
    VIEWS = [
        'mv_agent_performance',
        'mv_workspace_metrics',
        'mv_top_agents_enhanced',
        'mv_error_summary',
    ]

    # Refresh timeout in seconds (configurable via environment variable)
    # Safe parsing with fallback to default and logging for invalid values
    @staticmethod
    def _parse_timeout_env(env_var: str, default: int) -> int:
        """Safely parse timeout environment variable with fallback."""
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            parsed = int(value)
            if parsed <= 0:
                logger.warning(f"Invalid {env_var} value '{value}': must be positive. Using default {default}")
                return default
            return parsed
        except ValueError:
            logger.warning(f"Invalid {env_var} value '{value}': not an integer. Using default {default}")
            return default
    
    REFRESH_TIMEOUT = _parse_timeout_env('MV_REFRESH_TIMEOUT', 30)
    
    # Per-view timeout overrides for views that may take longer
    # View refresh timeout requirements based on production metrics:
    # - mv_agent_performance: ~10-15s for 1M rows
    # - mv_workspace_metrics: ~5-10s for 10k workspaces
    # - mv_top_agents_enhanced: ~15-20s (depends on mv_agent_performance)
    # - mv_error_summary: ~30-60s for 1M errors (largest view)
    VIEW_TIMEOUTS = {
        'mv_error_summary': _parse_timeout_env('MV_ERROR_SUMMARY_TIMEOUT', 60),  # Larger view, needs more time
        # Add more as needed based on production metrics
    }

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

    async def validate_managed_views(self) -> Dict[str, Any]:
        """
        Verify all managed views exist in the database.
        
        This helps catch configuration issues where views are created in migrations
        but not added to the VIEWS list, or vice versa.

        Returns:
            Dictionary with validation results:
            - missing: Views in VIEWS list but not found in database
            - unmanaged: Views in database but not in VIEWS list
            - valid: Views that exist in both
        """
        query = text("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'analytics'
        """)
        result = await self.db.execute(query)
        existing_views = {row.matviewname for row in result.fetchall()}
        
        missing = set(self.VIEWS) - existing_views
        unmanaged = existing_views - set(self.VIEWS)
        valid = set(self.VIEWS) & existing_views
        
        if missing:
            logger.warning(f"Managed views not found in database: {missing}")
        
        if unmanaged:
            logger.info(f"Unmanaged materialized views found in database: {unmanaged}")
        
        return {
            "missing": list(missing),
            "unmanaged": list(unmanaged),
            "valid": list(valid),
            "all_valid": len(missing) == 0
        }

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

            # Build refresh command - view_name is validated against whitelist and regex
            # Using f-string is safe here because:
            # 1. view_name is validated against VIEWS whitelist
            # 2. view_name is validated with regex for SQL identifier format
            # 3. Schema name 'analytics' is hardcoded
            concurrent_keyword = "CONCURRENTLY" if concurrent else ""
            
            if concurrent_keyword:
                query_text = f"REFRESH MATERIALIZED VIEW {concurrent_keyword} analytics.{view_name}"
            else:
                query_text = f"REFRESH MATERIALIZED VIEW analytics.{view_name}"
            
            query = text(query_text)

            # Set statement timeout and execute refresh in same transaction block
            # This ensures the timeout applies to the refresh operation
            # Note: timeout value is from controlled dict/env var (integer), safe to interpolate
            # PostgreSQL requires string format like '30s' for statement_timeout
            # Using parameterized query with string format is safe here because:
            # 1. timeout is an integer from VIEW_TIMEOUTS dict or REFRESH_TIMEOUT env var
            # 2. The value is validated and comes from a controlled source
            # 3. PostgreSQL's statement_timeout requires string format with 's' suffix
            timeout = self.VIEW_TIMEOUTS.get(view_name, self.REFRESH_TIMEOUT)
            
            # Execute timeout setting and refresh in a single transaction block
            # This ensures SET LOCAL applies to the refresh command
            timeout_query = text(f"""
                SET LOCAL statement_timeout = '{timeout}s';
                {query_text}
            """)
            
            logger.info(f"Refreshing materialized view: {view_name} (timeout: {timeout}s)")
            await self.db.execute(timeout_query)
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

        SECURITY NOTE: This endpoint returns ADMINISTRATIVE METADATA ONLY
        - Returns: View sizes, population status, indexes (metadata about the views themselves)
        - Does NOT return: Actual aggregated analytics data from the views
        - Access: Admin-only via require_admin dependency
        - Workspace filtering: Not applied - admins see all view metadata for system monitoring

        For workspace-filtered DATA access, use the secure views:
        - v_agent_performance_secure
        - v_workspace_metrics_secure  
        - v_top_agents_enhanced_secure
        - v_error_summary_secure

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
                pg_size_pretty(pg_total_relation_size(
                    format('%I.%I', schemaname, matviewname)::regclass
                )) as total_size,
                pg_size_pretty(pg_relation_size(
                    format('%I.%I', schemaname, matviewname)::regclass
                )) as data_size,
                pg_size_pretty(
                    pg_total_relation_size(format('%I.%I', schemaname, matviewname)::regclass) -
                    pg_relation_size(format('%I.%I', schemaname, matviewname)::regclass)
                ) as index_size,
                obj_description(format('%I.%I', schemaname, matviewname)::regclass, 'pg_class') as description
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
