"""Permission and role-based access control decorators."""

from functools import wraps
from fastapi import HTTPException, status
from typing import List, Callable, Dict, Any


def require_permission(*required_permissions: str):
    """Decorator to check for specific permissions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by FastAPI)
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_permissions = current_user.get("permissions", [])

            # Check if user has any of the required permissions
            has_permission = any(perm in user_permissions for perm in required_permissions)

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required permissions: {', '.join(required_permissions)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*allowed_roles: str):
    """Decorator to check for specific roles."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_role = current_user.get("role")

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: {' or '.join(allowed_roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_permission(user: Dict[str, Any], *required_permissions: str) -> bool:
    """Check if user has required permissions."""
    if not user:
        return False

    user_permissions = user.get("permissions", [])
    return any(perm in user_permissions for perm in required_permissions)


def check_role(user: Dict[str, Any], *allowed_roles: str) -> bool:
    """Check if user has required role."""
    if not user:
        return False

    user_role = user.get("role")
    return user_role in allowed_roles
