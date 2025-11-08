"""Database enumerations."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Metric type values."""

    USER = "user"
    AGENT = "agent"
    EXECUTION = "execution"
    WORKSPACE = "workspace"
    BUSINESS = "business"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
