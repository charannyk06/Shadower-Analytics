# Authentication System Documentation

## Overview

The Shadower Analytics microservice uses a shared JWT (JSON Web Token) authentication system that seamlessly integrates with the main Shadower application. This allows users to authenticate once in the main app and access analytics without additional login.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Main App      │         │   Analytics      │
│                 │         │   Microservice   │
│  ┌───────────┐  │         │                  │
│  │   Login   │  │         │  ┌────────────┐  │
│  └─────┬─────┘  │         │  │   Verify   │  │
│        │        │         │  │   Token    │  │
│        v        │         │  └────────────┘  │
│  ┌───────────┐  │         │                  │
│  │  Generate │  │  Token  │  ┌────────────┐  │
│  │    JWT    │──┼────────>│  │  Extract   │  │
│  └───────────┘  │         │  │    User    │  │
│                 │         │  └────────────┘  │
│                 │         │                  │
│  ┌───────────┐  │         │  ┌────────────┐  │
│  │  Refresh  │<─┼─────────┤  │   Check    │  │
│  │  Endpoint │  │         │  │   Perms    │  │
│  └───────────┘  │         │  └────────────┘  │
└─────────────────┘         └──────────────────┘
      Shared JWT Secret
```

## JWT Token Structure

### Payload Schema

```typescript
interface JWTPayload {
  // Standard JWT claims
  sub: string;           // Subject - User ID
  iat: number;           // Issued at timestamp
  exp: number;           // Expiration timestamp

  // Custom claims
  email: string;         // User email
  workspaceId: string;   // Current active workspace
  workspaces: string[];  // All accessible workspaces
  role: 'owner' | 'admin' | 'member' | 'viewer';
  permissions: string[]; // Array of permission strings
}
```

### Example Token

```json
{
  "sub": "usr_1234567890",
  "email": "john.doe@example.com",
  "workspaceId": "ws_abc123",
  "workspaces": ["ws_abc123", "ws_def456"],
  "role": "admin",
  "permissions": [
    "view_analytics",
    "export_analytics",
    "create_reports",
    "view_alerts",
    "create_alerts",
    "manage_alerts",
    "view_agents",
    "manage_agents",
    "view_metrics",
    "export_metrics"
  ],
  "iat": 1699999999,
  "exp": 1700086399
}
```

## Roles and Permissions

### Role Hierarchy

1. **Owner** (Highest privileges)
   - Full access to all features
   - Can manage workspace settings
   - Can manage all users
   - Access to financial metrics

2. **Admin**
   - Access to most features
   - Can manage agents and alerts
   - Cannot access financial metrics
   - Cannot manage workspace settings

3. **Member**
   - View and export analytics
   - View alerts and agents
   - Cannot create or manage resources

4. **Viewer** (Lowest privileges)
   - Read-only access
   - View analytics and metrics
   - Cannot export or create anything

### Permission Matrix

| Permission | Owner | Admin | Member | Viewer |
|-----------|-------|-------|--------|--------|
| `view_executive_dashboard` | ✓ | ✓ | ✗ | ✗ |
| `view_financial_metrics` | ✓ | ✗ | ✗ | ✗ |
| `view_analytics` | ✓ | ✓ | ✓ | ✓ |
| `export_analytics` | ✓ | ✓ | ✓ | ✗ |
| `create_reports` | ✓ | ✓ | ✗ | ✗ |
| `view_alerts` | ✓ | ✓ | ✓ | ✓ |
| `create_alerts` | ✓ | ✓ | ✗ | ✗ |
| `manage_alerts` | ✓ | ✓ | ✗ | ✗ |
| `manage_workspace` | ✓ | ✗ | ✗ | ✗ |
| `view_all_workspaces` | ✓ | ✗ | ✗ | ✗ |
| `manage_users` | ✓ | ✗ | ✗ | ✗ |
| `view_agents` | ✓ | ✓ | ✓ | ✓ |
| `manage_agents` | ✓ | ✓ | ✗ | ✗ |
| `view_metrics` | ✓ | ✓ | ✓ | ✓ |
| `export_metrics` | ✓ | ✓ | ✓ | ✗ |

## Backend Implementation

### Configuration

The backend uses the following environment variables:

```bash
# Required
JWT_SECRET_KEY=your-secret-key-here  # Must match main app!
JWT_ALGORITHM=HS256                   # Or RS256 for asymmetric

