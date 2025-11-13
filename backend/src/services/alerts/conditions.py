"""Alert condition validators and evaluators."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import logging

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Base class for alert condition evaluators."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        workspace_id: str,
        metric_type: str,
        condition_config: Dict[str, Any],
        current_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate alert condition.

        Returns:
            tuple of (is_triggered, context_data)
        """
        raise NotImplementedError("Subclasses must implement evaluate()")


class ThresholdConditionEvaluator(ConditionEvaluator):
    """Evaluator for threshold-based alerts."""

    async def evaluate(
        self,
        workspace_id: str,
        metric_type: str,
        condition_config: Dict[str, Any],
        current_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate threshold condition.

        Example condition_config:
        {
            "metric": "error_rate",
            "operator": ">",
            "value": 0.05,
            "duration_minutes": 5
        }
        """
        try:
            operator = condition_config.get("operator")
            threshold_value = condition_config.get("value")
            duration_minutes = condition_config.get("duration_minutes", 5)

            if current_data is None:
                # Fetch current metric value from database
                current_value = await self._get_current_metric_value(
                    workspace_id, metric_type, duration_minutes
                )
            else:
                current_value = current_data.get("value")

            if current_value is None:
                return False, None

            # Evaluate condition
            is_triggered = self._compare_values(current_value, operator, threshold_value)

            context = {
                "metric_type": metric_type,
                "current_value": float(current_value),
                "threshold_value": float(threshold_value),
                "operator": operator,
                "duration_minutes": duration_minutes
            }

            return is_triggered, context

        except Exception as e:
            logger.error(f"Error evaluating threshold condition: {str(e)}")
            return False, None

    def _compare_values(self, value: float, operator: str, threshold: float) -> bool:
        """Compare value against threshold using operator."""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return abs(value - threshold) < 1e-9  # Float equality with tolerance
        elif operator == "!=":
            return abs(value - threshold) >= 1e-9
        return False

    async def _get_current_metric_value(
        self,
        workspace_id: str,
        metric_type: str,
        duration_minutes: int
    ) -> Optional[float]:
        """Get current metric value from database."""
        # This would query the appropriate metrics table based on metric_type
        # For now, return None to indicate no data available
        # In production, this would query execution_metrics_hourly, etc.
        return None


class ChangeConditionEvaluator(ConditionEvaluator):
    """Evaluator for change-based alerts."""

    async def evaluate(
        self,
        workspace_id: str,
        metric_type: str,
        condition_config: Dict[str, Any],
        current_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate change condition.

        Example condition_config:
        {
            "metric": "credit_consumption",
            "change_type": "percent",
            "threshold": 50,
            "comparison_period": "previous_hour"
        }
        """
        try:
            change_type = condition_config.get("change_type", "percent")
            threshold = condition_config.get("threshold")
            comparison_period = condition_config.get("comparison_period", "previous_hour")

            # Get current and historical values
            current_value, previous_value = await self._get_comparison_values(
                workspace_id, metric_type, comparison_period
            )

            if current_value is None or previous_value is None:
                return False, None

            # Prevent division by zero
            if previous_value == 0 and change_type == "percent":
                return False, None

            # Calculate change
            if change_type == "percent":
                change = ((current_value - previous_value) / previous_value) * 100
            else:  # absolute
                change = current_value - previous_value

            # Check if change exceeds threshold
            is_triggered = abs(change) >= threshold

            context = {
                "metric_type": metric_type,
                "current_value": float(current_value),
                "previous_value": float(previous_value),
                "change": float(change),
                "change_type": change_type,
                "threshold": float(threshold),
                "comparison_period": comparison_period
            }

            return is_triggered, context

        except Exception as e:
            logger.error(f"Error evaluating change condition: {str(e)}")
            return False, None

    async def _get_comparison_values(
        self,
        workspace_id: str,
        metric_type: str,
        comparison_period: str
    ) -> tuple[Optional[float], Optional[float]]:
        """Get current and comparison period values."""
        # This would query metrics based on time periods
        # For now, return None values
        return None, None


class AnomalyConditionEvaluator(ConditionEvaluator):
    """Evaluator for anomaly detection alerts."""

    async def evaluate(
        self,
        workspace_id: str,
        metric_type: str,
        condition_config: Dict[str, Any],
        current_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate anomaly condition using statistical methods.

        Example condition_config:
        {
            "metric": "api_latency",
            "sensitivity": 2.5,
            "min_deviation_duration": 10
        }
        """
        try:
            sensitivity = condition_config.get("sensitivity", 2.5)
            min_deviation_duration = condition_config.get("min_deviation_duration", 10)

            # Get historical data for baseline
            historical_values = await self._get_historical_values(
                workspace_id, metric_type, lookback_hours=24
            )

            if len(historical_values) < 10:  # Need minimum data points
                return False, None

            # Calculate statistical baseline
            values_array = np.array(historical_values)
            mean = np.mean(values_array)
            std = np.std(values_array)

            # Get current value
            if current_data:
                current_value = current_data.get("value")
            else:
                current_value = await self._get_current_metric_value(
                    workspace_id, metric_type
                )

            if current_value is None:
                return False, None

            # Calculate z-score
            if std == 0:
                return False, None

            z_score = abs((current_value - mean) / std)

            # Check if anomaly
            is_triggered = z_score > sensitivity

            context = {
                "metric_type": metric_type,
                "current_value": float(current_value),
                "baseline_mean": float(mean),
                "baseline_std": float(std),
                "z_score": float(z_score),
                "sensitivity": sensitivity,
                "deviation_magnitude": float(current_value - mean)
            }

            return is_triggered, context

        except Exception as e:
            logger.error(f"Error evaluating anomaly condition: {str(e)}")
            return False, None

    async def _get_historical_values(
        self,
        workspace_id: str,
        metric_type: str,
        lookback_hours: int = 24
    ) -> List[float]:
        """Get historical metric values for baseline calculation."""
        # This would query historical metrics
        # For now, return empty list
        return []

    async def _get_current_metric_value(
        self,
        workspace_id: str,
        metric_type: str
    ) -> Optional[float]:
        """Get current metric value."""
        return None


class PatternConditionEvaluator(ConditionEvaluator):
    """Evaluator for pattern-based alerts."""

    async def evaluate(
        self,
        workspace_id: str,
        metric_type: str,
        condition_config: Dict[str, Any],
        current_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate pattern condition.

        Example condition_config:
        {
            "pattern": "increasing_errors",
            "window_minutes": 30,
            "min_occurrences": 3
        }
        """
        try:
            pattern = condition_config.get("pattern")
            window_minutes = condition_config.get("window_minutes", 30)
            min_occurrences = condition_config.get("min_occurrences", 3)

            # Get recent data points
            recent_values = await self._get_recent_values(
                workspace_id, metric_type, window_minutes
            )

            if len(recent_values) < min_occurrences:
                return False, None

            # Detect pattern
            pattern_detected = False

            if pattern == "increasing_errors":
                pattern_detected = self._is_increasing_trend(recent_values, min_occurrences)
            elif pattern == "decreasing_performance":
                pattern_detected = self._is_decreasing_trend(recent_values, min_occurrences)
            elif pattern == "spike":
                pattern_detected = self._is_spike(recent_values)
            elif pattern == "flat_line":
                pattern_detected = self._is_flat(recent_values)

            context = {
                "metric_type": metric_type,
                "pattern": pattern,
                "window_minutes": window_minutes,
                "data_points": len(recent_values),
                "recent_values": [float(v) for v in recent_values[-5:]]  # Last 5 values
            }

            return pattern_detected, context

        except Exception as e:
            logger.error(f"Error evaluating pattern condition: {str(e)}")
            return False, None

    def _is_increasing_trend(self, values: List[float], min_occurrences: int) -> bool:
        """Check if values show increasing trend."""
        if len(values) < 2:
            return False

        increasing_count = 0
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increasing_count += 1

        return increasing_count >= min_occurrences

    def _is_decreasing_trend(self, values: List[float], min_occurrences: int) -> bool:
        """Check if values show decreasing trend."""
        if len(values) < 2:
            return False

        decreasing_count = 0
        for i in range(1, len(values)):
            if values[i] < values[i-1]:
                decreasing_count += 1

        return decreasing_count >= min_occurrences

    def _is_spike(self, values: List[float]) -> bool:
        """Check if latest value is a spike compared to recent average."""
        if len(values) < 3:
            return False

        # Compare last value to average of previous values
        previous_avg = np.mean(values[:-1])
        current_value = values[-1]

        # Spike if current value is more than 2x the average
        return current_value > (previous_avg * 2)

    def _is_flat(self, values: List[float]) -> bool:
        """Check if values show no variation (flat line)."""
        if len(values) < 3:
            return False

        std = np.std(values)
        # Consider flat if std dev is very small
        return std < 0.01

    async def _get_recent_values(
        self,
        workspace_id: str,
        metric_type: str,
        window_minutes: int
    ) -> List[float]:
        """Get recent metric values within time window."""
        # This would query recent metrics
        # For now, return empty list
        return []


class ConditionValidator:
    """Validator for alert condition configurations."""

    @staticmethod
    def validate_threshold_condition(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate threshold condition configuration."""
        required_fields = ["metric", "operator", "value"]
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        valid_operators = [">", "<", ">=", "<=", "==", "!="]
        if config["operator"] not in valid_operators:
            return False, f"Invalid operator: {config['operator']}"

        if not isinstance(config["value"], (int, float)):
            return False, "Value must be a number"

        return True, None

    @staticmethod
    def validate_change_condition(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate change condition configuration."""
        required_fields = ["metric", "change_type", "threshold", "comparison_period"]
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        if config["change_type"] not in ["percent", "absolute"]:
            return False, f"Invalid change_type: {config['change_type']}"

        valid_periods = ["previous_hour", "previous_day", "previous_week"]
        if config["comparison_period"] not in valid_periods:
            return False, f"Invalid comparison_period: {config['comparison_period']}"

        return True, None

    @staticmethod
    def validate_anomaly_condition(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate anomaly condition configuration."""
        required_fields = ["metric"]
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        sensitivity = config.get("sensitivity", 2.5)
        if not isinstance(sensitivity, (int, float)) or sensitivity < 1.0 or sensitivity > 5.0:
            return False, "Sensitivity must be between 1.0 and 5.0"

        return True, None

    @staticmethod
    def validate_pattern_condition(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate pattern condition configuration."""
        required_fields = ["metric", "pattern"]
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        valid_patterns = ["increasing_errors", "decreasing_performance", "spike", "flat_line"]
        if config["pattern"] not in valid_patterns:
            return False, f"Invalid pattern: {config['pattern']}"

        return True, None

    @staticmethod
    def validate_condition(condition_type: str, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate condition configuration based on type."""
        validators = {
            "threshold": ConditionValidator.validate_threshold_condition,
            "change": ConditionValidator.validate_change_condition,
            "anomaly": ConditionValidator.validate_anomaly_condition,
            "pattern": ConditionValidator.validate_pattern_condition,
        }

        validator = validators.get(condition_type)
        if not validator:
            return False, f"Unknown condition type: {condition_type}"

        return validator(config)


def get_condition_evaluator(condition_type: str, db: AsyncSession) -> Optional[ConditionEvaluator]:
    """Factory function to get appropriate condition evaluator."""
    evaluators = {
        "threshold": ThresholdConditionEvaluator,
        "change": ChangeConditionEvaluator,
        "anomaly": AnomalyConditionEvaluator,
        "pattern": PatternConditionEvaluator,
    }

    evaluator_class = evaluators.get(condition_type)
    if evaluator_class:
        return evaluator_class(db)

    return None
