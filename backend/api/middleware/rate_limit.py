"""Redis sliding-window rate limiter."""

import time

from fastapi import HTTPException
from redis.asyncio import Redis

RATE_LIMITS: dict[str, int] = {
    "admin": 200,
    "internal": 200,
    "customer": 60,
    "public": 10,
}

_redis_client: Redis | None = None


def set_redis_client(client: Redis) -> None:
    global _redis_client
    _redis_client = client


async def check_rate_limit(caller_id: str, tier: str) -> None:
    """Sliding-window rate limiter backed by Redis sorted sets.

    Raises HTTP 429 with Retry-After header when the caller exceeds the
    per-minute request limit for their tier.
    """
    if _redis_client is None:
        # No Redis available — skip rate limiting (dev/test fallback)
        return

    key = f"rate:{tier}:{caller_id}"
    limit = RATE_LIMITS.get(tier, RATE_LIMITS["public"])
    window = 60  # seconds

    now = time.time()
    window_start = now - window

    pipe = _redis_client.pipeline()
    # Remove entries outside the current window
    pipe.zremrangebyscore(key, "-inf", window_start)
    # Count remaining entries
    pipe.zcard(key)
    # Add current request timestamp
    pipe.zadd(key, {str(now): now})
    # Expire key after window
    pipe.expire(key, window)
    results = await pipe.execute()

    current_count: int = results[1]
    if current_count >= limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window)},
        )
