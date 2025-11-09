"""Constants for metrics services."""

# Timeframe constants (in days)
TIMEFRAME_24H = 1
TIMEFRAME_7D = 7
TIMEFRAME_30D = 30
TIMEFRAME_90D = 90
TIMEFRAME_1Y = 365

# Default timeframe
DEFAULT_TIMEFRAME_DAYS = 30

# Cache TTL values (in seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 900  # 15 minutes
CACHE_TTL_LONG = 1800  # 30 minutes

# Calculation constants
PERCENTAGE_MULTIPLIER = 100.0
ZERO_TO_POSITIVE_GROWTH = 100.0  # Growth percentage when going from 0 to any positive value

# Error thresholds
DEFAULT_ERROR_RATE_THRESHOLD = 5.0  # Percentage

# Database query limits
MAX_QUERY_LIMIT = 10000
DEFAULT_PAGE_SIZE = 100
