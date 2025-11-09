"""Execution metrics service for comprehensive execution tracking."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.redis import RedisClient


class ExecutionMetricsService:
    """Service for calculating and retrieving execution metrics."""

    def __init__(self, db: AsyncSession, redis: Optional[RedisClient] = None):
        """Initialize the execution metrics service.

        Args:
            db: Database session
            redis: Redis client for caching (optional)
        """
        self.db = db
        self.redis = redis

    async def get_execution_metrics(
        self,
        workspace_id: str,
        timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """Get comprehensive execution metrics.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time window (e.g., '1h', '24h', '7d', '30d')

        Returns:
            Dictionary containing all execution metrics
        """
        end_time = datetime.utcnow()
        start_time = self._calculate_start_time(timeframe, end_time)

        # Fetch all metrics in parallel
        results = await asyncio.gather(
            self._get_realtime_metrics(workspace_id),
            self._get_throughput_metrics(workspace_id, start_time, end_time),
            self._get_latency_metrics(workspace_id, start_time, end_time),
            self._get_performance_metrics(workspace_id, start_time, end_time),
            self._get_execution_patterns(workspace_id, start_time, end_time),
            self._get_resource_utilization(workspace_id, start_time, end_time),
        )

        return {
            "timeframe": timeframe,
            "workspaceId": workspace_id,
            "realtime": results[0],
            "throughput": results[1],
            "latency": results[2],
            "performance": results[3],
            "patterns": results[4],
            "resources": results[5],
        }

    async def _get_realtime_metrics(self, workspace_id: str) -> Dict[str, Any]:
        """Get real-time execution status.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Real-time metrics including running executions and queue status
        """
        # Get currently running executions
        running_query = text("""
            SELECT
                execution_id as run_id,
                agent_id,
                'Agent ' || agent_id as agent_name,
                user_id,
                started_at,
                EXTRACT(EPOCH FROM (NOW() - started_at)) as elapsed_time,
                COALESCE(duration, 60) as estimated_runtime,
                metadata
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND status IN ('running', 'processing', 'pending')
                AND completed_at IS NULL
            ORDER BY started_at DESC
            LIMIT 50
        """)

        result = await self.db.execute(running_query, {"workspace_id": workspace_id})
        running = result.mappings().all()

        # Get queued executions
        queue_query = text("""
            SELECT
                queue_id,
                agent_id,
                priority,
                queued_at,
                estimated_start_time
            FROM execution_queue
            WHERE workspace_id = :workspace_id
                AND status = 'queued'
            ORDER BY priority DESC, queued_at ASC
            LIMIT 50
        """)

        result = await self.db.execute(queue_query, {"workspace_id": workspace_id})
        queued = result.mappings().all()

        # Calculate average queue wait time
        avg_wait_time = 0
        if queued:
            wait_times = [
                (datetime.utcnow() - q['queued_at']).total_seconds()
                for q in queued
                if q['queued_at']
            ]
            avg_wait_time = np.mean(wait_times) if wait_times else 0

        # Get system load (stub - replace with actual monitoring)
        system_load = await self._get_system_load()

        return {
            "currentlyRunning": len(running),
            "queueDepth": len(queued),
            "avgQueueWaitTime": round(avg_wait_time, 2),
            "executionsInProgress": [
                {
                    "runId": r['run_id'],
                    "agentId": r['agent_id'],
                    "agentName": r['agent_name'],
                    "userId": r['user_id'],
                    "startedAt": r['started_at'].isoformat() if r['started_at'] else None,
                    "elapsedTime": round(r['elapsed_time'], 2),
                    "estimatedCompletion": str(int(r['estimated_runtime']))
                }
                for r in running
            ],
            "queuedExecutions": [
                {
                    "queueId": q['queue_id'],
                    "agentId": q['agent_id'],
                    "priority": q['priority'],
                    "queuedAt": q['queued_at'].isoformat() if q['queued_at'] else None,
                    "estimatedStartTime": q['estimated_start_time'].isoformat() if q.get('estimated_start_time') else None
                }
                for q in queued
            ],
            "systemLoad": system_load
        }

    async def _get_throughput_metrics(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate throughput metrics.

        Args:
            workspace_id: Workspace identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Throughput metrics including executions per time unit
        """
        query = text("""
            WITH time_buckets AS (
                SELECT
                    DATE_TRUNC('minute', started_at) as minute,
                    COUNT(*) as executions
                FROM execution_logs
                WHERE workspace_id = :workspace_id
                    AND started_at BETWEEN :start_time AND :end_time
                GROUP BY DATE_TRUNC('minute', started_at)
            )
            SELECT
                COUNT(DISTINCT minute) as total_minutes,
                SUM(executions) as total_executions,
                AVG(executions) as avg_per_minute,
                MAX(executions) as peak_executions
            FROM time_buckets
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        stats = result.mappings().first()

        if not stats or stats['total_executions'] is None:
            stats = {
                'total_minutes': 0,
                'total_executions': 0,
                'avg_per_minute': 0,
                'peak_executions': 0
            }

        # Calculate throughput rates
        total_minutes = max(stats['total_minutes'], 1)
        total_hours = total_minutes / 60
        total_days = total_hours / 24

        executions_per_minute = stats['avg_per_minute'] or 0
        executions_per_hour = executions_per_minute * 60
        executions_per_day = executions_per_hour * 24

        # Get throughput trend
        trend_query = text("""
            SELECT
                DATE_TRUNC('hour', started_at) as timestamp,
                COUNT(*) as value
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
            GROUP BY DATE_TRUNC('hour', started_at)
            ORDER BY timestamp ASC
        """)

        result = await self.db.execute(
            trend_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        trend = result.mappings().all()

        return {
            "executionsPerMinute": round(executions_per_minute, 2),
            "executionsPerHour": round(executions_per_hour, 2),
            "executionsPerDay": round(executions_per_day, 2),
            "throughputTrend": [
                {
                    "timestamp": t['timestamp'].isoformat() if t['timestamp'] else None,
                    "value": t['value']
                }
                for t in trend
            ],
            "peakThroughput": {
                "value": int(stats['peak_executions'] or 0),
                "timestamp": end_time.isoformat()
            },
            "capacityUtilization": 0,  # Stub - calculate based on max capacity
            "maxCapacity": 1000  # Stub - should be configurable
        }

    async def _get_latency_metrics(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate latency percentiles.

        Args:
            workspace_id: Workspace identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Latency metrics with percentile calculations
        """
        # Get execution latency percentiles
        query = text("""
            SELECT
                -- Execution Latency (time to complete)
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration) as exec_p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY duration) as exec_p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY duration) as exec_p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration) as exec_p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration) as exec_p99,
                AVG(duration) as exec_avg,

                -- Queue Latency (stub - requires queue table with queue timestamps)
                0 as queue_avg,
                0 as queue_p50,
                0 as queue_p75,
                0 as queue_p90,
                0 as queue_p95,
                0 as queue_p99
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
                AND status IN ('success', 'failure', 'failed', 'error', 'completed')
                AND duration IS NOT NULL
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        stats = result.mappings().first()

        if not stats:
            stats = {
                'exec_avg': 0, 'exec_p50': 0, 'exec_p75': 0,
                'exec_p90': 0, 'exec_p95': 0, 'exec_p99': 0,
                'queue_avg': 0, 'queue_p50': 0, 'queue_p75': 0,
                'queue_p90': 0, 'queue_p95': 0, 'queue_p99': 0
            }

        # Get latency distribution
        distribution_query = text("""
            SELECT
                CASE
                    WHEN duration < 1 THEN '0-1s'
                    WHEN duration < 5 THEN '1-5s'
                    WHEN duration < 10 THEN '5-10s'
                    WHEN duration < 30 THEN '10-30s'
                    WHEN duration < 60 THEN '30-60s'
                    ELSE '60s+'
                END as bucket,
                COUNT(*) as count
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
                AND duration IS NOT NULL
            GROUP BY bucket
            ORDER BY
                CASE bucket
                    WHEN '0-1s' THEN 1
                    WHEN '1-5s' THEN 2
                    WHEN '5-10s' THEN 3
                    WHEN '10-30s' THEN 4
                    WHEN '30-60s' THEN 5
                    WHEN '60s+' THEN 6
                END
        """)

        result = await self.db.execute(
            distribution_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        distribution = result.mappings().all()

        total = sum(d['count'] for d in distribution)

        return {
            "queueLatency": {
                "avg": round(stats['queue_avg'] or 0, 2),
                "median": round(stats['queue_p50'] or 0, 2),
                "p50": round(stats['queue_p50'] or 0, 2),
                "p75": round(stats['queue_p75'] or 0, 2),
                "p90": round(stats['queue_p90'] or 0, 2),
                "p95": round(stats['queue_p95'] or 0, 2),
                "p99": round(stats['queue_p99'] or 0, 2)
            },
            "executionLatency": {
                "avg": round(stats['exec_avg'] or 0, 2),
                "median": round(stats['exec_p50'] or 0, 2),
                "p50": round(stats['exec_p50'] or 0, 2),
                "p75": round(stats['exec_p75'] or 0, 2),
                "p90": round(stats['exec_p90'] or 0, 2),
                "p95": round(stats['exec_p95'] or 0, 2),
                "p99": round(stats['exec_p99'] or 0, 2)
            },
            "endToEndLatency": {
                "avg": round(stats['exec_avg'] or 0, 2),
                "median": round(stats['exec_p50'] or 0, 2),
                "p50": round(stats['exec_p50'] or 0, 2),
                "p75": round(stats['exec_p75'] or 0, 2),
                "p90": round(stats['exec_p90'] or 0, 2),
                "p95": round(stats['exec_p95'] or 0, 2),
                "p99": round(stats['exec_p99'] or 0, 2)
            },
            "latencyDistribution": [
                {
                    "bucket": d['bucket'],
                    "count": d['count'],
                    "percentage": round(d['count'] / total * 100, 2) if total > 0 else 0
                }
                for d in distribution
            ]
        }

    async def _get_performance_metrics(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get performance metrics.

        Args:
            workspace_id: Workspace identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Performance metrics including success rates
        """
        # Get overall performance stats
        query = text("""
            SELECT
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                COUNT(*) FILTER (WHERE status IN ('failure', 'failed', 'error')) as failed,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        stats = result.mappings().first()

        total = stats['total_executions'] or 0
        successful = stats['successful'] or 0
        failed = stats['failed'] or 0
        cancelled = stats['cancelled'] or 0

        success_rate = (successful / total * 100) if total > 0 else 0
        failure_rate = (failed / total * 100) if total > 0 else 0
        cancellation_rate = (cancelled / total * 100) if total > 0 else 0

        # Get performance by agent
        by_agent_query = text("""
            SELECT
                agent_id,
                'Agent ' || agent_id as agent_name,
                COUNT(*) as executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                AVG(duration) as avg_runtime,
                COUNT(*) FILTER (WHERE status IN ('failure', 'failed', 'error')) as errors
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
            GROUP BY agent_id
            ORDER BY executions DESC
            LIMIT 10
        """)

        result = await self.db.execute(
            by_agent_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        by_agent = result.mappings().all()

        # Get performance by hour
        by_hour_query = text("""
            SELECT
                EXTRACT(HOUR FROM started_at) as hour,
                COUNT(*) as executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                AVG(duration) as avg_latency
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
            GROUP BY EXTRACT(HOUR FROM started_at)
            ORDER BY hour
        """)

        result = await self.db.execute(
            by_hour_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        by_hour = result.mappings().all()

        return {
            "totalExecutions": total,
            "successfulExecutions": successful,
            "failedExecutions": failed,
            "cancelledExecutions": cancelled,
            "successRate": round(success_rate, 2),
            "failureRate": round(failure_rate, 2),
            "cancellationRate": round(cancellation_rate, 2),
            "byAgent": [
                {
                    "agentId": a['agent_id'],
                    "agentName": a['agent_name'],
                    "executions": a['executions'],
                    "successRate": round((a['successful'] / a['executions'] * 100) if a['executions'] > 0 else 0, 2),
                    "avgRuntime": round(a['avg_runtime'] or 0, 2),
                    "errorRate": round((a['errors'] / a['executions'] * 100) if a['executions'] > 0 else 0, 2)
                }
                for a in by_agent
            ],
            "byHour": [
                {
                    "hour": int(h['hour']),
                    "executions": h['executions'],
                    "successRate": round((h['successful'] / h['executions'] * 100) if h['executions'] > 0 else 0, 2),
                    "avgLatency": round(h['avg_latency'] or 0, 2)
                }
                for h in by_hour
            ],
            "vsLastPeriod": {
                "executionsChange": 0,  # Stub - requires comparison
                "successRateChange": 0,
                "latencyChange": 0
            }
        }

    async def _get_execution_patterns(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get execution patterns and anomalies.

        Args:
            workspace_id: Workspace identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Execution patterns including timeline and anomalies
        """
        # Get timeline data
        timeline_query = text("""
            SELECT
                DATE_TRUNC('hour', started_at) as timestamp,
                COUNT(*) as executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                AVG(duration) as avg_duration
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at BETWEEN :start_time AND :end_time
            GROUP BY DATE_TRUNC('hour', started_at)
            ORDER BY timestamp ASC
        """)

        result = await self.db.execute(
            timeline_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        timeline = result.mappings().all()

        # Get detected patterns
        patterns_query = text("""
            SELECT
                pattern_type,
                start_time,
                end_time,
                peak_executions,
                total_executions,
                impact,
                severity,
                description
            FROM execution_patterns
            WHERE workspace_id = :workspace_id
                AND detected_at BETWEEN :start_time AND :end_time
            ORDER BY detected_at DESC
            LIMIT 10
        """)

        result = await self.db.execute(
            patterns_query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        bursts = result.mappings().all()

        return {
            "timeline": [
                {
                    "timestamp": t['timestamp'].isoformat() if t['timestamp'] else None,
                    "executions": t['executions'],
                    "successRate": round((t['successful'] / t['executions'] * 100) if t['executions'] > 0 else 0, 2),
                    "avgDuration": round(t['avg_duration'] or 0, 2)
                }
                for t in timeline
            ],
            "bursts": [
                {
                    "startTime": b['start_time'].isoformat() if b['start_time'] else None,
                    "endTime": b['end_time'].isoformat() if b.get('end_time') else None,
                    "peakExecutions": b['peak_executions'] or 0,
                    "totalExecutions": b['total_executions'] or 0,
                    "impact": b['impact'] or 'low'
                }
                for b in bursts if b['pattern_type'] == 'burst'
            ],
            "patterns": {
                "peakHours": [9, 10, 11, 14, 15, 16],  # Stub - calculate from data
                "quietHours": [0, 1, 2, 3, 4, 5],
                "averageDaily": 100,  # Stub
                "weekdayAverage": 120,
                "weekendAverage": 60
            },
            "anomalies": [
                {
                    "timestamp": b['start_time'].isoformat() if b['start_time'] else None,
                    "type": b['pattern_type'],
                    "severity": b['severity'],
                    "description": b['description'] or f"{b['pattern_type']} detected"
                }
                for b in bursts
            ]
        }

    async def _get_resource_utilization(
        self,
        workspace_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get resource utilization metrics.

        Args:
            workspace_id: Workspace identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Resource utilization metrics
        """
        # Stub implementation - would integrate with actual monitoring system
        return {
            "compute": {
                "cpuUsage": [],
                "memoryUsage": [],
                "gpuUsage": []
            },
            "modelUsage": {},
            "databaseLoad": {
                "connections": 10,
                "queryRate": 50,
                "avgQueryTime": 0.05
            }
        }

    async def _get_system_load(self) -> Dict[str, Any]:
        """Get current system load.

        Returns:
            System load metrics
        """
        # Stub - would integrate with actual system monitoring
        return {
            "cpu": 45.5,
            "memory": 62.3,
            "workers": {
                "total": 10,
                "busy": 3,
                "idle": 7
            }
        }

    def _calculate_start_time(self, timeframe: str, end_time: datetime) -> datetime:
        """Calculate start time from timeframe string.

        Args:
            timeframe: Time window (e.g., '1h', '24h', '7d', '30d')
            end_time: End time

        Returns:
            Start time
        """
        timeframe_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90)
        }

        delta = timeframe_map.get(timeframe, timedelta(hours=1))
        return end_time - delta


# Legacy functions for backward compatibility
async def get_execution_stats(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
) -> Dict:
    """Get execution statistics (legacy function).

    Args:
        db: Database session
        start_date: Start date
        end_date: End date

    Returns:
        Execution statistics
    """
    service = ExecutionMetricsService(db)
    # Calculate timeframe
    delta = end_date - start_date
    if delta.days <= 1:
        timeframe = "24h"
    elif delta.days <= 7:
        timeframe = "7d"
    else:
        timeframe = "30d"

    # Get metrics for first workspace (stub - should accept workspace_id)
    metrics = await service.get_execution_metrics("default", timeframe)

    return {
        "total_executions": metrics['performance']['totalExecutions'],
        "successful_executions": metrics['performance']['successfulExecutions'],
        "failed_executions": metrics['performance']['failedExecutions'],
        "avg_duration": metrics['latency']['executionLatency']['avg'],
        "p95_duration": metrics['latency']['executionLatency']['p95'],
        "p99_duration": metrics['latency']['executionLatency']['p99'],
    }


async def get_execution_trends(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    granularity: str = "daily",
) -> List[Dict]:
    """Get execution trends over time (legacy function).

    Args:
        db: Database session
        start_date: Start date
        end_date: End date
        granularity: Granularity ('hourly', 'daily', 'weekly')

    Returns:
        Time-series trend data
    """
    service = ExecutionMetricsService(db)
    delta = end_date - start_date
    if delta.days <= 1:
        timeframe = "24h"
    elif delta.days <= 7:
        timeframe = "7d"
    else:
        timeframe = "30d"

    metrics = await service.get_execution_metrics("default", timeframe)
    return metrics['patterns']['timeline']


async def get_execution_distribution(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
) -> Dict:
    """Get distribution of execution statuses (legacy function).

    Args:
        db: Database session
        start_date: Start date
        end_date: End date

    Returns:
        Execution status distribution
    """
    service = ExecutionMetricsService(db)
    delta = end_date - start_date
    if delta.days <= 1:
        timeframe = "24h"
    elif delta.days <= 7:
        timeframe = "7d"
    else:
        timeframe = "30d"

    metrics = await service.get_execution_metrics("default", timeframe)
    perf = metrics['performance']

    return {
        "success": perf['successfulExecutions'],
        "failure": perf['failedExecutions'],
        "timeout": 0,
        "cancelled": perf['cancelledExecutions'],
    }
