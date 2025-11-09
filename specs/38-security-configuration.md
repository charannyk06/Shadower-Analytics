# Specification: Security Configuration

## Overview
Define comprehensive security measures including authentication, authorization, encryption, vulnerability scanning, and compliance requirements.

## Technical Requirements

### Authentication & Authorization

#### JWT Token Security
```python
# backend/security/jwt_handler.py
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
from typing import Optional, Dict, Any

class JWTHandler:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # Rotate secrets periodically
        self.secret_rotation_interval = timedelta(days=30)
        self.last_rotation = datetime.utcnow()
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with security claims"""
        to_encode = data.copy()
        
        # Add security claims
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),  # JWT ID for tracking
            "type": "access",
            "iss": "analytics.shadower.ai",
            "aud": "shadower-analytics"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="shadower-analytics",
                issuer="analytics.shadower.ai"
            )
            
            # Check if token is blacklisted
            if self.is_token_blacklisted(payload.get("jti")):
                raise JWTError("Token has been revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token has expired")
        except JWTError as e:
            raise HTTPException(401, f"Invalid token: {str(e)}")
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is in blacklist"""
        return await redis.exists(f"blacklist:{jti}")
    
    async def blacklist_token(self, token: str, jti: str, exp: int):
        """Add token to blacklist"""
        ttl = exp - int(datetime.utcnow().timestamp())
        if ttl > 0:
            await redis.setex(f"blacklist:{jti}", ttl, "1")
```

#### Role-Based Access Control (RBAC)
```python
# backend/security/rbac.py
from enum import Enum
from typing import List, Set

class Role(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"

class Permission(Enum):
    # Dashboard permissions
    VIEW_EXECUTIVE_DASHBOARD = "view_executive_dashboard"
    VIEW_AGENT_ANALYTICS = "view_agent_analytics"
    VIEW_USER_ANALYTICS = "view_user_analytics"
    
    # Data permissions
    EXPORT_DATA = "export_data"
    VIEW_SENSITIVE_DATA = "view_sensitive_data"
    DELETE_DATA = "delete_data"
    
    # Configuration permissions
    MANAGE_ALERTS = "manage_alerts"
    MANAGE_REPORTS = "manage_reports"
    MANAGE_INTEGRATIONS = "manage_integrations"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_WORKSPACE = "manage_workspace"
    VIEW_AUDIT_LOGS = "view_audit_logs"

# Role-permission mapping
ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions
    
    Role.ADMIN: {
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_AGENT_ANALYTICS,
        Permission.VIEW_USER_ANALYTICS,
        Permission.EXPORT_DATA,
        Permission.VIEW_SENSITIVE_DATA,
        Permission.MANAGE_ALERTS,
        Permission.MANAGE_REPORTS,
        Permission.MANAGE_INTEGRATIONS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS
    },
    
    Role.ANALYST: {
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_AGENT_ANALYTICS,
        Permission.VIEW_USER_ANALYTICS,
        Permission.EXPORT_DATA,
        Permission.MANAGE_REPORTS
    },
    
    Role.VIEWER: {
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_AGENT_ANALYTICS
    },
    
    Role.API_USER: {
        Permission.VIEW_AGENT_ANALYTICS,
        Permission.EXPORT_DATA
    }
}

class PermissionChecker:
    @staticmethod
    def has_permission(
        user_role: Role,
        required_permission: Permission,
        custom_permissions: Set[Permission] = None
    ) -> bool:
        """Check if user has required permission"""
        base_permissions = ROLE_PERMISSIONS.get(user_role, set())
        user_permissions = base_permissions.union(custom_permissions or set())
        return required_permission in user_permissions
    
    @staticmethod
    def require_permission(permission: Permission):
        """Decorator to enforce permission requirement"""
        def decorator(func):
            async def wrapper(*args, user: User = Depends(get_current_user), **kwargs):
                if not PermissionChecker.has_permission(
                    user.role,
                    permission,
                    user.custom_permissions
                ):
                    raise HTTPException(
                        403,
                        f"Permission denied: {permission.value}"
                    )
                return await func(*args, user=user, **kwargs)
            return wrapper
        return decorator
```

### Data Encryption

