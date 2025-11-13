"""Custom application metrics collection."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from .prometheus import (
    active_users_gauge,
    database_connections_gauge,
    cache_items_total,
    cache_size_bytes,
)

logger = logging.getLogger(__name__)


@dataclass
class MetricsCollector:
    """Collector for custom application metrics."""

    db_session: AsyncSession
    redis_client: Optional[Redis] = None

    async def collect_business_metrics(self) -> Dict[str, Any]:
        """Collect business metrics for monitoring.

        Returns:
            Dictionary containing collected metrics
        """
        metrics = {}

        try:
            # Active users
            metrics['active_users'] = await self.get_active_users_count()

            # Credits consumption
            metrics['credits_consumed_today'] = await self.get_credits_consumed_today()

            # Error rates
            metrics['error_rate'] = await self.calculate_error_rate()

            # Agent performance
            metrics['agent_success_rates'] = await self.get_agent_success_rates()

            # Database metrics
            metrics['database'] = await self.get_database_metrics()

            # Cache metrics (if Redis available)
            if self.redis_client:
                metrics['cache'] = await self.get_cache_metrics()

            logger.info("Business metrics collected successfully", extra={'metrics_count': len(metrics)})

        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}", exc_info=True)
            metrics['error'] = str(e)

        return metrics

    async def get_active_users_count(self) -> Dict[str, int]:
        """Get count of active users per workspace.

        Returns:
            Dictionary mapping workspace_id to active user count
        """
        try:
            # Count users active in last 15 minutes
            query = text("""
                SELECT workspace_id, COUNT(DISTINCT user_id) as active_count
                FROM user_activity
                WHERE timestamp >= NOW() - INTERVAL '15 minutes'
                GROUP BY workspace_id
            """)

            result = await self.db_session.execute(query)
            rows = result.fetchall()

            active_users = {str(row.workspace_id): row.active_count for row in rows}

            return active_users

        except Exception as e:
            logger.error(f"Error getting active users: {e}", exc_info=True)
            return {}

    async def get_credits_consumed_today(self) -> Dict[str, Any]:
        """Get credits consumed today per workspace.

        Returns:
            Dictionary with credit consumption data
        """
        try:
            query = text("""
                SELECT
                    workspace_id,
                    SUM(credits_used) as total_credits,
                    COUNT(*) as execution_count
                FROM execution_logs
                WHERE DATE(timestamp) = CURRENT_DATE
                GROUP BY workspace_id
            """)

            result = await self.db_session.execute(query)
            rows = result.fetchall()

            credits_data = {
                str(row.workspace_id): {
                    'total_credits': float(row.total_credits or 0),
                    'execution_count': row.execution_count
                }
                for row in rows
            }

            return credits_data

        except Exception as e:
            logger.error(f"Error getting credits consumed: {e}", exc_info=True)
            return {}

    async def calculate_error_rate(self) -> float:
        """Calculate overall error rate for the last hour.

        Returns:
            Error rate as a percentage
        """
        try:
            query = text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'error') as errors,
                    COUNT(*) as total
                FROM execution_logs
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """)

            result = await self.db_session.execute(query)
            row = result.fetchone()

            if row and row.total > 0:
                error_rate = (row.errors / row.total) * 100
                return round(error_rate, 2)

            return 0.0

        except Exception as e:
            logger.error(f"Error calculating error rate: {e}", exc_info=True)
            return 0.0

    async def get_agent_success_rates(self) -> Dict[str, float]:
        """Get success rates per agent.

        Returns:
            Dictionary mapping agent_id to success rate percentage
        """
        try:
            query = text("""
                SELECT
                    agent_id,
                    COUNT(*) FILTER (WHERE status = 'success') as successes,
                    COUNT(*) as total
                FROM execution_logs
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY agent_id
            """)

            result = await self.db_session.execute(query)
            rows = result.fetchall()

            success_rates = {}
            for row in rows:
                if row.total > 0:
                    rate = (row.successes / row.total) * 100
                    success_rates[str(row.agent_id)] = round(rate, 2)

            return success_rates

        except Exception as e:
            logger.error(f"Error getting agent success rates: {e}", exc_info=True)
            return {}

    async def get_database_metrics(self) -> Dict[str, Any]:
        """Get database connection pool metrics.

        Returns:
            Dictionary with database metrics
        """
        try:
            # Get pool statistics from SQLAlchemy engine
            engine = self.db_session.get_bind()
            pool = engine.pool

            metrics = {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'total_connections': pool.size() + pool.overflow(),
            }

            # Calculate active and idle connections
            active_connections = metrics['checked_out']
            idle_connections = metrics['checked_in']

            # Update Prometheus gauges
            database_connections_gauge.labels(state='active').set(active_connections)
            database_connections_gauge.labels(state='idle').set(idle_connections)
            database_connections_gauge.labels(state='total').set(metrics['total_connections'])

            return metrics

        except Exception as e:
            logger.error(f"Error getting database metrics: {e}", exc_info=True)
            return {
                'error': str(e)
            }

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics from Redis.

        Returns:
            Dictionary with cache metrics
        """
        if not self.redis_client:
            return {'error': 'Redis client not available'}

        try:
            # Get Redis info
            info = await self.redis_client.info('memory')

            # Get number of keys
            db_info = await self.redis_client.info('keyspace')
            total_keys = 0
            if 'db0' in db_info:
                total_keys = db_info['db0'].get('keys', 0)

            metrics = {
                'used_memory_bytes': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'total_keys': total_keys,
                'hit_rate': await self._calculate_cache_hit_rate(),
            }

            # Update Prometheus gauges
            cache_size_bytes.set(metrics['used_memory_bytes'])
            cache_items_total.set(metrics['total_keys'])

            return metrics

        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}", exc_info=True)
            return {'error': str(e)}

    async def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from Redis stats.

        Returns:
            Hit rate as a percentage
        """
        try:
            info = await self.redis_client.info('stats')
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)

            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                return round(hit_rate, 2)

            return 0.0

        except Exception as e:
            logger.error(f"Error calculating cache hit rate: {e}", exc_info=True)
            return 0.0

    async def export_to_prometheus(self, metrics: Dict[str, Any]) -> None:
        """Export collected metrics to Prometheus gauges.

        Args:
            metrics: Collected metrics dictionary
        """
        try:
            # Update active users gauge
            if 'active_users' in metrics:
                for workspace_id, count in metrics['active_users'].items():
                    active_users_gauge.labels(workspace_id=workspace_id).set(count)

            logger.info("Metrics exported to Prometheus successfully")

        except Exception as e:
            logger.error(f"Error exporting metrics to Prometheus: {e}", exc_info=True)
