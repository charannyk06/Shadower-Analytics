"""Tests for security configuration and utilities."""

import pytest
from datetime import datetime, timedelta
import secrets
from unittest.mock import Mock, AsyncMock, patch

# Import security modules
from src.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
)
from src.core.permissions import (
    Permissions,
    Roles,
    has_permission,
    PermissionChecker,
    get_permissions_for_role,
)
from src.core.encryption import DataEncryption, get_encryptor
from src.core.validation import SecureInputValidator
from src.core.rate_limiting import RateLimiter


class TestJWTSecurity:
    """Test JWT token security enhancements."""

    def test_create_access_token_includes_security_claims(self):
        """Test that access tokens include all required security claims."""
        token = create_access_token(
            data={"sub": "user123", "workspace_id": "ws_abc123"}
        )

        assert token is not None
        assert isinstance(token, str)
        # Token should be a valid JWT (3 parts separated by dots)
        assert len(token.split(".")) == 3

    def test_token_includes_jti(self):
        """Test that tokens include a unique JTI claim."""
        token1 = create_access_token(data={"sub": "user123"})
        token2 = create_access_token(data={"sub": "user123"})

        # Tokens should be different even with same data (due to unique JTI)
        assert token1 != token2

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Hash should be different from original
        assert hashed != password

        # Verification should work
        assert verify_password(password, hashed) is True

        # Wrong password should fail
        assert verify_password("WrongPassword", hashed) is False


class TestRBAC:
    """Test Role-Based Access Control."""

    def test_role_permissions(self):
        """Test that roles have expected permissions."""
        # Super admin should have all permissions
        super_admin_perms = get_permissions_for_role(Roles.SUPER_ADMIN)
        assert Permissions.MANAGE_USERS in super_admin_perms
        assert Permissions.DELETE_DATA in super_admin_perms

        # Viewer should have limited permissions
        viewer_perms = get_permissions_for_role(Roles.VIEWER)
        assert Permissions.VIEW_ANALYTICS in viewer_perms
        assert Permissions.DELETE_DATA not in viewer_perms
        assert Permissions.MANAGE_USERS not in viewer_perms

    def test_has_permission(self):
        """Test permission checking."""
        # Admin should have analytics permissions
        assert has_permission(Roles.ADMIN, Permissions.VIEW_ANALYTICS) is True

        # Viewer should not have delete permission
        assert has_permission(Roles.VIEWER, Permissions.DELETE_DATA) is False

    def test_custom_permissions(self):
        """Test custom permissions override."""
        # Viewer normally can't export data
        assert has_permission(Roles.VIEWER, Permissions.EXPORT_DATA) is False

        # But with custom permission, they can
        custom_perms = {Permissions.EXPORT_DATA}
        assert (
            has_permission(Roles.VIEWER, Permissions.EXPORT_DATA, custom_perms)
            is True
        )

    def test_permission_checker_has_any(self):
        """Test checking for any of multiple permissions."""
        checker = PermissionChecker()

        # Admin should have at least one of these
        assert (
            checker.has_any_permission(
                Roles.ADMIN,
                [Permissions.MANAGE_USERS, Permissions.DELETE_DATA],
            )
            is True
        )

        # Viewer should not have any of these
        assert (
            checker.has_any_permission(
                Roles.VIEWER,
                [Permissions.MANAGE_USERS, Permissions.DELETE_DATA],
            )
            is False
        )

    def test_permission_checker_has_all(self):
        """Test checking for all permissions."""
        checker = PermissionChecker()

        # Owner should have all these permissions
        assert (
            checker.has_all_permissions(
                Roles.OWNER,
                [Permissions.VIEW_ANALYTICS, Permissions.EXPORT_DATA],
            )
            is True
        )

        # Viewer should not have all these
        assert (
            checker.has_all_permissions(
                Roles.VIEWER,
                [Permissions.VIEW_ANALYTICS, Permissions.EXPORT_DATA],
            )
            is False
        )


