"""Knowledge Base Analytics API routes."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException
import logging

from ...core.database import get_db
from ...models.schemas.knowledge_analytics import (
    KnowledgeBaseAnalyticsResponse,
    KnowledgeItemResponse,
    KnowledgeItemCreate,
    KnowledgeGraphResponse,
    KnowledgeBaseOptimizationRequest,
    GraphOptimizationResult,
    KnowledgeDriftDetectionRequest,
    DriftAnalysisResponse,
    KnowledgeTransferAnalysisRequest,
    TransferEffectivenessMetrics,
    AcquisitionMetrics,
    RetrievalMetricsResponse,
)
from ...services.analytics.knowledge_base_service import KnowledgeBaseService
from ...services.analytics.knowledge_acquisition_analyzer import KnowledgeAcquisitionAnalyzer
from ...services.analytics.knowledge_analyzers import (
    KnowledgeRetrievalAnalyzer,
    KnowledgeDriftDetector,
    KnowledgeGraphOptimizer,
)
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...utils.validators import validate_agent_id, validate_workspace_id

router = APIRouter(prefix="/api/v1/knowledge-analytics", tags=["knowledge-analytics"])
logger = logging.getLogger(__name__)


@router.get("/agents/{agent_id}/knowledge-base")
async def get_knowledge_base_analytics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    include_graph_metrics: bool = Query(True, description="Include graph structure metrics"),
    include_usage_patterns: bool = Query(True, description="Include usage pattern analytics"),
    timeframe: str = Query(
        "30d",
        description="Time range: 7d, 30d, 90d, all",
        pattern="^(7d|30d|90d|all)$",
    ),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive knowledge base analytics for an agent.

    This endpoint provides detailed analytics about the agent's knowledge base,
    including graph structure, acquisition patterns, retrieval efficiency, and usage metrics.

    **Parameters:**
    - **agent_id**: Unique identifier for the agent
    - **workspace_id**: Workspace context for the analytics
    - **include_graph_metrics**: Include knowledge graph structure metrics
    - **include_usage_patterns**: Include usage pattern analytics
    - **timeframe**: Time range for analysis (7d, 30d, 90d, all)

    **Returns:**
    - Comprehensive knowledge base analytics including:
        - Basic statistics (total items, verification rate, quality scores)
        - Domain coverage and distribution
        - Knowledge graph metrics (if requested)
        - Usage patterns (if requested)
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        logger.info(
            f"Fetching knowledge base analytics for agent {validated_agent_id} "
            f"in workspace {validated_workspace_id} (user: {current_user.get('user_id')})"
        )

        service = KnowledgeBaseService(db)
        analytics = await service.get_knowledge_base_analytics(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            include_graph_metrics=include_graph_metrics,
            include_usage_patterns=include_usage_patterns,
            timeframe=timeframe,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching knowledge base analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch knowledge base analytics: {str(e)}",
        )


@router.get("/agents/{agent_id}/knowledge-base/acquisition")
async def get_acquisition_analytics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get knowledge acquisition analytics for an agent.

    Analyzes learning patterns, acquisition rate, source quality, and knowledge gaps.

    **Returns:**
    - Acquisition rate and total items acquired
    - Learning curve analysis with phases
    - Source quality metrics
    - Identified knowledge gaps
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        analyzer = KnowledgeAcquisitionAnalyzer(db)
        analytics = await analyzer.analyze_learning_patterns(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching acquisition analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch acquisition analytics: {str(e)}",
        )


@router.get("/agents/{agent_id}/knowledge-base/retrieval")
async def get_retrieval_analytics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("7d", pattern="^(7d|30d|90d)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get knowledge retrieval performance analytics.

    Analyzes retrieval efficiency, search effectiveness, and access patterns.

    **Returns:**
    - Retrieval performance metrics (speed, cache hit rate)
    - Search effectiveness (precision, recall, F1 score)
    - Access distribution and inequality metrics
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        analyzer = KnowledgeRetrievalAnalyzer(db)
        analytics = await analyzer.analyze_retrieval_performance(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return analytics

    except Exception as e:
        logger.error(f"Error fetching retrieval analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch retrieval analytics: {str(e)}",
        )


@router.get("/agents/{agent_id}/knowledge-base/drift")
async def detect_knowledge_drift(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    drift_threshold: float = Query(0.3, ge=0, le=1, description="Drift detection threshold"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Detect knowledge drift for an agent.

    Identifies concept drift, stale facts, rule conflicts, and accuracy degradation.

    **Parameters:**
    - **drift_threshold**: Threshold for drift detection (0-1, default: 0.3)

    **Returns:**
    - Concept drift analysis with drift score
    - Stale facts identification
    - Rule conflicts
    - Drift rates (daily, weekly, monthly)
    - Remediation plan (if drift detected)
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        detector = KnowledgeDriftDetector(db)
        drift_analysis = await detector.detect_knowledge_drift(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            drift_threshold=drift_threshold,
        )

        return drift_analysis

    except Exception as e:
        logger.error(f"Error detecting knowledge drift: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect knowledge drift: {str(e)}",
        )


@router.post("/agents/{agent_id}/knowledge-base/optimize")
async def optimize_knowledge_base(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    request: KnowledgeBaseOptimizationRequest = None,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Optimize agent's knowledge base structure.

    Performs graph optimization including redundancy removal, edge optimization,
    and cluster reorganization.

    **Parameters:**
    - **optimization_type**: Type of optimization (comprehensive, redundancy, edges, clusters, paths)
    - **dry_run**: If true, only analyze without applying changes (default: true)

    **Returns:**
    - Identified optimizations
    - Improvement metrics (query speed, storage reduction, traversal efficiency)
    - Optimization details
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    if request is None:
        request = KnowledgeBaseOptimizationRequest()

    try:
        logger.info(
            f"Optimizing knowledge base for agent {validated_agent_id} "
            f"(type: {request.optimization_type}, dry_run: {request.dry_run})"
        )

        optimizer = KnowledgeGraphOptimizer(db)
        result = await optimizer.optimize_graph_structure(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            dry_run=request.dry_run,
        )

        return result

    except Exception as e:
        logger.error(f"Error optimizing knowledge base: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize knowledge base: {str(e)}",
        )


@router.get("/agents/{agent_id}/knowledge-base/graph-evolution")
async def get_graph_evolution(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get knowledge graph evolution over time.

    Returns historical snapshots of graph metrics showing how the knowledge base
    has evolved over the specified timeframe.

    **Returns:**
    - List of graph metric snapshots with timestamps
    - Evolution trends (nodes, edges, density, quality)
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        service = KnowledgeBaseService(db)
        evolution = await service.get_graph_evolution(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            timeframe=timeframe,
        )

        return {"agent_id": validated_agent_id, "timeframe": timeframe, "snapshots": evolution}

    except Exception as e:
        logger.error(f"Error fetching graph evolution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch graph evolution: {str(e)}",
        )


@router.post("/agents/{agent_id}/knowledge-base/snapshot")
async def create_graph_snapshot(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    snapshot_type: str = Query("on_demand", pattern="^(scheduled|on_demand|post_optimization)$"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Create a snapshot of current knowledge graph metrics.

    Useful for tracking graph changes over time and before/after optimization comparisons.

    **Parameters:**
    - **snapshot_type**: Type of snapshot (scheduled, on_demand, post_optimization)

    **Returns:**
    - Snapshot ID
    - Snapshot details
    """
    validated_agent_id = validate_agent_id(agent_id)
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        service = KnowledgeBaseService(db)
        snapshot_id = await service.save_graph_metrics_snapshot(
            agent_id=validated_agent_id,
            workspace_id=validated_workspace_id,
            snapshot_type=snapshot_type,
        )

        if not snapshot_id:
            raise HTTPException(
                status_code=404,
                detail="No knowledge items found for agent",
            )

        return {
            "snapshot_id": snapshot_id,
            "agent_id": validated_agent_id,
            "workspace_id": validated_workspace_id,
            "snapshot_type": snapshot_type,
            "created_at": "now",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating graph snapshot: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create graph snapshot: {str(e)}",
        )


