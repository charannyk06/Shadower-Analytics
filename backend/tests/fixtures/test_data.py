"""Test data fixtures."""

from datetime import datetime, date, timedelta


def get_sample_user_metrics():
    """Get sample user metrics data."""
    return {
        "dau": 150,
        "wau": 800,
        "mau": 2500,
        "retention_rate": 0.75,
    }


def get_sample_agent_metrics():
    """Get sample agent metrics data."""
    return {
        "agent_id": "sample-agent-1",
        "total_executions": 1000,
        "successful_executions": 950,
        "failed_executions": 50,
        "success_rate": 95.0,
        "avg_duration": 2.5,
    }


def get_sample_execution_logs():
    """Get sample execution logs."""
    return [
        {
            "execution_id": f"exec-{i}",
            "agent_id": "agent-1",
            "user_id": "user-1",
            "workspace_id": "workspace-1",
            "status": "success" if i % 10 != 0 else "failure",
            "duration": 2.0 + (i * 0.1),
            "started_at": datetime.now() - timedelta(hours=i),
            "completed_at": datetime.now() - timedelta(hours=i) + timedelta(seconds=2),
        }
        for i in range(100)
    ]
