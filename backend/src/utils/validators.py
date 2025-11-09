"""Input validation utilities."""

from datetime import date, datetime
from typing import Any
import re
import html
from fastapi import HTTPException, status


def validate_agent_id(agent_id: str) -> str:
    """
    Validate agent ID format to prevent path traversal and injection attacks.

    Args:
        agent_id: The agent ID to validate

    Returns:
        The validated agent ID

    Raises:
        HTTPException: If agent ID format is invalid
    """
    # Agent IDs: alphanumeric with underscores/hyphens, 1-255 chars
    pattern = r'^[a-zA-Z0-9_-]{1,255}$'

    if not agent_id or not isinstance(agent_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent ID is required and must be a string"
        )

    # Check for path traversal attempts
    if '..' in agent_id or '/' in agent_id or '\\' in agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID: path traversal characters not allowed"
        )

    # Check format (length is enforced by regex pattern {1,255})
    if not re.match(pattern, agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID format. Must be alphanumeric with optional underscores or hyphens (max 255 chars)"
        )

    return agent_id


def validate_workspace_id(workspace_id: str) -> str:
    """
    Validate workspace ID format.

    Workspace IDs are alphanumeric strings with optional hyphens/underscores.

    Args:
        workspace_id: The workspace ID to validate

    Returns:
        The validated workspace ID

    Raises:
        HTTPException: If workspace ID format is invalid
    """
    # Alphanumeric with hyphens/underscores, 1-64 chars
    pattern = r'^[a-zA-Z0-9_-]{1,64}$'

    if not workspace_id or not isinstance(workspace_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace ID is required and must be a string"
        )

    # Check for path traversal
    if '..' in workspace_id or '/' in workspace_id or '\\' in workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID: path traversal characters not allowed"
        )

    # Check format (length is enforced by regex pattern {1,64})
    if not re.match(pattern, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format. Must be alphanumeric with optional hyphens or underscores (max 64 chars)"
        )

    return workspace_id


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format.

    User IDs are alphanumeric strings with optional hyphens/underscores.

    Args:
        user_id: The user ID to validate

    Returns:
        The validated user ID

    Raises:
        HTTPException: If user ID format is invalid
    """
    # User IDs: alphanumeric with underscores/hyphens, 1-255 chars
    pattern = r'^[a-zA-Z0-9_-]{1,255}$'

    if not user_id or not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required and must be a string"
        )

    # Check for path traversal
    if '..' in user_id or '/' in user_id or '\\' in user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID: path traversal characters not allowed"
        )

    # Check format (length is enforced by regex pattern {1,255})
    if not re.match(pattern, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be alphanumeric with optional underscores or hyphens (max 255 chars)"
        )

    return user_id


def sanitize_html_content(content: str, max_length: int = 10000) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        content: The content to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized content

    Raises:
        HTTPException: If content is invalid
    """
    if not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content must be a string"
        )

    # Check length
    if len(content) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content too long (max {max_length} characters)"
        )

    # Escape HTML to prevent XSS
    # This converts < > & " ' to HTML entities
    sanitized = html.escape(content)

    return sanitized


def validate_sql_identifier(identifier: str) -> str:
    """
    Validate SQL identifiers (table names, column names) to prevent SQL injection.

    Args:
        identifier: The identifier to validate

    Returns:
        The validated identifier

    Raises:
        HTTPException: If identifier is invalid
    """
    # Only allow alphanumeric and underscores
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'

    if not identifier or not isinstance(identifier, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier is required and must be a string"
        )

    if not re.match(pattern, identifier):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid identifier format"
        )

    # Prevent SQL keywords
    sql_keywords = {
        'select', 'insert', 'update', 'delete', 'drop', 'create',
        'alter', 'truncate', 'exec', 'execute', 'union', 'where'
    }

    if identifier.lower() in sql_keywords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier cannot be a SQL keyword"
        )

    return identifier


def validate_date_range(start_date: date, end_date: date) -> bool:
    """Validate that date range is valid."""
    if start_date > end_date:
        raise ValueError("Start date must be before end date")

    # Check that range is not too large (e.g., max 2 years)
    max_days = 730  # 2 years
    delta = (end_date - start_date).days

    if delta > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")

    return True


def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe parameter."""
    valid_timeframes = ["7d", "30d", "90d", "1y"]

    if timeframe not in valid_timeframes:
        raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")

    return True


def validate_pagination(skip: int, limit: int) -> bool:
    """Validate pagination parameters."""
    if skip < 0:
        raise ValueError("Skip must be non-negative")

    if limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000")

    return True


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        raise ValueError("Value must be a string")

    # Strip whitespace
    value = value.strip()

    # Check length
    if len(value) > max_length:
        value = value[:max_length]

    return value
