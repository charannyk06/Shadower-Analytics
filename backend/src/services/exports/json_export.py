"""JSON export functionality."""

import json
from typing import Dict, List, Any
from datetime import datetime, date


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def export_to_json(data: Any, pretty: bool = True) -> str:
    """Export data to JSON format.

    Args:
        data: Data to export (dict, list, etc.)
        pretty: Whether to format JSON with indentation

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(data, cls=DateTimeEncoder, indent=2, sort_keys=True)
    return json.dumps(data, cls=DateTimeEncoder)


def export_metrics_to_json(metrics: Dict) -> str:
    """Export metrics data to JSON."""
    return export_to_json(metrics)
