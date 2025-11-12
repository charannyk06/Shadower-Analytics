"""Anomaly detection API routes."""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
import asyncio
import logging
from datetime import datetime
import uuid

from ...core.database import get_db
from ...services.analytics.anomaly_detection import AnomalyDetectionService
from ...models.database.tables import AnomalyDetection, AnomalyRule, BaselineModel
from ...models.schemas.anomalies import (
    DetectAnomaliesRequest,
    DetectUsageSpikesRequest,
    DetectErrorPatternsRequest,
    DetectUserBehaviorRequest,
    TrainBaselineRequest,
    AcknowledgeAnomalyRequest,
    CreateAnomalyRuleRequest,
    UpdateAnomalyRuleRequest,
    AnomalyDetectionResponse,
    AnomalyListResponse,
    AnomalyRuleResponse,
    BaselineModelResponse,
    BaselineModelDetailResponse,
    AnomalySummaryResponse,
    HealthCheckResponse,
    SeverityLevel,
    DetectionMethod,
)
from ...utils.validators import validate_workspace_id
from ..dependencies.auth import get_current_user
from ..middleware.rate_limit import RateLimiter
from ..middleware.workspace import WorkspaceAccess

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])

# Request timeout for anomaly detection (60 seconds)
DETECTION_TIMEOUT_SECONDS = 60

# Rate limiters for different operations
detection_limiter = RateLimiter(
    requests_per_minute=10,
    requests_per_hour=100,
)

rule_limiter = RateLimiter(
    requests_per_minute=20,
    requests_per_hour=200,
)


# === Detection Endpoints ===

