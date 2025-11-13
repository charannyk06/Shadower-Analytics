# Security Configuration

This document describes the comprehensive security measures implemented in the Shadower Analytics backend.

## Overview

The security configuration implements multiple layers of protection including:

- Enhanced JWT authentication with security claims
- Role-Based Access Control (RBAC)
- Data encryption at rest
- Rate limiting
- Input validation and sanitization
- Audit logging
- Vulnerability scanning
- GDPR compliance

## Authentication & Authorization

### JWT Token Security

**Location:** `src/core/security.py`, `src/core/token_manager.py`

#### Features:
- Enhanced JWT tokens with security claims:
  - `jti` (JWT ID) for token tracking and revocation
  - `iss` (Issuer) for token source validation
  - `aud` (Audience) for token recipient validation
  - `iat` (Issued At) timestamp
  - `exp` (Expiration) time
  - `type` (Token type: access/refresh)

- Token blacklisting using Redis
- Token caching for performance
- Audience and issuer validation

#### Usage:

```python
from src.core.security import create_access_token, verify_token

# Create token
token = create_access_token(
    data={"sub": user_id, "workspace_id": workspace_id},
    token_type="access"
)

# Verify token
payload = await verify_token(token)
```

### Role-Based Access Control (RBAC)

**Location:** `src/core/permissions.py`

#### Roles:
- **SUPER_ADMIN**: All permissions
- **OWNER**: Full workspace control
- **ADMIN**: Workspace management
- **ANALYST**: Data analysis and reporting
- **MEMBER**: Basic access
- **VIEWER**: Read-only access
- **API_USER**: Programmatic access

#### Permissions:

**Dashboard Permissions:**
- `VIEW_EXECUTIVE_DASHBOARD`
- `VIEW_AGENT_ANALYTICS`
- `VIEW_USER_ANALYTICS`
- `VIEW_FINANCIAL_METRICS`

**Data Permissions:**
- `EXPORT_DATA`
- `VIEW_SENSITIVE_DATA`
- `DELETE_DATA`

**Configuration Permissions:**
- `MANAGE_ALERTS`
- `MANAGE_REPORTS`
- `MANAGE_INTEGRATIONS`

**Admin Permissions:**
- `MANAGE_USERS`
- `MANAGE_WORKSPACE`
- `VIEW_AUDIT_LOGS`

#### Usage:

```python
from src.core.permissions import has_permission, Permissions, Roles

# Check permission
if has_permission(user.role, Permissions.EXPORT_DATA):
    # Allow export
    pass

# With custom permissions
custom_perms = {Permissions.EXPORT_DATA}
if has_permission(user.role, Permissions.EXPORT_DATA, custom_perms):
    pass
```

## Data Encryption

**Location:** `src/core/encryption.py`

### Features:
- Field-level encryption using Fernet (symmetric encryption)
- Key derivation using PBKDF2
- Context-specific encryption keys
- SQLAlchemy type decorators for automatic encryption

### Usage:

```python
from src.core.encryption import DataEncryption, EncryptedString
from sqlalchemy import Column

# Manual encryption
encryptor = DataEncryption()
encrypted = encryptor.encrypt_field("sensitive data", "field_name")
decrypted = encryptor.decrypt_field(encrypted, "field_name")

# Automatic encryption in SQLAlchemy models
class User(Base):
    ssn = Column(EncryptedString('ssn', 255))
    api_key = Column(EncryptedString('api_key', 255))
```

### Configuration:

Set environment variables:
```bash
MASTER_ENCRYPTION_KEY="your-secret-key"
ENCRYPTION_SALT="your-salt"
```

## Rate Limiting

**Location:** `src/core/rate_limiting.py`

### Features:
- Redis-based sliding window algorithm
- Configurable limits per endpoint type
- Automatic client identification (user_id, API key, or IP)

### Rate Limits:
- **Default**: 1000 requests/hour
- **API Key**: 5000 requests/hour
- **Export**: 10 requests/hour
- **Report**: 50 requests/hour
- **Auth**: 5 attempts/5 minutes
- **Analytics**: 100 requests/minute

### Usage:

```python
from src.core.rate_limiting import check_rate_limit, rate_limit

# Manual check
await check_rate_limit(request, "export")

# Decorator
@router.post("/export")
@rate_limit("export")
async def export_data(request: Request):
    pass

# Custom limit
@rate_limit(requests=100, window=3600)
async def custom_endpoint(request: Request):
    pass
```

## Input Validation & Sanitization

**Location:** `src/core/validation.py`

### Features:
- SQL injection prevention
- XSS attack prevention
- File upload validation
- Email/URL validation
- Filename sanitization

### Usage:

