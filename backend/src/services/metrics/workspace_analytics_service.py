"""Comprehensive workspace analytics service with proper error handling, caching, and logging."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from ..cache import cached, CacheKeys
from .constants import (
    TIMEFRAME_24H,
    TIMEFRAME_7D,
    TIMEFRAME_30D,
    TIMEFRAME_90D,
    MAX_QUERY_LIMIT,
    DEFAULT_PAGE_SIZE,
)

logger = logging.getLogger(__name__)


