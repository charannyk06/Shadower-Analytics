"""Authentication middleware."""

from fastapi import Request, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import time

from ...core.config import settings
from ...core.security import verify_token

security = HTTPBearer()


class JWTAuth:
    """JWT Authentication handler."""

    def __init__(self):
        self.secret = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM

    async def verify_token(
        self, credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """Verify JWT token and return payload."""
        token = credentials.credentials

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])

            # Check expiration
            if payload.get("exp", 0) < time.time():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """Get current user from token."""
        payload = await self.verify_token(credentials)

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "workspace_id": payload.get("workspaceId"),
            "workspaces": payload.get("workspaces", []),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
        }


# Initialize JWT auth
jwt_auth = JWTAuth()


async def verify_jwt_token(credentials: HTTPAuthorizationCredentials):
    """Verify JWT token from request."""
    try:
        token = credentials.credentials
        payload = await verify_token(token)
        return payload
    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) if str(e) else "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthMiddleware:
    """Authentication middleware for protected routes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # Skip auth for health and docs endpoints
        if request.url.path in [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]:
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
