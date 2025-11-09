# Specification: Authentication API Endpoints

## Overview
Define authentication and authorization API endpoints for secure access to the analytics service.

## Technical Requirements

### Authentication Endpoints

#### POST `/api/v1/auth/verify`
```python
@router.post("/auth/verify")
async def verify_token(
    token_data: TokenVerification
) -> APIResponse:
    """
    Verify JWT token from main app
    
    Request body:
    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "workspace_id": "ws_123"
    }
    """
    try:
        # Verify with shared secret
        payload = jwt.decode(
            token_data.token,
            SHARED_JWT_SECRET,
            algorithms=["HS256"]
        )
        
        # Validate workspace access
        user_id = payload.get("sub")
        workspace_ids = payload.get("workspace_ids", [])
        
        if token_data.workspace_id not in workspace_ids:
            raise HTTPException(403, "No access to workspace")
        
        return {
            "valid": True,
            "user_id": user_id,
            "workspace_id": token_data.workspace_id,
            "permissions": payload.get("permissions", []),
            "expires_at": payload.get("exp")
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

#### POST `/api/v1/auth/exchange`
```python
@router.post("/auth/exchange")
async def exchange_token(
    main_token: str = Header(alias="X-Main-Token")
) -> APIResponse:
    """
    Exchange main app token for analytics-specific token
    """
    # Verify main app token
    main_payload = verify_main_app_token(main_token)
    
    # Generate analytics token with specific claims
    analytics_token = jwt.encode(
        {
            "sub": main_payload["sub"],
            "workspace_ids": main_payload["workspace_ids"],
            "analytics_permissions": determine_analytics_permissions(main_payload),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        ANALYTICS_JWT_SECRET,
        algorithm="HS256"
    )
    
    return {
        "access_token": analytics_token,
        "token_type": "bearer",
        "expires_in": 86400
    }
```

#### POST `/api/v1/auth/refresh`
```python
@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str
) -> APIResponse:
    """
    Refresh analytics access token
    
    Request body:
    {
        "refresh_token": "refresh_token_string"
    }
    """
    try:
        payload = jwt.decode(
            refresh_token,
            REFRESH_TOKEN_SECRET,
            algorithms=["HS256"]
        )
        
        # Generate new access token
        new_token = generate_access_token(payload["sub"])
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")
```

### Permission Management Endpoints

#### GET `/api/v1/auth/permissions`
```python
@router.get("/auth/permissions")
async def get_user_permissions(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get user's analytics permissions for workspace
    """
    permissions = await get_analytics_permissions(user.id, workspace_id)
    
    return {
        "user_id": user.id,
        "workspace_id": workspace_id,
        "permissions": {
            "view_executive_dashboard": True,
            "view_agent_analytics": True,
            "view_user_analytics": False,
            "export_data": True,
            "manage_reports": False,
            "configure_alerts": False,
            "admin_access": False
        },
        "role": permissions.role,
        "custom_permissions": permissions.custom
    }
```

#### PUT `/api/v1/auth/permissions`
```python
@router.put("/auth/permissions")
async def update_user_permissions(
    permission_update: PermissionUpdate,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Update user's analytics permissions
    
    Request body:
    {
        "user_id": "user_123",
        "workspace_id": "ws_456",
        "permissions": {
            "view_user_analytics": true,
            "export_data": false
        }
    }
    """
    await update_analytics_permissions(
        permission_update.user_id,
        permission_update.workspace_id,
        permission_update.permissions
    )
    
    return {
        "updated": True,
        "user_id": permission_update.user_id,
        "workspace_id": permission_update.workspace_id
    }
```

### API Key Management

#### POST `/api/v1/auth/api-keys`
```python
@router.post("/auth/api-keys")
async def create_api_key(
    key_config: APIKeyConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Create API key for programmatic access
    
    Request body:
    {
        "name": "Production API Key",
        "workspace_id": "ws_123",
        "permissions": ["read_analytics", "export_data"],
        "expires_at": "2024-12-31T23:59:59Z",
        "rate_limit": 1000
    }
    """
    api_key = await generate_api_key(key_config, user.id)
    
    return {
        "api_key": api_key.key,  # Only shown once
        "key_id": api_key.id,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "warning": "Store this key securely. It won't be shown again."
    }
```

#### GET `/api/v1/auth/api-keys`
```python
@router.get("/auth/api-keys")
async def list_api_keys(
    workspace_id: str,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    List API keys for workspace
    """
    keys = await get_workspace_api_keys(workspace_id)
    
    return {
        "api_keys": [
            {
                "key_id": "key_123",
                "name": "Production Key",
                "last_4": "...abc4",
                "created_at": "2024-01-01T00:00:00Z",
                "last_used": "2024-01-15T10:30:00Z",
                "expires_at": "2024-12-31T23:59:59Z",
                "is_active": True,
                "usage_count": 5420
            }
        ]
    }
```

#### DELETE `/api/v1/auth/api-keys/{key_id}`
```python
@router.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Revoke API key
    """
    await revoke_key(key_id, user.id)
    
    return {
        "key_id": key_id,
        "revoked": True,
        "revoked_at": datetime.utcnow().isoformat()
    }
```

### Session Management

#### GET `/api/v1/auth/sessions`
```python
@router.get("/auth/sessions")
async def get_active_sessions(
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get user's active sessions
    """
    sessions = await get_user_sessions(user.id)
    
    return {
        "sessions": [
            {
                "session_id": "sess_123",
                "device": "Chrome on MacOS",
                "ip_address": "192.168.1.1",
                "location": "San Francisco, CA",
                "created_at": "2024-01-15T08:00:00Z",
                "last_active": "2024-01-15T14:30:00Z",
                "is_current": True
            }
        ]
    }
```

#### DELETE `/api/v1/auth/sessions/{session_id}`
```python
@router.delete("/auth/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Terminate specific session
    """
    await end_session(session_id, user.id)
    
    return {
        "session_id": session_id,
        "terminated": True
    }
```

### OAuth Integration

#### GET `/api/v1/auth/oauth/{provider}`
```python
@router.get("/auth/oauth/{provider}")
async def oauth_authorize(
    provider: str,
    redirect_uri: str
) -> APIResponse:
    """
    Initiate OAuth flow
    Providers: google, github, microsoft
    """
    auth_url = generate_oauth_url(provider, redirect_uri)
    
    return {
        "auth_url": auth_url,
        "provider": provider
    }
```

#### POST `/api/v1/auth/oauth/{provider}/callback`
```python
@router.post("/auth/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    callback_data: OAuthCallback
) -> APIResponse:
    """
    Handle OAuth callback
    
    Request body:
    {
        "code": "oauth_authorization_code",
        "state": "state_parameter"
    }
    """
    # Exchange code for tokens
    oauth_tokens = await exchange_oauth_code(
        provider,
        callback_data.code
    )
    
    # Get user info from provider
    user_info = await get_oauth_user_info(provider, oauth_tokens)
    
    # Create or update user
    user = await create_or_update_oauth_user(provider, user_info)
    
    # Generate analytics token
    analytics_token = generate_access_token(user.id)
    
    return {
        "access_token": analytics_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "provider": provider
        }
    }
```

### Two-Factor Authentication

#### POST `/api/v1/auth/2fa/setup`
```python
@router.post("/auth/2fa/setup")
async def setup_2fa(
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Setup two-factor authentication
    """
    secret = pyotp.random_base32()
    qr_code = generate_2fa_qr_code(user.email, secret)
    
    # Store secret temporarily
    await store_temp_2fa_secret(user.id, secret)
    
    return {
        "qr_code": qr_code,  # Base64 encoded image
        "secret": secret,
        "backup_codes": generate_backup_codes()
    }
```

#### POST `/api/v1/auth/2fa/verify`
```python
@router.post("/auth/2fa/verify")
async def verify_2fa(
    verification: TwoFactorVerification,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Verify 2FA code
    
    Request body:
    {
        "code": "123456"
    }
    """
    secret = await get_user_2fa_secret(user.id)
    totp = pyotp.TOTP(secret)
    
    if totp.verify(verification.code, valid_window=1):
        # Mark 2FA as verified
        await mark_2fa_verified(user.id)
        
        return {
            "verified": True,
            "2fa_enabled": True
        }
    else:
        raise HTTPException(400, "Invalid code")
```

### Security Headers

```python
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
```

### Authentication Decorators

```python
def require_permission(permission: str):
    """Decorator to require specific permission"""
    async def permission_checker(
        user: User = Depends(get_current_user),
        workspace_id: str = Query()
    ):
        perms = await get_analytics_permissions(user.id, workspace_id)
        if permission not in perms:
            raise HTTPException(403, f"Missing permission: {permission}")
        return user
    return permission_checker

# Usage
@router.get("/sensitive-data")
async def get_sensitive_data(
    user: User = Depends(require_permission("view_sensitive_data"))
):
    pass
```

## Implementation Priority
1. JWT token verification
2. Basic permission system
3. API key management
4. OAuth integration
5. 2FA support

## Success Metrics
- Authentication latency < 50ms
- Token validation success rate > 99%
- Security incident rate < 0.01%
- API key adoption rate > 60%