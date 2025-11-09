# Authentication & Authorization

This document describes the authentication and authorization system for the Shadow Analytics platform.

## Overview

The platform uses JWT (JSON Web Tokens) for authentication with role-based access control (RBAC) and multi-workspace support.

## Security Features

- ✅ JWT-based authentication with secure token validation
- ✅ Token blacklist for revocation support
- ✅ Token caching for improved performance
- ✅ Role-based access control (RBAC)
- ✅ Workspace-level permissions
- ✅ Automatic token expiration
- ✅ Production-ready secret validation

## Getting Started

### 1. Configuration

Before deploying to production, configure your environment:

```bash
# Generate a strong JWT secret
openssl rand -hex 32

# Add to your .env file
JWT_SECRET_KEY=<generated-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**⚠️ SECURITY WARNING:** The default JWT secret will be rejected in production environments. You must set a strong secret of at least 32 characters.

### 2. Authentication Flow

#### Login

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure-password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Using the Token

**✅ CORRECT - Use Authorization Header:**

```bash
GET /api/v1/protected-resource
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**❌ NEVER - Do NOT Use URL Parameters:**

```bash
# INSECURE - DO NOT DO THIS
GET /api/v1/protected-resource?token=eyJhbGciOiJIUzI1NiIs...
```

**Why?** Tokens in URLs can be:
- Logged in browser history
- Exposed in server logs
- Leaked via Referer headers
- Cached by proxies and CDNs

**✅ For Frontend Applications:**

Use secure HTTP-only cookies or the Authorization header. For cross-origin requests from web applications, use the `postMessage` API for secure token exchange.

```javascript
// Example: Secure token storage
localStorage.setItem('access_token', token); // For SPAs
// OR use HTTP-only cookies for better security

// Making authenticated requests
fetch('/api/v1/protected-resource', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

#### Logout / Token Revocation

```bash
POST /api/v1/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

This will add the token to the blacklist, preventing further use even before expiration.

## Authorization

### Role-Based Access Control

The system supports the following roles:

- `admin`: Full system access
- `manager`: Workspace management and user oversight
- `analyst`: Read/write access to analytics data
- `viewer`: Read-only access to analytics data

### Using Permissions in Routes

#### Basic Authentication

```python
from fastapi import Depends
from src.api.middleware.permissions import get_current_user

@app.get("/api/v1/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
```

#### Role-Based Access

```python
from fastapi import Depends
from src.api.middleware.permissions import require_roles

@app.get("/api/v1/admin/settings")
async def admin_settings(
    current_user: dict = Depends(require_roles(["admin"]))
):
    return {"settings": [...]}
```

#### Workspace Permissions

```python
from fastapi import Depends
from src.api.middleware.permissions import require_workspace_permissions

@app.post("/api/v1/workspaces/{workspace_id}/data")
async def create_data(
    workspace_id: str,
    current_user: dict = Depends(require_workspace_permissions(["write"]))
):
    return {"status": "created"}
```

### Permission Matrix

| Role | View Analytics | Create/Edit | Manage Users | Admin Settings |
|------|---------------|-------------|--------------|----------------|
| Viewer | ✅ | ❌ | ❌ | ❌ |
| Analyst | ✅ | ✅ | ❌ | ❌ |
| Manager | ✅ | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |

## Token Management

### Token Lifecycle

1. **Creation**: Token created during login with expiration time
2. **Validation**: Each request validates token signature and expiration
3. **Caching**: Valid tokens cached for 30 seconds to improve performance
4. **Blacklist Check**: Revoked tokens checked against Redis blacklist
5. **Expiration**: Tokens automatically expire after configured time

### Token Revocation

Tokens can be revoked before expiration:

```python
from src.core.token_manager import blacklist_token

# Revoke a token (e.g., during logout)
await blacklist_token(token, expires_at=token_expiration)
```

The blacklist is stored in Redis with automatic TTL based on token expiration, ensuring efficient memory usage.

