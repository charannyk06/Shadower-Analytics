"""Alert engine API routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from uuid import UUID
import logging

from ...core.database import get_db
from ...services.alerts import AlertEngine
from ...models.database.tables import (
    AlertRule,
    Alert,
    EscalationPolicy,
    AlertSuppression,
    NotificationHistory
)
from ...models.schemas.alerts import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertResponse,
    AlertAcknowledge,
    AlertResolve,
    EscalationPolicyCreate,
    EscalationPolicyUpdate,
    EscalationPolicyResponse,
    AlertSuppressionCreate,
    AlertSuppressionResponse,
    AlertQueryParams,
    AlertHistoryQueryParams,
    AlertStats,
    AlertRuleTest,
    AlertRuleTestResult
)
from ..dependencies.auth import get_current_user
from ..middleware.workspace import WorkspaceAccess
from ..middleware.rate_limit import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Rate limiters
alert_rules_limiter = RateLimiter(requests_per_minute=10, requests_per_hour=200)
alert_query_limiter = RateLimiter(requests_per_minute=30, requests_per_hour=500)


# ============================================================================
# Alert Rules Endpoints
# ============================================================================

@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    workspace_id: str = Query(..., description="Workspace ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical|emergency)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get all alert rules for a workspace.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Build query
        conditions = [AlertRule.workspace_id == UUID(workspace_id)]

        if is_active is not None:
            conditions.append(AlertRule.is_active == is_active)

        if severity:
            conditions.append(AlertRule.severity == severity)

        stmt = select(AlertRule).where(and_(*conditions)).order_by(desc(AlertRule.created_at))

        result = await db.execute(stmt)
        rules = result.scalars().all()

        return rules

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert rules")


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule_data: AlertRuleCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new alert rule.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(rule_data.workspace_id))

        # Validate condition configuration
        alert_engine = AlertEngine(db)
        is_valid, error_msg = await alert_engine.validate_alert_condition(
            rule_data.condition_type,
            rule_data.condition_config
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid condition: {error_msg}")

        # Check for duplicate rule name
        stmt = select(AlertRule).where(
            and_(
                AlertRule.workspace_id == rule_data.workspace_id,
                AlertRule.rule_name == rule_data.rule_name
            )
        )
        result = await db.execute(stmt)
        existing_rule = result.scalar_one_or_none()

        if existing_rule:
            raise HTTPException(status_code=409, detail="Alert rule with this name already exists")

        # Create rule
        rule = AlertRule(
            workspace_id=rule_data.workspace_id,
            rule_name=rule_data.rule_name,
            description=rule_data.description,
            metric_type=rule_data.metric_type,
            condition_type=rule_data.condition_type,
            condition_config=rule_data.condition_config,
            severity=rule_data.severity,
            is_active=rule_data.is_active,
            check_interval_minutes=rule_data.check_interval_minutes,
            cooldown_minutes=rule_data.cooldown_minutes,
            notification_channels=rule_data.notification_channels,
            escalation_policy_id=rule_data.escalation_policy_id,
            created_by=UUID(current_user["user_id"])
        )

        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        logger.info(f"Alert rule created: {rule.id} for workspace {rule_data.workspace_id}")

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert rule: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str = Path(..., description="Alert rule ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get a specific alert rule by ID.

    Requires authentication and workspace access.
    """
    try:
        stmt = select(AlertRule).where(AlertRule.id == UUID(rule_id))
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(rule.workspace_id))

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert rule")


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str = Path(..., description="Alert rule ID"),
    rule_data: AlertRuleUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update an existing alert rule.

    Requires authentication and workspace access.
    """
    try:
        # Get existing rule
        stmt = select(AlertRule).where(AlertRule.id == UUID(rule_id))
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(rule.workspace_id))

        # Update fields
        update_data = rule_data.dict(exclude_unset=True)

        # Validate condition if changed
        if "condition_type" in update_data or "condition_config" in update_data:
            condition_type = update_data.get("condition_type", rule.condition_type)
            condition_config = update_data.get("condition_config", rule.condition_config)

            alert_engine = AlertEngine(db)
            is_valid, error_msg = await alert_engine.validate_alert_condition(
                condition_type,
                condition_config
            )

            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid condition: {error_msg}")

        for field, value in update_data.items():
            setattr(rule, field, value)

        rule.updated_at = datetime.now()

        await db.commit()
        await db.refresh(rule)

        logger.info(f"Alert rule updated: {rule_id}")

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert rule: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update alert rule")


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str = Path(..., description="Alert rule ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Delete an alert rule.

    Requires authentication and workspace access.
    """
    try:
        # Get existing rule
        stmt = select(AlertRule).where(AlertRule.id == UUID(rule_id))
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(rule.workspace_id))

        await db.delete(rule)
        await db.commit()

        logger.info(f"Alert rule deleted: {rule_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert rule: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete alert rule")