@router.get("/knowledge-items/{item_id}")
async def get_knowledge_item_details(
    item_id: str = Path(..., description="Knowledge item ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get detailed information about a specific knowledge item.

    **Returns:**
    - Complete knowledge item details
    - Quality metrics
    - Usage statistics
    - Graph position metrics
    """
    try:
        service = KnowledgeBaseService(db)
        item_details = await service.get_knowledge_item_details(knowledge_item_id=item_id)

        if not item_details:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge item {item_id} not found",
            )

        return item_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching knowledge item details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch knowledge item details: {str(e)}",
        )


@router.get("/workspaces/{workspace_id}/knowledge-analytics/summary")
async def get_workspace_knowledge_summary(
    workspace_id: str = Path(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get knowledge analytics summary for all agents in a workspace.

    **Returns:**
    - Aggregate knowledge base metrics across all agents
    - Top performing agents by knowledge quality
    - Workspace-wide knowledge gaps
    """
    validated_workspace_id = validate_workspace_id(workspace_id)

    try:
        # TODO: Implement workspace-level knowledge analytics aggregation
        return {
            "workspace_id": validated_workspace_id,
            "total_agents_with_knowledge": 0,
            "total_knowledge_items": 0,
            "avg_quality_score": 0.0,
            "top_agents": [],
        }

    except Exception as e:
        logger.error(f"Error fetching workspace knowledge summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch workspace knowledge summary: {str(e)}",
        )
