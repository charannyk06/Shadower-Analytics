"""Security middleware for HTTP security headers."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    This middleware implements best practices for HTTP security headers
    to protect against common web vulnerabilities.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response with security headers added
        """
        # Process the request
        response = await call_next(request)

        # Add security headers
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS connections (strict transport security)
        # max-age: 1 year in seconds
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Content Security Policy
        # Restrict resources to same origin by default
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for development
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles
            "img-src 'self' data: https:",  # Allow images from self, data URIs, and HTTPS
            "font-src 'self' data:",  # Allow fonts from self and data URIs
            "connect-src 'self' ws: wss:",  # Allow WebSocket connections
            "frame-ancestors 'none'",  # Equivalent to X-Frame-Options: DENY
            "base-uri 'self'",  # Restrict base tag URLs
            "form-action 'self'",  # Restrict form submissions
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer policy - control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (formerly Feature-Policy)
        # Disable potentially dangerous browser features
        permissions_directives = [
            "geolocation=()",  # Disable geolocation
            "microphone=()",   # Disable microphone
            "camera=()",       # Disable camera
            "payment=()",      # Disable payment API
            "usb=()",          # Disable USB API
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        # Remove server header for security through obscurity
        response.headers.pop("Server", None)

        # Add custom security header with API version
        response.headers["X-API-Version"] = "v1"

        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit information to response headers.

    This helps clients understand their rate limit status.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add rate limit headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response with rate limit headers
        """
        response = await call_next(request)

        # Add rate limit headers (values would come from actual rate limiting logic)
        # These are placeholders - actual values should come from rate limiter
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "999"
        response.headers["X-RateLimit-Reset"] = "3600"

        return response
