"""Structured logging configuration with JSON formatting."""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log records."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add service information
        log_record['service'] = 'analytics-backend'
        log_record['environment'] = os.getenv('APP_ENV', 'development')
        log_record['version'] = os.getenv('APP_VERSION', 'unknown')

        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id

        if hasattr(record, 'workspace_id'):
            log_record['workspace_id'] = record.workspace_id

        # Add trace context if available
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id

        if hasattr(record, 'span_id'):
            log_record['span_id'] = record.span_id

        # Ensure level is included
        if 'level' not in log_record:
            log_record['level'] = record.levelname


def setup_logging() -> logging.Logger:
    """Configure structured logging for the application.

    Returns:
        Root logger instance
    """
    # Create JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={
            'levelname': 'level',
            'name': 'logger',
            'pathname': 'file',
            'lineno': 'line'
        }
    )

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    root_logger.addHandler(console_handler)

    # Configure third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('alembic').setLevel(logging.INFO)
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('redis').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(
        "Structured logging initialized",
        extra={
            'environment': os.getenv('APP_ENV', 'development'),
            'version': os.getenv('APP_VERSION', 'unknown')
        }
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
