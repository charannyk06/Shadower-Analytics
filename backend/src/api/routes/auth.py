"""Authentication and authorization routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from uuid import uuid4
import logging
import secrets
import hashlib

from ...models.schemas.auth import (
    TokenVerification,
    TokenVerificationResponse,
    TokenResponse,
    RefreshTokenRequest,
    UserPermissionsResponse,
    PermissionUpdate,
    PermissionSet,
    UserRole,
    LogoutResponse,
    CurrentUserResponse,
    APIKeyConfig,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyListItem,
    APIKeyRevokeResponse,
    SessionInfo,
    SessionListResponse,
    SessionTerminateResponse,
)
from ...models.database.tables import APIKey, UserSession
from ...core.security import create_access_token, verify_token
from ...core.config import settings
from ...core.token_manager import blacklist_token, invalidate_token_cache
from ...core.permissions import get_permissions_for_role, has_permission
from ...core.database import get_db
from ..dependencies.auth import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/verify", response_model=TokenVerificationResponse)
async def verify_token_endpoint(
    token_data: TokenVerification,
) -> TokenVerificationResponse:
    """
    Verify JWT token from main app.

    This endpoint validates tokens issued by the main Shadower application
    and verifies workspace access permissions.

    Args:
        token_data: Token and workspace ID to verify

    Returns:
        Token verification response with user info and permissions

    Raises:
        HTTPException: 401 if token is invalid or expired
        HTTPException: 403 if user lacks workspace access
    """
    try:
        # Verify token using shared secret
        payload = await verify_token(token_data.token)

        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        # Validate workspace access
        workspace_ids = payload.get("workspace_ids", [])
        if isinstance(workspace_ids, str):
            workspace_ids = [workspace_ids]

        if token_data.workspace_id not in workspace_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to workspace",
            )

        # Get user role and permissions
        role = payload.get("role", "viewer")
        permissions = payload.get("permissions", [])

        # If permissions not in token, derive from role
        if not permissions:
            permissions = get_permissions_for_role(role)

        return TokenVerificationResponse(
            valid=True,
            user_id=user_id,
            workspace_id=token_data.workspace_id,
            permissions=permissions,
            expires_at=payload.get("exp", 0),
            role=role,
        )

    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        elif "revoked" in error_msg or "blacklist" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )


@router.post("/exchange", response_model=TokenResponse)
async def exchange_token(
    main_token: str = Header(alias="X-Main-Token"),
) -> TokenResponse:
    """
    Exchange main app token for analytics-specific token.

    This endpoint allows clients to exchange a token from the main
    Shadower application for an analytics-specific token with
    appropriate claims and permissions.

    Args:
        main_token: Token from main application (in X-Main-Token header)

    Returns:
        New analytics token with extended validity

    Raises:
        HTTPException: 401 if main token is invalid
    """
    try:
        # Verify main app token
        main_payload = await verify_token(main_token)

        # Determine analytics permissions based on main app role
        role = main_payload.get("role", "viewer")
        analytics_permissions = get_permissions_for_role(role)

        # Generate analytics token with specific claims
        token_data = {
            "sub": main_payload.get("sub"),
            "email": main_payload.get("email"),
            "workspace_ids": main_payload.get("workspace_ids", []),
            "role": role,
            "analytics_permissions": analytics_permissions,
            "iat": datetime.now(timezone.utc).timestamp(),
        }

        # Create token with 24 hour expiration
        analytics_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        )

        return TokenResponse(
            access_token=analytics_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        )

    except ValueError as e:
        logger.warning(f"Token exchange failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid main app token",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
) -> TokenResponse:
    """
    Refresh analytics access token.

    This endpoint allows clients to obtain a new access token using
    a valid refresh token without re-authentication.

    Args:
        refresh_data: Refresh token request

    Returns:
        New access token

    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    try:
        # Verify refresh token
        # Note: In production, you might want to use a different secret for refresh tokens
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Generate new access token
        token_data = {
            "sub": user_id,
            "email": payload.get("email"),
            "workspace_ids": payload.get("workspace_ids", []),
            "role": payload.get("role", "viewer"),
            "permissions": payload.get("permissions", []),
        }

        new_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return TokenResponse(
            access_token=new_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except JWTError as e:
        logger.warning(f"Refresh token invalid: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> LogoutResponse:
    """
    Logout user by blacklisting their token.

    This endpoint invalidates the current access token by adding it
    to the blacklist, preventing further use.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Logout confirmation
    """
    token = credentials.credentials

    try:
        # Decode to get expiration time
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # Don't verify expiration for logout
        )

        # Get expiration time
        exp = payload.get("exp")
        expires_at = None
        if exp:
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)

        # Blacklist the token
        await blacklist_token(token, expires_at)

        # Invalidate cache
        await invalidate_token_cache(token)

        logger.info(f"User {payload.get('sub')} logged out successfully")

        return LogoutResponse(
            success=True,
            message="Successfully logged out",
        )

    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        # Even if blacklisting fails, return success to user
        # The token will still expire naturally
        return LogoutResponse(
            success=True,
            message="Logged out (token will expire naturally)",
        )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> CurrentUserResponse:
    """
    Get current authenticated user information.

    Returns information about the currently authenticated user,
    including their workspaces and roles.

    Args:
        current_user: Current user from JWT token

    Returns:
        Current user information
    """
    workspace_ids = current_user.get("workspace_ids", [])
    if isinstance(workspace_ids, str):
        workspace_ids = [workspace_ids]

    return CurrentUserResponse(
        id=current_user.get("sub", ""),
        email=current_user.get("email", ""),
        name=current_user.get("name"),
        is_active=True,
        email_verified=current_user.get("email_verified", False),
        two_factor_enabled=current_user.get("two_factor_enabled", False),
        created_at=datetime.fromtimestamp(
            current_user.get("iat", datetime.now(timezone.utc).timestamp()),
            tz=timezone.utc,
        ),
        updated_at=None,
        last_login=datetime.now(timezone.utc),
        workspaces=workspace_ids,
        default_workspace_id=workspace_ids[0] if workspace_ids else None,
    )


