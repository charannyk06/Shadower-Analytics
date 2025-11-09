"""Shared constants and validation patterns."""

# Timeframe validation
VALID_TIMEFRAMES = ["7d", "30d", "90d", "1y", "24h", "1w", "1m", "3m", "6m", "all"]
TIMEFRAME_REGEX = r"^(7d|30d|90d|1y|24h|1w|1m|3m|6m|all)$"

# Cache key validation
CACHE_KEY_MAX_LENGTH = 256
CACHE_KEY_PATTERN = r"^[a-zA-Z0-9:_\-\.]+$"

# Rate limiting
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_RATE_LIMIT_PER_HOUR = 1000

# Cache TTL defaults (in seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 1800  # 30 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_VERY_LONG = 86400  # 24 hours

# Timeframe to TTL mapping
TIMEFRAME_TTL_MAP = {
    "24h": CACHE_TTL_SHORT,  # 5 minutes
    "7d": CACHE_TTL_MEDIUM,  # 30 minutes
    "1w": CACHE_TTL_MEDIUM,  # 30 minutes
    "30d": CACHE_TTL_LONG,  # 1 hour
    "1m": CACHE_TTL_LONG,  # 1 hour
    "90d": CACHE_TTL_LONG,  # 1 hour
    "3m": CACHE_TTL_LONG,  # 1 hour
    "6m": CACHE_TTL_VERY_LONG,  # 24 hours
    "1y": CACHE_TTL_VERY_LONG,  # 24 hours
    "all": CACHE_TTL_VERY_LONG,  # 24 hours
}
