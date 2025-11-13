# Authentication API Implementation

This document describes the authentication and authorization API endpoints implemented for the Shadow Analytics service.

## Overview

The authentication system provides secure access to the analytics service through:
- JWT token verification from the main Shadower application
- Token exchange for analytics-specific tokens
- Permission-based access control
- API key management for programmatic access
- Session management
- Security headers middleware

## Architecture

The analytics service uses a **shared JWT authentication** model:

1. Users authenticate in the main Shadower application
2. Main app generates JWT tokens with user claims
3. Analytics service verifies tokens using the shared JWT secret
4. Tokens can be exchanged for analytics-specific tokens

## API Endpoints

### Authentication Endpoints

#### POST `/api/v1/auth/verify`
Verify JWT token from main app and validate workspace access.

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "workspace_id": "ws_123"
}
```

**Response:**
```json
{
  "valid": true,
  "user_id": "user_123",
  "workspace_id": "ws_123",
  "permissions": ["view_executive_dashboard", "export_data"],
  "expires_at": 1234567890,
  "role": "admin"
}
```

#### POST `/api/v1/auth/exchange`
Exchange main app token for analytics-specific token.

**Headers:**
- `X-Main-Token`: Token from main application

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST `/api/v1/auth/refresh`
Refresh analytics access token.

**Request:**
```json
{
  "refresh_token": "refresh_token_string"
}
```

**Response:**
```json
{
  "access_token": "new_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST `/api/v1/auth/logout`
Logout user by blacklisting their token.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

#### GET `/api/v1/auth/me`
Get current authenticated user information.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "is_active": true,
  "email_verified": true,
  "two_factor_enabled": false,
  "created_at": "2024-01-01T00:00:00Z",
  "workspaces": ["ws_123", "ws_456"],
  "default_workspace_id": "ws_123"
}
```

### Permission Management

#### GET `/api/v1/auth/permissions`
Get user's analytics permissions for workspace.

**Query Parameters:**
- `workspace_id` (required): Workspace ID

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "user_id": "user_123",
  "workspace_id": "ws_123",
  "permissions": {
    "view_executive_dashboard": true,
    "view_agent_analytics": true,
    "view_user_analytics": false,
    "export_data": true,
    "manage_reports": false,
    "configure_alerts": false,
    "admin_access": false,
    "view_sensitive_data": false
  },
  "role": "admin",
  "custom_permissions": null
}
```

#### PUT `/api/v1/auth/permissions`
Update user's analytics permissions (admin only).

**Request:**
```json
{
  "user_id": "user_123",
  "workspace_id": "ws_456",
  "permissions": {
    "view_user_analytics": true,
    "export_data": false
  }
}
```

### API Key Management

#### POST `/api/v1/auth/api-keys`
Create API key for programmatic access (admin only).

**Request:**
```json
{
  "name": "Production API Key",
  "workspace_id": "ws_123",
  "permissions": ["read_analytics", "export_data"],
  "expires_at": "2024-12-31T23:59:59Z",
  "rate_limit": 1000
}
```

**Response:**
```json
{
  "api_key": "sk_7h3_4c7u41_k3y_sh0wn_0nc3",
  "key_id": "key_123",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z",
  "warning": "Store this key securely. It won't be shown again."
}
```

#### GET `/api/v1/auth/api-keys`
List API keys for workspace (admin only).

**Query Parameters:**
- `workspace_id` (required): Workspace ID

**Response:**
```json
{
  "api_keys": [
    {
      "key_id": "key_123",
      "name": "Production Key",
      "last_4": "...abc4",
      "created_at": "2024-01-01T00:00:00Z",
      "last_used": "2024-01-15T10:30:00Z",
      "expires_at": "2024-12-31T23:59:59Z",
      "is_active": true,
      "usage_count": 5420
    }
  ]
}
```

#### DELETE `/api/v1/auth/api-keys/{key_id}`
Revoke API key (admin only).

**Response:**
```json
{
  "key_id": "key_123",
  "revoked": true,
  "revoked_at": "2024-01-15T14:30:00Z"
}
```

### Session Management