class TestEncryption:
    """Test data encryption utilities."""

    def test_encrypt_decrypt_field(self):
        """Test field encryption and decryption."""
        encryptor = DataEncryption()

        plaintext = "sensitive data"
        encrypted = encryptor.encrypt_field(plaintext, "test_field")

        # Encrypted should be different from plaintext
        assert encrypted != plaintext

        # Decryption should recover original
        decrypted = encryptor.decrypt_field(encrypted, "test_field")
        assert decrypted == plaintext

    def test_encryption_with_different_contexts(self):
        """Test that different contexts produce different encrypted values."""
        encryptor = DataEncryption()

        plaintext = "same data"
        encrypted1 = encryptor.encrypt_field(plaintext, "context1")
        encrypted2 = encryptor.encrypt_field(plaintext, "context2")

        # Same plaintext with different contexts should produce different ciphertext
        assert encrypted1 != encrypted2

    def test_empty_string_encryption(self):
        """Test handling of empty strings."""
        encryptor = DataEncryption()

        # Empty string should return empty string
        assert encryptor.encrypt_field("", "test") == ""
        assert encryptor.decrypt_field("", "test") == ""


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_prevention(self):
        """Test SQL injection detection."""
        validator = SecureInputValidator()

        # Should raise on SQL keywords
        with pytest.raises(ValueError, match="SQL keyword"):
            validator.sanitize_sql_input("'; DROP TABLE users; --")

        with pytest.raises(ValueError, match="SQL keyword"):
            validator.sanitize_sql_input("admin' OR '1'='1")

    def test_safe_sql_input(self):
        """Test that safe input passes validation."""
        validator = SecureInputValidator()

        safe_input = "normal search query"
        sanitized = validator.sanitize_sql_input(safe_input)

        assert sanitized == safe_input

    def test_html_sanitization(self):
        """Test HTML sanitization."""
        validator = SecureInputValidator()

        malicious_html = '<script>alert("XSS")</script>Hello'
        sanitized = validator.sanitize_html_input(malicious_html)

        # Script tags should be removed/escaped
        assert "<script>" not in sanitized
        assert "Hello" in sanitized

    def test_filename_sanitization(self):
        """Test filename sanitization."""
        validator = SecureInputValidator()

        # Dangerous filename with path traversal
        dangerous = "../../etc/passwd"
        sanitized = validator.sanitize_filename(dangerous)

        # Should not contain path separators
        assert "/" not in sanitized
        assert "\\" not in sanitized

    def test_file_upload_validation(self):
        """Test file upload validation."""
        validator = SecureInputValidator()

        # Valid file should pass
        assert (
            validator.validate_file_upload(
                filename="data.csv",
                content_type="text/csv",
                file_size=1024,
            )
            is True
        )

        # Too large file should fail
        with pytest.raises(ValueError, match="size exceeds"):
            validator.validate_file_upload(
                filename="large.csv",
                content_type="text/csv",
                file_size=100 * 1024 * 1024,  # 100MB
            )

        # Dangerous extension should fail
        with pytest.raises(ValueError, match="extension.*not allowed"):
            validator.validate_file_upload(
                filename="malware.exe",
                content_type="application/x-executable",
                file_size=1024,
            )

    def test_email_validation(self):
        """Test email address validation."""
        validator = SecureInputValidator()

        # Valid emails
        assert validator.validate_email("user@example.com") is True
        assert validator.validate_email("test.user+tag@domain.co.uk") is True

        # Invalid emails
        with pytest.raises(ValueError):
            validator.validate_email("not-an-email")

        with pytest.raises(ValueError):
            validator.validate_email("missing@domain")

    def test_url_validation(self):
        """Test URL validation."""
        validator = SecureInputValidator()

        # Valid URLs
        assert validator.validate_url("https://example.com") is True
        assert validator.validate_url("http://api.example.com/path") is True

        # Invalid/dangerous URLs
        with pytest.raises(ValueError):
            validator.validate_url("javascript:alert(1)")

        with pytest.raises(ValueError):
            validator.validate_url("not a url")

    def test_workspace_id_validation(self):
        """Test workspace ID format validation."""
        validator = SecureInputValidator()

        # Valid workspace ID
        assert validator.validate_workspace_id("ws_1234567890") is True

        # Invalid format
        with pytest.raises(ValueError):
            validator.validate_workspace_id("invalid_id")

        with pytest.raises(ValueError):
            validator.validate_workspace_id("ws_short")


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()

        assert limiter.limits is not None
        assert "default" in limiter.limits
        assert "api_key" in limiter.limits

    @pytest.mark.asyncio
    async def test_rate_limit_config(self):
        """Test rate limit configurations."""
        limiter = RateLimiter()

        # Check that limits are tuples of (requests, window)
        for limit_type, config in limiter.limits.items():
            assert isinstance(config, tuple)
            assert len(config) == 2
            assert isinstance(config[0], int)  # requests
            assert isinstance(config[1], int)  # window


class TestAuditLogging:
    """Test audit logging system."""

    @pytest.mark.asyncio
    async def test_sensitive_field_sanitization(self):
        """Test that sensitive fields are redacted from audit logs."""
        from src.core.audit import AuditLogger

        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        details = {
            "username": "testuser",
            "password": "secret123",
            "api_key": "key_abc123",
            "email": "test@example.com",
        }

        sanitized = logger._sanitize_details(details)

        # Sensitive fields should be redacted
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"

        # Non-sensitive fields should remain
        assert sanitized["username"] == "testuser"
        assert sanitized["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_nested_sanitization(self):
        """Test sanitization of nested dictionaries."""
        from src.core.audit import AuditLogger

        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        details = {
            "user": {
                "name": "John",
                "password": "secret",
            },
            "config": {
                "api_key": "key123",
                "timeout": 30,
            },
        }

        sanitized = logger._sanitize_details(details)

        assert sanitized["user"]["password"] == "[REDACTED]"
        assert sanitized["config"]["api_key"] == "[REDACTED]"
        assert sanitized["user"]["name"] == "John"
        assert sanitized["config"]["timeout"] == 30


class TestGDPRCompliance:
    """Test GDPR compliance utilities."""

    @pytest.mark.asyncio
    async def test_export_user_data_structure(self):
        """Test that user data export has required structure."""
        from src.core.gdpr import GDPRCompliance

        mock_db = AsyncMock()
        gdpr = GDPRCompliance(mock_db)

        # Mock the helper methods
        gdpr._get_user_profile = AsyncMock(return_value={"user_id": "test123"})
        gdpr._get_user_activities = AsyncMock(return_value=[])
        gdpr._get_user_analytics = AsyncMock(return_value={})
        gdpr._get_user_preferences = AsyncMock(return_value={})
        gdpr._get_user_audit_logs = AsyncMock(return_value=[])
        gdpr._log_gdpr_action = AsyncMock()

        export = await gdpr.export_user_data("test123")

        # Check required fields
        assert "export_metadata" in export
        assert "user_profile" in export
        assert "activity_logs" in export

        # Check metadata
        assert export["export_metadata"]["user_id"] == "test123"
        assert "export_timestamp" in export["export_metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