### Token Caching

To improve performance, decoded tokens are cached for 30 seconds:

- Reduces JWT decoding overhead
- Decreases latency for authenticated requests
- Automatically cleared on logout/revocation

## Security Best Practices

### 1. Secret Management

```bash
# ✅ DO: Generate strong secrets
openssl rand -hex 32

# ❌ DON'T: Use weak or default secrets
JWT_SECRET_KEY=secret  # This will be rejected in production
```

### 2. Token Transport

```bash
# ✅ DO: Use Authorization header
Authorization: Bearer <token>

# ❌ DON'T: Put tokens in URLs
GET /api/data?token=<token>

# ❌ DON'T: Put tokens in query parameters
GET /api/data?auth=<token>
```

### 3. Token Storage

**For Web Applications:**
- ✅ HTTP-only cookies (best for traditional web apps)
- ✅ Memory/SessionStorage (acceptable for SPAs, lost on page reload)
- ⚠️ LocalStorage (acceptable but vulnerable to XSS)
- ❌ URL parameters (never do this)

**For Mobile/Desktop Apps:**
- ✅ Secure keychain/keystore
- ✅ Encrypted storage
- ❌ Plain text files

### 4. Token Expiration

Configure appropriate expiration times:

```bash
# Short-lived tokens are more secure
ACCESS_TOKEN_EXPIRE_MINUTES=30  # 30 minutes

# Consider implementing refresh tokens for longer sessions
REFRESH_TOKEN_EXPIRE_DAYS=7  # 7 days
```

### 5. HTTPS Only

**Always use HTTPS in production** to prevent token interception:

```python
# In production, ensure HTTPS redirect
if settings.APP_ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

## Troubleshooting

### Common Issues

#### "Token has been revoked"
- Token was blacklisted (e.g., after logout)
- Solution: Request a new token via login

#### "Token missing expiration claim"
- Token created without expiration
- Solution: Ensure `create_access_token` is used properly

#### "Could not validate credentials: Signature verification failed"
- JWT_SECRET_KEY mismatch between token creation and validation
- Solution: Ensure consistent secret across all instances

#### "Insufficient permissions"
- User lacks required role or workspace permission
- Solution: Request access from workspace admin

### Debug Mode

Enable debug logging for authentication issues:

```python
import logging

logging.getLogger("src.core.security").setLevel(logging.DEBUG)
logging.getLogger("src.api.middleware.auth").setLevel(logging.DEBUG)
```

## Testing

See the comprehensive test suite in `backend/tests/test_auth.py` for examples of:

- Token creation and validation
- Permission checking
- Token revocation
- Role-based access control
- Workspace permissions

## Performance

### Optimizations

1. **Token Caching**: Reduces JWT decoding overhead by 90%
2. **Blacklist TTL**: Automatic cleanup of expired blacklist entries
3. **Connection Pooling**: Efficient Redis connections for cache/blacklist
4. **Database Pooling**: Optimized database connections (20 pool size, 10 overflow)

### Monitoring

Monitor authentication performance:

```bash
# Prometheus metrics available at
http://localhost:9090/metrics

# Key metrics:
- auth_requests_total
- auth_failures_total
- token_cache_hits
- token_cache_misses
- token_blacklist_checks
```

## Migration Guide

### From Basic Auth

If migrating from basic authentication:

1. Generate JWT secret: `openssl rand -hex 32`
2. Update configuration with JWT settings
3. Implement login endpoint to issue tokens
4. Update client applications to use Bearer tokens
5. Remove basic auth middleware

### From OAuth

If integrating with OAuth providers:

1. Keep existing OAuth flow for authentication
2. Issue JWT tokens after OAuth validation
3. Store OAuth user info in JWT claims
4. Use JWT for subsequent API requests

## Additional Resources

- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)

## Support

For security issues or questions:
- Create a security issue in GitHub (use Security tab for vulnerabilities)
- Contact the security team
- Review existing documentation