@router.get("/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserPermissionsResponse:
    """
    Get user's analytics permissions for workspace.

    Returns the complete set of permissions for the authenticated user
    within the specified workspace.

    Args:
        workspace_id: Workspace ID to get permissions for
        current_user: Current user from JWT token

    Returns:
        User permissions for the workspace

    Raises:
        HTTPException: 403 if user lacks workspace access
    """
    # Validate workspace access
    workspace_ids = current_user.get("workspace_ids", [])
    if isinstance(workspace_ids, str):
        workspace_ids = [workspace_ids]

    if workspace_id not in workspace_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to workspace",
        )

    # Get user role
    role = current_user.get("role", "viewer")

    # Get permissions from token or derive from role
    permissions_list = current_user.get("analytics_permissions") or \
                      current_user.get("permissions") or \
                      get_permissions_for_role(role)

    # Convert permissions list to PermissionSet
    permission_set = PermissionSet(
        view_executive_dashboard="view_executive_dashboard" in permissions_list,
        view_agent_analytics="view_agent_analytics" in permissions_list,
        view_user_analytics="view_user_analytics" in permissions_list,
        export_data="export_data" in permissions_list,
        manage_reports="manage_reports" in permissions_list,
        configure_alerts="configure_alerts" in permissions_list,
        admin_access="admin_access" in permissions_list,
        view_sensitive_data="view_sensitive_data" in permissions_list,
    )

    return UserPermissionsResponse(
        user_id=current_user.get("sub", ""),
        workspace_id=workspace_id,
        permissions=permission_set,
        role=UserRole(role),
        custom_permissions=current_user.get("custom_permissions"),
    )


