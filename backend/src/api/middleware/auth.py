"""Authentication middleware."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional

from ...core.config import settings
from ...core.security import verify_token

security = HTTPBearer()


async def verify_jwt_token(credentials: HTTPAuthorizationCredentials):
    """Verify JWT token from request."""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthMiddleware:
    """Authentication middleware for protected routes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # Skip auth for health and docs endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = await verify_token(token)
                request.state.user = payload
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e) if str(e) else "Invalid authentication credentials",
                )

        response = await call_next(request)
        return response
