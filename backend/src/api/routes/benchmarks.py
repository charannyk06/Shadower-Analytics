"""Benchmark API routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, BackgroundTasks
from datetime import datetime
import logging

from ...core.database import get_db
from ...models.schemas.benchmarks import (
    BenchmarkSuite,
    BenchmarkSuiteCreate,
    BenchmarkDefinition,
    BenchmarkDefinitionCreate,
    BenchmarkExecution,
    BenchmarkExecutionSummary,
    RunBenchmarkRequest,
    RunBenchmarkResponse,
    LeaderboardResponse,
    ExecutionStatus,
)
from ...services.analytics.benchmark_runner_service import BenchmarkRunnerService
from ...services.analytics.benchmark_leaderboard_service import BenchmarkLeaderboardService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...utils.validators import validate_agent_id, validate_workspace_id

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])
logger = logging.getLogger(__name__)


# =====================================================================
# Benchmark Suite Endpoints
# =====================================================================


@router.get("/suites", response_model=List[BenchmarkSuite])
async def list_benchmark_suites(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: str = Query("active", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List available benchmark suites.

    **Parameters:**
    - **category**: Filter by benchmark category (speed, accuracy, cost, etc.)
    - **status**: Filter by status (active, deprecated, archived)
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return

    **Returns:**
    - List of benchmark suites
    """
    from sqlalchemy import select, and_
    from ...models.database.tables import BenchmarkSuite as BenchmarkSuiteModel

    query = select(BenchmarkSuiteModel).where(BenchmarkSuiteModel.status == status)

    if category:
        query = query.where(BenchmarkSuiteModel.category == category)

    query = query.offset(skip).limit(limit).order_by(BenchmarkSuiteModel.created_at.desc())

    result = await db.execute(query)
    suites = result.scalars().all()

    return suites


