"""
Redis-based rate limiter for API endpoints.

Uses sliding window algorithm with Redis INCR + EXPIRE.
Supports per-IP and per-user rate limiting with configurable tiers.
"""

import time
from typing import Optional, Tuple

from fastapi import Request, HTTPException, status

from cache.manager import CacheManager
from config.settings import settings
from utils.logger import logger


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.

    Key format: "afdas:ratelimit:{tier}:{identifier}"
    Uses Redis INCR with TTL for atomic counting.
    """

    PREFIX = "afdas:ratelimit:"

    @classmethod
    async def check_rate_limit(
        cls,
        identifier: str,
        tier: str = "general",
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """
        Check if a request is within rate limits.

        Args:
            identifier: IP address or user ID
            tier: Rate limit tier (general, auth, chat)
            max_requests: Override max requests for this check
            window_seconds: Override window size for this check

        Returns:
            (allowed: bool, remaining: int, reset_in: int)
        """
        # Determine limits based on tier
        if max_requests is None or window_seconds is None:
            if tier == "auth":
                max_requests = max_requests or settings.RATE_LIMIT_AUTH_REQUESTS
                window_seconds = window_seconds or settings.RATE_LIMIT_AUTH_WINDOW
            elif tier == "chat":
                max_requests = max_requests or settings.RATE_LIMIT_CHAT_REQUESTS
                window_seconds = window_seconds or settings.RATE_LIMIT_CHAT_WINDOW
            else:
                max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
                window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS

        key = f"{cls.PREFIX}{tier}:{identifier}"

        try:
            client = CacheManager.get_client()

            # Atomic increment
            current = await client.incr(key)

            # Set expiry on first request in window
            if current == 1:
                await client.expire(key, window_seconds)

            # Get TTL for reset time
            ttl = await client.ttl(key)
            if ttl < 0:
                ttl = window_seconds

            remaining = max(0, max_requests - current)
            allowed = current <= max_requests

            return allowed, remaining, ttl

        except Exception as e:
            # If Redis is down, allow the request (fail-open for availability)
            logger.warning(f"Rate limiter error (allowing request): {e}")
            return True, max_requests, window_seconds

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        """Extract client IP from request (handles proxies)."""
        # Check X-Forwarded-For header (behind reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in the chain is the client
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Direct connection
        if request.client:
            return request.client.host

        return "unknown"


class BruteForceProtection:
    """
    Protects login endpoint from brute force attacks.
    Tracks failed attempts per IP and locks out after threshold.
    """

    PREFIX = "afdas:bruteforce:"

    @classmethod
    async def record_failed_attempt(cls, identifier: str) -> Tuple[int, bool]:
        """
        Record a failed login attempt.

        Returns:
            (attempt_count, is_locked_out)
        """
        key = f"{cls.PREFIX}{identifier}"

        try:
            client = CacheManager.get_client()

            current = await client.incr(key)

            # Set expiry on first failure
            if current == 1:
                await client.expire(key, settings.LOGIN_LOCKOUT_SECONDS)

            is_locked = current >= settings.LOGIN_MAX_ATTEMPTS
            return current, is_locked

        except Exception as e:
            logger.warning(f"Brute force protection error: {e}")
            return 0, False

    @classmethod
    async def is_locked_out(cls, identifier: str) -> Tuple[bool, int]:
        """
        Check if an IP/user is currently locked out.

        Returns:
            (is_locked: bool, remaining_seconds: int)
        """
        key = f"{cls.PREFIX}{identifier}"

        try:
            client = CacheManager.get_client()

            attempts = await client.get(key)
            if attempts is None:
                return False, 0

            count = int(attempts)
            if count >= settings.LOGIN_MAX_ATTEMPTS:
                ttl = await client.ttl(key)
                return True, max(0, ttl)

            return False, 0

        except Exception as e:
            logger.warning(f"Brute force check error: {e}")
            return False, 0

    @classmethod
    async def clear_attempts(cls, identifier: str) -> None:
        """Clear failed attempts after successful login."""
        key = f"{cls.PREFIX}{identifier}"
        try:
            client = CacheManager.get_client()
            await client.delete(key)
        except Exception:
            pass
