"""Rate limiting middleware."""
import time
from collections import defaultdict

from fastapi import HTTPException, status

from app.core.config import settings


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self) -> None:
        """Initialize rate limiter."""
        # Structure: {user_id: [(timestamp, count)]}
        self.user_requests: dict[str, list[tuple[float, int]]] = defaultdict(list)
        # Structure: {ip: [(timestamp, count)]}
        self.ip_requests: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def _clean_old_entries(
        self, entries: list[tuple[float, int]], window_seconds: int
    ) -> list[tuple[float, int]]:
        """Remove entries older than window."""
        current_time = time.time()
        cutoff = current_time - window_seconds
        return [(ts, count) for ts, count in entries if ts > cutoff]

    def _count_requests(
        self, entries: list[tuple[float, int]], window_seconds: int
    ) -> int:
        """Count requests in window."""
        current_time = time.time()
        cutoff = current_time - window_seconds
        return sum(count for ts, count in entries if ts > cutoff)

    def check_rate_limit(
        self, user_id: str | None, client_ip: str
    ) -> None:
        """
        Check if request is within rate limits.

        Args:
            user_id: User identifier
            client_ip: Client IP address

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not settings.rate_limit.rate_limit_enabled:
            return

        current_time = time.time()

        # Check per-user limits
        if user_id:
            self.user_requests[user_id] = self._clean_old_entries(
                self.user_requests[user_id], 3600
            )

            # Check per-minute limit
            minute_count = self._count_requests(self.user_requests[user_id], 60)
            if minute_count >= settings.rate_limit.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: too many requests per minute",
                    headers={"Retry-After": "60"},
                )

            # Check per-hour limit
            hour_count = self._count_requests(self.user_requests[user_id], 3600)
            if hour_count >= settings.rate_limit.requests_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: too many requests per hour",
                    headers={"Retry-After": "3600"},
                )

            # Record request
            self.user_requests[user_id].append((current_time, 1))

        # Check per-IP limits
        self.ip_requests[client_ip] = self._clean_old_entries(
            self.ip_requests[client_ip], 60
        )

        ip_minute_count = self._count_requests(self.ip_requests[client_ip], 60)
        if ip_minute_count >= settings.rate_limit.requests_per_ip_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: too many requests from IP",
                headers={"Retry-After": "60"},
            )

        # Record IP request
        self.ip_requests[client_ip].append((current_time, 1))


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
