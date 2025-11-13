"""
Business Impact Calculator

Calculates comprehensive business impact for errors including
financial, operational, user, and reputation impacts.

Author: Claude Code
Date: 2025-11-13
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BusinessImpactCalculator:
    """
    Calculates multi-dimensional business impact of errors:
    - Financial impact (revenue loss, costs, refunds)
    - Operational impact (downtime, manual work, SLA violations)
    - User impact (satisfaction, churn risk, support tickets)
    - Reputation impact (severity, visibility, recovery expectations)
    """

    # Configuration constants
    CREDIT_TO_REVENUE_RATIO = 0.01  # $1 per 100 credits
    MANUAL_HOUR_COST = 75.0  # Cost per hour of manual intervention
    SUPPORT_TICKET_COST = 25.0  # Average cost per support ticket

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_error_impact(
        self,
        error_id: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive business impact for an error.

        Args:
            error_id: Error identifier

        Returns:
            Complete business impact analysis
        """
        try:
            logger.info(f"Calculating business impact for error {error_id}")

            # Fetch error details with all related data
            error_data = await self._get_error_with_context(error_id)

            if not error_data:
                return {"error": "Error not found", "error_id": error_id}

            # Get affected executions
            affected_executions = await self._get_affected_executions(error_id)

            # Calculate each impact dimension
            financial_impact = self._calculate_financial_impact(error_data, affected_executions)
            operational_impact = await self._calculate_operational_impact(error_data, affected_executions)
            user_impact = self._calculate_user_impact(error_data, affected_executions)
            reputation_impact = self._calculate_reputation_impact(error_data, affected_executions)

            # Sum total financial impact
            financial_impact["total_financial_impact"] = (
                financial_impact["lost_revenue"] +
                financial_impact["additional_costs"] +
                financial_impact["credit_refunds"]
            )

            impact = {
                "error_id": error_id,
                "workspace_id": error_data["workspace_id"],
                "error_type": error_data["error_type"],
                "financial_impact": financial_impact,
                "operational_impact": operational_impact,
                "user_impact": user_impact,
                "reputation_impact": reputation_impact,
                "overall_severity": self._determine_overall_severity(
                    financial_impact,
                    operational_impact,
                    user_impact,
                    reputation_impact
                ),
                "calculated_at": datetime.utcnow().isoformat(),
                "calculation_version": "v1.0.0"
            }

            # Store impact calculation
            await self._store_impact_calculation(error_id, impact)

            return impact

        except Exception as e:
            logger.error(f"Error calculating business impact: {e}", exc_info=True)
            raise

    def _calculate_financial_impact(
        self,
        error_data: Dict[str, Any],
        affected_executions: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate financial impact."""
        credits_lost = float(error_data.get("credits_lost", 0))

        # Calculate lost revenue (credits that failed)
        lost_revenue = credits_lost * self.CREDIT_TO_REVENUE_RATIO

        # Calculate additional costs (support, investigation, etc.)
        # Base cost on severity and number of affected users
        severity_multiplier = {
            "critical": 5.0,
            "high": 3.0,
            "medium": 1.5,
            "low": 0.5
        }
        severity = error_data.get("severity", "medium")
        users_affected = len(error_data.get("users_affected", []))

        # Additional costs = base investigation cost + per-user support cost
        investigation_cost = 100 * severity_multiplier.get(severity, 1.0)
        support_cost = min(users_affected * self.SUPPORT_TICKET_COST, 1000)  # Cap at $1000
        additional_costs = investigation_cost + support_cost

        # Calculate credit refunds (estimated based on severity and user impact)
        refund_rate = {
            "critical": 1.0,  # 100% refund
            "high": 0.5,      # 50% refund
            "medium": 0.25,   # 25% refund
            "low": 0.0        # No refund
        }
        credit_refunds = credits_lost * self.CREDIT_TO_REVENUE_RATIO * refund_rate.get(severity, 0.0)

        return {
            "lost_revenue": round(lost_revenue, 2),
            "additional_costs": round(additional_costs, 2),
            "credit_refunds": round(credit_refunds, 2),
            "total_financial_impact": 0.0  # Will be calculated by caller
        }

    async def _calculate_operational_impact(
        self,
        error_data: Dict[str, Any],
        affected_executions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate operational impact."""
        # Calculate downtime
        first_seen = error_data.get("first_seen")
        resolved_at = error_data.get("resolved_at")

        if resolved_at and first_seen:
            downtime_minutes = int((resolved_at - first_seen).total_seconds() / 60)
        else:
            # If not resolved, use time since first seen
            downtime_minutes = int((datetime.utcnow() - first_seen).total_seconds() / 60)

        # Get affected workflows (unique agents)
        affected_workflows = error_data.get("agents_affected", [])

        # Estimate manual intervention hours based on severity
        severity = error_data.get("severity", "medium")
        manual_hours_estimate = {
            "critical": 4.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5
        }
        manual_intervention_hours = manual_hours_estimate.get(severity, 1.0)

        # Check for SLA violations
        sla_violations = await self._check_sla_violations(error_data)

        return {
            "downtime_minutes": downtime_minutes,
            "affected_workflows": affected_workflows,
            "manual_intervention_hours": manual_intervention_hours,
            "sla_violations": sla_violations
        }

    def _calculate_user_impact(
        self,
        error_data: Dict[str, Any],
        affected_executions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate user impact."""
        users_affected = error_data.get("users_affected", [])
        affected_users_count = len(users_affected)

        # Calculate user satisfaction impact (negative score)
        # More users affected = greater impact
        satisfaction_impact_per_user = -0.1
        user_satisfaction_impact = satisfaction_impact_per_user * min(affected_users_count, 100)

        # Calculate churn risk based on severity and occurrence count
        severity = error_data.get("severity", "medium")
        occurrence_count = error_data.get("occurrence_count", 1)

        base_churn_risk = {
            "critical": 0.30,
            "high": 0.15,
            "medium": 0.05,
            "low": 0.01
        }

        # Increase churn risk for recurring errors
        churn_risk = base_churn_risk.get(severity, 0.05)
        if occurrence_count > 10:
            churn_risk *= 1.5
        if occurrence_count > 50:
            churn_risk *= 2.0

        churn_risk = min(churn_risk, 0.95)  # Cap at 95%

        # Estimate support tickets
        # Not all affected users create tickets
        ticket_rate = {
            "critical": 0.8,
            "high": 0.5,
            "medium": 0.3,
            "low": 0.1
        }
        support_tickets_generated = int(
            affected_users_count * ticket_rate.get(severity, 0.3)
        )

        return {
            "affected_users": affected_users_count,
            "user_satisfaction_impact": round(user_satisfaction_impact, 2),
            "churn_risk": round(churn_risk, 3),
            "support_tickets_generated": support_tickets_generated
        }

    def _calculate_reputation_impact(
        self,
        error_data: Dict[str, Any],
        affected_executions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate reputation impact."""
        severity = error_data.get("severity", "medium")
        occurrence_count = error_data.get("occurrence_count", 1)
        users_affected = len(error_data.get("users_affected", []))

        # Calculate reputation severity score (0-100)
        severity_scores = {
            "critical": 100,
            "high": 70,
            "medium": 40,
            "low": 10
        }
        base_score = severity_scores.get(severity, 40)

        # Adjust for widespread impact
        if users_affected > 100:
            base_score *= 1.5
        elif users_affected > 50:
            base_score *= 1.25

        # Adjust for recurring issues
        if occurrence_count > 50:
            base_score *= 1.3

        reputation_severity_score = min(base_score, 100)

        # Determine public visibility risk
        public_visibility = (
            severity in ["critical", "high"] and
            users_affected > 20
        )

        # Estimate recovery time expectation (minutes)
        recovery_expectations = {
            "critical": 30,
            "high": 120,
            "medium": 480,
            "low": 1440
        }
        recovery_time_expectation = recovery_expectations.get(severity, 480)

        return {
            "severity_score": round(reputation_severity_score, 2),
            "public_visibility": public_visibility,
            "recovery_time_expectation": recovery_time_expectation
        }

    def _determine_overall_severity(
        self,
        financial: Dict[str, Any],
        operational: Dict[str, Any],
        user: Dict[str, Any],
        reputation: Dict[str, Any]
    ) -> str:
        """Determine overall severity based on all impact dimensions."""
        # Critical if any of these conditions are met
        if (financial["total_financial_impact"] > 1000 or
            operational["downtime_minutes"] > 120 or
            user["affected_users"] > 100 or
            reputation["public_visibility"]):
            return "critical"

        # High if any of these conditions are met
        if (financial["total_financial_impact"] > 500 or
            operational["downtime_minutes"] > 60 or
            user["affected_users"] > 50 or
            user["churn_risk"] > 0.2):
            return "high"

        # Medium if any of these conditions are met
        if (financial["total_financial_impact"] > 100 or
            operational["downtime_minutes"] > 30 or
            user["affected_users"] > 10):
            return "medium"

        return "low"

    async def _get_error_with_context(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Fetch error with complete context."""
        query = text("""
            SELECT * FROM analytics.errors WHERE error_id = :error_id
        """)

        result = await self.db.execute(query, {"error_id": error_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "error_id": str(row.error_id),
            "workspace_id": str(row.workspace_id),
            "error_type": row.error_type,
            "severity": row.severity,
            "first_seen": row.first_seen,
            "last_seen": row.last_seen,
            "resolved_at": row.resolved_at,
            "occurrence_count": row.occurrence_count,
            "users_affected": row.users_affected or [],
            "agents_affected": row.agents_affected or [],
            "credits_lost": float(row.credits_lost or 0),
            "executions_affected": row.executions_affected or 0
        }

    async def _get_affected_executions(self, error_id: str) -> Dict[str, Any]:
        """Get statistics about affected executions."""
        query = text("""
            SELECT
                COUNT(*) as total_executions,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT agent_id) as unique_agents
            FROM analytics.error_occurrences
            WHERE error_id = :error_id
        """)

        result = await self.db.execute(query, {"error_id": error_id})
        row = result.fetchone()

        if not row:
            return {
                "total_executions": 0,
                "unique_users": 0,
                "unique_agents": 0
            }

        return {
            "total_executions": row.total_executions,
            "unique_users": row.unique_users,
            "unique_agents": row.unique_agents
        }

    async def _check_sla_violations(self, error_data: Dict[str, Any]) -> int:
        """Check for SLA violations based on error severity and duration."""
        severity = error_data.get("severity")
        first_seen = error_data.get("first_seen")
        resolved_at = error_data.get("resolved_at")

        # SLA targets (in minutes)
        sla_targets = {
            "critical": 30,
            "high": 120,
            "medium": 480,
            "low": 1440
        }

        target_minutes = sla_targets.get(severity, 480)

        if resolved_at and first_seen:
            actual_minutes = (resolved_at - first_seen).total_seconds() / 60
        else:
            actual_minutes = (datetime.utcnow() - first_seen).total_seconds() / 60

        # Count as violation if exceeded SLA
        return 1 if actual_minutes > target_minutes else 0

    async def _store_impact_calculation(
        self,
        error_id: str,
        impact: Dict[str, Any]
    ) -> None:
        """Store business impact calculation in database."""
        try:
            query = text("""
                INSERT INTO analytics.error_business_impact (
                    error_id,
                    workspace_id,
                    lost_revenue,
                    additional_costs,
                    credit_refunds,
                    total_financial_impact,
                    downtime_minutes,
                    affected_workflows,
                    manual_intervention_hours,
                    sla_violations,
                    affected_users_count,
                    user_satisfaction_impact,
                    churn_risk,
                    support_tickets_generated,
                    reputation_severity_score,
                    public_visibility,
                    recovery_time_expectation_minutes,
                    calculation_version
                ) VALUES (
                    :error_id,
                    :workspace_id,
                    :lost_revenue,
                    :additional_costs,
                    :credit_refunds,
                    :total_financial_impact,
                    :downtime_minutes,
                    :affected_workflows,
                    :manual_intervention_hours,
                    :sla_violations,
                    :affected_users_count,
                    :user_satisfaction_impact,
                    :churn_risk,
                    :support_tickets_generated,
                    :reputation_severity_score,
                    :public_visibility,
                    :recovery_time_expectation_minutes,
                    :calculation_version
                )
                ON CONFLICT (error_id) DO UPDATE SET
                    lost_revenue = EXCLUDED.lost_revenue,
                    additional_costs = EXCLUDED.additional_costs,
                    credit_refunds = EXCLUDED.credit_refunds,
                    total_financial_impact = EXCLUDED.total_financial_impact,
                    downtime_minutes = EXCLUDED.downtime_minutes,
                    affected_workflows = EXCLUDED.affected_workflows,
                    manual_intervention_hours = EXCLUDED.manual_intervention_hours,
                    sla_violations = EXCLUDED.sla_violations,
                    affected_users_count = EXCLUDED.affected_users_count,
                    user_satisfaction_impact = EXCLUDED.user_satisfaction_impact,
                    churn_risk = EXCLUDED.churn_risk,
                    support_tickets_generated = EXCLUDED.support_tickets_generated,
                    reputation_severity_score = EXCLUDED.reputation_severity_score,
                    public_visibility = EXCLUDED.public_visibility,
                    recovery_time_expectation_minutes = EXCLUDED.recovery_time_expectation_minutes,
                    calculated_at = NOW(),
                    updated_at = NOW()
            """)

            financial = impact["financial_impact"]
            operational = impact["operational_impact"]
            user = impact["user_impact"]
            reputation = impact["reputation_impact"]

            await self.db.execute(
                query,
                {
                    "error_id": error_id,
                    "workspace_id": impact["workspace_id"],
                    "lost_revenue": financial["lost_revenue"],
                    "additional_costs": financial["additional_costs"],
                    "credit_refunds": financial["credit_refunds"],
                    "total_financial_impact": financial["total_financial_impact"],
                    "downtime_minutes": operational["downtime_minutes"],
                    "affected_workflows": operational["affected_workflows"],
                    "manual_intervention_hours": operational["manual_intervention_hours"],
                    "sla_violations": operational["sla_violations"],
                    "affected_users_count": user["affected_users"],
                    "user_satisfaction_impact": user["user_satisfaction_impact"],
                    "churn_risk": user["churn_risk"],
                    "support_tickets_generated": user["support_tickets_generated"],
                    "reputation_severity_score": reputation["severity_score"],
                    "public_visibility": reputation["public_visibility"],
                    "recovery_time_expectation_minutes": reputation["recovery_time_expectation"],
                    "calculation_version": impact["calculation_version"]
                }
            )

            await self.db.commit()
            logger.info(f"Stored business impact calculation for error {error_id}")

        except Exception as e:
            logger.error(f"Error storing business impact: {e}", exc_info=True)
            await self.db.rollback()
