"""Redis cache invalidator.

Deletes all Redis cache keys associated with a given source_id so that
stale query-cache entries are flushed after re-ingestion.

Key naming convention (must match query pipeline cache layer):
  cache:query:{query_id}               — main entry
  cache:src_idx:{source_id}:{query_id} — secondary index
"""

import logging

import redis.asyncio as aioredis

from backend.ingestion.settings import settings

logger = logging.getLogger(__name__)


class CacheInvalidator:
    def __init__(self) -> None:
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def invalidate_source(self, source_id: str) -> int:
        """Delete all cache entries whose source_ids include *source_id*.

        Scans the secondary index ``cache:src_idx:{source_id}:*`` to discover
        affected query_ids, then deletes both the main entry and the index key.

        Returns the number of main cache entries deleted.
        """
        pattern = f"cache:src_idx:{source_id}:*"
        deleted = 0

        async for idx_key in self.redis.scan_iter(pattern):
            # idx_key format: cache:src_idx:{source_id}:{query_id}
            query_id = await self.redis.get(idx_key)
            if query_id:
                await self.redis.delete(f"cache:query:{query_id}")
                deleted += 1
            await self.redis.delete(idx_key)

        logger.info(
            "CacheInvalidator: deleted %d cache entries for source_id='%s'",
            deleted,
            source_id,
        )
        return deleted

    async def close(self) -> None:
        await self.redis.aclose()