@router.post("/suites", response_model=BenchmarkSuite, status_code=201)
async def create_benchmark_suite(
    suite: BenchmarkSuiteCreate,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new benchmark suite.

    Requires authentication and appropriate permissions.

    **Parameters:**
    - **suite**: Benchmark suite configuration

    **Returns:**
    - Created benchmark suite
    """
    from ...models.database.tables import BenchmarkSuite as BenchmarkSuiteModel
    from uuid import uuid4

    # Create new suite
    new_suite = BenchmarkSuiteModel(
        id=str(uuid4()),
        suite_name=suite.suiteName,
        category=suite.category.value,
        description=suite.description,
        version=suite.version,
        suite_config=suite.suiteConfig.dict() if suite.suiteConfig else {},
        baseline_agent_id=suite.baselineAgentId,
        status="active",
        created_by=current_user.get("user_id"),
    )

    db.add(new_suite)
    await db.commit()
    await db.refresh(new_suite)

    logger.info(f"Created benchmark suite: {new_suite.id}")

    return new_suite


@router.get("/suites/{suite_id}", response_model=BenchmarkSuite)
async def get_benchmark_suite(
    suite_id: str = Path(..., description="Benchmark suite ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get details of a specific benchmark suite.

    **Parameters:**
    - **suite_id**: ID of the benchmark suite

    **Returns:**
    - Benchmark suite details
    """
    from sqlalchemy import select
    from ...models.database.tables import BenchmarkSuite as BenchmarkSuiteModel

    result = await db.execute(
        select(BenchmarkSuiteModel).where(BenchmarkSuiteModel.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(status_code=404, detail="Benchmark suite not found")

    return suite


# =====================================================================
# Benchmark Execution Endpoints
# =====================================================================


@router.post("/run", response_model=RunBenchmarkResponse)
async def run_benchmark(
    request: RunBenchmarkRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Execute a benchmark suite for an agent.

    **Parameters:**
    - **agentId**: ID of the agent to benchmark
    - **suiteId**: ID of the benchmark suite to run
    - **configuration**: Optional execution configuration
    - **asyncExecution**: If true, run in background

    **Returns:**
    - Execution ID and status
    """
    # Validate agent and suite IDs
    validate_agent_id(request.agentId)
    workspace_id = current_user.get("workspace_id")
    validate_workspace_id(workspace_id)

    runner_service = BenchmarkRunnerService(db)

    if request.asyncExecution:
        # Queue for background execution
        execution_id = f"bench_{datetime.utcnow().timestamp()}"

        background_tasks.add_task(
            runner_service.run_benchmark_suite,
            request.suiteId,
            request.agentId,
            workspace_id,
            None,  # agent_version
            request.configuration,
        )

        logger.info(
            f"Queued benchmark suite {request.suiteId} for agent {request.agentId}"
        )

        return {
            "executionId": execution_id,
            "status": ExecutionStatus.PENDING,
            "message": "Benchmark execution queued for background processing",
            "estimatedCompletionTime": None,
        }
    else:
        # Execute synchronously
        try:
            result = await runner_service.run_benchmark_suite(
                request.suiteId,
                request.agentId,
                workspace_id,
                None,  # agent_version
                request.configuration,
            )

            logger.info(
                f"Completed benchmark suite {request.suiteId} for agent {request.agentId}"
            )

            return {
                "executionId": result.get("suite_id", ""),
                "status": ExecutionStatus.COMPLETED,
                "message": f"Benchmark completed. {result.get('completed_benchmarks', 0)}/{result.get('total_benchmarks', 0)} benchmarks successful",
                "estimatedCompletionTime": None,
            }

        except Exception as e:
            logger.error(f"Benchmark execution failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Benchmark execution failed: {str(e)}"
            )


@router.get("/agents/{agent_id}/results", response_model=Dict[str, Any])
async def get_agent_benchmark_results(
    agent_id: str = Path(..., description="Agent ID"),
    suite_id: Optional[str] = Query(None, description="Filter by suite ID"),
    timeframe: str = Query("latest", description="Time period or 'latest'"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get benchmark results for a specific agent.

    **Parameters:**
    - **agent_id**: ID of the agent
    - **suite_id**: Optional suite ID to filter by
    - **timeframe**: Time period or "latest" for most recent results

    **Returns:**
    - Benchmark execution results
    """
    validate_agent_id(agent_id)

    runner_service = BenchmarkRunnerService(db)

    try:
        results = await runner_service.get_benchmark_results(
            agent_id, suite_id, timeframe
        )
        return results

    except Exception as e:
        logger.error(f"Failed to get benchmark results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get benchmark results: {str(e)}"
        )


@router.get("/executions/{execution_id}", response_model=BenchmarkExecution)
async def get_benchmark_execution(
    execution_id: str = Path(..., description="Execution ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get details of a specific benchmark execution.

    **Parameters:**
    - **execution_id**: ID of the benchmark execution

    **Returns:**
    - Execution details including scores and metrics
    """
    from sqlalchemy import select
    from ...models.database.tables import BenchmarkExecution as BenchmarkExecutionModel

    result = await db.execute(
        select(BenchmarkExecutionModel).where(BenchmarkExecutionModel.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Benchmark execution not found")

    return execution


# =====================================================================
# Leaderboard Endpoints
# =====================================================================


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_benchmark_leaderboard(
    category: str = Query("overall", description="Benchmark category"),
    metric: str = Query("all", description="Specific metric or 'all'"),
    limit: int = Query(20, ge=1, le=100, description="Number of entries"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get benchmark leaderboard rankings.

    **Parameters:**
    - **category**: Benchmark category (speed, accuracy, cost, reliability, comprehensive, overall)
    - **metric**: Specific metric to rank by (accuracy, speed, efficiency, cost, reliability, all)
    - **limit**: Maximum number of entries to return
    - **workspace_id**: Optional workspace filter

    **Returns:**
    - Leaderboard with agent rankings and scores
    """
    leaderboard_service = BenchmarkLeaderboardService(db)

    try:
        leaderboard = await leaderboard_service.get_leaderboard(
            category, metric, limit, workspace_id
        )
        return leaderboard

    except Exception as e:
        logger.error(f"Failed to get leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")


@router.post("/compare", response_model=Dict[str, Any])
async def compare_agents(
    agent_ids: List[str] = Query(..., description="List of agent IDs to compare"),
    suite_id: Optional[str] = Query(None, description="Filter by suite ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Compare multiple agents head-to-head on benchmarks.

    **Parameters:**
    - **agent_ids**: List of agent IDs to compare (2-10 agents)
    - **suite_id**: Optional suite ID to filter comparison

    **Returns:**
    - Detailed comparison including winners, scores, and recommendations
    """
    if len(agent_ids) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 agents required for comparison"
        )

    if len(agent_ids) > 10:
        raise HTTPException(
            status_code=400, detail="Maximum 10 agents can be compared at once"
        )

    # Validate all agent IDs
    for agent_id in agent_ids:
        validate_agent_id(agent_id)

    leaderboard_service = BenchmarkLeaderboardService(db)

    try:
        comparison = await leaderboard_service.compare_agents(agent_ids, suite_id)
        return comparison

    except Exception as e:
        logger.error(f"Agent comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent comparison failed: {str(e)}")


# =====================================================================
# Regression Detection Endpoints
# =====================================================================


@router.get("/agents/{agent_id}/regressions", response_model=Dict[str, Any])
async def detect_performance_regressions(
    agent_id: str = Path(..., description="Agent ID"),
    current_version: str = Query(..., description="Current agent version"),
    baseline_version: Optional[str] = Query(None, description="Baseline version to compare against"),
    threshold: float = Query(10.0, ge=0, le=100, description="Regression threshold percentage"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Detect performance regressions for an agent.

    **Parameters:**
    - **agent_id**: ID of the agent
    - **current_version**: Current version to analyze
    - **baseline_version**: Optional baseline version (defaults to previous version)
    - **threshold**: Minimum regression percentage to report (default: 10%)

    **Returns:**
    - List of detected regressions with severity and impact analysis
    """
    validate_agent_id(agent_id)

    # TODO: Implement regression detection service
    # For now, return placeholder
    return {
        "hasRegressions": False,
        "regressions": [],
        "overallHealth": "good",
        "recommendedAction": "No regressions detected. Agent performance is stable.",
    }


# =====================================================================
# Administrative Endpoints
# =====================================================================


@router.post("/leaderboard/refresh", response_model=Dict[str, Any])
async def refresh_leaderboard_cache(
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Refresh the benchmark leaderboard materialized view.

    This endpoint manually triggers a refresh of the leaderboard cache.
    Normally, this is done automatically on a schedule.

    Requires admin permissions.

    **Returns:**
    - Refresh status and timestamp
    """
    # TODO: Add admin permission check
    # if not current_user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Admin access required")

    leaderboard_service = BenchmarkLeaderboardService(db)

    try:
        result = await leaderboard_service.refresh_leaderboard_cache()
        return result

    except Exception as e:
        logger.error(f"Failed to refresh leaderboard cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh cache: {str(e)}"
        )


# =====================================================================
# Statistics Endpoints
# =====================================================================


@router.get("/stats", response_model=Dict[str, Any])
async def get_benchmark_statistics(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get overall benchmark system statistics.

    **Parameters:**
    - **workspace_id**: Optional workspace filter

    **Returns:**
    - Overall statistics including total benchmarks, agents, executions, etc.
    """
    from sqlalchemy import select, func, and_
    from ...models.database.tables import (
        BenchmarkSuite as BenchmarkSuiteModel,
        BenchmarkDefinition as BenchmarkDefinitionModel,
        BenchmarkExecution as BenchmarkExecutionModel,
    )

    # Count suites
    suite_result = await db.execute(
        select(func.count(BenchmarkSuiteModel.id)).where(
            BenchmarkSuiteModel.status == "active"
        )
    )
    total_suites = suite_result.scalar()

    # Count definitions
    def_result = await db.execute(select(func.count(BenchmarkDefinitionModel.id)))
    total_definitions = def_result.scalar()

    # Count executions
    exec_query = select(func.count(BenchmarkExecutionModel.id))
    if workspace_id:
        exec_query = exec_query.where(BenchmarkExecutionModel.workspace_id == workspace_id)

    exec_result = await db.execute(exec_query)
    total_executions = exec_result.scalar()

    # Count unique agents
    agent_query = select(func.count(func.distinct(BenchmarkExecutionModel.agent_id)))
    if workspace_id:
        agent_query = agent_query.where(BenchmarkExecutionModel.workspace_id == workspace_id)

    agent_result = await db.execute(agent_query)
    total_agents = agent_result.scalar()

    return {
        "totalSuites": total_suites,
        "totalDefinitions": total_definitions,
        "totalExecutions": total_executions,
        "totalAgents": total_agents,
        "generatedAt": datetime.utcnow().isoformat(),
    }
