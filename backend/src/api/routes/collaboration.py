"""Collaboration analytics API routes."""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.api.dependencies.database import get_db
from src.api.dependencies.auth import require_authenticated_user, get_current_user
from src.services.analytics.collaboration_service import CollaborationAnalyticsService
from src.models.schemas.collaboration import (
    WorkflowCollaborationRequest,
    WorkflowCollaborationResponse,
    CollaborationPatternRequest,
    CollaborationPatternResponse,
    WorkflowOptimizationRequest,
    WorkflowOptimizationResponse,
    CollectiveIntelligenceRequest,
    CollectiveIntelligenceResponse,
    OptimizationGoal,
)
from src.models.schemas.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["Collaboration Analytics"])


@router.get("/workflows/{workflow_id}/collaboration", response_model=WorkflowCollaborationResponse)
async def get_workflow_collaboration_metrics(
    workflow_id: str,
    include_handoffs: bool = Query(default=True, description="Include handoff details"),
    include_dependencies: bool = Query(default=True, description="Include dependency analysis"),
    include_patterns: bool = Query(default=False, description="Include detected patterns"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    """
    Get collaboration analytics for a specific workflow.

    This endpoint provides comprehensive collaboration metrics including:
    - Agent nodes and their performance
    - Agent interactions and communication patterns
    - Handoff metrics and efficiency
    - Dependency analysis
    - Detected collaboration patterns

    **Permissions Required:**
    - view_analytics

    **Performance:**
    - Response time: < 500ms
    - Caching: 5 minutes
    """
    try:
        service = CollaborationAnalyticsService(db)
        metrics = await service.get_workflow_collaboration_metrics(
            workflow_id=workflow_id,
            include_handoffs=include_handoffs,
            include_dependencies=include_dependencies,
            include_patterns=include_patterns,
        )
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting workflow collaboration metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/patterns", response_model=CollaborationPatternResponse)
async def get_collaboration_patterns(
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query(default="30d", description="Analysis timeframe (e.g., '7d', '30d', '90d')"),
    pattern_type: Optional[str] = Query(default=None, description="Filter by pattern type"),
    min_frequency: int = Query(default=2, description="Minimum occurrence frequency"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    """
    Identify and analyze collaboration patterns in a workspace.

    This endpoint detects various collaboration patterns including:
    - Common workflows and execution patterns
    - Collaboration clusters (groups of frequently interacting agents)
    - Communication patterns and bottlenecks
    - Emergent behaviors and synergy opportunities
    - Redundancy detection

    **Permissions Required:**
    - view_analytics

    **Performance:**
    - Response time: < 2s for 30-day analysis
    - Caching: 1 hour
    """
    try:
        service = CollaborationAnalyticsService(db)
        patterns = await service.analyze_collaboration_patterns(
            workspace_id=workspace_id,
            timeframe=timeframe,
            pattern_type=pattern_type,
            min_frequency=min_frequency,
        )
        return patterns
    except Exception as e:
        logger.error(f"Error analyzing collaboration patterns: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/workflows/{workflow_id}/optimize", response_model=WorkflowOptimizationResponse)
async def optimize_workflow_collaboration(
    workflow_id: str,
    request: WorkflowOptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    """
    Generate workflow optimization recommendations.

    This endpoint analyzes a workflow and provides:
    - Identified bottlenecks and their impact
    - Inefficiencies in coordination and communication
    - Potential failure points
    - Optimization strategies with estimated improvements
    - Priority ranking for improvements

    **Permissions Required:**
    - view_analytics

    **Performance:**
    - Response time: < 1s
    - Caching: 10 minutes
    """
    try:
        service = CollaborationAnalyticsService(db)
        optimization = await service.optimize_workflow(
            workflow_id=workflow_id,
            optimization_goals=[goal.value for goal in request.optimization_goals],
            constraints=request.constraints,
        )
        return optimization
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error optimizing workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/collective-intelligence", response_model=CollectiveIntelligenceResponse)
async def get_collective_intelligence_metrics(
    workspace_id: str = Query(..., description="Workspace ID"),
    metric_types: List[str] = Query(
        default=["emergence", "adaptation", "efficiency"],
        description="Metric types to analyze"
    ),
    timeframe: str = Query(default="30d", description="Analysis timeframe"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    """
    Analyze collective intelligence metrics for multi-agent systems.

    This endpoint provides metrics on:
    - Diversity index (variety of agent capabilities)
    - Collective accuracy (combined performance vs individual)
    - Emergence score (capabilities emerging from collaboration)
    - Adaptation rate (how quickly the system adapts)
    - Synergy factor (collaboration effectiveness)
    - Decision quality and consensus efficiency
    - Collective learning rate

    **Permissions Required:**
    - view_analytics

    **Performance:**
    - Response time: < 800ms
    - Caching: 15 minutes
    """
    try:
        service = CollaborationAnalyticsService(db)
        metrics = await service.get_collective_intelligence_metrics(
            workspace_id=workspace_id,
            metric_types=metric_types,
            timeframe=timeframe,
        )
        return metrics
    except Exception as e:
        logger.error(f"Error getting collective intelligence metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def collaboration_health_check():
    """
    Health check endpoint for collaboration analytics service.

    Returns service status and availability.
    """
    return {
        "status": "healthy",
        "service": "collaboration-analytics",
        "version": "1.0.0",
    }