```python
from src.core.validation import SecureInputValidator

validator = SecureInputValidator()

# Sanitize SQL input
clean = validator.sanitize_sql_input(user_input)

# Sanitize HTML
clean_html = validator.sanitize_html_input(html_input)

# Validate file upload
validator.validate_file_upload(
    filename="data.csv",
    content_type="text/csv",
    file_size=1024
)

# Validate email
validator.validate_email("user@example.com")
```

## Audit Logging

**Location:** `src/core/audit.py`, `src/models/database/tables.py`

### Features:
- Comprehensive security event logging
- Automatic sensitive data redaction
- Database storage with efficient indexing
- Security alert triggering for critical events

### Event Types:
- `authentication` - Login/logout events
- `authorization` - Access control events
- `data_access` - Data read operations
- `data_export` - Data export operations
- `data_modification` - Data changes
- `data_deletion` - Data deletion
- `admin_action` - Administrative actions
- `security_breach` - Security incidents
- `unauthorized_access` - Failed access attempts

### Usage:

```python
from src.core.audit import AuditLogger, log_authentication, log_data_export

# Using AuditLogger
logger = AuditLogger(db_session)
await logger.log_event(
    event_type="data_export",
    action="export",
    user_id=user.id,
    workspace_id=workspace.id,
    resource_type="analytics",
    details={"format": "csv", "records": 1000}
)

# Convenience functions
await log_authentication(
    db=db_session,
    user_id=user.id,
    action="login",
    status="success",
    ip_address=request.client.host
)
```

## Vulnerability Scanning

**Location:** `src/core/vulnerability_scanner.py`

### Features:
- Dependency vulnerability scanning (using `safety`)
- Code security analysis (using `bandit`)
- Secret detection (using `detect-secrets`)

### Usage:

```python
from src.core.vulnerability_scanner import run_security_scan

# Run all scans
results = await run_security_scan()

# Run specific scans
results = await run_security_scan(scan_types=["dependencies", "code"])

# Generate report
scanner = SecurityScanner()
report = scanner.get_scan_report(results)
print(report)
```

### Running Manually:

```bash
# Install security tools
pip install safety bandit detect-secrets

# Run scans
safety check
bandit -r .
detect-secrets scan
```

## GDPR Compliance

**Location:** `src/core/gdpr.py`

### Features:
- Right to access (Article 15)
- Right to erasure/be forgotten (Article 17)
- Right to data portability (Article 20)
- Consent management
- Data retention policies

### Usage:

```python
from src.core.gdpr import GDPRCompliance, export_user_data, delete_user_data

gdpr = GDPRCompliance(db_session)

# Export user data
user_data = await gdpr.export_user_data(user_id)

# Delete user data (with anonymization)
result = await gdpr.delete_user_data(user_id, anonymize=True)

# Get consent status
consent = await gdpr.get_consent_status(user_id)

# Update consent
await gdpr.update_consent(user_id, "analytics", granted=True)
```

## Security Headers

**Location:** `src/api/middleware/security.py`

### Headers Applied:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: ...`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

## Database Migration

To create the audit_logs table, run:

```bash
cd backend
alembic upgrade head
```

## Environment Variables

Required environment variables for security:

```bash
# JWT Configuration
JWT_SECRET_KEY="your-secret-key-min-32-chars"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Encryption
MASTER_ENCRYPTION_KEY="your-encryption-master-key"
ENCRYPTION_SALT="your-encryption-salt"

# Redis (for rate limiting and token blacklisting)
REDIS_URL="redis://localhost:6379"
REDIS_PASSWORD="your-redis-password"

# Database
DATABASE_URL="postgresql://user:pass@localhost/db"
```

## Testing

Run security tests:

```bash
cd backend
pytest tests/test_security_configuration.py -v
```

## Security Best Practices

1. **Always use HTTPS** in production
2. **Rotate JWT secrets** periodically
3. **Monitor audit logs** for suspicious activity
4. **Run vulnerability scans** regularly
5. **Keep dependencies updated**
6. **Use strong passwords** for all services
7. **Enable rate limiting** on all public endpoints
8. **Validate and sanitize** all user inputs
9. **Encrypt sensitive data** at rest and in transit
10. **Implement least privilege** access control

## Security Incident Response

1. Check audit logs: `SELECT * FROM analytics.audit_logs WHERE severity = 'critical'`
2. Review failed authentication attempts
3. Check for unusual data exports
4. Verify rate limit violations
5. Run security scan: `python -m src.core.vulnerability_scanner`

## Compliance

This security configuration helps meet requirements for:
- **GDPR** (General Data Protection Regulation)
- **SOC 2** (Service Organization Control 2)
- **ISO 27001** (Information Security Management)
- **OWASP Top 10** (Web Application Security)

## Support

For security issues or questions:
1. Review this documentation
2. Check audit logs for details
3. Run security scans
4. Contact security team

## License

See main project LICENSE file.