@router.get("/{workspace_id}", dependencies=[Depends(detection_limiter)])
async def get_anomalies(
    workspace_id: str,
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of detected anomalies.

    Args:
        workspace_id: Workspace ID
        date_from: Start date for filtering
        date_to: End date for filtering
        severity: Filter by severity level
        metric_type: Filter by metric type
        is_acknowledged: Filter by acknowledgment status
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Paginated list of anomalies with metadata
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Build query
        query = select(AnomalyDetection).where(
            AnomalyDetection.workspace_id == workspace_id
        )

        # Apply filters
        if date_from:
            query = query.where(AnomalyDetection.detected_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.where(AnomalyDetection.detected_at <= datetime.fromisoformat(date_to))
        if severity:
            query = query.where(AnomalyDetection.severity == severity.value)
        if metric_type:
            query = query.where(AnomalyDetection.metric_type == metric_type)
        if is_acknowledged is not None:
            query = query.where(AnomalyDetection.is_acknowledged == is_acknowledged)

        # Order by detected_at descending
        query = query.order_by(AnomalyDetection.detected_at.desc())

        # Count total
        count_query = select(AnomalyDetection).where(
            AnomalyDetection.workspace_id == workspace_id
        )
        if date_from:
            count_query = count_query.where(AnomalyDetection.detected_at >= datetime.fromisoformat(date_from))
        if date_to:
            count_query = count_query.where(AnomalyDetection.detected_at <= datetime.fromisoformat(date_to))
        if severity:
            count_query = count_query.where(AnomalyDetection.severity == severity.value)
        if metric_type:
            count_query = count_query.where(AnomalyDetection.metric_type == metric_type)
        if is_acknowledged is not None:
            count_query = count_query.where(AnomalyDetection.is_acknowledged == is_acknowledged)

        total_result = await db.execute(count_query)
        total = len(total_result.fetchall())

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        anomalies = result.scalars().all()

        # Convert to response schema
        anomaly_responses = []
        for anomaly in anomalies:
            anomaly_responses.append(AnomalyDetectionResponse(
                id=anomaly.id,
                metric_type=anomaly.metric_type,
                workspace_id=anomaly.workspace_id,
                detected_at=anomaly.detected_at.isoformat(),
                anomaly_value=anomaly.anomaly_value,
                expected_range=anomaly.expected_range,
                anomaly_score=anomaly.anomaly_score,
                severity=SeverityLevel(anomaly.severity),
                detection_method=anomaly.detection_method,
                context=anomaly.context,
                is_acknowledged=anomaly.is_acknowledged,
                acknowledged_by=anomaly.acknowledged_by,
                acknowledged_at=anomaly.acknowledged_at.isoformat() if anomaly.acknowledged_at else None,
                notes=anomaly.notes,
                created_at=anomaly.created_at.isoformat() if anomaly.created_at else None,
            ))

        return AnomalyListResponse(
            anomalies=anomaly_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch anomalies")


@router.post("/{workspace_id}/detect", dependencies=[Depends(detection_limiter)])
async def detect_anomalies(
    workspace_id: str,
    request: DetectAnomaliesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run on-demand anomaly detection for specified metric.

    Args:
        workspace_id: Workspace ID
        request: Detection parameters

    Returns:
        List of detected anomalies
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Override workspace_id from path
        request.workspace_id = workspace_id

        service = AnomalyDetectionService(db)

        result = await asyncio.wait_for(
            service.detect_metric_anomalies(
                metric_type=request.metric_type,
                workspace_id=request.workspace_id,
                lookback_days=request.lookback_days,
                sensitivity=request.sensitivity,
                method=request.method.value,
            ),
            timeout=DETECTION_TIMEOUT_SECONDS
        )

        return {"anomalies": result, "count": len(result)}

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Detection timed out after {DETECTION_TIMEOUT_SECONDS} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")


@router.post("/{workspace_id}/detect/usage-spikes", dependencies=[Depends(detection_limiter)])
async def detect_usage_spikes(
    workspace_id: str,
    request: DetectUsageSpikesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect unusual spikes in credit consumption.

    Args:
        workspace_id: Workspace ID
        request: Detection parameters

    Returns:
        List of detected usage spikes
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = AnomalyDetectionService(db)

        result = await asyncio.wait_for(
            service.detect_usage_spikes(
                workspace_id=workspace_id,
                sensitivity=request.sensitivity,
                window_hours=request.window_hours,
            ),
            timeout=DETECTION_TIMEOUT_SECONDS
        )

        return {"anomalies": result, "count": len(result)}

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Detection timed out after {DETECTION_TIMEOUT_SECONDS} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting usage spikes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect usage spikes")


@router.post("/{workspace_id}/detect/error-patterns", dependencies=[Depends(detection_limiter)])
async def detect_error_patterns(
    workspace_id: str,
    request: DetectErrorPatternsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify unusual error patterns or rates.

    Args:
        workspace_id: Workspace ID
        request: Detection parameters

    Returns:
        List of detected error pattern anomalies
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = AnomalyDetectionService(db)

        result = await asyncio.wait_for(
            service.detect_error_patterns(
                workspace_id=workspace_id,
                window_hours=request.window_hours,
            ),
            timeout=DETECTION_TIMEOUT_SECONDS
        )

        return {"anomalies": result, "count": len(result)}

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Detection timed out after {DETECTION_TIMEOUT_SECONDS} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting error patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect error patterns")


@router.post("/{workspace_id}/detect/user-behavior", dependencies=[Depends(detection_limiter)])
async def detect_user_behavior_anomalies(
    workspace_id: str,
    request: DetectUserBehaviorRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect unusual user activity patterns.

    Args:
        workspace_id: Workspace ID
        request: Detection parameters

    Returns:
        List of detected behavioral anomalies
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = AnomalyDetectionService(db)

        result = await asyncio.wait_for(
            service.detect_user_behavior_anomalies(
                user_id=request.user_id,
                workspace_id=workspace_id,
                lookback_days=request.lookback_days,
            ),
            timeout=DETECTION_TIMEOUT_SECONDS
        )

        return {"anomalies": result, "count": len(result)}

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Detection timed out after {DETECTION_TIMEOUT_SECONDS} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting user behavior anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect user behavior anomalies")


# === Anomaly Management Endpoints ===

@router.put("/{workspace_id}/{anomaly_id}/acknowledge", dependencies=[Depends(rule_limiter)])
async def acknowledge_anomaly(
    workspace_id: str,
    anomaly_id: str,
    request: AcknowledgeAnomalyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledge an anomaly as reviewed.

    Args:
        workspace_id: Workspace ID
        anomaly_id: Anomaly ID
        request: Acknowledgment details

    Returns:
        Updated anomaly
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Fetch anomaly
        query = select(AnomalyDetection).where(
            and_(
                AnomalyDetection.id == anomaly_id,
                AnomalyDetection.workspace_id == workspace_id
            )
        )
        result = await db.execute(query)
        anomaly = result.scalar_one_or_none()

        if not anomaly:
            raise HTTPException(status_code=404, detail="Anomaly not found")

        # Update anomaly
        anomaly.is_acknowledged = True
        anomaly.acknowledged_by = current_user.get('user_id')
        anomaly.acknowledged_at = datetime.utcnow()
        anomaly.notes = request.notes

        await db.commit()
        await db.refresh(anomaly)

        return AnomalyDetectionResponse(
            id=anomaly.id,
            metric_type=anomaly.metric_type,
            workspace_id=anomaly.workspace_id,
            detected_at=anomaly.detected_at.isoformat(),
            anomaly_value=anomaly.anomaly_value,
            expected_range=anomaly.expected_range,
            anomaly_score=anomaly.anomaly_score,
            severity=SeverityLevel(anomaly.severity),
            detection_method=anomaly.detection_method,
            context=anomaly.context,
            is_acknowledged=anomaly.is_acknowledged,
            acknowledged_by=anomaly.acknowledged_by,
            acknowledged_at=anomaly.acknowledged_at.isoformat() if anomaly.acknowledged_at else None,
            notes=anomaly.notes,
            created_at=anomaly.created_at.isoformat() if anomaly.created_at else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error acknowledging anomaly: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to acknowledge anomaly")


# === Rule Management Endpoints ===

@router.get("/{workspace_id}/rules", dependencies=[Depends(rule_limiter)])
async def get_anomaly_rules(
    workspace_id: str,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get anomaly detection rules for workspace.

    Args:
        workspace_id: Workspace ID
        is_active: Filter by active status
        metric_type: Filter by metric type

    Returns:
        List of anomaly rules
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        query = select(AnomalyRule).where(
            AnomalyRule.workspace_id == workspace_id
        )

        if is_active is not None:
            query = query.where(AnomalyRule.is_active == is_active)
        if metric_type:
            query = query.where(AnomalyRule.metric_type == metric_type)

        result = await db.execute(query)
        rules = result.scalars().all()

        return {
            "rules": [
                AnomalyRuleResponse(
                    id=rule.id,
                    workspace_id=rule.workspace_id,
                    metric_type=rule.metric_type,
                    rule_name=rule.rule_name,
                    detection_method=rule.detection_method,
                    parameters=rule.parameters,
                    is_active=rule.is_active,
                    auto_alert=rule.auto_alert,
                    alert_channels=rule.alert_channels,
                    created_by=rule.created_by,
                    created_at=rule.created_at.isoformat(),
                    updated_at=rule.updated_at.isoformat(),
                )
                for rule in rules
            ],
            "count": len(rules)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching anomaly rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch anomaly rules")


@router.post("/{workspace_id}/rules", dependencies=[Depends(rule_limiter)])
async def create_anomaly_rule(
    workspace_id: str,
    request: CreateAnomalyRuleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new anomaly detection rule.

    Args:
        workspace_id: Workspace ID
        request: Rule configuration

    Returns:
        Created rule
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        # Create rule
        rule = AnomalyRule(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            metric_type=request.metric_type,
            rule_name=request.rule_name,
            detection_method=request.detection_method.value,
            parameters=request.parameters,
            is_active=True,
            auto_alert=request.auto_alert,
            alert_channels=request.alert_channels,
            created_by=current_user.get('user_id'),
        )

        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        return AnomalyRuleResponse(
            id=rule.id,
            workspace_id=rule.workspace_id,
            metric_type=rule.metric_type,
            rule_name=rule.rule_name,
            detection_method=rule.detection_method,
            parameters=rule.parameters,
            is_active=rule.is_active,
            auto_alert=rule.auto_alert,
            alert_channels=rule.alert_channels,
            created_by=rule.created_by,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating anomaly rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create anomaly rule")


# === Baseline Model Endpoints ===

@router.post("/{workspace_id}/baseline/train", dependencies=[Depends(detection_limiter)])
async def train_baseline_model(
    workspace_id: str,
    request: TrainBaselineRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Train baseline model for normal behavior.

    Args:
        workspace_id: Workspace ID
        request: Training parameters

    Returns:
        Baseline model statistics and metadata
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        service = AnomalyDetectionService(db)

        result = await asyncio.wait_for(
            service.train_baseline_model(
                metric_type=request.metric_type,
                workspace_id=workspace_id,
                training_days=request.training_days,
                model_type=request.model_type.value,
            ),
            timeout=DETECTION_TIMEOUT_SECONDS
        )

        return result

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Training timed out after {DETECTION_TIMEOUT_SECONDS} seconds"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error training baseline model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to train baseline model")


@router.get("/{workspace_id}/baseline", dependencies=[Depends(rule_limiter)])
async def get_baseline_models(
    workspace_id: str,
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get baseline models for workspace.

    Args:
        workspace_id: Workspace ID
        metric_type: Filter by metric type

    Returns:
        List of baseline models
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        query = select(BaselineModel).where(
            BaselineModel.workspace_id == workspace_id
        )

        if metric_type:
            query = query.where(BaselineModel.metric_type == metric_type)

        result = await db.execute(query)
        models = result.scalars().all()

        return {
            "models": [
                BaselineModelDetailResponse(
                    id=model.id,
                    workspace_id=model.workspace_id,
                    metric_type=model.metric_type,
                    model_type=model.model_type,
                    model_parameters=model.model_parameters,
                    statistics=model.statistics,
                    training_data_start=model.training_data_start.isoformat(),
                    training_data_end=model.training_data_end.isoformat(),
                    accuracy_metrics=model.accuracy_metrics,
                    last_updated=model.last_updated.isoformat(),
                )
                for model in models
            ],
            "count": len(models)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching baseline models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch baseline models")


# === Summary and Health Endpoints ===

@router.get("/{workspace_id}/summary", dependencies=[Depends(rule_limiter)])
async def get_anomaly_summary(
    workspace_id: str,
    days: int = Query(7, ge=1, le=90, description="Number of days for summary"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for anomalies.

    Args:
        workspace_id: Workspace ID
        days: Number of days to include in summary

    Returns:
        Anomaly summary statistics
    """
    try:
        workspace_id = validate_workspace_id(workspace_id)
        await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)

        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(AnomalyDetection).where(
            and_(
                AnomalyDetection.workspace_id == workspace_id,
                AnomalyDetection.detected_at >= start_date
            )
        )

        result = await db.execute(query)
        anomalies = result.scalars().all()

        # Calculate statistics
        total = len(anomalies)
        by_severity = {}
        by_metric_type = {}
        by_detection_method = {}
        acknowledged = 0
        unacknowledged = 0

        for anomaly in anomalies:
            by_severity[anomaly.severity] = by_severity.get(anomaly.severity, 0) + 1
            by_metric_type[anomaly.metric_type] = by_metric_type.get(anomaly.metric_type, 0) + 1
            by_detection_method[anomaly.detection_method] = by_detection_method.get(anomaly.detection_method, 0) + 1

            if anomaly.is_acknowledged:
                acknowledged += 1
            else:
                unacknowledged += 1

        # Get recent anomalies (last 10)
        recent_query = select(AnomalyDetection).where(
            and_(
                AnomalyDetection.workspace_id == workspace_id,
                AnomalyDetection.detected_at >= start_date
            )
        ).order_by(AnomalyDetection.detected_at.desc()).limit(10)

        recent_result = await db.execute(recent_query)
        recent_anomalies = recent_result.scalars().all()

        return AnomalySummaryResponse(
            total_anomalies=total,
            by_severity=by_severity,
            by_metric_type=by_metric_type,
            by_detection_method=by_detection_method,
            acknowledged_count=acknowledged,
            unacknowledged_count=unacknowledged,
            recent_anomalies=[
                AnomalyDetectionResponse(
                    id=a.id,
                    metric_type=a.metric_type,
                    workspace_id=a.workspace_id,
                    detected_at=a.detected_at.isoformat(),
                    anomaly_value=a.anomaly_value,
                    expected_range=a.expected_range,
                    anomaly_score=a.anomaly_score,
                    severity=SeverityLevel(a.severity),
                    detection_method=a.detection_method,
                    context=a.context,
                    is_acknowledged=a.is_acknowledged,
                    acknowledged_by=a.acknowledged_by,
                    acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                    notes=a.notes,
                    created_at=a.created_at.isoformat() if a.created_at else None,
                )
                for a in recent_anomalies
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating anomaly summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate anomaly summary")