#### Encryption at Rest
```python
# backend/security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class DataEncryption:
    def __init__(self):
        self.master_key = os.getenv("MASTER_ENCRYPTION_KEY")
        self.salt = os.getenv("ENCRYPTION_SALT").encode()
        
    def get_encryption_key(self, context: str = "") -> bytes:
        """Derive encryption key from master key"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt + context.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_key.encode())
        )
        return key
    
    def encrypt_field(self, data: str, field_name: str) -> str:
        """Encrypt sensitive field"""
        key = self.get_encryption_key(field_name)
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    def decrypt_field(self, encrypted_data: str, field_name: str) -> str:
        """Decrypt sensitive field"""
        key = self.get_encryption_key(field_name)
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()

# Database field encryption
from sqlalchemy import TypeDecorator, String

class EncryptedString(TypeDecorator):
    impl = String
    
    def __init__(self, encryption_context: str, *args, **kwargs):
        self.encryption_context = encryption_context
        self.encryptor = DataEncryption()
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encryptor.encrypt_field(value, self.encryption_context)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encryptor.decrypt_field(value, self.encryption_context)
        return value
```

### API Security

#### Rate Limiting
```python
# backend/security/rate_limiting.py
from typing import Dict, Tuple
import time

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.limits = {
            "default": (1000, 3600),  # 1000 requests per hour
            "api_key": (5000, 3600),  # 5000 requests per hour
            "export": (10, 3600),     # 10 exports per hour
            "report": (50, 3600),      # 50 reports per hour
        }
    
    async def check_rate_limit(
        self,
        key: str,
        limit_type: str = "default",
        custom_limit: Tuple[int, int] = None
    ) -> Dict[str, Any]:
        """Check and update rate limit"""
        limit, window = custom_limit or self.limits[limit_type]
        
        # Use sliding window algorithm
        now = time.time()
        window_start = now - window
        
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in window
        request_count = await self.redis.zcard(key)
        
        if request_count >= limit:
            # Rate limit exceeded
            reset_time = await self.redis.zrange(key, 0, 0, withscores=True)
            if reset_time:
                reset_in = int(reset_time[0][1] + window - now)
            else:
                reset_in = window
            
            raise HTTPException(
                429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": window,
                    "reset_in": reset_in
                },
                headers={"Retry-After": str(reset_in)}
            )
        
        # Add current request
        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, window)
        
        return {
            "limit": limit,
            "remaining": limit - request_count - 1,
            "reset_in": window
        }
```

#### Input Validation & Sanitization
```python
# backend/security/validation.py
from pydantic import BaseModel, validator, constr, conint
import re
import html
import bleach

class SecureInputValidator:
    # SQL injection prevention
    SQL_BLACKLIST = [
        "SELECT", "INSERT", "UPDATE", "DELETE", "DROP",
        "EXEC", "UNION", "--", "/*", "*/"
    ]
    
    # XSS prevention
    ALLOWED_TAGS = ['b', 'i', 'u', 'strong', 'em', 'p', 'br']
    ALLOWED_ATTRIBUTES = {}
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """Sanitize input for SQL queries"""
        upper_value = value.upper()
        for keyword in SecureInputValidator.SQL_BLACKLIST:
            if keyword in upper_value:
                raise ValueError(f"Potentially dangerous SQL keyword detected: {keyword}")
        
        # Escape special characters
        return re.sub(r'[^\w\s\-\.]', '', value)
    
    @staticmethod
    def sanitize_html_input(value: str) -> str:
        """Sanitize HTML input to prevent XSS"""
        # Clean HTML
        cleaned = bleach.clean(
            value,
            tags=SecureInputValidator.ALLOWED_TAGS,
            attributes=SecureInputValidator.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        # Additional escaping
        return html.escape(cleaned)
    
    @staticmethod
    def validate_file_upload(file) -> bool:
        """Validate uploaded files"""
        # Check file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            raise ValueError("File size exceeds 10MB limit")
        
        # Check file extension
        allowed_extensions = {'.csv', '.json', '.xlsx', '.pdf'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"File type {file_ext} not allowed")
        
        # Check MIME type
        allowed_mimes = {
            'text/csv', 'application/json',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/pdf'
        }
        if file.content_type not in allowed_mimes:
            raise ValueError(f"MIME type {file.content_type} not allowed")
        
        return True

# Pydantic models with validation
class SecureQueryParams(BaseModel):
    workspace_id: constr(regex=r'^ws_[a-zA-Z0-9]{10,}$')
    search_query: constr(max_length=200)
    
    @validator('search_query')
    def sanitize_search(cls, v):
        return SecureInputValidator.sanitize_sql_input(v)
```

