"""
Constants for Trend Analysis Service

All configuration values and magic numbers extracted for maintainability
"""

from typing import Dict

# Data Requirements
MIN_DATA_POINTS_FOR_ANALYSIS = 14
MIN_DATA_POINTS_FOR_DECOMPOSITION = 14
MIN_DATA_POINTS_FOR_FORECAST = 14
MIN_DATA_POINTS_FOR_CYCLES = 20

# Statistical Thresholds
ANOMALY_THRESHOLD_STD_DEVS = 2.0
SEASONALITY_ACF_THRESHOLD = 0.3
STRONG_TREND_THRESHOLD = 0.8
MODERATE_TREND_THRESHOLD = 0.5
VOLATILITY_THRESHOLD = 50.0
STABLE_TREND_THRESHOLD = 0.1

# Forecasting Parameters
SHORT_TERM_FORECAST_DAYS = 7
LONG_TERM_FORECAST_MONTHS = 3
FORECAST_CONFIDENCE_LEVEL = 0.95
PROPHET_CHANGEPOINT_PRIOR_SCALE = 0.05

# Moving Average Windows
MOVING_AVERAGE_WINDOW_SIZE = 7
MIN_MOVING_AVERAGE_WINDOW = 2

# Cache Configuration (in hours)
CACHE_DURATION_7D = 1
CACHE_DURATION_30D = 6
CACHE_DURATION_90D = 24
CACHE_DURATION_1Y = 48

CACHE_DURATIONS: Dict[str, int] = {
    '7d': CACHE_DURATION_7D,
    '30d': CACHE_DURATION_30D,
    '90d': CACHE_DURATION_90D,
    '1y': CACHE_DURATION_1Y
}

# Timeframe Mappings (in days)
TIMEFRAME_DAYS: Dict[str, int] = {
    '7d': 7,
    '30d': 30,
    '90d': 90,
    '1y': 365
}

DEFAULT_TIMEFRAME_DAYS = 30
MAX_TIMEFRAME_DAYS = 365

# ACF Parameters
MAX_ACF_LAGS = 40
MIN_ACF_LAGS = 14

# Cycle Detection
CYCLE_SIGNIFICANCE_THRESHOLD = 2.0  # standard deviations

# Seasonality Period Thresholds
DAILY_PERIOD_MAX = 1
WEEKLY_PERIOD_MAX = 7
MONTHLY_PERIOD_MAX = 31
QUARTERLY_PERIOD_MAX = 92

# Growth Projection
GROWTH_PROJECTION_DAYS = 30

# Comparison Percentages
HIGH_IMPACT_THRESHOLD = 20.0
MEDIUM_IMPACT_THRESHOLD = 10.0

# Top Cycles to Return
MAX_CYCLES_TO_RETURN = 3

# Allowed Metrics (for validation)
ALLOWED_METRICS = {
    'executions',
    'users',
    'credits',
    'errors',
    'success_rate',
    'revenue'
}

# Allowed Timeframes (for validation)
ALLOWED_TIMEFRAMES = {'7d', '30d', '90d', '1y'}

# Error Messages
ERROR_INSUFFICIENT_DATA = "insufficient_data"
ERROR_INVALID_METRIC = "invalid_metric"
ERROR_INVALID_TIMEFRAME = "invalid_timeframe"
ERROR_UNAUTHORIZED = "unauthorized"

MSG_INSUFFICIENT_DATA = "Not enough data points for trend analysis (minimum {} required)"
MSG_INVALID_METRIC = "Invalid metric. Allowed metrics: {}"
MSG_INVALID_TIMEFRAME = "Invalid timeframe. Allowed timeframes: {}"
MSG_UNAUTHORIZED_ACCESS = "Unauthorized access to workspace"
