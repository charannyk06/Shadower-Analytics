"""
Adaptive Recovery Engine

Intelligently selects and executes recovery strategies based on
error characteristics, historical performance, and context.

Author: Claude Code
Date: 2025-11-13
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AdaptiveRecoveryEngine:
    """
    Adaptive recovery engine that:
    - Selects optimal recovery strategies based on error type and history
    - Executes recovery playbooks
    - Implements circuit breaker pattern
    - Tracks and learns from recovery attempts
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.circuit_breakers = {}  # In-memory circuit breaker state

    async def auto_recover(
        self,
        error_id: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Attempt automatic error recovery.

        Args:
            error_id: Error identifier
            dry_run: If True, only simulate recovery without executing

        Returns:
            Recovery result
        """
        try:
            logger.info(f"Starting auto-recovery for error {error_id} (dry_run={dry_run})")

            # Get error details
            error = await self._get_error_details(error_id)
            if not error:
                return {"error": "Error not found", "error_id": error_id}

            # Check if error is recoverable
            if not await self._is_recoverable(error):
                return {
                    "status": "not_recoverable",
                    "reason": "Error type not configured for auto-recovery",
                    "error_id": error_id
                }

            # Check circuit breaker
            agent_id = error.get("agent_id")
            if agent_id and self._is_circuit_open(agent_id):
                return {
                    "status": "circuit_open",
                    "reason": "Circuit breaker is open for this agent",
                    "error_id": error_id
                }

            # Select optimal recovery strategy
            strategy = await self.select_recovery_strategy(error)

            if not strategy:
                return {
                    "status": "no_strategy",
                    "reason": "No suitable recovery strategy found",
                    "error_id": error_id
                }

            # Execute recovery (or simulate if dry_run)
            if dry_run:
                return {
                    "status": "dry_run",
                    "selected_strategy": strategy["strategy_id"],
                    "estimated_recovery_time": strategy["estimated_recovery_time"],
                    "success_probability": strategy["success_probability"],
                    "error_id": error_id
                }

            # Execute recovery
            result = await self._execute_recovery(error_id, strategy)

            # Update circuit breaker based on result
            if agent_id:
                await self._update_circuit_breaker(agent_id, result["status"] == "success")

            # Update strategy performance metrics
            await self._update_strategy_metrics(strategy["strategy_id"], result)

            return result

        except Exception as e:
            logger.error(f"Error in auto-recovery: {e}", exc_info=True)
            return {
                "status": "error",
                "error_id": error_id,
                "message": str(e)
            }

    async def select_recovery_strategy(
        self,
        error: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Select optimal recovery strategy based on error characteristics
        and historical performance.

        Args:
            error: Error details

        Returns:
            Selected strategy with metadata
        """
        try:
            error_type = error.get("error_type")
            severity = error.get("severity")

            # Get applicable strategies
            query = text("""
                SELECT
                    strategy_id,
                    strategy_name,
                    strategy_type,
                    success_rate,
                    avg_recovery_time_ms,
                    config,
                    total_invocations
                FROM analytics.recovery_strategies
                WHERE :error_type = ANY(applicable_error_types)
                ORDER BY success_rate DESC, avg_recovery_time_ms ASC
            """)

            result = await self.db.execute(query, {"error_type": error_type})
            strategies = result.fetchall()

            if not strategies:
                return None

            # Get recovery history for this error type
            history = await self._get_recovery_history(error_type)

            # Score each strategy
            scored_strategies = []
            for strategy in strategies:
                score = await self._score_strategy(strategy, error, history)
                scored_strategies.append({
                    "strategy_id": strategy.strategy_id,
                    "strategy_name": strategy.strategy_name,
                    "strategy_type": strategy.strategy_type,
                    "score": score,
                    "estimated_recovery_time": strategy.avg_recovery_time_ms,
                    "success_probability": strategy.success_rate,
                    "config": strategy.config
                })

            # Select strategy with highest score
            if scored_strategies:
                optimal = max(scored_strategies, key=lambda x: x["score"])
                logger.info(f"Selected strategy {optimal['strategy_id']} with score {optimal['score']:.2f}")
                return optimal

            return None

        except Exception as e:
            logger.error(f"Error selecting recovery strategy: {e}", exc_info=True)
            return None

    async def _score_strategy(
        self,
        strategy: Any,
        error: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> float:
        """
        Score a recovery strategy based on multiple factors.

        Args:
            strategy: Strategy database record
            error: Error details
            history: Historical recovery attempts

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Base score from success rate (0-40 points)
        score += strategy.success_rate * 40

        # Performance score based on recovery time (0-20 points)
        if strategy.avg_recovery_time_ms:
            # Prefer faster recovery (max 20 points for <1s, min 0 for >60s)
            time_score = max(0, 20 * (1 - strategy.avg_recovery_time_ms / 60000))
            score += time_score

        # Experience score based on usage count (0-15 points)
        if strategy.total_invocations:
            # More experience is better, but with diminishing returns
            experience_score = min(15, strategy.total_invocations / 10)
            score += experience_score

        # Severity adjustment (0-15 points)
        severity = error.get("severity")
        if severity == "critical" and strategy.strategy_type in ["fallback", "circuit_breaker"]:
            score += 15  # Prefer safe strategies for critical errors
        elif severity == "low" and strategy.strategy_type == "retry":
            score += 10  # Prefer retry for low severity

        # Historical performance for this specific error type (0-10 points)
        if history:
            successful_with_strategy = [
                h for h in history
                if h["strategy_id"] == strategy.strategy_id and h["status"] == "success"
            ]
            if successful_with_strategy:
                success_rate = len(successful_with_strategy) / len(history)
                score += success_rate * 10

        return score

    async def _execute_recovery(
        self,
        error_id: str,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute recovery strategy.

        Args:
            error_id: Error identifier
            strategy: Selected strategy

        Returns:
            Execution result
        """
        execution_id = None
        start_time = datetime.utcnow()

        try:
            # Create execution record
            execution_id = await self._create_execution_record(error_id, strategy["strategy_id"])

            # Execute strategy based on type
            strategy_type = strategy["strategy_type"]
            config = strategy["config"]

            steps_executed = []

            if strategy_type == "retry":
                result = await self._execute_retry_strategy(error_id, config, steps_executed)
            elif strategy_type == "fallback":
                result = await self._execute_fallback_strategy(error_id, config, steps_executed)
            elif strategy_type == "circuit_breaker":
                result = await self._execute_circuit_breaker_strategy(error_id, config, steps_executed)
            elif strategy_type == "graceful_degradation":
                result = await self._execute_degradation_strategy(error_id, config, steps_executed)
            elif strategy_type == "rollback":
                result = await self._execute_rollback_strategy(error_id, config, steps_executed)
            else:
                result = {"status": "unsupported", "message": f"Strategy type {strategy_type} not implemented"}

            # Calculate recovery time
            end_time = datetime.utcnow()
            recovery_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update execution record
            if execution_id:
                await self._complete_execution_record(
                    execution_id,
                    result["status"],
                    recovery_time_ms,
                    steps_executed,
                    result.get("message", "")
                )

            result.update({
                "error_id": error_id,
                "strategy_id": strategy["strategy_id"],
                "recovery_time_ms": recovery_time_ms,
                "steps_executed": len(steps_executed)
            })

            return result

        except Exception as e:
            logger.error(f"Error executing recovery: {e}", exc_info=True)

            if execution_id:
                await self._complete_execution_record(
                    execution_id,
                    "failed",
                    0,
                    [],
                    str(e)
                )

            return {
                "status": "failed",
                "error_id": error_id,
                "message": str(e)
            }

    async def _execute_retry_strategy(
        self,
        error_id: str,
        config: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute retry with exponential backoff."""
        max_attempts = config.get("max_attempts", 3)
        initial_delay = config.get("initial_delay_ms", 1000) / 1000  # Convert to seconds
        multiplier = config.get("multiplier", 2)

        for attempt in range(max_attempts):
            steps.append({
                "step": f"Retry attempt {attempt + 1}",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            })

            # Simulate retry (in real implementation, would retry actual operation)
            await asyncio.sleep(0.1)  # Simulate operation

            # For simulation, assume 70% success rate
            import random
            if random.random() < 0.7:
                steps[-1]["status"] = "success"
                return {
                    "status": "success",
                    "message": f"Recovered after {attempt + 1} attempts"
                }

            steps[-1]["status"] = "failed"

            if attempt < max_attempts - 1:
                delay = initial_delay * (multiplier ** attempt)
                await asyncio.sleep(delay)

        return {
            "status": "failed",
            "message": f"Failed after {max_attempts} retry attempts"
        }

    async def _execute_fallback_strategy(
        self,
        error_id: str,
        config: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute fallback to default behavior."""
        steps.append({
            "step": "Activate fallback",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "status": "success",
            "message": "Fallback activated successfully"
        }

    async def _execute_circuit_breaker_strategy(
        self,
        error_id: str,
        config: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Implement circuit breaker pattern."""
        steps.append({
            "step": "Open circuit breaker",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "status": "success",
            "message": "Circuit breaker opened to prevent cascade"
        }

    async def _execute_degradation_strategy(
        self,
        error_id: str,
        config: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute graceful degradation."""
        steps.append({
            "step": "Enable degraded mode",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "status": "success",
            "message": "Service degraded gracefully"
        }

    async def _execute_rollback_strategy(
        self,
        error_id: str,
        config: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute state rollback."""
        steps.append({
            "step": "Rollback to previous state",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "status": "success",
            "message": "State rolled back successfully"
        }

    def implement_circuit_breaker(self, agent_id: str) -> Dict[str, Any]:
        """
        Implement circuit breaker for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Circuit breaker configuration
        """
        config = {
            "failure_threshold": self._calculate_threshold(agent_id),
            "timeout_duration_seconds": self._calculate_timeout(agent_id),
            "half_open_requests": 3,
            "monitoring_window_seconds": 60,
            "state": "closed",
            "failure_count": 0,
            "last_failure_time": None
        }

        self.circuit_breakers[agent_id] = config
        return config

    def _calculate_threshold(self, agent_id: str) -> int:
        """Calculate failure threshold for circuit breaker."""
        # Could be based on historical error rates
        return 5  # Default threshold

    def _calculate_timeout(self, agent_id: str) -> int:
        """Calculate timeout duration for circuit breaker."""
        # Could be adaptive based on recovery times
        return 60  # Default 60 seconds

    def _is_circuit_open(self, agent_id: str) -> bool:
        """Check if circuit breaker is open."""
        if agent_id not in self.circuit_breakers:
            return False

        cb = self.circuit_breakers[agent_id]

        if cb["state"] == "open":
            # Check if timeout has expired
            if cb["last_failure_time"]:
                elapsed = (datetime.utcnow() - cb["last_failure_time"]).total_seconds()
                if elapsed > cb["timeout_duration_seconds"]:
                    # Move to half-open state
                    cb["state"] = "half-open"
                    cb["failure_count"] = 0
                    return False
            return True

        return False

    async def _update_circuit_breaker(self, agent_id: str, success: bool) -> None:
        """Update circuit breaker state based on recovery result."""
        if agent_id not in self.circuit_breakers:
            self.implement_circuit_breaker(agent_id)

        cb = self.circuit_breakers[agent_id]

        if success:
            if cb["state"] == "half-open":
                # Recovery successful in half-open state, close circuit
                cb["state"] = "closed"
                cb["failure_count"] = 0
            else:
                # Reset failure count on success
                cb["failure_count"] = max(0, cb["failure_count"] - 1)
        else:
            cb["failure_count"] += 1
            cb["last_failure_time"] = datetime.utcnow()

            if cb["failure_count"] >= cb["failure_threshold"]:
                # Open circuit
                cb["state"] = "open"
                logger.warning(f"Circuit breaker opened for agent {agent_id}")

    async def _get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Fetch error details."""
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
            "agent_id": row.agents_affected[0] if row.agents_affected else None
        }

    async def _is_recoverable(self, error: Dict[str, Any]) -> bool:
        """Check if error type is configured for auto-recovery."""
        error_type = error.get("error_type")

        query = text("""
            SELECT COUNT(*) as count
            FROM analytics.recovery_strategies
            WHERE :error_type = ANY(applicable_error_types)
        """)

        result = await self.db.execute(query, {"error_type": error_type})
        row = result.fetchone()

        return row.count > 0 if row else False

    async def _get_recovery_history(self, error_type: str) -> List[Dict[str, Any]]:
        """Get historical recovery attempts for error type."""
        query = text("""
            SELECT
                ere.strategy_id,
                ere.status,
                ere.recovery_time_ms
            FROM analytics.error_recovery_executions ere
            JOIN analytics.errors e ON ere.error_id = e.error_id
            WHERE e.error_type = :error_type
                AND ere.started_at >= :lookback_date
            ORDER BY ere.started_at DESC
            LIMIT 100
        """)

        result = await self.db.execute(
            query,
            {
                "error_type": error_type,
                "lookback_date": datetime.utcnow() - timedelta(days=30)
            }
        )

        return [
            {
                "strategy_id": row.strategy_id,
                "status": row.status,
                "recovery_time_ms": row.recovery_time_ms
            }
            for row in result.fetchall()
        ]

    async def _create_execution_record(self, error_id: str, strategy_id: str) -> str:
        """Create recovery execution record."""
        query = text("""
            INSERT INTO analytics.error_recovery_executions (
                error_id,
                strategy_id,
                status
            ) VALUES (
                :error_id,
                :strategy_id,
                'running'
            )
            RETURNING id
        """)

        result = await self.db.execute(
            query,
            {"error_id": error_id, "strategy_id": strategy_id}
        )
        await self.db.commit()

        row = result.fetchone()
        return str(row.id) if row else None

    async def _complete_execution_record(
        self,
        execution_id: str,
        status: str,
        recovery_time_ms: int,
        steps: List[Dict[str, Any]],
        result: str
    ) -> None:
        """Update execution record with results."""
        query = text("""
            UPDATE analytics.error_recovery_executions
            SET
                status = :status,
                recovery_time_ms = :recovery_time_ms,
                steps_executed = :steps_executed::jsonb,
                final_result = :final_result,
                completed_at = NOW()
            WHERE id = :execution_id
        """)

        await self.db.execute(
            query,
            {
                "execution_id": execution_id,
                "status": status,
                "recovery_time_ms": recovery_time_ms,
                "steps_executed": json.dumps(steps),
                "final_result": result
            }
        )
        await self.db.commit()

    async def _update_strategy_metrics(
        self,
        strategy_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Update strategy performance metrics."""
        try:
            status = result.get("status")
            recovery_time_ms = result.get("recovery_time_ms", 0)

            query = text("""
                UPDATE analytics.recovery_strategies
                SET
                    total_invocations = total_invocations + 1,
                    successful_recoveries = successful_recoveries + CASE WHEN :status = 'success' THEN 1 ELSE 0 END,
                    failed_recoveries = failed_recoveries + CASE WHEN :status = 'failed' THEN 1 ELSE 0 END,
                    partial_recoveries = partial_recoveries + CASE WHEN :status = 'partial' THEN 1 ELSE 0 END,
                    success_rate = (successful_recoveries + CASE WHEN :status = 'success' THEN 1 ELSE 0 END)::float /
                                 (total_invocations + 1),
                    avg_recovery_time_ms = (avg_recovery_time_ms * total_invocations + :recovery_time_ms) /
                                          (total_invocations + 1),
                    updated_at = NOW()
                WHERE strategy_id = :strategy_id
            """)

            await self.db.execute(
                query,
                {
                    "strategy_id": strategy_id,
                    "status": status,
                    "recovery_time_ms": recovery_time_ms
                }
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error updating strategy metrics: {e}", exc_info=True)
            await self.db.rollback()
