"""Comprehensive resource analytics service with optimization and forecasting."""

import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class TokenEfficiencyAnalyzer:
    """Analyzer for token usage efficiency and optimization opportunities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_token_usage(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "7d",
    ) -> Dict[str, Any]:
        """Analyze token usage patterns and identify optimization opportunities."""
        start_date = calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        results = await asyncio.gather(
            self._calculate_token_distribution(agent_id, workspace_id, start_date, end_date),
            self._calculate_efficiency_metrics(agent_id, workspace_id, start_date, end_date),
            self._identify_optimizations(agent_id, workspace_id, start_date, end_date),
            self._analyze_token_costs(agent_id, workspace_id, start_date, end_date),
            return_exceptions=True,
        )

        return {
            "tokenDistribution": results[0] if not isinstance(results[0], Exception) else {},
            "efficiencyMetrics": results[1] if not isinstance(results[1], Exception) else {},
            "optimizationOpportunities": results[2] if not isinstance(results[2], Exception) else [],
            "costAnalysis": results[3] if not isinstance(results[3], Exception) else {},
        }

    async def _calculate_token_distribution(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate token distribution across different categories."""
        query = text("""
            SELECT
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(embedding_tokens) as embedding_tokens,
                AVG(context_window_used) as avg_context_used,
                MAX(context_window_used) as max_context_used
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if not row:
            return {}

        total = row.input_tokens + row.output_tokens + row.embedding_tokens
        return {
            "inputTokens": int(row.input_tokens or 0),
            "outputTokens": int(row.output_tokens or 0),
            "embeddingTokens": int(row.embedding_tokens or 0),
            "totalTokens": int(total),
            "contextUtilization": {
                "averageUsed": float(row.avg_context_used or 0),
                "maxUsed": int(row.max_context_used or 0),
            },
        }

    async def _calculate_efficiency_metrics(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate token efficiency metrics."""
        query = text("""
            SELECT
                AVG(total_tokens::float / NULLIF(execution_duration_ms, 0) * 1000) as tokens_per_second,
                SUM(prompt_cache_hits) as cache_hits,
                COUNT(*) as total_executions,
                SUM(total_tokens) as total_tokens,
                SUM(token_cost_usd) as total_cost
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if not row or row.total_executions == 0:
            return {}

        cache_hit_rate = (row.cache_hits / row.total_executions) * 100 if row.total_executions > 0 else 0
        tokens_per_dollar = row.total_tokens / row.total_cost if row.total_cost > 0 else 0

        return {
            "tokensPerSecond": float(row.tokens_per_second or 0),
            "cacheHitRate": float(cache_hit_rate),
            "tokensPerDollar": float(tokens_per_dollar),
            "totalCacheHits": int(row.cache_hits or 0),
        }

    async def _identify_optimizations(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Identify token optimization opportunities."""
        optimizations = []

        # Check for low cache hit rate
        query = text("""
            SELECT
                SUM(prompt_cache_hits) as cache_hits,
                COUNT(*) as total_executions
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if row and row.total_executions > 0:
            cache_hit_rate = (row.cache_hits / row.total_executions) * 100
            if cache_hit_rate < 20:
                optimizations.append({
                    "type": "caching",
                    "title": "Low Prompt Cache Hit Rate",
                    "description": f"Current cache hit rate is {cache_hit_rate:.1f}%. Implementing prompt caching could reduce costs.",
                    "estimatedSavings": "20-40%",
                    "priority": "high",
                })

        # Check for high context window usage
        query = text("""
            SELECT AVG(context_window_used) as avg_context
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if row and row.avg_context > 8000:
            optimizations.append({
                "type": "context_optimization",
                "title": "High Context Window Usage",
                "description": "Average context window usage is high. Consider prompt compression or summarization.",
                "estimatedSavings": "15-30%",
                "priority": "medium",
            })

        return optimizations

    async def _analyze_token_costs(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze token costs and trends."""
        query = text("""
            SELECT
                DATE(created_at) as date,
                SUM(total_tokens) as daily_tokens,
                SUM(token_cost_usd) as daily_cost
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        rows = result.fetchall()

        if not rows:
            return {}

        total_cost = sum(float(row.daily_cost) for row in rows)
        total_tokens = sum(int(row.daily_tokens) for row in rows)

        trend_data = [
            {
                "date": row.date.isoformat(),
                "tokens": int(row.daily_tokens),
                "cost": float(row.daily_cost),
            }
            for row in rows
        ]

        return {
            "totalCost": float(total_cost),
            "totalTokens": int(total_tokens),
            "avgCostPerDay": float(total_cost / len(rows)),
            "trendData": trend_data,
        }


class CostOptimizationEngine:
    """Engine for cost analysis and optimization recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_cost_optimizations(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "30d",
    ) -> Dict[str, Any]:
        """Generate cost optimization recommendations."""
        start_date = calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        current_costs = await self._get_current_costs(agent_id, workspace_id, start_date, end_date)

        optimizations = []

        # Check for expensive model usage
        model_optimization = await self._analyze_model_selection(agent_id, workspace_id, start_date, end_date)
        if model_optimization:
            optimizations.append(model_optimization)

        # Check for compute inefficiencies
        compute_optimization = await self._analyze_compute_efficiency(agent_id, workspace_id, start_date, end_date)
        if compute_optimization:
            optimizations.append(compute_optimization)

        # Calculate potential savings
        total_savings = sum(opt.get("estimatedSavingsUsd", 0) for opt in optimizations)

        return {
            "currentMonthlyCost": current_costs.get("monthlyCost", 0),
            "potentialSavings": float(total_savings),
            "optimizationRecommendations": optimizations,
        }

    async def _get_current_costs(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get current cost metrics."""
        query = text("""
            SELECT
                SUM(total_cost_usd) as total_cost,
                COUNT(*) as days
            FROM analytics.daily_resource_utilization
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND usage_date BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date.date(), "end_date": end_date.date()},
        )
        row = result.fetchone()

        if not row or row.days == 0:
            return {"monthlyCost": 0}

        avg_daily_cost = row.total_cost / row.days
        monthly_cost = avg_daily_cost * 30

        return {"monthlyCost": float(monthly_cost)}

    async def _analyze_model_selection(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Analyze if cheaper models could be used."""
        query = text("""
            SELECT
                model_provider,
                model_name,
                SUM(token_cost_usd) as model_cost,
                COUNT(*) as usage_count
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
            GROUP BY model_provider, model_name
            ORDER BY model_cost DESC
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if not row or row.model_cost < 10:  # Only suggest if significant cost
            return None

        # Simple heuristic: suggest reviewing expensive model usage
        potential_savings = float(row.model_cost) * 0.3  # Assume 30% potential savings

        return {
            "type": "model_selection",
            "category": "tokens",
            "priority": "high",
            "title": "Optimize Model Selection",
            "description": f"Current primary model ({row.model_name}) accounts for ${row.model_cost:.2f} in costs. Consider using a cheaper model for simpler tasks.",
            "estimatedSavingsUsd": potential_savings,
            "implementationEffort": "medium",
        }

    async def _analyze_compute_efficiency(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Analyze compute resource efficiency."""
        query = text("""
            SELECT
                AVG(cpu_average_percent) as avg_cpu,
                AVG(memory_average_mb) as avg_memory,
                AVG(memory_allocation_mb) as avg_allocation
            FROM analytics.resource_utilization_metrics
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id,
             "start_date": start_date, "end_date": end_date},
        )
        row = result.fetchone()

        if not row:
            return None

        # Check for over-provisioned resources
        if row.avg_memory and row.avg_allocation:
            utilization = (row.avg_memory / row.avg_allocation) * 100
            if utilization < 50:  # Less than 50% memory utilization
                return {
                    "type": "right_sizing",
                    "category": "compute",
                    "priority": "medium",
                    "title": "Right-size Compute Resources",
                    "description": f"Average memory utilization is {utilization:.1f}%. Consider reducing allocated resources.",
                    "estimatedSavingsUsd": 5.0,  # Placeholder
                    "implementationEffort": "low",
                }

        return None


class ResourceWasteAnalyzer:
    """Analyzer for detecting and quantifying resource waste."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def identify_resource_waste(
        self,
        workspace_id: str,
        agent_id: Optional[str] = None,
        timeframe: str = "7d",
    ) -> Dict[str, Any]:
        """Identify resource waste across all categories."""
        start_date = calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        # Get waste events from database
        query = text("""
            SELECT
                waste_type,
                waste_category,
                SUM(waste_cost_usd) as total_waste_cost,
                COUNT(*) as event_count,
                COUNT(*) FILTER (WHERE is_resolved = false) as unresolved_count
            FROM analytics.resource_waste_events
            WHERE workspace_id = :workspace_id
                AND (:agent_id IS NULL OR agent_id = :agent_id)
                AND detected_at BETWEEN :start_date AND :end_date
            GROUP BY waste_type, waste_category
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        rows = result.fetchall()

        total_waste = sum(float(row.total_waste_cost) for row in rows)
        unresolved_count = sum(int(row.unresolved_count) for row in rows)

        waste_by_type = {}
        for row in rows:
            waste_by_type[row.waste_type] = float(row.total_waste_cost)

        # Calculate potential monthly savings (extrapolate from timeframe)
        days_in_period = (end_date - start_date).days or 1
        monthly_savings = (total_waste / days_in_period) * 30

        return {
            "totalWasteCostUsd": float(total_waste),
            "wasteByType": waste_by_type,
            "unresolvedCount": unresolved_count,
            "potentialMonthlySavings": float(monthly_savings),
        }


class ResourceDemandForecaster:
    """Forecaster for resource demand and cost projections."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def forecast_resource_usage(
        self,
        agent_id: str,
        workspace_id: str,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """Forecast future resource usage and costs."""
        # Get historical data for forecasting
        historical_data = await self._get_historical_data(agent_id, workspace_id, days=60)

        if len(historical_data) < 7:
            # Not enough data for forecasting
            return {
                "tokenUsage": None,
                "computeUsage": None,
                "projectedCosts": None,
                "budgetAlerts": ["Insufficient historical data for forecasting"],
            }

        # Simple linear trend forecast for tokens
        token_forecast = self._forecast_linear_trend(
            [row["tokens"] for row in historical_data],
            horizon_days
        )

        # Forecast compute usage
        compute_forecast = self._forecast_linear_trend(
            [row["cpu_seconds"] for row in historical_data],
            horizon_days
        )

        # Forecast costs
        cost_forecast = self._forecast_linear_trend(
            [row["cost"] for row in historical_data],
            horizon_days
        )

        # Check for budget alerts
        budget_alerts = []
        if cost_forecast.get("projected_value", 0) > 100:  # Example threshold
            budget_alerts.append("Projected costs may exceed budget")

        return {
            "tokenUsage": {
                "projectedValue": token_forecast.get("projected_value", 0),
                "lowerBound": token_forecast.get("lower_bound", 0),
                "upperBound": token_forecast.get("upper_bound", 0),
                "confidence": 0.80,
            },
            "computeUsage": {
                "projectedValue": compute_forecast.get("projected_value", 0),
                "lowerBound": compute_forecast.get("lower_bound", 0),
                "upperBound": compute_forecast.get("upper_bound", 0),
                "confidence": 0.75,
            },
            "projectedCosts": {
                "projectedMonthlyCost": cost_forecast.get("projected_value", 0),
                "lowerBound": cost_forecast.get("lower_bound", 0),
                "upperBound": cost_forecast.get("upper_bound", 0),
                "growthRate": cost_forecast.get("growth_rate", 0),
            },
            "budgetAlerts": budget_alerts,
        }

    async def _get_historical_data(
        self, agent_id: str, workspace_id: str, days: int = 60
    ) -> List[Dict[str, Any]]:
        """Get historical data for forecasting."""
        query = text("""
            SELECT
                usage_date,
                total_tokens as tokens,
                total_cpu_seconds as cpu_seconds,
                total_cost as cost
            FROM analytics.daily_resource_utilization
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND usage_date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY usage_date ASC
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id, "days": days},
        )
        rows = result.fetchall()

        return [
            {
                "date": row.usage_date,
                "tokens": int(row.tokens or 0),
                "cpu_seconds": float(row.cpu_seconds or 0),
                "cost": float(row.cost or 0),
            }
            for row in rows
        ]

    def _forecast_linear_trend(
        self, values: List[float], horizon_days: int
    ) -> Dict[str, Any]:
        """Simple linear trend forecast."""
        if len(values) < 2:
            return {"projected_value": 0, "lower_bound": 0, "upper_bound": 0, "growth_rate": 0}

        # Calculate linear trend
        x = np.arange(len(values))
        y = np.array(values, dtype=float)

        # Handle zeros and missing values
        y = np.nan_to_num(y, nan=0.0)

        # Simple linear regression
        if np.std(x) > 0:
            slope = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 0
        else:
            slope = 0
        intercept = np.mean(y) - slope * np.mean(x)

        # Project forward
        future_x = len(values) + horizon_days - 1
        projected_value = slope * future_x + intercept
        projected_value = max(0, projected_value)  # Ensure non-negative

        # Calculate confidence bounds (simple ±20%)
        lower_bound = projected_value * 0.8
        upper_bound = projected_value * 1.2

        # Calculate growth rate
        avg_value = np.mean(y) if len(y) > 0 else 1
        growth_rate = (slope / avg_value * 100) if avg_value > 0 else 0

        return {
            "projected_value": float(projected_value),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "growth_rate": float(growth_rate),
        }


class ResourceAnalyticsService:
    """Comprehensive resource analytics service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_analyzer = TokenEfficiencyAnalyzer(db)
        self.cost_optimizer = CostOptimizationEngine(db)
        self.waste_analyzer = ResourceWasteAnalyzer(db)
        self.forecaster = ResourceDemandForecaster(db)

    async def get_comprehensive_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "7d",
    ) -> Dict[str, Any]:
        """Get comprehensive resource analytics including all components."""
        results = await asyncio.gather(
            self.token_analyzer.analyze_token_usage(agent_id, workspace_id, timeframe),
            self.cost_optimizer.analyze_cost_optimizations(agent_id, workspace_id, timeframe),
            self.waste_analyzer.identify_resource_waste(workspace_id, agent_id, timeframe),
            self.forecaster.forecast_resource_usage(agent_id, workspace_id),
            return_exceptions=True,
        )

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "tokenAnalysis": results[0] if not isinstance(results[0], Exception) else {},
            "costOptimization": results[1] if not isinstance(results[1], Exception) else {},
            "wasteDetection": results[2] if not isinstance(results[2], Exception) else {},
            "forecasts": results[3] if not isinstance(results[3], Exception) else {},
        }
