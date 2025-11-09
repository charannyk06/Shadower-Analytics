"""Token management for blacklisting and caching."""

from typing import Optional, Dict
from datetime import datetime, timezone
import json
import logging
from .redis import get_redis_client
from .config import settings

logger = logging.getLogger(__name__)

# Cache TTL in seconds (30 seconds for decoded tokens)
TOKEN_CACHE_TTL = 30

# Blacklist key prefix
BLACKLIST_PREFIX = "token:blacklist:"


async def blacklist_token(token: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Add a token to the blacklist.

    Args:
        token: The JWT token to blacklist
        expires_at: When the token expires (optional, for TTL optimization)

    Returns:
        True if successfully blacklisted, False otherwise
    """
    try:
        redis = await get_redis_client()
        if not redis:
            logger.error("Redis client not available for token blacklist")
            return False

        key = f"{BLACKLIST_PREFIX}{token}"

        # Calculate TTL - only keep blacklisted tokens until they expire
        if expires_at:
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl <= 0:
                # Token already expired, no need to blacklist
                return True
        else:
            # Default to token expiration time from settings
            ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        await redis.setex(key, ttl, "1")
        logger.info(f"Token blacklisted with TTL: {ttl}s")
        return True

    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        return False


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token: The JWT token to check

    Returns:
        True if blacklisted, False otherwise
    """
    try:
        redis = await get_redis_client()
        if not redis:
            logger.warning("Redis client not available, cannot check blacklist")
            return False

        key = f"{BLACKLIST_PREFIX}{token}"
        result = await redis.exists(key)
        return bool(result)

    except Exception as e:
        logger.error(f"Failed to check token blacklist: {e}")
        # Fail open - if Redis is down, allow the token
        # The token will still be validated for expiration
        return False


async def cache_decoded_token(token: str, payload: Dict) -> bool:
    """
    Cache a decoded token payload.

    Args:
        token: The JWT token (used as cache key)
        payload: The decoded token payload

    Returns:
        True if successfully cached, False otherwise
    """
    try:
        redis = await get_redis_client()
        if not redis:
            logger.warning("Redis client not available for token caching")
            return False

        cache_key = f"token:cache:{token}"

        # Store the payload as JSON
        await redis.setex(
            cache_key,
            TOKEN_CACHE_TTL,
            json.dumps(payload),
        )
        return True

    except Exception as e:
        logger.error(f"Failed to cache token: {e}")
        return False


async def get_cached_token(token: str) -> Optional[Dict]:
    """
    Retrieve a cached token payload.

    Args:
        token: The JWT token to retrieve

    Returns:
        The cached payload if found, None otherwise
    """
    try:
        redis = await get_redis_client()
        if not redis:
            return None

        cache_key = f"token:cache:{token}"
        cached = await redis.get(cache_key)

        if cached:
            return json.loads(cached)

        return None

    except Exception as e:
        logger.error(f"Failed to retrieve cached token: {e}")
        return None


async def invalidate_token_cache(token: str) -> bool:
    """
    Invalidate a cached token.

    Args:
        token: The JWT token to invalidate

    Returns:
        True if successfully invalidated, False otherwise
    """
    try:
        redis = await get_redis_client()
        if not redis:
            return False

        cache_key = f"token:cache:{token}"
        await redis.delete(cache_key)
        return True

    except Exception as e:
        logger.error(f"Failed to invalidate token cache: {e}")
        return False
