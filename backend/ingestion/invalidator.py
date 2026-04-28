"""Redis cache invalidator.

Deletes all Redis cache keys associated with a given source_id so that
stale query-cache entries are flushed after re-ingestion.

Key naming convention (must match query pipeline cache layer):
  cache:<query_hash>:<source_id>:<anything>
"""

import logging

import redis.asyncio as aioredis

from backend.ingestion.settings import settings

logger = logging.getLogger(__name__)


class CacheInvalidator:
    def __init__(self) -> None:
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def invalidate_source(self, source_id: str) -> int:
        """Delete all Redis keys matching `cache:*:<source_id>:*`.

        Returns the number of keys deleted.
        """
        pattern = f"cache:*:{source_id}:*"
        deleted = 0

        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)
            deleted += 1

        logger.info(
            "CacheInvalidator: deleted %d Redis keys for source_id='%s'",
            deleted,
            source_id,
        )
        return deleted

    async def close(self) -> None:
        await self.redis.aclose()