# ============================================================================
# Alerts Endpoints
# ============================================================================

@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    workspace_id: str = Query(..., description="Workspace ID"),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical|emergency)$"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get active (unresolved) alerts for a workspace.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Build query
        conditions = [
            Alert.workspace_id == UUID(workspace_id),
            Alert.resolved_at.is_(None)
        ]

        if severity:
            conditions.append(Alert.severity == severity)

        if acknowledged is not None:
            if acknowledged:
                conditions.append(Alert.acknowledged_at.isnot(None))
            else:
                conditions.append(Alert.acknowledged_at.is_(None))

        stmt = (
            select(Alert)
            .where(and_(*conditions))
            .order_by(desc(Alert.triggered_at))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return alerts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching active alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch active alerts")


@router.get("/history", response_model=List[AlertResponse])
async def get_alert_history(
    workspace_id: str = Query(..., description="Workspace ID"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get alert history for a workspace.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Build query
        conditions = [Alert.workspace_id == UUID(workspace_id)]

        if rule_id:
            conditions.append(Alert.rule_id == UUID(rule_id))

        if date_from:
            conditions.append(Alert.triggered_at >= date_from)

        if date_to:
            conditions.append(Alert.triggered_at <= date_to)

        stmt = (
            select(Alert)
            .where(and_(*conditions))
            .order_by(desc(Alert.triggered_at))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return alerts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert history")


@router.put("/{alert_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert ID"),
    ack_data: AlertAcknowledge = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Acknowledge an alert.

    Requires authentication and workspace access.
    """
    try:
        # Get alert
        stmt = select(Alert).where(Alert.id == UUID(alert_id))
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(alert.workspace_id))

        # Check if already acknowledged
        if alert.acknowledged_at:
            raise HTTPException(status_code=400, detail="Alert already acknowledged")

        # Acknowledge alert
        alert_engine = AlertEngine(db)
        success = await alert_engine.acknowledge_alert(
            alert_id,
            str(ack_data.acknowledged_by),
            ack_data.notes
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to acknowledge alert")

        return {
            "success": True,
            "message": "Alert acknowledged successfully",
            "alert_id": alert_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.put("/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: str = Path(..., description="Alert ID"),
    resolve_data: AlertResolve = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Resolve an alert.

    Requires authentication and workspace access.
    """
    try:
        # Get alert
        stmt = select(Alert).where(Alert.id == UUID(alert_id))
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(alert.workspace_id))

        # Check if already resolved
        if alert.resolved_at:
            raise HTTPException(status_code=400, detail="Alert already resolved")

        # Resolve alert
        alert_engine = AlertEngine(db)
        success = await alert_engine.resolve_alert(
            alert_id,
            str(resolve_data.resolved_by),
            resolve_data.resolution_notes,
            resolve_data.permanent_fix
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to resolve alert")

        return {
            "success": True,
            "message": "Alert resolved successfully",
            "alert_id": alert_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


# ============================================================================
# Escalation Policies Endpoints
# ============================================================================

@router.get("/escalation-policies", response_model=List[EscalationPolicyResponse])
async def get_escalation_policies(
    workspace_id: str = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get escalation policies for a workspace.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        stmt = select(EscalationPolicy).where(
            EscalationPolicy.workspace_id == UUID(workspace_id)
        ).order_by(desc(EscalationPolicy.created_at))

        result = await db.execute(stmt)
        policies = result.scalars().all()

        return policies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching escalation policies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch escalation policies")


@router.post("/escalation-policies", response_model=EscalationPolicyResponse, status_code=201)
async def create_escalation_policy(
    policy_data: EscalationPolicyCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new escalation policy.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(policy_data.workspace_id))

        # Create policy
        policy = EscalationPolicy(
            workspace_id=policy_data.workspace_id,
            policy_name=policy_data.policy_name,
            escalation_levels=[level.dict() for level in policy_data.escalation_levels],
            is_active=policy_data.is_active
        )

        db.add(policy)
        await db.commit()
        await db.refresh(policy)

        logger.info(f"Escalation policy created: {policy.id}")

        return policy

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating escalation policy: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create escalation policy")


# ============================================================================
# Alert Suppressions Endpoints
# ============================================================================

@router.post("/suppressions", response_model=AlertSuppressionResponse, status_code=201)
async def create_alert_suppression(
    suppression_data: AlertSuppressionCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create an alert suppression.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, str(suppression_data.workspace_id))

        # Create suppression
        suppression = AlertSuppression(
            workspace_id=suppression_data.workspace_id,
            suppression_type=suppression_data.suppression_type,
            pattern=suppression_data.pattern,
            start_time=suppression_data.start_time,
            end_time=suppression_data.end_time,
            reason=suppression_data.reason,
            created_by=UUID(current_user["user_id"])
        )

        db.add(suppression)
        await db.commit()
        await db.refresh(suppression)

        logger.info(f"Alert suppression created: {suppression.id}")

        return suppression

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert suppression: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create alert suppression")


# ============================================================================
# Testing and Statistics Endpoints
# ============================================================================

@router.post("/test", response_model=Dict[str, Any])
async def test_alert_rule(
    test_data: Dict[str, Any] = Body(..., description="Alert rule test configuration"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Test an alert rule against historical data.

    Requires authentication.
    """
    try:
        # Validate condition
        condition_type = test_data.get("condition_type")
        condition_config = test_data.get("condition_config")

        if not condition_type or not condition_config:
            raise HTTPException(status_code=400, detail="Missing condition_type or condition_config")

        alert_engine = AlertEngine(db)
        is_valid, error_msg = await alert_engine.validate_alert_condition(
            condition_type,
            condition_config
        )

        if not is_valid:
            return {
                "valid": False,
                "error": error_msg
            }

        return {
            "valid": True,
            "message": "Alert condition is valid"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing alert rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test alert rule")


@router.get("/stats", response_model=Dict[str, Any])
async def get_alert_stats(
    workspace_id: str = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get alert statistics for a workspace.

    Requires authentication and workspace access.
    """
    try:
        # Validate workspace access
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Get counts
        total_stmt = select(func.count(Alert.id)).where(Alert.workspace_id == UUID(workspace_id))
        total_result = await db.execute(total_stmt)
        total_alerts = total_result.scalar()

        active_stmt = select(func.count(Alert.id)).where(
            and_(
                Alert.workspace_id == UUID(workspace_id),
                Alert.resolved_at.is_(None)
            )
        )
        active_result = await db.execute(active_stmt)
        active_alerts = active_result.scalar()

        acknowledged_stmt = select(func.count(Alert.id)).where(
            and_(
                Alert.workspace_id == UUID(workspace_id),
                Alert.acknowledged_at.isnot(None),
                Alert.resolved_at.is_(None)
            )
        )
        acknowledged_result = await db.execute(acknowledged_stmt)
        acknowledged_alerts = acknowledged_result.scalar()

        critical_stmt = select(func.count(Alert.id)).where(
            and_(
                Alert.workspace_id == UUID(workspace_id),
                Alert.severity == "critical",
                Alert.resolved_at.is_(None)
            )
        )
        critical_result = await db.execute(critical_stmt)
        critical_alerts = critical_result.scalar()

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "resolved_alerts": total_alerts - active_alerts,
            "critical_alerts": critical_alerts
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert statistics")
