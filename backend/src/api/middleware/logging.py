"""Request logging middleware."""

import time
import logging
from fastapi import Request
from typing import Callable

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log all incoming requests and responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {response.status_code} ({duration:.3f}s)",
            extra={
                "status_code": response.status_code,
                "duration": duration,
                "path": request.url.path,
            },
        )

        # Add custom headers
        response.headers["X-Process-Time"] = str(duration)

        return response