# Optional
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=30
JWT_PUBLIC_KEY=                       # For RS256
JWT_PRIVATE_KEY=                      # For RS256
```

### JWT Verification

Located in `backend/src/api/middleware/auth.py`:

```python
from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer

class JWTAuth:
    def __init__(self):
        self.secret = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM

    async def verify_token(self, credentials):
        """Verify JWT token and return payload."""
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )

            # Check expiration
            if payload.get("exp", 0) < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )

            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid credentials: {str(e)}"
            )
```

### Dependency Injection

Use FastAPI's dependency injection for route protection:

```python
from fastapi import Depends
from src.api.dependencies.auth import (
    get_current_user,
    require_owner_or_admin,
    require_owner
)

@router.get("/executive/overview")
async def get_overview(
    current_user = Depends(require_owner_or_admin)
):
    # current_user contains the JWT payload
    workspace_id = current_user["workspace_id"]
    role = current_user["role"]
    permissions = current_user["permissions"]

    # Your logic here
    return {"data": "..."}
```

### Workspace Validation

Always validate workspace access:

```python
from src.api.middleware.workspace import WorkspaceAccess

@router.get("/metrics")
async def get_metrics(
    workspace_id: str,
    current_user = Depends(get_current_user)
):
    # Validate user has access to workspace
    await WorkspaceAccess.validate_workspace_access(
        current_user,
        workspace_id
    )

    # Proceed with logic
    return {"metrics": "..."}
```

### Custom Permission Checks

For fine-grained control:

```python
from src.api.middleware.permissions import check_permission

@router.post("/reports")
async def create_report(
    current_user = Depends(get_current_user)
):
    # Check specific permission
    if not check_permission(current_user, "create_reports"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied"
        )

    # Create report
    return {"report": "..."}
```

## Frontend Implementation

### Auth Context

The `AuthContext` provides authentication state throughout the app:

```typescript
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const {
    user,           // User object or null
    token,          // JWT token string or null
    isLoading,      // Loading state
    isAuthenticated, // Boolean
    login,          // Function to login with token
    logout,         // Function to logout
    refreshToken    // Function to refresh token
  } = useAuth();

  if (isLoading) return <Spinner />;
  if (!isAuthenticated) return <LoginRedirect />;

  return (
    <div>
      <p>Welcome, {user.email}</p>
      <p>Role: {user.role}</p>
    </div>
  );
}
```

### Protected Routes

Wrap pages with `ProtectedRoute`:

```typescript
import { ProtectedRoute } from '@/components/auth';
import { ROLES, PERMISSIONS } from '@/types/permissions';

export default function ExecutivePage() {
  return (
    <ProtectedRoute
      requiredRole={[ROLES.OWNER, ROLES.ADMIN]}
      requiredPermissions={[PERMISSIONS.VIEW_EXECUTIVE_DASHBOARD]}
    >
      <ExecutiveDashboard />
    </ProtectedRoute>
  );
}
```

### API Client

The API client automatically includes tokens and handles refresh:

```typescript
import apiClient from '@/lib/api/client';

async function fetchMetrics() {
  try {
    const response = await apiClient.get('/api/v1/metrics');
    return response.data;
  } catch (error) {
    // 401 errors trigger automatic token refresh
    // 403 errors mean permission denied
    console.error('Error fetching metrics:', error);
  }
}
```

### Permission Checks in UI

Hide/show UI elements based on permissions:

```typescript
import { useAuth } from '@/contexts/AuthContext';
import { PERMISSIONS } from '@/types/permissions';

