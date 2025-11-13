"""Benchmark runner service for executing agent performance benchmarks."""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from uuid import uuid4

from ...models.database.tables import (
    BenchmarkSuite,
    BenchmarkDefinition,
    BenchmarkExecution,
)
from ...models.schemas.benchmarks import (
    ExecutionStatus,
    PerformanceScores,
    QualityMetrics,
)

logger = logging.getLogger(__name__)


class BenchmarkRunnerService:
    """Service for executing agent benchmarks and collecting metrics."""

    # Configuration
    QUERY_TIMEOUT_SECONDS = 60
    MAX_WARMUP_RUNS = 10
    MAX_BENCHMARK_RUNS = 20
    DEFAULT_NUM_RUNS = 5
    DEFAULT_WARMUP_RUNS = 3

    def __init__(self, db: AsyncSession):
        """Initialize the benchmark runner service.

        Args:
            db: Async database session
        """
        self.db = db

    async def run_benchmark_suite(
        self,
        suite_id: str,
        agent_id: str,
        workspace_id: str,
        agent_version: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a complete benchmark suite for an agent.

        Args:
            suite_id: ID of the benchmark suite to run
            agent_id: ID of the agent to benchmark
            workspace_id: ID of the workspace
            agent_version: Version of the agent (optional)
            configuration: Additional configuration options

        Returns:
            Dictionary containing suite execution results

        Raises:
            ValueError: If suite or agent not found
            RuntimeError: If execution fails
        """
        logger.info(f"Starting benchmark suite {suite_id} for agent {agent_id}")

        # Load benchmark suite
        suite = await self._load_benchmark_suite(suite_id)
        if not suite:
            raise ValueError(f"Benchmark suite {suite_id} not found")

        # Load benchmark definitions for this suite
        benchmarks = await self._load_benchmark_definitions(suite_id)
        if not benchmarks:
            raise ValueError(f"No benchmark definitions found for suite {suite_id}")

        logger.info(f"Found {len(benchmarks)} benchmarks in suite")

        # Execute each benchmark
        results = []
        for benchmark in benchmarks:
            try:
                logger.info(f"Executing benchmark: {benchmark.benchmark_name}")

                # Run warmup executions
                if benchmark.warmup_runs > 0:
                    await self._run_warmup_executions(
                        benchmark, agent_id, workspace_id, configuration
                    )

                # Run actual benchmark executions
                benchmark_results = await self._run_benchmark_executions(
                    suite_id,
                    benchmark,
                    agent_id,
                    workspace_id,
                    agent_version,
                    configuration,
                )

                results.extend(benchmark_results)

                logger.info(
                    f"Completed benchmark {benchmark.benchmark_name} with {len(benchmark_results)} runs"
                )

            except Exception as e:
                logger.error(
                    f"Error executing benchmark {benchmark.benchmark_name}: {str(e)}",
                    exc_info=True,
                )
                # Create failed execution record
                await self._create_failed_execution(
                    suite_id,
                    benchmark.id,
                    agent_id,
                    workspace_id,
                    agent_version,
                    str(e),
                )

        # Generate suite-level report
        report = await self._generate_suite_report(suite_id, agent_id, results)

        logger.info(f"Benchmark suite {suite_id} completed for agent {agent_id}")

        return report

    async def _load_benchmark_suite(self, suite_id: str) -> Optional[BenchmarkSuite]:
        """Load a benchmark suite from database."""
        result = await self.db.execute(
            select(BenchmarkSuite).where(
                and_(
                    BenchmarkSuite.id == suite_id,
                    BenchmarkSuite.status == "active",
                )
            )
        )
        return result.scalar_one_or_none()

    async def _load_benchmark_definitions(
        self, suite_id: str
    ) -> List[BenchmarkDefinition]:
        """Load all benchmark definitions for a suite."""
        result = await self.db.execute(
            select(BenchmarkDefinition)
            .where(BenchmarkDefinition.suite_id == suite_id)
            .order_by(BenchmarkDefinition.created_at)
        )
        return result.scalars().all()

    async def _run_warmup_executions(
        self,
        benchmark: BenchmarkDefinition,
        agent_id: str,
        workspace_id: str,
        configuration: Optional[Dict[str, Any]],
    ) -> None:
        """Run warmup executions to stabilize performance measurements."""
        num_warmup = min(benchmark.warmup_runs, self.MAX_WARMUP_RUNS)

        logger.info(f"Running {num_warmup} warmup executions")

        for i in range(num_warmup):
            try:
                await self._execute_agent(
                    agent_id,
                    benchmark.test_data,
                    configuration,
                    benchmark.constraints.timeLimitMs
                    if benchmark.constraints
                    else None,
                )
            except Exception as e:
                logger.warning(f"Warmup execution {i+1} failed: {str(e)}")
                # Continue with other warmup runs

    async def _run_benchmark_executions(
        self,
        suite_id: str,
        benchmark: BenchmarkDefinition,
        agent_id: str,
        workspace_id: str,
        agent_version: Optional[str],
        configuration: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Run multiple benchmark executions and store results."""
        num_runs = min(benchmark.num_runs, self.MAX_BENCHMARK_RUNS)
        execution_ids = []

        for run_number in range(1, num_runs + 1):
            try:
                execution_id = await self._execute_single_benchmark(
                    suite_id,
                    benchmark,
                    agent_id,
                    workspace_id,
                    agent_version,
                    configuration,
                    run_number,
                )
                execution_ids.append(execution_id)

            except Exception as e:
                logger.error(f"Benchmark run {run_number} failed: {str(e)}")
                # Create failed execution record
                await self._create_failed_execution(
                    suite_id,
                    benchmark.id,
                    agent_id,
                    workspace_id,
                    agent_version,
                    str(e),
                    run_number,
                )

        return execution_ids

    async def _execute_single_benchmark(
        self,
        suite_id: str,
        benchmark: BenchmarkDefinition,
        agent_id: str,
        workspace_id: str,
        agent_version: Optional[str],
        configuration: Optional[Dict[str, Any]],
        run_number: int,
    ) -> str:
        """Execute a single benchmark run and store results."""
        execution_id = str(uuid4())
        start_time = datetime.utcnow()
        start_metrics = await self._capture_system_metrics()

        # Create execution record (pending status)
        execution = BenchmarkExecution(
            id=execution_id,
            suite_id=suite_id,
            benchmark_id=benchmark.id,
            agent_id=agent_id,
            agent_version=agent_version,
            workspace_id=workspace_id,
            run_number=run_number,
            start_time=start_time,
            status=ExecutionStatus.RUNNING.value,
            execution_environment=await self._get_execution_environment(),
            model_configuration=configuration or {},
        )

        self.db.add(execution)
        await self.db.flush()

        try:
            # Execute the agent with benchmark input
            output, execution_time_ms = await self._execute_agent(
                agent_id,
                benchmark.test_data,
                configuration,
                benchmark.constraints.timeLimitMs if benchmark.constraints else None,
            )

            end_time = datetime.utcnow()
            end_metrics = await self._capture_system_metrics()

            # Validate output against expected results
            validation_results = await self._validate_output(
                output, benchmark.expected_outputs
            )

            # Calculate performance scores
            scores = await self._calculate_scores(
                benchmark,
                output,
                validation_results,
                execution_time_ms,
                end_metrics,
                start_metrics,
            )

            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(
                output, benchmark.expected_outputs, validation_results
            )

            # Calculate comparative metrics
            percentile_rank = await self._calculate_percentile_rank(
                benchmark.id, scores.get("overall_score", 0)
            )

            # Update execution record with results
            execution.end_time = end_time
            execution.total_duration_ms = execution_time_ms
            execution.status = ExecutionStatus.COMPLETED.value

            # Scores
            execution.accuracy_score = scores.get("accuracy_score")
            execution.speed_score = scores.get("speed_score")
            execution.efficiency_score = scores.get("efficiency_score")
            execution.cost_score = scores.get("cost_score")
            execution.reliability_score = scores.get("reliability_score")
            execution.overall_score = scores.get("overall_score")

            # Quality metrics
            execution.output_correctness = quality_metrics.get("correctness")
            execution.output_completeness = quality_metrics.get("completeness")
            execution.output_relevance = quality_metrics.get("relevance")

            # Resource metrics
            execution.tokens_used = scores.get("tokens_used", 0)
            execution.api_calls_made = scores.get("api_calls_made", 0)
            execution.memory_peak_mb = end_metrics.get("memory_mb")
            execution.cpu_usage_percent = end_metrics.get("cpu_percent")

            # Results
            execution.actual_output = output
            execution.validation_results = validation_results
            execution.detailed_metrics = scores
            execution.percentile_rank = percentile_rank

            await self.db.commit()

            logger.info(
                f"Benchmark execution {execution_id} completed successfully. "
                f"Overall score: {scores.get('overall_score', 0):.2f}"
            )

            return execution_id

        except asyncio.TimeoutError:
            # Handle timeout
            execution.status = ExecutionStatus.TIMEOUT.value
            execution.error_details = "Execution exceeded time limit"
            await self.db.commit()
            raise

        except Exception as e:
            # Handle other errors
            execution.status = ExecutionStatus.FAILED.value
            execution.error_details = str(e)
            await self.db.commit()
            raise

    async def _execute_agent(
        self,
        agent_id: str,
        test_data: Dict[str, Any],
        configuration: Optional[Dict[str, Any]],
        timeout_ms: Optional[int],
    ) -> tuple[Dict[str, Any], int]:
        """Execute the agent with the given test data.

        Args:
            agent_id: ID of the agent to execute
            test_data: Input test data
            configuration: Execution configuration
            timeout_ms: Timeout in milliseconds

        Returns:
            Tuple of (output, execution_time_ms)
        """
        # TODO: Implement actual agent execution
        # This is a placeholder that should integrate with your agent execution system
        start_time = time.time()

        try:
            # Simulate agent execution
            # In production, this would call your actual agent execution API
            await asyncio.sleep(0.1)  # Simulate work
            output = {
                "result": "success",
                "data": "Sample output",
                "metadata": {"agent_id": agent_id},
            }

            execution_time_ms = int((time.time() - start_time) * 1000)

            return output, execution_time_ms

        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            raise

    async def _capture_system_metrics(self) -> Dict[str, Any]:
        """Capture current system resource metrics."""
        # TODO: Implement actual system metrics capture
        # This would use psutil or similar to capture real metrics
        return {
            "memory_mb": 256.5,
            "cpu_percent": 45.2,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _get_execution_environment(self) -> Dict[str, Any]:
        """Get execution environment details."""
        # TODO: Capture actual environment details
        return {
            "platform": "linux",
            "python_version": "3.11",
            "cpu_cores": 4,
            "memory_total_gb": 16,
        }

    async def _validate_output(
        self, output: Dict[str, Any], expected_outputs: Optional[List[Any]]
    ) -> Dict[str, Any]:
        """Validate agent output against expected results."""
        if not expected_outputs:
            return {"validated": False, "reason": "No expected outputs defined"}

        # TODO: Implement sophisticated output validation
        # This could include:
        # - Exact match checking
        # - Fuzzy matching for text
        # - Semantic similarity for natural language
        # - Structural comparison for JSON/objects

        return {
            "validated": True,
            "match_score": 95.5,
            "differences": [],
        }

    async def _calculate_scores(
        self,
        benchmark: BenchmarkDefinition,
        output: Dict[str, Any],
        validation_results: Dict[str, Any],
        execution_time_ms: int,
        end_metrics: Dict[str, Any],
        start_metrics: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate performance scores based on benchmark results."""
        scoring_rubric = benchmark.scoring_rubric or {}

        # Accuracy score (based on output validation)
        accuracy_score = validation_results.get("match_score", 0)

        # Speed score (based on execution time vs time limit)
        if benchmark.constraints and benchmark.constraints.timeLimitMs:
            time_ratio = execution_time_ms / benchmark.constraints.timeLimitMs
            speed_score = max(0, min(100, 100 * (2 - time_ratio)))
        else:
            # Use a default baseline
            baseline_time_ms = 10000  # 10 seconds
            time_ratio = execution_time_ms / baseline_time_ms
            speed_score = max(0, min(100, 100 * (2 - time_ratio)))

        # Efficiency score (resource usage vs limits)
        memory_used = end_metrics.get("memory_mb", 0) - start_metrics.get(
            "memory_mb", 0
        )
        if benchmark.constraints and benchmark.constraints.memoryLimitMb:
            memory_ratio = memory_used / benchmark.constraints.memoryLimitMb
            efficiency_score = max(0, min(100, 100 * (2 - memory_ratio)))
        else:
            # Default baseline
            efficiency_score = max(0, min(100, 100 - (memory_used / 100) * 10))

        # Cost score (token usage vs limit)
        tokens_used = output.get("metadata", {}).get("tokens_used", 0)
        if benchmark.constraints and benchmark.constraints.tokenLimit:
            token_ratio = tokens_used / benchmark.constraints.tokenLimit
            cost_score = max(0, min(100, 100 * (2 - token_ratio)))
        else:
            # Default baseline
            baseline_tokens = 1000
            token_ratio = tokens_used / baseline_tokens
            cost_score = max(0, min(100, 100 * (2 - token_ratio)))

        # Reliability score (successful execution = high score)
        reliability_score = 100 if validation_results.get("validated") else 50

        # Overall score (weighted average based on rubric or defaults)
        weights = scoring_rubric.get(
            "weights",
            {
                "accuracy": 0.3,
                "speed": 0.2,
                "efficiency": 0.2,
                "cost": 0.15,
                "reliability": 0.15,
            },
        )

        overall_score = (
            accuracy_score * weights.get("accuracy", 0.3)
            + speed_score * weights.get("speed", 0.2)
            + efficiency_score * weights.get("efficiency", 0.2)
            + cost_score * weights.get("cost", 0.15)
            + reliability_score * weights.get("reliability", 0.15)
        )

        return {
            "accuracy_score": round(accuracy_score, 2),
            "speed_score": round(speed_score, 2),
            "efficiency_score": round(efficiency_score, 2),
            "cost_score": round(cost_score, 2),
            "reliability_score": round(reliability_score, 2),
            "overall_score": round(overall_score, 2),
            "tokens_used": tokens_used,
            "api_calls_made": output.get("metadata", {}).get("api_calls", 1),
        }

    async def _calculate_quality_metrics(
        self,
        output: Dict[str, Any],
        expected_outputs: Optional[List[Any]],
        validation_results: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate output quality metrics."""
        # TODO: Implement sophisticated quality assessment
        return {
            "correctness": validation_results.get("match_score", 0),
            "completeness": 95.0,
            "relevance": 90.0,
        }

    async def _calculate_percentile_rank(
        self, benchmark_id: str, score: float
    ) -> Optional[float]:
        """Calculate percentile rank for a score within a benchmark."""
        try:
            # Query all scores for this benchmark
            result = await self.db.execute(
                select(BenchmarkExecution.overall_score)
                .where(
                    and_(
                        BenchmarkExecution.benchmark_id == benchmark_id,
                        BenchmarkExecution.status == ExecutionStatus.COMPLETED.value,
                        BenchmarkExecution.overall_score.isnot(None),
                    )
                )
                .order_by(BenchmarkExecution.overall_score)
            )

            scores = [s[0] for s in result.fetchall()]
            if not scores:
                return None

            # Calculate percentile
            scores.append(score)
            scores.sort()
            rank = scores.index(score) / len(scores) * 100

            return round(rank, 2)

        except Exception as e:
            logger.error(f"Error calculating percentile rank: {str(e)}")
            return None

    async def _create_failed_execution(
        self,
        suite_id: str,
        benchmark_id: str,
        agent_id: str,
        workspace_id: str,
        agent_version: Optional[str],
        error_message: str,
        run_number: int = 1,
    ) -> None:
        """Create a failed execution record."""
        execution = BenchmarkExecution(
            id=str(uuid4()),
            suite_id=suite_id,
            benchmark_id=benchmark_id,
            agent_id=agent_id,
            agent_version=agent_version,
            workspace_id=workspace_id,
            run_number=run_number,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status=ExecutionStatus.FAILED.value,
            error_details=error_message[:500],  # Limit error message length
        )

        self.db.add(execution)
        await self.db.commit()

    async def _generate_suite_report(
        self, suite_id: str, agent_id: str, execution_ids: List[str]
    ) -> Dict[str, Any]:
        """Generate a comprehensive report for the benchmark suite execution."""
        if not execution_ids:
            return {
                "suite_id": suite_id,
                "agent_id": agent_id,
                "status": "failed",
                "message": "No successful executions",
            }

        # Fetch all execution results
        result = await self.db.execute(
            select(BenchmarkExecution).where(
                BenchmarkExecution.id.in_(execution_ids)
            )
        )
        executions = result.scalars().all()

        # Calculate aggregate metrics
        completed_executions = [
            e for e in executions if e.status == ExecutionStatus.COMPLETED.value
        ]

        if not completed_executions:
            return {
                "suite_id": suite_id,
                "agent_id": agent_id,
                "status": "failed",
                "message": "No completed executions",
            }

        avg_accuracy = sum(e.accuracy_score or 0 for e in completed_executions) / len(
            completed_executions
        )
        avg_speed = sum(e.speed_score or 0 for e in completed_executions) / len(
            completed_executions
        )
        avg_efficiency = sum(e.efficiency_score or 0 for e in completed_executions) / len(
            completed_executions
        )
        avg_cost = sum(e.cost_score or 0 for e in completed_executions) / len(
            completed_executions
        )
        avg_reliability = sum(
            e.reliability_score or 0 for e in completed_executions
        ) / len(completed_executions)
        avg_overall = sum(e.overall_score or 0 for e in completed_executions) / len(
            completed_executions
        )

        return {
            "suite_id": suite_id,
            "agent_id": agent_id,
            "status": "completed",
            "total_benchmarks": len(execution_ids),
            "completed_benchmarks": len(completed_executions),
            "failed_benchmarks": len(executions) - len(completed_executions),
            "average_scores": {
                "accuracy": round(avg_accuracy, 2),
                "speed": round(avg_speed, 2),
                "efficiency": round(avg_efficiency, 2),
                "cost": round(avg_cost, 2),
                "reliability": round(avg_reliability, 2),
                "overall": round(avg_overall, 2),
            },
            "execution_ids": execution_ids,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def get_benchmark_results(
        self,
        agent_id: str,
        suite_id: Optional[str] = None,
        timeframe: str = "latest",
    ) -> Dict[str, Any]:
        """Get benchmark results for an agent.

        Args:
            agent_id: ID of the agent
            suite_id: Optional suite ID to filter by
            timeframe: Time period or "latest" for most recent

        Returns:
            Dictionary containing benchmark results
        """
        query = select(BenchmarkExecution).where(
            and_(
                BenchmarkExecution.agent_id == agent_id,
                BenchmarkExecution.status == ExecutionStatus.COMPLETED.value,
            )
        )

        if suite_id:
            query = query.where(BenchmarkExecution.suite_id == suite_id)

        if timeframe == "latest":
            query = query.order_by(desc(BenchmarkExecution.created_at)).limit(10)
        else:
            # TODO: Parse timeframe and filter by date
            pass

        result = await self.db.execute(query)
        executions = result.scalars().all()

        return {
            "agent_id": agent_id,
            "total_executions": len(executions),
            "executions": [
                {
                    "id": e.id,
                    "benchmark_id": e.benchmark_id,
                    "suite_id": e.suite_id,
                    "overall_score": e.overall_score,
                    "accuracy_score": e.accuracy_score,
                    "speed_score": e.speed_score,
                    "efficiency_score": e.efficiency_score,
                    "cost_score": e.cost_score,
                    "reliability_score": e.reliability_score,
                    "duration_ms": e.total_duration_ms,
                    "executed_at": e.created_at.isoformat(),
                }
                for e in executions
            ],
        }