### Security Headers

#### Security Middleware
```python
# backend/security/headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = self.get_csp()
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
    
    def get_csp(self) -> str:
        """Generate Content Security Policy"""
        return "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' wss://analytics.shadower.ai",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ])
```

### Audit Logging

#### Audit Logger
```python
# backend/security/audit.py
from typing import Any, Dict
import json

class AuditLogger:
    def __init__(self, db_session):
        self.db = db_session
        self.sensitive_fields = {
            'password', 'token', 'secret', 'api_key', 'credit_card'
        }
    
    async def log_event(
        self,
        event_type: str,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """Log security-relevant event"""
        # Sanitize sensitive data
        sanitized_details = self.sanitize_details(details)
        
        audit_log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=json.dumps(sanitized_details),
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        
        # Alert on critical events
        if event_type in ['security_breach', 'unauthorized_access', 'data_export']:
            await self.send_security_alert(audit_log)
    
    def sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from audit logs"""
        sanitized = {}
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized
```

### Vulnerability Scanning

#### Security Scanner Configuration
```python
# backend/security/scanner.py
import subprocess
import json

class SecurityScanner:
    def __init__(self):
        self.scanners = {
            "dependencies": self.scan_dependencies,
            "code": self.scan_code,
            "containers": self.scan_containers,
            "secrets": self.scan_secrets
        }
    
    async def run_security_scan(self) -> Dict[str, Any]:
        """Run comprehensive security scan"""
        results = {}
        
        for scan_type, scanner_func in self.scanners.items():
            try:
                results[scan_type] = await scanner_func()
            except Exception as e:
                results[scan_type] = {"error": str(e)}
        
        return results
    
    async def scan_dependencies(self) -> Dict[str, Any]:
        """Scan Python dependencies for vulnerabilities"""
        # Using safety
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    
    async def scan_code(self) -> Dict[str, Any]:
        """Scan code for security issues"""
        # Using bandit
        result = subprocess.run(
            ["bandit", "-r", ".", "-f", "json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    
    async def scan_secrets(self) -> Dict[str, Any]:
        """Scan for hardcoded secrets"""
        # Using trufflehog
        result = subprocess.run(
            ["trufflehog", "filesystem", ".", "--json"],
            capture_output=True,
            text=True
        )
        findings = []
        for line in result.stdout.splitlines():
            if line:
                findings.append(json.loads(line))
        return {"findings": findings}
```

### Compliance

#### GDPR Compliance
```python
# backend/security/gdpr.py
class GDPRCompliance:
    @staticmethod
    async def export_user_data(user_id: str) -> Dict[str, Any]:
        """Export all user data for GDPR request"""
        data = {
            "user_profile": await get_user_profile(user_id),
            "activity_logs": await get_user_activities(user_id),
            "analytics_data": await get_user_analytics(user_id),
            "preferences": await get_user_preferences(user_id)
        }
        
        # Log data export
        await audit_logger.log_event(
            event_type="gdpr_data_export",
            user_id=user_id,
            action="export_personal_data"
        )
        
        return data
    
    @staticmethod
    async def delete_user_data(user_id: str):
        """Delete user data for GDPR right to be forgotten"""
        # Anonymize instead of delete for analytics integrity
        await anonymize_user_data(user_id)
        
        # Log deletion
        await audit_logger.log_event(
            event_type="gdpr_data_deletion",
            user_id=user_id,
            action="anonymize_personal_data"
        )
```

## Implementation Priority
1. JWT authentication and RBAC
2. Input validation and sanitization
3. Rate limiting
4. Audit logging
5. Vulnerability scanning

## Success Metrics
- Zero security breaches
- Authentication latency < 50ms
- 100% audit log coverage for sensitive operations
- Vulnerability scan frequency: daily