@router.put("/permissions", response_model=UserPermissionsResponse)
async def update_user_permissions(
    permission_update: PermissionUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> UserPermissionsResponse:
    """
    Update user's analytics permissions.

    This endpoint allows administrators to modify permissions for
    users within their workspace. Requires admin role.

    Args:
        permission_update: Permission update request
        current_user: Current admin user from JWT token

    Returns:
        Updated user permissions

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if target user not found
    """
    # In a real implementation, this would:
    # 1. Validate that current user is admin in the workspace
    # 2. Fetch the target user from database
    # 3. Update their permissions
    # 4. Save to database
    # 5. Invalidate any cached permissions

    # For now, return a mock response
    # TODO: Implement database integration for permission management

    logger.info(
        f"Admin {current_user.get('sub')} updating permissions for "
        f"user {permission_update.user_id} in workspace {permission_update.workspace_id}"
    )

    # Build updated permission set
    permission_set = PermissionSet(**permission_update.permissions)

    return UserPermissionsResponse(
        user_id=permission_update.user_id,
        workspace_id=permission_update.workspace_id,
        permissions=permission_set,
        role=UserRole.MEMBER,  # Would be fetched from database
        custom_permissions=permission_update.permissions,
    )


# Health check for auth service
@router.get("/health")
async def auth_health_check():
    """Authentication service health check."""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# API Key Management Endpoints
# ============================================================================

def generate_api_key() -> str:
    """Generate a secure random API key."""
    # Generate a 32-byte random key and encode as hex (64 characters)
    return f"sk_{secrets.token_urlsafe(48)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_config: APIKeyConfig,
    current_user: Dict[str, Any] = Depends(require_admin),
    db=Depends(get_db),
) -> APIKeyResponse:
    """
    Create API key for programmatic access.

    This endpoint allows administrators to create API keys for
    programmatic access to the analytics API. The actual key is
    only shown once and should be stored securely.

    Args:
        key_config: API key configuration
        current_user: Current admin user from JWT token
        db: Database session

    Returns:
        Created API key (shown only once)

    Raises:
        HTTPException: 403 if user is not admin
    """
    # Generate a secure API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    # Create API key record
    db_api_key = APIKey(
        id=str(uuid4()),
        key_hash=key_hash,
        name=key_config.name,
        user_id=current_user.get("sub"),
        workspace_id=key_config.workspace_id,
        permissions=key_config.permissions,
        rate_limit=key_config.rate_limit or 1000,
        expires_at=key_config.expires_at,
        created_by=current_user.get("sub"),
        is_active=True,
        usage_count=0,
    )

    try:
        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)

        logger.info(
            f"API key created: {db_api_key.id} by user {current_user.get('sub')} "
            f"for workspace {key_config.workspace_id}"
        )

        return APIKeyResponse(
            api_key=api_key,  # Only shown once!
            key_id=db_api_key.id,
            created_at=db_api_key.created_at,
            expires_at=db_api_key.expires_at,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: Dict[str, Any] = Depends(require_admin),
    db=Depends(get_db),
) -> APIKeyListResponse:
    """
    List API keys for workspace.

    Returns all API keys for the specified workspace. The actual
    key values are not returned, only metadata.

    Args:
        workspace_id: Workspace ID to list keys for
        current_user: Current admin user from JWT token
        db: Database session

    Returns:
        List of API keys

    Raises:
        HTTPException: 403 if user is not admin
    """
    try:
        # Query API keys for workspace
        keys = db.query(APIKey).filter(
            APIKey.workspace_id == workspace_id
        ).order_by(APIKey.created_at.desc()).all()

        # Convert to response format
        api_keys = [
            APIKeyListItem(
                key_id=key.id,
                name=key.name,
                last_4="..." + key.key_hash[-4:],  # Last 4 chars of hash
                created_at=key.created_at,
                last_used=key.last_used,
                expires_at=key.expires_at,
                is_active=key.is_active,
                usage_count=key.usage_count,
            )
            for key in keys
        ]

        return APIKeyListResponse(api_keys=api_keys)

    except Exception as e:
        logger.error(f"Failed to list API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys",
        )


