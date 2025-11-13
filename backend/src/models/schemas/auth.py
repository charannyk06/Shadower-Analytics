"""Authentication and authorization schemas."""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OAuthProvider(str, Enum):
    """OAuth provider enumeration."""

    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


# Token schemas
class TokenVerification(BaseModel):
    """Token verification request."""

    token: str = Field(..., description="JWT token to verify")
    workspace_id: str = Field(..., description="Workspace ID to validate access")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token if applicable")


class TokenVerificationResponse(BaseModel):
    """Token verification response."""

    valid: bool = Field(..., description="Whether the token is valid")
    user_id: str = Field(..., description="User ID from token")
    workspace_id: str = Field(..., description="Workspace ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    expires_at: int = Field(..., description="Token expiration timestamp")
    role: Optional[str] = Field(None, description="User role in workspace")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


# User schemas
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User full name")


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8, description="User password")


class UserLogin(BaseModel):
    """User login schema."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class UserResponse(UserBase):
    """User response schema."""

    id: str = Field(..., description="User ID")
    is_active: bool = Field(default=True, description="Whether user is active")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    two_factor_enabled: bool = Field(default=False, description="Whether 2FA is enabled")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update schema."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None


class CurrentUserResponse(UserResponse):
    """Current authenticated user response."""

    workspaces: List[str] = Field(default_factory=list, description="User's workspace IDs")
    default_workspace_id: Optional[str] = None


# Permission schemas
class PermissionSet(BaseModel):
    """Permission set for a user in a workspace."""

    view_executive_dashboard: bool = Field(default=True)
    view_agent_analytics: bool = Field(default=True)
    view_user_analytics: bool = Field(default=False)
    export_data: bool = Field(default=True)
    manage_reports: bool = Field(default=False)
    configure_alerts: bool = Field(default=False)
    admin_access: bool = Field(default=False)
    view_sensitive_data: bool = Field(default=False)


class UserPermissionsResponse(BaseModel):
    """User permissions response."""

    user_id: str = Field(..., description="User ID")
    workspace_id: str = Field(..., description="Workspace ID")
    permissions: PermissionSet = Field(..., description="User permissions")
    role: UserRole = Field(..., description="User role in workspace")
    custom_permissions: Optional[Dict[str, bool]] = Field(None, description="Custom permissions")


class PermissionUpdate(BaseModel):
    """Permission update request."""

    user_id: str = Field(..., description="User ID to update permissions for")
    workspace_id: str = Field(..., description="Workspace ID")
    permissions: Dict[str, bool] = Field(..., description="Permissions to update")


# API Key schemas
class APIKeyConfig(BaseModel):
    """API key configuration."""

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    workspace_id: str = Field(..., description="Workspace ID")
    permissions: List[str] = Field(default_factory=list, description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    rate_limit: Optional[int] = Field(1000, description="Rate limit per hour")


class APIKeyResponse(BaseModel):
    """API key response (shown only once)."""

    api_key: str = Field(..., description="The API key - store securely")
    key_id: str = Field(..., description="API key ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    warning: str = Field(
        default="Store this key securely. It won't be shown again.",
        description="Security warning"
    )


class APIKeyListItem(BaseModel):
    """API key list item (without the actual key)."""

    key_id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    last_4: str = Field(..., description="Last 4 characters of key")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last used timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(default=True, description="Whether key is active")
    usage_count: int = Field(default=0, description="Number of times used")


class APIKeyListResponse(BaseModel):
    """List of API keys."""

    api_keys: List[APIKeyListItem] = Field(default_factory=list, description="API keys")


class APIKeyRevokeResponse(BaseModel):
    """API key revoke response."""

    key_id: str = Field(..., description="Revoked key ID")
    revoked: bool = Field(default=True, description="Whether revocation was successful")
    revoked_at: datetime = Field(..., description="Revocation timestamp")


# Session schemas
class SessionInfo(BaseModel):
    """Session information."""

    session_id: str = Field(..., description="Session ID")
    device: str = Field(..., description="Device information")
    ip_address: str = Field(..., description="IP address")
    location: Optional[str] = Field(None, description="Geographic location")
    created_at: datetime = Field(..., description="Session creation time")
    last_active: datetime = Field(..., description="Last activity time")
    is_current: bool = Field(default=False, description="Whether this is the current session")


class SessionListResponse(BaseModel):
    """List of active sessions."""

    sessions: List[SessionInfo] = Field(default_factory=list, description="Active sessions")


class SessionTerminateResponse(BaseModel):
    """Session termination response."""

    session_id: str = Field(..., description="Terminated session ID")
    terminated: bool = Field(default=True, description="Whether termination was successful")


# OAuth schemas
class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization response."""

    auth_url: str = Field(..., description="OAuth authorization URL")
    provider: OAuthProvider = Field(..., description="OAuth provider")


class OAuthCallback(BaseModel):
    """OAuth callback data."""

    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="State parameter for CSRF protection")


class OAuthTokenResponse(BaseModel):
    """OAuth token response."""

    access_token: str = Field(..., description="Access token")
    user: UserResponse = Field(..., description="User information")


# Two-Factor Authentication schemas
class TwoFactorSetupResponse(BaseModel):
    """Two-factor authentication setup response."""

    qr_code: str = Field(..., description="QR code as base64 encoded image")
    secret: str = Field(..., description="2FA secret key")
    backup_codes: List[str] = Field(..., description="Backup codes for account recovery")


class TwoFactorVerification(BaseModel):
    """Two-factor verification request."""

    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate that code is 6 digits."""
        if not v.isdigit():
            raise ValueError('Code must contain only digits')
        return v


class TwoFactorVerificationResponse(BaseModel):
    """Two-factor verification response."""

    verified: bool = Field(..., description="Whether code was verified")
    two_factor_enabled: bool = Field(..., description="Whether 2FA is now enabled")


# Password reset schemas
class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordResetResponse(BaseModel):
    """Password reset response."""

    success: bool = Field(default=True, description="Whether reset was successful")
    message: str = Field(..., description="Response message")


# Email verification schemas
class EmailVerificationRequest(BaseModel):
    """Email verification request."""

    token: str = Field(..., description="Email verification token")


class EmailVerificationResponse(BaseModel):
    """Email verification response."""

    success: bool = Field(default=True, description="Whether verification was successful")
    email_verified: bool = Field(default=True, description="Email verification status")


# Logout schemas
class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool = Field(default=True, description="Whether logout was successful")
    message: str = Field(default="Successfully logged out", description="Response message")


# Generic API response
class APIResponse(BaseModel):
    """Generic API response wrapper."""

    success: bool = Field(default=True, description="Whether request was successful")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
