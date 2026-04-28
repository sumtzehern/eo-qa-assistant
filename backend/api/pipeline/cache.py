"""Semantic cache layer using Redis.

Stores query embeddings + answers keyed by query_id.
On lookup, scans existing cache keys and returns a hit if
cosine similarity >= threshold.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
            keys = await self._redis.keys("cache:query:*")
            for key in keys:
                entry = await self._redis.hgetall(key)
                if not entry:
                    continue
                stored_emb = json.loads(entry.get(b"embedding") or entry.get("embedding", "null"))
                if stored_emb is None:
                    continue
                sim = self._cosine_sim(query_embedding, stored_emb)
                if sim >= self._threshold:
                    answer = (entry.get(b"answer") or entry.get("answer", b"")).decode(
                        "utf-8"
                    ) if isinstance(entry.get(b"answer") or entry.get("answer"), bytes) else str(entry.get(b"answer") or entry.get("answer", ""))
                    citations = json.loads(
                        entry.get(b"citations") or entry.get("citations", "[]")
                    )
                    confidence = float(
                        entry.get(b"confidence") or entry.get("confidence", 0.0)
                    )
                    return CacheHit(
                        answer=answer,
                        citations=citations,
                        confidence=confidence,
                    )
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
        except Exception:
            logger.warning("Cache set failed", exc_info=True)