function ExportButton() {
  const { user } = useAuth();

  if (!user?.permissions.includes(PERMISSIONS.EXPORT_ANALYTICS)) {
    return null; // Hide button
  }

  return <button onClick={handleExport}>Export</button>;
}
```

## Authentication Flow

### Initial Authentication

1. User accesses analytics URL with token parameter:
   ```
   https://analytics.example.com?token=eyJhbGciOiJIUzI1NiIs...
   ```

2. Frontend extracts token from URL
3. Token is validated (expiration check)
4. Token is stored in localStorage
5. URL is cleaned (token removed from visible URL)
6. Default Authorization header is set
7. User object is populated from token payload

### Subsequent Requests

1. API client reads token from localStorage
2. Adds `Authorization: Bearer <token>` header
3. Backend validates token
4. Request proceeds if valid

### Token Refresh

Automatic refresh occurs 5 minutes before expiration:

1. Frontend detects token will expire soon
2. Calls main app's `/api/auth/refresh` endpoint
3. New token is returned
4. Token is updated in localStorage and headers
5. Process repeats

### Logout

1. User clicks logout
2. Token is removed from localStorage
3. Default Authorization header is removed
4. User is redirected to main app login page

## Security Best Practices

### Token Storage

- ✅ Use localStorage for persistence across sessions
- ✅ Clear token on logout
- ❌ Never expose token in URLs (clean after initial load)
- ❌ Never log tokens to console in production

### Secret Management

- ✅ Use strong 256-bit secrets
- ✅ Rotate secrets periodically
- ✅ Use different secrets for dev/staging/prod
- ❌ Never commit secrets to version control

### Token Validation

- ✅ Always verify signature
- ✅ Check expiration on every request
- ✅ Validate issuer if using multiple apps
- ✅ Implement token revocation for logout

### Transport Security

- ✅ Use HTTPS in production
- ✅ Set secure cookie flags if using cookies
- ✅ Implement CORS properly
- ✅ Use rate limiting

## Troubleshooting

### "Token has expired"

**Cause**: Token's `exp` claim is in the past

**Solution**:
- Implement automatic refresh
- Reduce token expiration time
- Clear localStorage and re-authenticate

### "Invalid authentication credentials"

**Cause**: Token signature doesn't match

**Solution**:
- Verify JWT_SECRET_KEY matches between apps
- Check JWT_ALGORITHM setting
- Ensure token wasn't tampered with

### "Permission denied" (403)

**Cause**: User lacks required permissions

**Solution**:
- Check user's role and permissions
- Verify permission requirements
- Update user's role if appropriate

### Token not being sent

**Cause**: Token not in localStorage or headers

**Solution**:
- Verify token is stored: `localStorage.getItem('auth_token')`
- Check API client interceptor is working
- Ensure AuthProvider wraps your app

## Performance Considerations

### Optimization Targets

- Token verification: <10ms
- Permission check: <5ms
- Token refresh: <200ms
- Auth state hydration: <100ms

### Caching

- Cache decoded token payload to avoid repeated decode
- Cache permission checks for the same request
- Use Redis for revoked tokens list

### Monitoring

Track these metrics:

- Authentication success/failure rate
- Token expiration rate
- Refresh token usage
- Permission denial rate
- Average verification time

## Testing

### Backend Tests

```python
import pytest
from src.api.middleware.auth import jwt_auth

def test_valid_token():
    token = create_test_token(
        user_id="test123",
        role="admin"
    )
    payload = await jwt_auth.verify_token(token)
    assert payload["sub"] == "test123"
    assert payload["role"] == "admin"

def test_expired_token():
    token = create_expired_token()
    with pytest.raises(HTTPException) as exc:
        await jwt_auth.verify_token(token)
    assert exc.value.status_code == 401
```

### Frontend Tests

```typescript
import { renderHook } from '@testing-library/react-hooks';
import { useAuth } from '@/contexts/AuthContext';

test('login sets user and token', () => {
  const { result } = renderHook(() => useAuth());

  act(() => {
    result.current.login(validToken);
  });

  expect(result.current.user).toBeTruthy();
  expect(result.current.isAuthenticated).toBe(true);
});

test('logout clears user and token', () => {
  const { result } = renderHook(() => useAuth());

  act(() => {
    result.current.logout();
  });

  expect(result.current.user).toBeNull();
  expect(result.current.isAuthenticated).toBe(false);
});
```

## Migration Guide

### From Basic Auth

1. Update JWT_SECRET_KEY in both apps
2. Deploy backend with new auth middleware
3. Update frontend to use AuthContext
4. Wrap protected routes with ProtectedRoute
5. Update API client to use interceptors
6. Test authentication flow end-to-end
7. Deploy to production

### Adding New Permissions

1. Add permission constant to `backend/src/core/permissions.py`
2. Add to frontend `frontend/src/types/permissions.ts`
3. Update ROLE_PERMISSIONS mapping
4. Add permission checks to relevant routes
5. Update UI to show/hide based on permission
6. Add tests for new permission

## Support

For authentication issues:

1. Check the troubleshooting section
2. Verify environment configuration
3. Check logs for detailed error messages
4. Open a GitHub issue with:
   - Error message
   - Steps to reproduce
   - Environment details (dev/staging/prod)
   - Relevant logs
