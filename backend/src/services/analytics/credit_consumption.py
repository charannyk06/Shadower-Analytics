"""Credit consumption tracking and analytics service."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np

logger = logging.getLogger(__name__)


class CreditConsumptionService:
    """Service for comprehensive credit consumption analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_credit_consumption(
        self,
        workspace_id: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Get comprehensive credit consumption analytics.

        Args:
            workspace_id: Workspace ID to analyze
            timeframe: Time window (7d, 30d, 90d, 1y)

        Returns:
            Complete credit consumption analytics data
        """
        try:
            end_date = datetime.utcnow()
            start_date = self._calculate_start_date(timeframe)

            # Fetch all data in parallel
            results = await asyncio.gather(
                self._get_current_status(workspace_id),
                self._get_consumption_breakdown(workspace_id, start_date, end_date),
                self._get_consumption_trends(workspace_id, start_date, end_date),
                self._get_budget_status(workspace_id),
                self._get_cost_analysis(workspace_id, start_date, end_date),
                self._get_optimization_recommendations(workspace_id),
                self._forecast_usage(workspace_id)
            )

            return {
                "workspaceId": workspace_id,
                "timeframe": timeframe,
                "currentStatus": results[0],
                "breakdown": results[1],
                "trends": results[2],
                "budget": results[3],
                "costAnalysis": results[4],
                "optimizations": results[5],
                "forecast": results[6]
            }
        except Exception as e:
            logger.error(f"Error getting credit consumption: {e}", exc_info=True)
            raise

    async def _get_current_status(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get current credit status and projections."""
        query = text("""
            WITH credit_data AS (
                SELECT
                    COALESCE(wc.allocated_credits, 0) as allocated_credits,
                    COALESCE(wc.consumed_credits, 0) as consumed_credits,
                    wc.period_start,
                    wc.period_end,
                    COALESCE(wc.allocated_credits, 0) - COALESCE(wc.consumed_credits, 0) as remaining_credits
                FROM public.workspace_credits wc
                WHERE wc.workspace_id = :workspace_id
            ),
            burn_rate AS (
                SELECT
                    DATE(consumed_at) as date,
                    SUM(credits_consumed) as daily_credits
                FROM analytics.credit_consumption
                WHERE workspace_id = :workspace_id
                    AND consumed_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(consumed_at)
            )
            SELECT
                cd.*,
                COALESCE(AVG(br.daily_credits), 0) as avg_daily_burn,
                COALESCE(AVG(br.daily_credits), 0) * 7 as avg_weekly_burn,
                COALESCE(AVG(br.daily_credits), 0) * 30 as avg_monthly_burn
            FROM credit_data cd
            LEFT JOIN burn_rate br ON true
            GROUP BY cd.allocated_credits, cd.consumed_credits,
                     cd.period_start, cd.period_end, cd.remaining_credits
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        row = result.fetchone()

        if not row:
            # Return default values if no credit data exists
            return {
                "allocatedCredits": 0,
                "consumedCredits": 0,
                "remainingCredits": 0,
                "utilizationRate": 0,
                "periodStart": datetime.utcnow().isoformat(),
                "periodEnd": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "daysRemaining": 30,
                "dailyBurnRate": 0,
                "weeklyBurnRate": 0,
                "monthlyBurnRate": 0,
                "projectedExhaustion": None,
                "projectedMonthlyUsage": 0,
                "recommendedTopUp": None
            }

        # Calculate projections
        days_remaining = (row.period_end - datetime.utcnow()).days if row.period_end else 30
        projected_exhaustion = None
        recommended_top_up = None

        if row.avg_daily_burn > 0 and row.remaining_credits > 0:
            days_until_exhaustion = row.remaining_credits / row.avg_daily_burn

            if days_until_exhaustion < days_remaining:
                projected_exhaustion = (
                    datetime.utcnow() + timedelta(days=days_until_exhaustion)
                ).isoformat()

                recommended_top_up = (
                    row.avg_daily_burn * days_remaining -
                    row.remaining_credits
                )

        utilization_rate = 0
        if row.allocated_credits > 0:
            utilization_rate = (row.consumed_credits / row.allocated_credits * 100)

        return {
            "allocatedCredits": float(row.allocated_credits),
            "consumedCredits": float(row.consumed_credits),
            "remainingCredits": float(row.remaining_credits),
            "utilizationRate": round(utilization_rate, 2),
            "periodStart": row.period_start.isoformat() if row.period_start else datetime.utcnow().isoformat(),
            "periodEnd": row.period_end.isoformat() if row.period_end else (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "daysRemaining": max(0, days_remaining),
            "dailyBurnRate": round(float(row.avg_daily_burn or 0), 2),
            "weeklyBurnRate": round(float(row.avg_weekly_burn or 0), 2),
            "monthlyBurnRate": round(float(row.avg_monthly_burn or 0), 2),
            "projectedExhaustion": projected_exhaustion,
            "projectedMonthlyUsage": round(float(row.avg_monthly_burn or 0), 2),
            "recommendedTopUp": round(recommended_top_up, 2) if recommended_top_up and recommended_top_up > 0 else None
        }

    async def _get_consumption_breakdown(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get consumption breakdown by model, agent, user, and feature."""
        # Get breakdown by model
        model_query = text("""
            SELECT
                model,
                provider,
                SUM(credits_consumed) as credits,
                SUM(COALESCE(tokens_used, 0)) as tokens,
                COUNT(*) as calls,
                AVG(credits_consumed) as avg_credits_per_call
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= :start_date
                AND consumed_at <= :end_date
            GROUP BY model, provider
            ORDER BY credits DESC
        """)

        model_result = await self.db.execute(
            model_query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        models = model_result.fetchall()

        total_credits = sum(float(m.credits) for m in models)

        by_model = []
        for model in models:
            percentage = (float(model.credits) / total_credits * 100) if total_credits > 0 else 0
            by_model.append({
                "model": model.model,
                "provider": model.provider,
                "credits": round(float(model.credits), 2),
                "percentage": round(percentage, 2),
                "tokens": int(model.tokens),
                "calls": int(model.calls),
                "avgCreditsPerCall": round(float(model.avg_credits_per_call), 2),
                "trend": "stable"  # TODO: Calculate actual trend
            })

        # Get breakdown by agent
        agent_query = text("""
            SELECT
                cc.agent_id,
                COUNT(DISTINCT cc.run_id) as runs,
                SUM(cc.credits_consumed) as credits,
                AVG(cc.credits_consumed) as avg_credits_per_run
            FROM analytics.credit_consumption cc
            WHERE cc.workspace_id = :workspace_id
                AND cc.consumed_at >= :start_date
                AND cc.consumed_at <= :end_date
                AND cc.agent_id IS NOT NULL
            GROUP BY cc.agent_id
            ORDER BY credits DESC
            LIMIT 20
        """)

        agent_result = await self.db.execute(
            agent_query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        agents = agent_result.fetchall()

        by_agent = []
        for agent in agents:
            percentage = (float(agent.credits) / total_credits * 100) if total_credits > 0 else 0
            by_agent.append({
                "agentId": str(agent.agent_id),
                "agentName": f"Agent {str(agent.agent_id)[:8]}",  # TODO: Get actual agent name
                "credits": round(float(agent.credits), 2),
                "percentage": round(percentage, 2),
                "runs": int(agent.runs),
                "avgCreditsPerRun": round(float(agent.avg_credits_per_run), 2),
                "efficiency": round(float(agent.avg_credits_per_run), 2)
            })

        # Get breakdown by user
        user_query = text("""
            SELECT
                cc.user_id,
                COUNT(DISTINCT cc.run_id) as executions,
                SUM(cc.credits_consumed) as credits,
                AVG(cc.credits_consumed) as avg_credits_per_execution
            FROM analytics.credit_consumption cc
            WHERE cc.workspace_id = :workspace_id
                AND cc.consumed_at >= :start_date
                AND cc.consumed_at <= :end_date
                AND cc.user_id IS NOT NULL
            GROUP BY cc.user_id
            ORDER BY credits DESC
            LIMIT 20
        """)

        user_result = await self.db.execute(
            user_query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        users = user_result.fetchall()

        by_user = []
        for user in users:
            percentage = (float(user.credits) / total_credits * 100) if total_credits > 0 else 0
            by_user.append({
                "userId": str(user.user_id),
                "userName": f"User {str(user.user_id)[:8]}",  # TODO: Get actual user name
                "credits": round(float(user.credits), 2),
                "percentage": round(percentage, 2),
                "executions": int(user.executions),
                "avgCreditsPerExecution": round(float(user.avg_credits_per_execution), 2)
            })

        return {
            "byModel": by_model,
            "byAgent": by_agent,
            "byUser": by_user,
            "byFeature": []  # TODO: Implement feature tracking
        }

    async def _get_consumption_trends(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get consumption trends over time."""
        # Daily consumption
        daily_query = text("""
            SELECT
                date,
                total_credits as credits,
                SUM(total_credits) OVER (ORDER BY date) as cumulative,
                model_breakdown
            FROM analytics.credit_consumption_daily
            WHERE workspace_id = :workspace_id
                AND date >= :start_date
                AND date <= :end_date
            ORDER BY date ASC
        """)

        daily_result = await self.db.execute(
            daily_query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date.date(),
                "end_date": end_date.date()
            }
        )
        daily_data = daily_result.fetchall()

        daily = []
        for row in daily_data:
            breakdown = {}
            if row.model_breakdown:
                for model, data in row.model_breakdown.items():
                    if isinstance(data, dict):
                        breakdown[model] = float(data.get('credits', 0))

            daily.append({
                "date": row.date.isoformat(),
                "credits": round(float(row.credits), 2),
                "cumulative": round(float(row.cumulative), 2),
                "breakdown": breakdown
            })

        # Hourly pattern (average by hour of day)
        hourly_query = text("""
            SELECT
                EXTRACT(HOUR FROM consumed_at) as hour,
                AVG(credits_consumed) as avg_credits,
                DATE(MAX(consumed_at)) as peak_day
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= :start_date
                AND consumed_at <= :end_date
            GROUP BY EXTRACT(HOUR FROM consumed_at)
            ORDER BY hour
        """)

        hourly_result = await self.db.execute(
            hourly_query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        hourly_data = hourly_result.fetchall()

        hourly_pattern = [
            {
                "hour": int(row.hour),
                "avgCredits": round(float(row.avg_credits), 2),
                "peakDay": row.peak_day.isoformat()
            }
            for row in hourly_data
        ]

        # Weekly pattern
        weekly_query = text("""
            SELECT
                TO_CHAR(consumed_at, 'Day') as day_of_week,
                AVG(credits_consumed) as avg_credits
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= :start_date
                AND consumed_at <= :end_date
            GROUP BY TO_CHAR(consumed_at, 'Day'), EXTRACT(DOW FROM consumed_at)
            ORDER BY EXTRACT(DOW FROM consumed_at)
        """)

        weekly_result = await self.db.execute(
            weekly_query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        weekly_data = weekly_result.fetchall()

        weekly_pattern = [
            {
                "dayOfWeek": row.day_of_week.strip(),
                "avgCredits": round(float(row.avg_credits), 2)
            }
            for row in weekly_data
        ]

        # Calculate growth rates
        growth_rate = {
            "daily": 0,
            "weekly": 0,
            "monthly": 0
        }

        if len(daily) >= 2:
            recent_avg = np.mean([d['credits'] for d in daily[-7:]])
            previous_avg = np.mean([d['credits'] for d in daily[-14:-7]]) if len(daily) >= 14 else recent_avg
            if previous_avg > 0:
                growth_rate["daily"] = round(((recent_avg - previous_avg) / previous_avg * 100), 2)

        return {
            "daily": daily,
            "hourlyPattern": hourly_pattern,
            "weeklyPattern": weekly_pattern,
            "growthRate": growth_rate
        }

    async def _get_budget_status(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get budget status and alerts."""
        query = text("""
            SELECT
                monthly_budget,
                weekly_budget,
                daily_limit,
                consumed_credits,
                allocated_credits
            FROM public.workspace_credits
            WHERE workspace_id = :workspace_id
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        row = result.fetchone()

        if not row:
            return {
                "monthlyBudget": None,
                "weeklyBudget": None,
                "dailyLimit": None,
                "budgetUtilization": 0,
                "budgetRemaining": 0,
                "isOverBudget": False,
                "projectedOverage": None,
                "alerts": [],
                "agentLimits": []
            }

        budget = row.monthly_budget or row.allocated_credits
        budget_utilization = 0
        budget_remaining = 0
        is_over_budget = False

        if budget and budget > 0:
            budget_utilization = (row.consumed_credits / budget * 100)
            budget_remaining = budget - row.consumed_credits
            is_over_budget = row.consumed_credits > budget

        # Get active alerts
        alerts_query = text("""
            SELECT
                alert_type,
                threshold,
                current_value,
                message,
                triggered_at
            FROM analytics.credit_budget_alerts
            WHERE workspace_id = :workspace_id
                AND is_acknowledged = false
            ORDER BY triggered_at DESC
            LIMIT 10
        """)

        alerts_result = await self.db.execute(alerts_query, {"workspace_id": workspace_id})
        alert_rows = alerts_result.fetchall()

        alerts = [
            {
                "type": row.alert_type,
                "threshold": float(row.threshold),
                "currentValue": float(row.current_value),
                "message": row.message,
                "triggeredAt": row.triggered_at.isoformat()
            }
            for row in alert_rows
        ]

        return {
            "monthlyBudget": float(row.monthly_budget) if row.monthly_budget else None,
            "weeklyBudget": float(row.weekly_budget) if row.weekly_budget else None,
            "dailyLimit": float(row.daily_limit) if row.daily_limit else None,
            "budgetUtilization": round(budget_utilization, 2),
            "budgetRemaining": round(float(budget_remaining), 2),
            "isOverBudget": is_over_budget,
            "projectedOverage": None,  # TODO: Calculate based on trends
            "alerts": alerts,
            "agentLimits": []  # TODO: Implement agent limits
        }

    async def _get_cost_analysis(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get cost analysis and efficiency metrics."""
        # Assuming $0.001 per credit as base cost
        COST_PER_CREDIT = 0.001

        query = text("""
            SELECT
                SUM(credits_consumed) as total_credits,
                COUNT(*) as total_calls
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= :start_date
                AND consumed_at <= :end_date
        """)

        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id, "start_date": start_date, "end_date": end_date}
        )
        row = result.fetchone()

        total_credits = float(row.total_credits or 0)
        total_calls = int(row.total_calls or 0)
        total_cost = total_credits * COST_PER_CREDIT

        days_diff = (end_date - start_date).days or 1
        avg_cost_per_day = total_cost / days_diff
        avg_cost_per_run = total_cost / total_calls if total_calls > 0 else 0

        return {
            "totalCost": round(total_cost, 2),
            "avgCostPerDay": round(avg_cost_per_day, 2),
            "avgCostPerRun": round(avg_cost_per_run, 4),
            "avgCostPerUser": 0,  # TODO: Calculate
            "successCost": 0,  # TODO: Calculate from run status
            "failureCost": 0,
            "wastedCredits": 0,
            "efficiencyRate": 100,  # TODO: Calculate actual efficiency
            "modelComparison": []  # TODO: Implement model cost comparison
        }

    async def _get_optimization_recommendations(
        self,
        workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Generate credit optimization recommendations."""
        recommendations = []

        # Check for potential model optimization
        model_query = text("""
            SELECT
                model,
                provider,
                SUM(credits_consumed) as total_credits,
                COUNT(*) as call_count,
                AVG(credits_consumed) as avg_credits
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= NOW() - INTERVAL '30 days'
            GROUP BY model, provider
            HAVING SUM(credits_consumed) > 1000
            ORDER BY total_credits DESC
        """)

        result = await self.db.execute(model_query, {"workspace_id": workspace_id})
        models = result.fetchall()

        for model in models:
            # Suggest optimization if using expensive models heavily
            if 'gpt-4' in model.model.lower():
                savings = float(model.total_credits) * 0.5  # Potential 50% savings
                recommendations.append({
                    "type": "model_switch",
                    "title": f"Consider switching from {model.model} to GPT-3.5 for simple tasks",
                    "description": f"You're using {model.model} heavily. For simpler tasks, GPT-3.5 Turbo could provide similar results at 50% lower cost.",
                    "currentCost": round(float(model.total_credits) * 0.001, 2),
                    "projectedCost": round(float(model.total_credits) * 0.001 * 0.5, 2),
                    "potentialSavings": round(savings * 0.001, 2),
                    "savingsPercentage": 50,
                    "implementation": "Review agent configurations and identify tasks suitable for lighter models",
                    "effort": "low"
                })

        # Check for caching opportunities
        repeat_query = text("""
            SELECT
                COUNT(*) as total_calls,
                COUNT(*) FILTER (WHERE metadata->>'is_similar' = 'true') as similar_calls
            FROM analytics.credit_consumption
            WHERE workspace_id = :workspace_id
                AND consumed_at >= NOW() - INTERVAL '7 days'
        """)

        result = await self.db.execute(repeat_query, {"workspace_id": workspace_id})
        row = result.fetchone()

        if row and row.total_calls > 100:
            repeat_rate = (row.similar_calls or 0) / row.total_calls
            if repeat_rate > 0.1:  # More than 10% similar calls
                recommendations.append({
                    "type": "caching",
                    "title": "Implement response caching for repeated queries",
                    "description": f"About {repeat_rate*100:.1f}% of queries could benefit from caching. This can reduce both costs and response times.",
                    "currentCost": 0,
                    "projectedCost": 0,
                    "potentialSavings": 0,
                    "savingsPercentage": 90,
                    "implementation": "Add Redis caching layer with appropriate TTL for common queries",
                    "effort": "medium"
                })

        return recommendations

    async def _forecast_usage(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Forecast future credit usage using time series analysis."""
        # Get historical data
        query = text("""
            SELECT
                date,
                total_credits as credits
            FROM analytics.credit_consumption_daily
            WHERE workspace_id = :workspace_id
                AND date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY date ASC
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        history = result.fetchall()

        if len(history) < 7:  # Need at least a week of data
            return self._default_forecast()

        # Simple moving average forecast
        credits = [float(row.credits) for row in history]
        recent_avg = np.mean(credits[-7:])  # Last 7 days average
        weekly_avg = np.mean(credits[-7:]) if len(credits) >= 7 else recent_avg
        monthly_avg = np.mean(credits[-30:]) if len(credits) >= 30 else recent_avg

        # Calculate standard deviation for confidence intervals
        std_dev = np.std(credits[-30:]) if len(credits) >= 30 else 0

        next_month_forecast = recent_avg * 30

        return {
            "nextDay": round(recent_avg, 2),
            "nextWeek": round(recent_avg * 7, 2),
            "nextMonth": round(next_month_forecast, 2),
            "confidence": {
                "low": round(max(0, next_month_forecast - 1.96 * std_dev * 30), 2),
                "high": round(next_month_forecast + 1.96 * std_dev * 30, 2)
            },
            "seasonalFactors": {
                "weekday": round(weekly_avg, 2),
                "weekend": round(weekly_avg * 0.8, 2),  # Assuming 20% less on weekends
                "monthEnd": round(monthly_avg, 2)
            },
            "projectedGrowth": [
                {
                    "period": f"Month {i+1}",
                    "credits": round(next_month_forecast * (1 + 0.05 * i), 2),
                    "cost": round(next_month_forecast * (1 + 0.05 * i) * 0.001, 2)
                }
                for i in range(3)
            ]
        }

    def _default_forecast(self) -> Dict[str, Any]:
        """Return default forecast when insufficient data."""
        return {
            "nextDay": 0,
            "nextWeek": 0,
            "nextMonth": 0,
            "confidence": {"low": 0, "high": 0},
            "seasonalFactors": {"weekday": 0, "weekend": 0, "monthEnd": 0},
            "projectedGrowth": []
        }

    def _calculate_start_date(self, timeframe: str) -> datetime:
        """Calculate start date based on timeframe."""
        now = datetime.utcnow()
        if timeframe == "7d":
            return now - timedelta(days=7)
        elif timeframe == "30d":
            return now - timedelta(days=30)
        elif timeframe == "90d":
            return now - timedelta(days=90)
        elif timeframe == "1y":
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)