@router.delete("/api-keys/{key_id}", response_model=APIKeyRevokeResponse)
async def revoke_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db=Depends(get_db),
) -> APIKeyRevokeResponse:
    """
    Revoke API key.

    This endpoint permanently revokes an API key, preventing
    further use for authentication.

    Args:
        key_id: API key ID to revoke
        current_user: Current admin user from JWT token
        db: Database session

    Returns:
        Revocation confirmation

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if key not found
    """
    try:
        # Find the API key
        api_key = db.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        # Revoke the key
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        api_key.revoked_by = current_user.get("sub")

        db.commit()

        logger.info(
            f"API key revoked: {key_id} by user {current_user.get('sub')}"
        )

        return APIKeyRevokeResponse(
            key_id=key_id,
            revoked=True,
            revoked_at=api_key.revoked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key",
        )


# ============================================================================
# Session Management Endpoints
# ============================================================================

def parse_user_agent(user_agent: str) -> str:
    """
    Parse user agent string to extract device info.

    This is a simplified version. In production, use a library like
    user-agents or httpagentparser for better parsing.
    """
    if not user_agent:
        return "Unknown Device"

    user_agent = user_agent.lower()

    # Detect OS
    if "windows" in user_agent:
        os = "Windows"
    elif "mac" in user_agent:
        os = "MacOS"
    elif "linux" in user_agent:
        os = "Linux"
    elif "android" in user_agent:
        os = "Android"
    elif "iphone" in user_agent or "ipad" in user_agent:
        os = "iOS"
    else:
        os = "Unknown OS"

    # Detect browser
    if "chrome" in user_agent and "edg" not in user_agent:
        browser = "Chrome"
    elif "firefox" in user_agent:
        browser = "Firefox"
    elif "safari" in user_agent and "chrome" not in user_agent:
        browser = "Safari"
    elif "edg" in user_agent:
        browser = "Edge"
    else:
        browser = "Unknown Browser"

    return f"{browser} on {os}"


@router.get("/sessions", response_model=SessionListResponse)
async def get_active_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SessionListResponse:
    """
    Get user's active sessions.

    Returns all active sessions for the authenticated user,
    including device and location information.

    Args:
        current_user: Current user from JWT token
        db: Database session

    Returns:
        List of active sessions
    """
    try:
        user_id = current_user.get("sub")

        # Query active sessions for user
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc),
        ).order_by(UserSession.last_active.desc()).all()

        # Convert to response format
        session_list = [
            SessionInfo(
                session_id=session.id,
                device=session.device_info or "Unknown Device",
                ip_address=session.ip_address or "Unknown",
                location=session.location or "Unknown Location",
                created_at=session.created_at,
                last_active=session.last_active,
                is_current=False,  # Would need current session ID to determine
            )
            for session in sessions
        ]

        return SessionListResponse(sessions=session_list)

    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


@router.delete("/sessions/{session_id}", response_model=SessionTerminateResponse)
async def terminate_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SessionTerminateResponse:
    """
    Terminate specific session.

    This endpoint allows users to terminate their own sessions,
    useful for logging out from other devices.

    Args:
        session_id: Session ID to terminate
        current_user: Current user from JWT token
        db: Database session

    Returns:
        Termination confirmation

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 403 if session belongs to another user
    """
    try:
        user_id = current_user.get("sub")

        # Find the session
        session = db.query(UserSession).filter(
            UserSession.id == session_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify session belongs to current user
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot terminate another user's session",
            )

        # Terminate the session
        session.is_active = False
        session.terminated_at = datetime.now(timezone.utc)

        db.commit()

        logger.info(f"Session terminated: {session_id} by user {user_id}")

        return SessionTerminateResponse(
            session_id=session_id,
            terminated=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to terminate session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate session",
        )
