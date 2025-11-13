"""WebSocket rate limiting."""

import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections."""

    # Rate limits per action per minute
    WS_RATE_LIMITS = {
        "subscribe": 10,  # 10 subscribe requests per minute
        "unsubscribe": 10,
        "start_stream": 5,  # 5 stream starts per minute
        "stop_stream": 10,
        "get_metrics": 30,  # 30 metrics requests per minute
        "request_metrics": 30,
        "join_room": 10,
        "leave_room": 10,
        "default": 60,  # 60 general messages per minute
    }

    def __init__(self):
        # Track action counts: {user_id: {action: [(timestamp, count)]}}
        self.action_counts: Dict[str, Dict[str, list]] = {}

    def check_rate_limit(self, user_id: str, action: str) -> bool:
        """
        Check if user has exceeded rate limit for action.

        Args:
            user_id: User identifier
            action: Action type

        Returns:
            True if within rate limit, False if exceeded
        """
        current_time = time.time()
        limit = self.WS_RATE_LIMITS.get(action, self.WS_RATE_LIMITS["default"])

        # Initialize user tracking if needed
        if user_id not in self.action_counts:
            self.action_counts[user_id] = {}

        if action not in self.action_counts[user_id]:
            self.action_counts[user_id][action] = []

        # Clean up old entries (older than 1 minute)
        self.action_counts[user_id][action] = [
            (ts, count)
            for ts, count in self.action_counts[user_id][action]
            if current_time - ts < 60
        ]

        # Count actions in last minute
        total_count = sum(
            count for _, count in self.action_counts[user_id][action]
        )

        if total_count >= limit:
            logger.warning(
                f"Rate limit exceeded for user {user_id}, action {action}: "
                f"{total_count}/{limit}"
            )
            return False

        # Add current action
        self.action_counts[user_id][action].append((current_time, 1))
        return True

    def get_remaining_quota(self, user_id: str, action: str) -> int:
        """
        Get remaining quota for user action.

        Args:
            user_id: User identifier
            action: Action type

        Returns:
            Number of remaining actions allowed
        """
        current_time = time.time()
        limit = self.WS_RATE_LIMITS.get(action, self.WS_RATE_LIMITS["default"])

        if user_id not in self.action_counts:
            return limit

        if action not in self.action_counts[user_id]:
            return limit

        # Clean up old entries
        self.action_counts[user_id][action] = [
            (ts, count)
            for ts, count in self.action_counts[user_id][action]
            if current_time - ts < 60
        ]

        # Count actions in last minute
        total_count = sum(
            count for _, count in self.action_counts[user_id][action]
        )

        return max(0, limit - total_count)

    def reset_user_limits(self, user_id: str):
        """Reset all rate limits for a user."""
        if user_id in self.action_counts:
            del self.action_counts[user_id]
            logger.info(f"Reset rate limits for user {user_id}")

    def cleanup_old_entries(self):
        """Clean up old rate limit entries (should be called periodically)."""
        current_time = time.time()
        users_to_remove = []

        for user_id in self.action_counts:
            for action in list(self.action_counts[user_id].keys()):
                # Remove entries older than 1 minute
                self.action_counts[user_id][action] = [
                    (ts, count)
                    for ts, count in self.action_counts[user_id][action]
                    if current_time - ts < 60
                ]

                # Remove empty action lists
                if not self.action_counts[user_id][action]:
                    del self.action_counts[user_id][action]

            # Mark user for removal if no actions
            if not self.action_counts[user_id]:
                users_to_remove.append(user_id)

        # Remove users with no actions
        for user_id in users_to_remove:
            del self.action_counts[user_id]

        if users_to_remove:
            logger.debug(
                f"Cleaned up rate limit entries for {len(users_to_remove)} users"
            )


# Global instance
rate_limiter = WebSocketRateLimiter()
