"""Comprehensive resource utilization metrics service."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)

# Cost calculation constants (based on standard cloud pricing)
CPU_COST_PER_HOUR = 0.06  # $0.06 per CPU hour
MEMORY_COST_PER_GB_HOUR = 0.004  # $0.004 per GB-hour
GPU_COST_PER_UNIT = 0.0001  # Varies by provider
NETWORK_COST_PER_GB = 0.01  # $0.01 per GB transferred

# Token cost constants (example rates - should be configurable)
TOKEN_COST_PER_1K_INPUT = 0.003  # $3 per 1M tokens
TOKEN_COST_PER_1K_OUTPUT = 0.015  # $15 per 1M tokens


class ResourceMetricsService:
    """Service for comprehensive resource utilization analytics."""

    QUERY_TIMEOUT_SECONDS = 30
    MAX_FORECAST_DAYS = 90
    DEFAULT_FORECAST_HORIZON = 30

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_resource_usage(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "7d",
    ) -> Dict[str, Any]:
        """Get comprehensive resource usage metrics for an agent.

        Args:
            agent_id: Agent UUID
            workspace_id: Workspace UUID
            timeframe: Time period (e.g., "7d", "30d", "90d")

        Returns:
            Dictionary containing resource metrics, costs, and analytics
        """
        start_date = calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        # Fetch all metrics in parallel
        results = await asyncio.gather(
            self._get_compute_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_token_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_api_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_storage_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_cost_breakdown(agent_id, workspace_id, start_date, end_date),
            self._get_efficiency_metrics(agent_id, workspace_id, start_date, end_date),
            return_exceptions=True,
        )

        # Handle errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in resource metrics component {i}: {result}", exc_info=True)
                results[i] = {}

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "periodStart": start_date.isoformat(),
            "periodEnd": end_date.isoformat(),
            "computeMetrics": results[0],
            "tokenMetrics": results[1],
            "apiMetrics": results[2],
            "storageMetrics": results[3],
            "costBreakdown": results[4],
            "efficiencyMetrics": results[5],
        }

    async def _get_compute_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get compute resource metrics (CPU, memory, GPU)."""
        query = text("""
            SELECT
                -- CPU metrics
                SUM(cpu_seconds) as total_cpu_seconds,
                AVG(cpu_average_percent) as avg_cpu_percent,
                MAX(cpu_peak_percent) as max_cpu_percent,

                -- Memory metrics
                SUM(memory_mb_seconds) as total_memory_mb_seconds,
                AVG(memory_average_mb) as avg_memory_mb,
                MAX(memory_peak_mb) as max_memory_mb,
                AVG(memory_allocation_mb) as avg_memory_allocation_mb,

                -- GPU metrics
                SUM(COALESCE(gpu_compute_units, 0)) as total_gpu_units,
                AVG(COALESCE(gpu_utilization_percent, 0)) as avg_gpu_utilization,
                MAX(COALESCE(gpu_memory_mb, 0)) as max_gpu_memory_mb,

                -- Network metrics
                SUM(network_bytes_sent) as total_bytes_sent,
                SUM(network_bytes_received) as total_bytes_received,
                SUM(network_api_calls) as total_network_api_calls,

                -- Execution metrics
                COUNT(DISTINCT execution_id) as total_executions,
                AVG(execution_duration_ms) as avg_execution_duration_ms,
                AVG(queue_wait_time_ms) as avg_queue_wait_ms

            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_executions == 0:
            return self._empty_compute_metrics()

        return {
            "cpuUsage": {
                "totalCpuSeconds": float(row.total_cpu_seconds or 0),
                "averagePercent": float(row.avg_cpu_percent or 0),
                "peakPercent": float(row.max_cpu_percent or 0),
            },
            "memoryUsage": {
                "totalMbSeconds": float(row.total_memory_mb_seconds or 0),
                "averageMb": float(row.avg_memory_mb or 0),
                "peakMb": float(row.max_memory_mb or 0),
                "averageAllocationMb": float(row.avg_memory_allocation_mb or 0),
            },
            "gpuUsage": {
                "totalComputeUnits": float(row.total_gpu_units or 0),
                "averageUtilizationPercent": float(row.avg_gpu_utilization or 0),
                "maxMemoryMb": float(row.max_gpu_memory_mb or 0),
            },
            "networkIo": {
                "totalBytesSent": int(row.total_bytes_sent or 0),
                "totalBytesReceived": int(row.total_bytes_received or 0),
                "totalApiCalls": int(row.total_network_api_calls or 0),
                "totalBytesTransferred": int((row.total_bytes_sent or 0) + (row.total_bytes_received or 0)),
            },
            "executionMetrics": {
                "totalExecutions": int(row.total_executions or 0),
                "avgDurationMs": float(row.avg_execution_duration_ms or 0),
                "avgQueueWaitMs": float(row.avg_queue_wait_ms or 0),
            },
        }

    async def _get_token_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get token usage and efficiency metrics."""
        query = text("""
            SELECT
                -- Token counts
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(embedding_tokens) as total_embedding_tokens,
                SUM(total_tokens) as total_tokens,

                -- Token averages
                AVG(input_tokens) as avg_input_tokens,
                AVG(output_tokens) as avg_output_tokens,
                AVG(total_tokens) as avg_tokens_per_execution,

                -- Context and caching
                AVG(context_window_used) as avg_context_window_used,
                SUM(prompt_cache_hits) as total_cache_hits,
                COUNT(*) as total_executions,

                -- Cost
                SUM(token_cost_usd) as total_token_cost,
                AVG(token_cost_usd) as avg_token_cost_per_execution,

                -- Model usage
                model_provider,
                model_name,
                COUNT(*) as model_usage_count

            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
            GROUP BY model_provider, model_name
            ORDER BY total_tokens DESC
            LIMIT 10
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        rows = result.fetchall()

        if not rows:
            return self._empty_token_metrics()

        # Aggregate across all models
        total_input = sum(row.total_input_tokens or 0 for row in rows)
        total_output = sum(row.total_output_tokens or 0 for row in rows)
        total_embedding = sum(row.total_embedding_tokens or 0 for row in rows)
        total_all = sum(row.total_tokens or 0 for row in rows)
        total_cost = sum(float(row.total_token_cost or 0) for row in rows)
        total_executions = sum(row.total_executions or 0 for row in rows)
        total_cache_hits = sum(row.total_cache_hits or 0 for row in rows)

        # Calculate efficiency metrics
        tokens_per_dollar = total_all / total_cost if total_cost > 0 else 0
        cache_hit_rate = (total_cache_hits / total_executions * 100) if total_executions > 0 else 0

        # Model breakdown
        model_usage = []
        for row in rows:
            model_usage.append({
                "provider": row.model_provider,
                "model": row.model_name,
                "totalTokens": int(row.total_tokens or 0),
                "usageCount": int(row.model_usage_count or 0),
                "costUsd": float(row.total_token_cost or 0),
            })

        return {
            "totalTokens": int(total_all),
            "tokenDistribution": {
                "inputTokens": int(total_input),
                "outputTokens": int(total_output),
                "embeddingTokens": int(total_embedding),
                "inputPercent": (total_input / total_all * 100) if total_all > 0 else 0,
                "outputPercent": (total_output / total_all * 100) if total_all > 0 else 0,
                "embeddingPercent": (total_embedding / total_all * 100) if total_all > 0 else 0,
            },
            "averages": {
                "tokensPerExecution": float(total_all / total_executions) if total_executions > 0 else 0,
                "inputTokensPerExecution": float(total_input / total_executions) if total_executions > 0 else 0,
                "outputTokensPerExecution": float(total_output / total_executions) if total_executions > 0 else 0,
            },
            "efficiency": {
                "tokensPerDollar": float(tokens_per_dollar),
                "cacheHitRate": float(cache_hit_rate),
                "totalCacheHits": int(total_cache_hits),
            },
            "cost": {
                "totalCostUsd": float(total_cost),
                "avgCostPerExecution": float(total_cost / total_executions) if total_executions > 0 else 0,
                "costPerThousandTokens": float(total_cost / total_all * 1000) if total_all > 0 else 0,
            },
            "modelUsage": model_usage,
        }

    async def _get_api_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get external API usage metrics."""
        query = text("""
            SELECT
                api_endpoint,
                api_provider,
                SUM(total_calls) as total_calls,
                SUM(successful_calls) as successful_calls,
                SUM(failed_calls) as failed_calls,
                SUM(rate_limited_calls) as rate_limited_calls,
                AVG(avg_latency_ms) as avg_latency_ms,
                AVG(p95_latency_ms) as p95_latency_ms,
                SUM(total_cost_usd) as total_cost,
                SUM(wasted_cost_failed_calls) as wasted_cost,
                AVG(error_rate) as avg_error_rate
            FROM analytics.api_usage_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND period_start >= :start_date
                AND period_end <= :end_date
            GROUP BY api_endpoint, api_provider
            ORDER BY total_calls DESC
            LIMIT 20
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        rows = result.fetchall()

        if not rows:
            return self._empty_api_metrics()

        # Aggregate totals
        total_calls = sum(row.total_calls or 0 for row in rows)
        total_successful = sum(row.successful_calls or 0 for row in rows)
        total_failed = sum(row.failed_calls or 0 for row in rows)
        total_rate_limited = sum(row.rate_limited_calls or 0 for row in rows)
        total_cost = sum(float(row.total_cost or 0) for row in rows)
        total_wasted = sum(float(row.wasted_cost or 0) for row in rows)

        # API endpoint breakdown
        api_breakdown = []
        for row in rows:
            api_breakdown.append({
                "endpoint": row.api_endpoint,
                "provider": row.api_provider,
                "totalCalls": int(row.total_calls or 0),
                "successfulCalls": int(row.successful_calls or 0),
                "failedCalls": int(row.failed_calls or 0),
                "rateLimitedCalls": int(row.rate_limited_calls or 0),
                "avgLatencyMs": float(row.avg_latency_ms or 0),
                "p95LatencyMs": float(row.p95_latency_ms or 0),
                "costUsd": float(row.total_cost or 0),
                "errorRate": float(row.avg_error_rate or 0),
            })

        return {
            "totalApiCalls": int(total_calls),
            "successRate": (total_successful / total_calls * 100) if total_calls > 0 else 0,
            "statistics": {
                "totalSuccessful": int(total_successful),
                "totalFailed": int(total_failed),
                "totalRateLimited": int(total_rate_limited),
            },
            "cost": {
                "totalCostUsd": float(total_cost),
                "wastedCostUsd": float(total_wasted),
                "costPerCall": float(total_cost / total_calls) if total_calls > 0 else 0,
            },
            "apiBreakdown": api_breakdown,
        }

    async def _get_storage_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get storage utilization metrics."""
        query = text("""
            SELECT
                AVG(temp_storage_mb) as avg_temp_storage,
                MAX(temp_storage_mb) as max_temp_storage,
                AVG(persistent_storage_mb) as avg_persistent_storage,
                MAX(persistent_storage_mb) as max_persistent_storage,
                AVG(cache_size_mb) as avg_cache_size,
                MAX(cache_size_mb) as max_cache_size,
                SUM(database_operations) as total_db_operations,
                SUM(storage_cost_usd) as total_storage_cost
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row:
            return self._empty_storage_metrics()

        return {
            "tempStorage": {
                "averageMb": float(row.avg_temp_storage or 0),
                "maxMb": float(row.max_temp_storage or 0),
            },
            "persistentStorage": {
                "averageMb": float(row.avg_persistent_storage or 0),
                "maxMb": float(row.max_persistent_storage or 0),
            },
            "cache": {
                "averageSizeMb": float(row.avg_cache_size or 0),
                "maxSizeMb": float(row.max_cache_size or 0),
            },
            "database": {
                "totalOperations": int(row.total_db_operations or 0),
            },
            "cost": {
                "totalCostUsd": float(row.total_storage_cost or 0),
            },
        }

    async def _get_cost_breakdown(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        query = text("""
            SELECT
                SUM(compute_cost_usd) as total_compute_cost,
                SUM(token_cost_usd) as total_token_cost,
                SUM(api_cost_usd) as total_api_cost,
                SUM(storage_cost_usd) as total_storage_cost,
                SUM(network_cost_usd) as total_network_cost,
                SUM(total_cost_usd) as total_cost,
                COUNT(DISTINCT execution_id) as total_executions,
                AVG(total_cost_usd) as avg_cost_per_execution
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_cost == 0:
            return self._empty_cost_breakdown()

        total = float(row.total_cost or 0)
        compute = float(row.total_compute_cost or 0)
        token = float(row.total_token_cost or 0)
        api = float(row.total_api_cost or 0)
        storage = float(row.total_storage_cost or 0)
        network = float(row.total_network_cost or 0)

        return {
            "totalCostUsd": total,
            "costByCategory": {
                "computeCostUsd": compute,
                "tokenCostUsd": token,
                "apiCostUsd": api,
                "storageCostUsd": storage,
                "networkCostUsd": network,
            },
            "costDistribution": {
                "computePercent": (compute / total * 100) if total > 0 else 0,
                "tokenPercent": (token / total * 100) if total > 0 else 0,
                "apiPercent": (api / total * 100) if total > 0 else 0,
                "storagePercent": (storage / total * 100) if total > 0 else 0,
                "networkPercent": (network / total * 100) if total > 0 else 0,
            },
            "averageCostPerExecution": float(row.avg_cost_per_execution or 0),
            "totalExecutions": int(row.total_executions or 0),
        }

    async def _get_efficiency_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get efficiency scoring metrics."""

        # Get data from materialized view if available
        query = text("""
            SELECT
                overall_efficiency_score,
                tokens_per_dollar,
                executions_per_dollar,
                throughput_score,
                cost_efficiency_percent,
                total_tokens,
                total_executions,
                total_30d_cost,
                total_30d_waste
            FROM analytics.agent_efficiency_scorecard
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id},
        )
        row = result.fetchone()

        if row:
            return {
                "overallScore": float(row.overall_efficiency_score or 0),
                "tokensPerDollar": float(row.tokens_per_dollar or 0),
                "executionsPerDollar": float(row.executions_per_dollar or 0),
                "throughputScore": float(row.throughput_score or 0),
                "costEfficiencyPercent": float(row.cost_efficiency_percent or 0),
                "totalWasteCostUsd": float(row.total_30d_waste or 0),
            }

        # Fallback to calculating on the fly
        return await self._calculate_efficiency_metrics(
            agent_id, workspace_id, start_date, end_date
        )

    async def _calculate_efficiency_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate efficiency metrics from raw data."""
        query = text("""
            SELECT
                SUM(total_tokens) as total_tokens,
                SUM(total_cost_usd) as total_cost,
                COUNT(DISTINCT execution_id) as total_executions,
                AVG(execution_duration_ms) as avg_duration_ms
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_cost == 0:
            return self._empty_efficiency_metrics()

        tokens_per_dollar = row.total_tokens / row.total_cost if row.total_cost > 0 else 0
        executions_per_dollar = row.total_executions / row.total_cost if row.total_cost > 0 else 0
        throughput_score = 1000000.0 / row.avg_duration_ms if row.avg_duration_ms > 0 else 0

        # Calculate overall score (0-100)
        overall_score = (
            min(tokens_per_dollar / 1000, 1) * 30 +
            min(executions_per_dollar / 10, 1) * 30 +
            min(throughput_score / 100, 1) * 20 +
            20  # Assume no waste for now
        )

        return {
            "overallScore": float(overall_score),
            "tokensPerDollar": float(tokens_per_dollar),
            "executionsPerDollar": float(executions_per_dollar),
            "throughputScore": float(throughput_score),
            "costEfficiencyPercent": 100.0,
            "totalWasteCostUsd": 0.0,
        }

    # Helper methods for empty responses
    def _empty_compute_metrics(self) -> Dict[str, Any]:
        """Return empty compute metrics structure."""
        return {
            "cpuUsage": {"totalCpuSeconds": 0, "averagePercent": 0, "peakPercent": 0},
            "memoryUsage": {"totalMbSeconds": 0, "averageMb": 0, "peakMb": 0, "averageAllocationMb": 0},
            "gpuUsage": {"totalComputeUnits": 0, "averageUtilizationPercent": 0, "maxMemoryMb": 0},
            "networkIo": {"totalBytesSent": 0, "totalBytesReceived": 0, "totalApiCalls": 0, "totalBytesTransferred": 0},
            "executionMetrics": {"totalExecutions": 0, "avgDurationMs": 0, "avgQueueWaitMs": 0},
        }

    def _empty_token_metrics(self) -> Dict[str, Any]:
        """Return empty token metrics structure."""
        return {
            "totalTokens": 0,
            "tokenDistribution": {"inputTokens": 0, "outputTokens": 0, "embeddingTokens": 0,
                                "inputPercent": 0, "outputPercent": 0, "embeddingPercent": 0},
            "averages": {"tokensPerExecution": 0, "inputTokensPerExecution": 0, "outputTokensPerExecution": 0},
            "efficiency": {"tokensPerDollar": 0, "cacheHitRate": 0, "totalCacheHits": 0},
            "cost": {"totalCostUsd": 0, "avgCostPerExecution": 0, "costPerThousandTokens": 0},
            "modelUsage": [],
        }

    def _empty_api_metrics(self) -> Dict[str, Any]:
        """Return empty API metrics structure."""
        return {
            "totalApiCalls": 0,
            "successRate": 0,
            "statistics": {"totalSuccessful": 0, "totalFailed": 0, "totalRateLimited": 0},
            "cost": {"totalCostUsd": 0, "wastedCostUsd": 0, "costPerCall": 0},
            "apiBreakdown": [],
        }

    def _empty_storage_metrics(self) -> Dict[str, Any]:
        """Return empty storage metrics structure."""
        return {
            "tempStorage": {"averageMb": 0, "maxMb": 0},
            "persistentStorage": {"averageMb": 0, "maxMb": 0},
            "cache": {"averageSizeMb": 0, "maxSizeMb": 0},
            "database": {"totalOperations": 0},
            "cost": {"totalCostUsd": 0},
        }

    def _empty_cost_breakdown(self) -> Dict[str, Any]:
        """Return empty cost breakdown structure."""
        return {
            "totalCostUsd": 0,
            "costByCategory": {
                "computeCostUsd": 0, "tokenCostUsd": 0, "apiCostUsd": 0,
                "storageCostUsd": 0, "networkCostUsd": 0
            },
            "costDistribution": {
                "computePercent": 0, "tokenPercent": 0, "apiPercent": 0,
                "storagePercent": 0, "networkPercent": 0
            },
            "averageCostPerExecution": 0,
            "totalExecutions": 0,
        }

    def _empty_efficiency_metrics(self) -> Dict[str, Any]:
        """Return empty efficiency metrics structure."""
        return {
            "overallScore": 0,
            "tokensPerDollar": 0,
            "executionsPerDollar": 0,
            "throughputScore": 0,
            "costEfficiencyPercent": 0,
            "totalWasteCostUsd": 0,
        }