#### GET `/api/v1/auth/sessions`
Get user's active sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sess_123",
      "device": "Chrome on MacOS",
      "ip_address": "192.168.1.1",
      "location": "San Francisco, CA",
      "created_at": "2024-01-15T08:00:00Z",
      "last_active": "2024-01-15T14:30:00Z",
      "is_current": true
    }
  ]
}
```

#### DELETE `/api/v1/auth/sessions/{session_id}`
Terminate specific session.

**Response:**
```json
{
  "session_id": "sess_123",
  "terminated": true
}
```

## Database Schema

### API Keys Table
```sql
CREATE TABLE api_keys (
    id VARCHAR(255) PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb NOT NULL,
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_used TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(255)
);
```

### User Sessions Table
```sql
CREATE TABLE user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_token_hash VARCHAR(255) UNIQUE NOT NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    country_code VARCHAR(2),
    city VARCHAR(100),
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    terminated_at TIMESTAMP
);
```

### Refresh Tokens Table
```sql
CREATE TABLE refresh_tokens (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    access_token_jti VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    last_used TIMESTAMP
);
```

## Security Features

### Security Headers Middleware

The `SecurityHeadersMiddleware` adds the following headers to all responses:

- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Enforces HTTPS
- `Content-Security-Policy` - Restricts resource loading
- `Referrer-Policy` - Controls referrer information
- `Permissions-Policy` - Disables dangerous browser features

### Token Security

- Tokens are verified using JWT with HS256 algorithm
- Token blacklisting via Redis for revoked tokens
- Token caching for performance (30s TTL)
- Automatic token expiration checking

### API Key Security

- API keys are hashed with SHA-256 before storage
- Keys are only shown once during creation
- Support for key expiration and revocation
- Rate limiting per key
- Usage tracking

## Configuration

### Environment Variables

```env
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=30

# Redis (for token blacklist and caching)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/shadower_analytics
```

## User Roles and Permissions

### Roles
- `owner` - Full access to all features
- `admin` - Administrative access, can manage users and permissions
- `member` - Standard access to analytics features
- `viewer` - Read-only access

### Permission Matrix

| Permission | Owner | Admin | Member | Viewer |
|------------|-------|-------|--------|--------|
| view_executive_dashboard | ✓ | ✓ | ✓ | ✓ |
| view_agent_analytics | ✓ | ✓ | ✓ | ✓ |
| view_user_analytics | ✓ | ✓ | ✗ | ✗ |
| export_data | ✓ | ✓ | ✓ | ✗ |
| manage_reports | ✓ | ✓ | ✗ | ✗ |
| configure_alerts | ✓ | ✓ | ✗ | ✗ |
| admin_access | ✓ | ✓ | ✗ | ✗ |
| view_sensitive_data | ✓ | ✗ | ✗ | ✗ |

## Implementation Files

### Backend Files
- `backend/src/models/schemas/auth.py` - Pydantic models for auth
- `backend/src/api/routes/auth.py` - Authentication endpoints
- `backend/src/models/database/tables.py` - SQLAlchemy models (APIKey, UserSession, RefreshToken)
- `backend/src/api/middleware/security.py` - Security headers middleware
- `backend/src/core/security.py` - JWT utilities (existing)
- `backend/src/core/token_manager.py` - Token blacklist and caching (existing)
- `backend/src/core/permissions.py` - Permission utilities (existing)

### Database Migrations
- `database/migrations/027_create_auth_tables.sql` - Creates auth tables
- `database/migrations/027_rollback_auth_tables.sql` - Rollback migration

## Usage Examples

### Verifying a Token

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/verify",
    json={
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "workspace_id": "ws_123"
    }
)

if response.json()["valid"]:
    print(f"User: {response.json()['user_id']}")
    print(f"Permissions: {response.json()['permissions']}")
```

### Creating an API Key

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/api-keys",
    headers={"Authorization": "Bearer <admin_token>"},
    json={
        "name": "Production API Key",
        "workspace_id": "ws_123",
        "permissions": ["read_analytics", "export_data"],
        "rate_limit": 1000
    }
)

# IMPORTANT: Save this key - it won't be shown again!
api_key = response.json()["api_key"]
print(f"API Key: {api_key}")
```

### Using an API Key

```python
import requests

# Use the API key in the Authorization header
headers = {
    "Authorization": f"Bearer {api_key}"
}

response = requests.get(
    "http://localhost:8000/api/v1/executive/summary",
    headers=headers
)
```

## Testing

### Run Database Migration

```bash
cd database
./run_migrations.sh
```

### Test Authentication Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/auth/health

# Verify token
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"<jwt_token>","workspace_id":"ws_123"}'

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

## Performance Considerations

- Token verification is cached in Redis (30s TTL)
- API key lookups use database indexes on key_hash
- Session queries are indexed by user_id and is_active
- Expired tokens/sessions are automatically excluded from queries

## Security Best Practices

1. **Always use HTTPS in production** - The `Strict-Transport-Security` header enforces this
2. **Rotate JWT secrets regularly** - Update `JWT_SECRET_KEY` periodically
3. **Set strong API key rate limits** - Default is 1000 requests/hour
4. **Monitor failed authentication attempts** - Implement alerting for suspicious activity
5. **Use token expiration** - Tokens should expire and require refresh
6. **Revoke compromised tokens immediately** - Use the logout endpoint
7. **Audit API key usage** - Track `last_used` and `usage_count`

## Future Enhancements

- OAuth integration (Google, GitHub, Microsoft)
- Two-factor authentication (2FA)
- Password reset functionality
- Email verification
- Webhook notifications for security events
- Advanced rate limiting per user/workspace
- IP whitelisting for API keys
- Audit logs for all authentication events

## Support

For issues or questions about the authentication system, please contact the development team or create an issue in the repository.
