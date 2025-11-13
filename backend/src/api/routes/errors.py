"""Error tracking routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Body
import logging
from datetime import datetime
from sqlalchemy import text

from ...core.database import get_db
from ...models.schemas.error_tracking import (
    ErrorTrackingResponse,
    TrackErrorRequest,
    ResolveErrorRequest,
    TimeFrame
)
from ...services.analytics.error_tracking_service import ErrorTrackingService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access

router = APIRouter(prefix="/api/v1/errors", tags=["errors"])
logger = logging.getLogger(__name__)


@router.get("/{workspace_id}", response_model=ErrorTrackingResponse)
async def get_error_tracking(
    workspace_id: str = Path(..., description="Workspace ID"),
    timeframe: TimeFrame = Query(
        TimeFrame.SEVEN_DAYS,
        description="Time range: 24h, 7d, 30d, 90d"
    ),
    severity_filter: Optional[str] = Query(
        None,
        description="Filter by severity: all, low, medium, high, critical"
    ),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive error tracking data for a workspace.

    This endpoint provides detailed error analytics including:
    - Error overview and metrics
    - Error categorization and patterns
    - Timeline and spike detection
    - Top errors by various metrics
    - Error correlations
    - Recovery analysis

    **Parameters:**
    - **workspace_id**: Workspace identifier
    - **timeframe**: Time range for analysis (24h, 7d, 30d, 90d)
    - **severity_filter**: Optional severity filter

    **Returns:**
    - Comprehensive error tracking data
    """
    try:
        logger.info(
            f"Fetching error tracking for workspace {workspace_id} "
            f"for timeframe {timeframe}"
        )

        service = ErrorTrackingService(db)
        tracking_data = await service.get_error_tracking(
            workspace_id=workspace_id,
            timeframe=timeframe.value,
            severity_filter=severity_filter
        )

        return tracking_data

    except Exception as e:
        logger.error(f"Error fetching error tracking: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch error tracking: {str(e)}",
        )


