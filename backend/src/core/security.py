"""Security utilities for authentication and authorization."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings
from .token_manager import (
    is_token_blacklisted,
    is_jti_blacklisted,
    cache_decoded_token,
    get_cached_token,
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """
    Create JWT access token with enhanced security claims.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time
        token_type: Type of token (access or refresh)

    Returns:
        Encoded JWT token with security claims
    """
    import secrets

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add enhanced security claims
    to_encode.update({
        "exp": expire,  # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
        "jti": secrets.token_urlsafe(16),  # JWT ID for tracking/revocation
        "type": token_type,  # Token type
        "iss": "analytics.shadower.ai",  # Issuer
        "aud": "shadower-analytics",  # Audience
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


async def verify_token(token: str) -> Dict:
    """
    Verify and decode JWT token with enhanced security validation.

    Args:
        token: The JWT token to verify

    Returns:
        The decoded token payload

    Raises:
        ValueError: If token is invalid, expired, or blacklisted
    """
    # Check blacklist first
    if await is_token_blacklisted(token):
        raise ValueError("Token has been revoked")

    # Check cache for previously decoded token
    cached_payload = await get_cached_token(token)
    if cached_payload:
        # Even if cached, check if JTI was blacklisted
        jti = cached_payload.get("jti")
        if jti and await is_jti_blacklisted(jti):
            raise ValueError("Token has been revoked")
        return cached_payload

    try:
        # Decode and verify the token with audience and issuer validation
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience="shadower-analytics",
            issuer="analytics.shadower.ai",
        )

        # Explicitly check for required claims
        required_claims = ["exp", "jti", "type"]
        for claim in required_claims:
            if claim not in payload:
                raise ValueError(f"Token missing required claim: {claim}")

        # Check if JTI is blacklisted
        if await is_jti_blacklisted(payload["jti"]):
            raise ValueError("Token has been revoked")

        # Cache the decoded token for future requests
        await cache_decoded_token(token, payload)

        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidAudienceError:
        raise ValueError("Invalid token audience")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid token issuer")
    except JWTError as e:
        raise ValueError(f"Could not validate credentials: {str(e)}")
