"""Semantic cache layer using Redis.

Stores query embeddings + answers keyed by query_id.
On lookup, scans existing cache keys and returns a hit if
cosine similarity >= threshold.

Key schema:
  cache:query:{query_id}              — main entry (hash)
  cache:src_idx:{source_id}:{query_id} — secondary index for invalidation (string)
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_STATS_KEY = "cache:stats"


@dataclass
class CacheHit:
    answer: str
    citations: list
    confidence: float
    cached: bool = True


class CacheLayer:
    def __init__(self, redis_client, embedder, threshold: float = 0.92) -> None:
        self._redis = redis_client
        self._embedder = embedder
        self._threshold = threshold

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, query_embedding: list[float], query_id: str) -> CacheHit | None:
        """Return a CacheHit if a semantically similar query is cached."""
        try:
            async for key in self._redis.scan_iter("cache:query:*"):
                entry = await self._redis.hgetall(key)
                if not entry:
                    continue
                stored_emb = json.loads(entry.get("embedding", "null"))
                if stored_emb is None:
                    continue
                sim = self._cosine_sim(query_embedding, stored_emb)
                if sim >= self._threshold:
                    await self._redis.hincrby(_STATS_KEY, "hits", 1)
                    return CacheHit(
                        answer=entry.get("answer", ""),
                        citations=json.loads(entry.get("citations", "[]")),
                        confidence=float(entry.get("confidence", 0.0)),
                    )
            # No hit found
            await self._redis.hincrby(_STATS_KEY, "misses", 1)
        except Exception:
            logger.warning("Cache lookup failed", exc_info=True)
        return None

    async def set(
        self,
        query_id: str,
        source_ids: list[str],
        embedding: list[float],
        answer: str,
        citations: list,
        confidence: float,
    ) -> None:
        """Store a query result in Redis with a 24-hour TTL."""
        try:
            key = f"cache:query:{query_id}"
            mapping = {
                "embedding": json.dumps(embedding),
                "answer": answer,
                "citations": json.dumps(citations),
                "confidence": str(confidence),
                "source_ids": json.dumps(source_ids),
            }
            await self._redis.hset(key, mapping=mapping)
            await self._redis.expire(key, 86400)

            # Write secondary index keys for invalidation
            for source_id in source_ids:
                idx_key = f"cache:src_idx:{source_id}:{query_id}"
                await self._redis.set(idx_key, query_id, ex=86400)
        except Exception:
            logger.warning("Cache set failed", exc_info=True)

    async def get_stats(self) -> dict:
        """Return cache hit/miss counters and computed hit_rate."""
        try:
            raw = await self._redis.hgetall(_STATS_KEY)
            hits = int(raw.get("hits", 0))
            misses = int(raw.get("misses", 0))
            total = hits + misses
            hit_rate = hits / total if total > 0 else None
            return {"hits": hits, "misses": misses, "hit_rate": hit_rate}
        except Exception:
            logger.warning("Cache stats lookup failed", exc_info=True)
            return {"hits": 0, "misses": 0, "hit_rate": None}