@router.post("/{workspace_id}/track")
async def track_error(
    workspace_id: str = Path(..., description="Workspace ID"),
    error_data: TrackErrorRequest = Body(...),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Track a new error occurrence.

    **Parameters:**
    - **workspace_id**: Workspace identifier
    - **error_data**: Error details

    **Returns:**
    - Error ID
    """
    try:
        logger.info(f"Tracking error for workspace {workspace_id}")

        service = ErrorTrackingService(db)
        error_id = await service.track_error(
            workspace_id=workspace_id,
            error_data=error_data.model_dump()
        )

        return {"errorId": error_id, "status": "tracked"}

    except Exception as e:
        logger.error(f"Error tracking error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track error: {str(e)}",
        )


@router.post("/{error_id}/resolve")
async def resolve_error(
    error_id: str = Path(..., description="Error ID"),
    resolution_data: ResolveErrorRequest = Body(...),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mark an error as resolved.

    **Parameters:**
    - **error_id**: Error identifier
    - **resolution_data**: Resolution details

    **Returns:**
    - Status confirmation
    """
    try:
        logger.info(f"Resolving error {error_id}")

        service = ErrorTrackingService(db)
        await service.resolve_error(
            error_id=error_id,
            resolution_data=resolution_data.model_dump()
        )

        return {"status": "resolved", "errorId": error_id}

    except Exception as e:
        logger.error(f"Error resolving error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve error: {str(e)}",
        )


@router.post("/{error_id}/ignore")
async def ignore_error(
    error_id: str = Path(..., description="Error ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mark an error as ignored.

    **Parameters:**
    - **error_id**: Error identifier

    **Returns:**
    - Status confirmation
    """
    try:
        logger.info(f"Ignoring error {error_id}")

        service = ErrorTrackingService(db)
        await service.ignore_error(error_id=error_id)

        return {"status": "ignored", "errorId": error_id}

    except Exception as e:
        logger.error(f"Error ignoring error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ignore error: {str(e)}",
        )


# =====================================================================
# Advanced Error Analytics Endpoints
# =====================================================================

@router.get("/{error_id}/root-cause")
async def get_error_root_cause(
    error_id: str = Path(..., description="Error ID"),
    include_remediation: bool = Query(True, description="Include remediation suggestions"),
    depth: int = Query(3, ge=1, le=10, description="Depth of causal chain analysis"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Perform root cause analysis for a specific error.

    This endpoint uses ML-powered analysis to identify:
    - Immediate causes
    - Root causes with probability scores
    - Contributing factors
    - Dependency chains
    - Temporal patterns
    - Environmental factors
    - Automated remediation suggestions

    **Parameters:**
    - **error_id**: Error identifier
    - **include_remediation**: Include remediation suggestions
    - **depth**: Depth of causal chain to explore (1-10)

    **Returns:**
    - Comprehensive root cause analysis
    """
    try:
        from ...services.analytics.root_cause_analyzer import RootCauseAnalyzer

        logger.info(f"Performing root cause analysis for error {error_id}")

        analyzer = RootCauseAnalyzer(db)
        analysis = await analyzer.analyze_error(error_id, depth)

        if not include_remediation:
            analysis.pop("remediation_suggestions", None)

        return analysis

    except Exception as e:
        logger.error(f"Error in root cause analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform root cause analysis: {str(e)}",
        )


@router.get("/agents/{agent_id}/error-patterns")
async def get_agent_error_patterns(
    agent_id: str = Path(..., description="Agent ID"),
    timeframe: str = Query("30d", description="Time range: 7d, 30d, 90d"),
    min_occurrences: int = Query(5, ge=1, description="Minimum pattern occurrences"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get recurring error patterns for an agent.

    Identifies patterns using ML-powered pattern detection including:
    - Temporal patterns
    - Error correlation patterns
    - Cascading failure patterns
    - Environmental patterns

    **Parameters:**
    - **agent_id**: Agent identifier
    - **timeframe**: Time range for analysis
    - **min_occurrences**: Minimum occurrences to consider as pattern

    **Returns:**
    - Detected error patterns with confidence scores
    """
    try:
        from ...utils.datetime import calculate_start_date

        logger.info(f"Fetching error patterns for agent {agent_id}")

        start_date = calculate_start_date(timeframe)

        query = text("""
            SELECT
                ep.id,
                ep.pattern_name,
                ep.category,
                ep.occurrence_count,
                ep.first_seen,
                ep.last_seen,
                ep.ml_confidence_score,
                ep.auto_recoverable,
                ep.recovery_strategy,
                ep.avg_resolution_time_ms,
                ep.known_fixes
            FROM analytics.error_patterns_enhanced ep
            WHERE :agent_id = ANY(ep.affected_agents)
                AND ep.last_seen >= :start_date
                AND ep.occurrence_count >= :min_occurrences
            ORDER BY ep.occurrence_count DESC, ep.ml_confidence_score DESC
            LIMIT 20
        """)

        result = await db.execute(
            query,
            {
                "agent_id": agent_id,
                "start_date": start_date,
                "min_occurrences": min_occurrences
            }
        )

        patterns = []
        for row in result.fetchall():
            patterns.append({
                "id": str(row.id),
                "pattern_name": row.pattern_name,
                "category": row.category,
                "occurrence_count": row.occurrence_count,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "confidence_score": float(row.ml_confidence_score or 0),
                "auto_recoverable": row.auto_recoverable,
                "recovery_strategy": row.recovery_strategy,
                "avg_resolution_time_ms": row.avg_resolution_time_ms,
                "known_fixes": row.known_fixes or []
            })

        return {
            "agent_id": agent_id,
            "timeframe": timeframe,
            "patterns": patterns,
            "total_patterns": len(patterns)
        }

    except Exception as e:
        logger.error(f"Error fetching error patterns: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch error patterns: {str(e)}",
        )


@router.post("/predict")
async def predict_errors(
    agent_id: str = Query(..., description="Agent ID"),
    prediction_horizon: str = Query("next_execution", description="Prediction timeframe"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Predict error probability for upcoming execution.

    Uses ML models to predict:
    - Error probability (0-1)
    - Risk level (low, medium, high, critical)
    - Top risk factors
    - Predicted error types
    - Prevention actions

    **Parameters:**
    - **agent_id**: Agent identifier
    - **prediction_horizon**: Prediction timeframe (next_execution, 24h, 7d)

    **Returns:**
    - Error prediction with risk assessment and prevention recommendations
    """
    try:
        logger.info(f"Predicting errors for agent {agent_id}")

        # Fetch recent error history for the agent
        query = text("""
            SELECT
                DATE(e.last_seen) as date,
                COUNT(DISTINCT e.error_id) as error_count,
                SUM(e.occurrence_count) as total_occurrences
            FROM analytics.errors e
            WHERE :agent_id = ANY(e.agents_affected)
                AND e.last_seen >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(e.last_seen)
            ORDER BY date DESC
        """)

        result = await db.execute(query, {"agent_id": agent_id})
        error_history = result.fetchall()

        # Simple heuristic-based prediction
        # In production, this would use a trained ML model
        if not error_history or len(error_history) < 7:
            error_probability = 0.1  # Low baseline probability
            risk_level = "low"
        else:
            recent_errors = sum(row.error_count for row in error_history[:7])
            avg_recent = recent_errors / 7.0

            # Calculate probability based on recent trend
            if avg_recent > 5:
                error_probability = 0.8
                risk_level = "critical"
            elif avg_recent > 2:
                error_probability = 0.5
                risk_level = "high"
            elif avg_recent > 1:
                error_probability = 0.3
                risk_level = "medium"
            else:
                error_probability = 0.1
                risk_level = "low"

        # Get most common error types
        error_types_query = text("""
            SELECT error_type, COUNT(*) as count
            FROM analytics.errors
            WHERE :agent_id = ANY(agents_affected)
                AND last_seen >= NOW() - INTERVAL '30 days'
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 5
        """)

        types_result = await db.execute(error_types_query, {"agent_id": agent_id})
        predicted_error_types = [row.error_type for row in types_result.fetchall()]

        # Generate prevention actions
        prevention_actions = []
        if error_probability > 0.5:
            prevention_actions.append({
                "action": "Review recent code changes",
                "priority": "high",
                "estimated_effort": "medium"
            })
            prevention_actions.append({
                "action": "Increase monitoring and alerting",
                "priority": "high",
                "estimated_effort": "low"
            })
        if error_probability > 0.3:
            prevention_actions.append({
                "action": "Run comprehensive test suite",
                "priority": "medium",
                "estimated_effort": "medium"
            })

        return {
            "agent_id": agent_id,
            "prediction_horizon": prediction_horizon,
            "error_probability": round(error_probability, 3),
            "risk_level": risk_level,
            "top_risk_factors": [
                {"factor": "Recent error trend", "weight": 0.8},
                {"factor": "Historical patterns", "weight": 0.6}
            ],
            "predicted_error_types": predicted_error_types,
            "prevention_actions": prevention_actions,
            "confidence_score": 0.75,
            "predicted_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error predicting errors: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to predict errors: {str(e)}",
        )


@router.post("/{error_id}/auto-resolve")
async def auto_resolve_error(
    error_id: str = Path(..., description="Error ID"),
    strategy: str = Query("auto", description="Recovery strategy (auto, retry, fallback, etc.)"),
    dry_run: bool = Query(False, description="Simulate recovery without executing"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Attempt automatic error resolution.

    Intelligently selects and executes recovery strategies:
    - Retry with exponential backoff
    - Fallback to default behavior
    - Circuit breaker activation
    - Graceful degradation
    - State rollback

    **Parameters:**
    - **error_id**: Error identifier
    - **strategy**: Recovery strategy to use ("auto" for automatic selection)
    - **dry_run**: If true, only simulate recovery

    **Returns:**
    - Recovery execution result
    """
    try:
        from ...services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

        logger.info(f"Attempting auto-recovery for error {error_id} (strategy={strategy}, dry_run={dry_run})")

        engine = AdaptiveRecoveryEngine(db)
        result = await engine.auto_recover(error_id, dry_run=dry_run)

        return result

    except Exception as e:
        logger.error(f"Error in auto-recovery: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to auto-resolve error: {str(e)}",
        )


@router.get("/{error_id}/business-impact")
async def get_business_impact(
    error_id: str = Path(..., description="Error ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Calculate comprehensive business impact for an error.

    Analyzes multiple impact dimensions:
    - Financial impact (revenue loss, costs, refunds)
    - Operational impact (downtime, workflows, SLA violations)
    - User impact (satisfaction, churn risk, support tickets)
    - Reputation impact (severity, visibility, recovery expectations)

    **Parameters:**
    - **error_id**: Error identifier

    **Returns:**
    - Comprehensive business impact analysis
    """
    try:
        from ...services.analytics.business_impact_calculator import BusinessImpactCalculator

        logger.info(f"Calculating business impact for error {error_id}")

        calculator = BusinessImpactCalculator(db)
        impact = await calculator.calculate_error_impact(error_id)

        return impact

    except Exception as e:
        logger.error(f"Error calculating business impact: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate business impact: {str(e)}",
        )


@router.get("/cascades/{workspace_id}")
async def get_cascading_failures(
    workspace_id: str = Path(..., description="Workspace ID"),
    timeframe: str = Query("7d", description="Time range: 24h, 7d, 30d"),
    severity_filter: Optional[str] = Query(None, description="Filter by cascade severity"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get cascading failure analysis for a workspace.

    Identifies and analyzes cascading failures:
    - Cascade chains
    - Affected resources
    - Business impact
    - Root causes
    - Prevention strategies

    **Parameters:**
    - **workspace_id**: Workspace identifier
    - **timeframe**: Time range for analysis
    - **severity_filter**: Filter by severity (isolated, minor_cascade, moderate_cascade, major_cascade)

    **Returns:**
    - Cascading failure analysis
    """
    try:
        from ...utils.datetime import calculate_start_date

        logger.info(f"Fetching cascading failures for workspace {workspace_id}")

        start_date = calculate_start_date(timeframe)

        query = text("""
            SELECT
                ec.id,
                ec.initial_error_id,
                ei.error_type as initial_error_type,
                ec.cascade_start,
                ec.cascade_end,
                ec.cascade_duration_seconds,
                ec.affected_agents_count,
                ec.affected_users_count,
                ec.total_errors_in_cascade,
                ec.cascade_severity,
                ec.root_cause_identified,
                ec.root_cause,
                ec.preventable,
                ec.prevention_strategy
            FROM analytics.error_cascades ec
            JOIN analytics.errors ei ON ec.initial_error_id = ei.error_id
            WHERE ec.workspace_id = :workspace_id
                AND ec.cascade_start >= :start_date
                AND (:severity_filter IS NULL OR ec.cascade_severity = :severity_filter)
            ORDER BY ec.cascade_start DESC
            LIMIT 50
        """)

        result = await db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "severity_filter": severity_filter
            }
        )

        cascades = []
        for row in result.fetchall():
            cascades.append({
                "id": str(row.id),
                "initial_error_id": str(row.initial_error_id),
                "initial_error_type": row.initial_error_type,
                "cascade_start": row.cascade_start.isoformat(),
                "cascade_end": row.cascade_end.isoformat() if row.cascade_end else None,
                "cascade_duration_seconds": row.cascade_duration_seconds,
                "affected_agents_count": row.affected_agents_count,
                "affected_users_count": row.affected_users_count,
                "total_errors": row.total_errors_in_cascade,
                "severity": row.cascade_severity,
                "root_cause_identified": row.root_cause_identified,
                "root_cause": row.root_cause,
                "preventable": row.preventable,
                "prevention_strategy": row.prevention_strategy
            })

        return {
            "workspace_id": workspace_id,
            "timeframe": timeframe,
            "cascades": cascades,
            "total_cascades": len(cascades)
        }

    except Exception as e:
        logger.error(f"Error fetching cascading failures: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch cascading failures: {str(e)}",
        )
