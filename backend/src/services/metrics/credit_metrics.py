"""Credit usage tracking metrics."""

from datetime import date
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession


async def get_credit_usage(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> Dict:
    """Get credit usage statistics."""
    return {
        "total_credits_used": 0,
        "total_credits_purchased": 0,
        "avg_credits_per_user": 0.0,
        "avg_credits_per_execution": 0.0,
    }


async def get_credit_usage_by_user(
    db: AsyncSession,
    user_id: str,
    start_date: date,
    end_date: date,
) -> Dict:
    """Get credit usage for specific user."""
    return {
        "user_id": user_id,
        "total_credits_used": 0,
        "total_credits_remaining": 0,
        "usage_trend": [],
    }


async def get_top_credit_consumers(
    db: AsyncSession,
    limit: int = 10,
) -> List[Dict]:
    """Get top credit consuming users or workspaces."""
    return []
