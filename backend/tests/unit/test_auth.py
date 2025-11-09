"""Comprehensive authentication tests."""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
)
from src.core.config import settings
from src.core.token_manager import (
    blacklist_token,
    is_token_blacklisted,
    cache_decoded_token,
    get_cached_token,
)


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "secure_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "secure_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_token_basic(self):
        """Test basic token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 0

        # Decode without verification to check structure
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded

    def test_create_token_with_custom_expiration(self):
        """Test token creation with custom expiration."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires_delta)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Check expiration is approximately 60 minutes from now
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta
        time_diff = abs((exp_time - expected_time).total_seconds())

        assert time_diff < 2  # Allow 2 seconds difference

    def test_create_token_with_roles(self):
        """Test token creation with roles."""
        data = {
            "sub": "user123",
            "email": "admin@example.com",
            "roles": ["admin", "manager"],
        }
        token = create_access_token(data)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert decoded["roles"] == ["admin", "manager"]

    def test_create_token_with_workspaces(self):
        """Test token creation with workspace information."""
        data = {
            "sub": "user123",
            "workspaces": {
                "ws-1": {"permissions": ["read", "write"]},
                "ws-2": {"permissions": ["read"]},
            },
        }
        token = create_access_token(data)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert "ws-1" in decoded["workspaces"]
        assert decoded["workspaces"]["ws-1"]["permissions"] == ["read", "write"]


class TestTokenVerification:
    """Test JWT token verification."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        """Test verification of valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        # Mock Redis calls
        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                with patch("src.core.security.cache_decoded_token", return_value=True):
                    from src.core.security import verify_token

                    payload = await verify_token(token)

                    assert payload["sub"] == "user123"
                    assert payload["email"] == "test@example.com"
                    assert "exp" in payload

    @pytest.mark.asyncio
    async def test_verify_expired_token(self):
        """Test verification of expired token."""
        data = {"sub": "user123"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires_delta)

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                from src.core.security import verify_token

                with pytest.raises(ValueError, match="Could not validate credentials"):
                    await verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_blacklisted_token(self):
        """Test verification of blacklisted token."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        with patch("src.core.security.is_token_blacklisted", return_value=True):
            from src.core.security import verify_token

            with pytest.raises(ValueError, match="Token has been revoked"):
                await verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_without_expiration(self):
        """Test verification of token without expiration claim."""
        # Create a token manually without exp claim
        data = {"sub": "user123"}
        token = jwt.encode(
            data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                from src.core.security import verify_token

                with pytest.raises(ValueError, match="Token missing expiration claim"):
                    await verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_with_invalid_signature(self):
        """Test verification of token with invalid signature."""
        data = {"sub": "user123"}
        # Create token with different secret
        token = jwt.encode(
            data,
            "wrong-secret-key",
            algorithm=settings.JWT_ALGORITHM,
        )

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=None):
                from src.core.security import verify_token

                with pytest.raises(ValueError, match="Could not validate credentials"):
                    await verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_cached_token(self):
        """Test that cached tokens are returned without decoding."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        cached_payload = {"sub": "user123", "email": "test@example.com", "exp": 12345}

        with patch("src.core.security.is_token_blacklisted", return_value=False):
            with patch("src.core.security.get_cached_token", return_value=cached_payload):
                from src.core.security import verify_token

                payload = await verify_token(token)

                # Should return cached payload
                assert payload == cached_payload


class TestTokenBlacklist:
    """Test token blacklist functionality."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self):
        """Test adding token to blacklist."""
        token = "test_token_123"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await blacklist_token(token, expires_at)

            assert result is True
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_blacklist_expired_token(self):
        """Test blacklisting already expired token."""
        token = "test_token_123"
        # Token already expired
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        result = await blacklist_token(token, expires_at)

        # Should return True without actually blacklisting
        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self):
        """Test checking if token is blacklisted (true)."""
        token = "test_token_123"

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await is_token_blacklisted(token)

            assert result is True
            mock_redis.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self):
        """Test checking if token is blacklisted (false)."""
        token = "test_token_123"

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await is_token_blacklisted(token)

            assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_without_redis(self):
        """Test blacklist operations when Redis is unavailable."""
        token = "test_token_123"

        with patch("src.core.token_manager.get_redis_client", return_value=None):
            # Should handle gracefully
            result = await blacklist_token(token)
            assert result is False

            # Should fail open (allow token)
            is_blacklisted = await is_token_blacklisted(token)
            assert is_blacklisted is False


class TestTokenCache:
    """Test token caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_token(self):
        """Test caching decoded token."""
        token = "test_token_123"
        payload = {"sub": "user123", "email": "test@example.com"}

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await cache_decoded_token(token, payload)

            assert result is True
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_token_exists(self):
        """Test retrieving cached token that exists."""
        token = "test_token_123"
        cached_payload = '{"sub": "user123", "email": "test@example.com"}'

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_payload)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await get_cached_token(token)

            assert result == {"sub": "user123", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_get_cached_token_not_exists(self):
        """Test retrieving cached token that doesn't exist."""
        token = "test_token_123"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("src.core.token_manager.get_redis_client", return_value=mock_redis):
            result = await get_cached_token(token)

            assert result is None

    @pytest.mark.asyncio
    async def test_cache_without_redis(self):
        """Test cache operations when Redis is unavailable."""
        token = "test_token_123"
        payload = {"sub": "user123"}

        with patch("src.core.token_manager.get_redis_client", return_value=None):
            # Should handle gracefully
            result = await cache_decoded_token(token, payload)
            assert result is False

            cached = await get_cached_token(token)
            assert cached is None


class TestConfigValidation:
    """Test configuration validation."""

    def test_weak_jwt_secret_development(self):
        """Test that weak secrets are allowed in development."""
        from src.core.config import Settings

        # Should not raise error in development
        settings = Settings(
            APP_ENV="development",
            JWT_SECRET_KEY="your-secret-key-change-in-production",
        )
        assert settings.JWT_SECRET_KEY == "your-secret-key-change-in-production"

    def test_weak_jwt_secret_production(self):
        """Test that weak secrets are rejected in production."""
        from src.core.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be changed"):
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="your-secret-key-change-in-production",
            )

    def test_short_jwt_secret_production(self):
        """Test that short secrets are rejected in production."""
        from src.core.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="at least 32 characters"):
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="short",
            )

    def test_strong_jwt_secret_production(self):
        """Test that strong secrets are accepted in production."""
        from src.core.config import Settings

        strong_secret = "a" * 32  # 32 character secret
        settings = Settings(
            APP_ENV="production",
            JWT_SECRET_KEY=strong_secret,
        )
        assert settings.JWT_SECRET_KEY == strong_secret
