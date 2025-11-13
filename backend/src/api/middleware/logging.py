"""Request logging middleware with structured logging and request tracking."""

import time
import logging
import uuid
from fastapi import Request
from typing import Callable

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log all incoming requests and responses with structured context."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract user context if available
        user_id = None
        workspace_id = None

        # Try to get user context from request state (set by auth middleware)
        if hasattr(request.state, 'user'):
            user = request.state.user
            user_id = getattr(user, 'id', None)
            workspace_id = getattr(user, 'workspace_id', None)

        # Start timer
        start_time = time.time()

        # Build log context
        log_context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "workspace_id": workspace_id,
        }

        # Log request
        logger.info(
            "Request started",
            extra=log_context
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Update log context with response info
            response_context = {
                **log_context,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }

            # Log response with appropriate level based on status code
            if response.status_code >= 500:
                logger.error("Request failed with server error", extra=response_context)
            elif response.status_code >= 400:
                logger.warning("Request failed with client error", extra=response_context)
            else:
                logger.info("Request completed", extra=response_context)

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log exception
            error_context = {
                **log_context,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration * 1000, 2)
            }

            logger.error(
                "Request failed with exception",
                extra=error_context,
                exc_info=True
            )

            # Re-raise exception
            raise
