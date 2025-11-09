"""Security utilities for authentication and authorization."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings
from .token_manager import (
    is_token_blacklisted,
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
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


async def verify_token(token: str) -> Dict:
    """
    Verify and decode JWT token with blacklist and cache support.

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
        return cached_payload

    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Explicitly check for expiration claim
        exp = payload.get("exp")
        if exp is None:
            raise ValueError("Token missing expiration claim")

        # Cache the decoded token for future requests
        await cache_decoded_token(token, payload)

        return payload
    except JWTError as e:
        raise ValueError(f"Could not validate credentials: {str(e)}")
