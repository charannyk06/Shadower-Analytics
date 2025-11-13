"""WebSocket error codes and error handling."""

from typing import Tuple, Dict
from fastapi import WebSocket
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebSocketErrorCode:
    """WebSocket error codes."""

    # Authentication errors (4001-4003)
    INVALID_TOKEN = (4001, "Invalid authentication token")
    TOKEN_EXPIRED = (4002, "Authentication token expired")
    ACCESS_DENIED = (4003, "Access denied to resource")

    # Rate limiting (4004)
    RATE_LIMITED = (4004, "Rate limit exceeded")

    # Message errors (4005-4006)
    INVALID_MESSAGE = (4005, "Invalid message format")
    UNKNOWN_MESSAGE_TYPE = (4006, "Unknown message type")

    # Stream errors (4007-4008)
    STREAM_ALREADY_ACTIVE = (4007, "Stream already active")
    STREAM_NOT_FOUND = (4008, "Stream not found")

    # General errors (4000, 4009)
    INTERNAL_ERROR = (4000, "Internal server error")
    INVALID_PARAMETER = (4009, "Invalid parameter")


async def handle_ws_error(
    websocket: WebSocket,
    error_code: Tuple[int, str],
    details: str = None,
    close_connection: bool = True,
):
    """
    Handle WebSocket errors consistently.

    Args:
        websocket: WebSocket connection
        error_code: Tuple of (code, reason)
        details: Optional additional error details
        close_connection: Whether to close the connection after sending error
    """
    code, reason = error_code

    error_message = {
        "type": "error",
        "code": code,
        "message": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        error_message["details"] = details

    try:
        await websocket.send_json(error_message)
        logger.warning(
            f"WebSocket error {code}: {reason}"
            + (f" - {details}" if details else "")
        )

        if close_connection:
            await websocket.close(code=code, reason=reason)

    except Exception as e:
        logger.error(f"Error sending WebSocket error message: {e}")
        try:
            await websocket.close(code=code, reason=reason)
        except:
            pass


async def send_error_message(
    websocket: WebSocket,
    error_type: str,
    message: str,
    details: Dict = None,
):
    """
    Send error message without closing connection.

    Args:
        websocket: WebSocket connection
        error_type: Type of error
        message: Error message
        details: Optional additional details
    """
    error_msg = {
        "type": "error",
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        error_msg["details"] = details

    try:
        await websocket.send_json(error_msg)
    except Exception as e:
        logger.error(f"Error sending error message: {e}")
