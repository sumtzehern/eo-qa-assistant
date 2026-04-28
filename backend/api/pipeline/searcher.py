"""Hybrid search: dense ANN (Qdrant) + sparse BM25, fused with Reciprocal Rank Fusion.

The searcher is intentionally stateless — callers instantiate it per-request
or reuse a shared instance (Qdrant client is async-safe).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, ScoredPoint

logger = logging.getLogger(__name__)

_RRF_K = 60  # standard RRF constant


@dataclass
class SearchResult:
    chunk_id: str
    content: str
    title: str
    url: str
    section: str
    source_id: str
    score: float


def _rrf_fusion(
    dense_hits: list[tuple[str, dict]],
    sparse_hits: list[tuple[str, dict]],
    top_k: int,
) -> list[tuple[str, dict, float]]:
    """Reciprocal Rank Fusion over two ranked lists.

    Each list is a sequence of (chunk_id, payload) pairs ordered by
    descending score (rank 0 = best).

    Returns a list of (chunk_id, payload, rrf_score) sorted by rrf_score desc,
    truncated to top_k.
    """
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for rank, (chunk_id, payload) in enumerate(dense_hits):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
        payloads[chunk_id] = payload

    for rank, (chunk_id, payload) in enumerate(sparse_hits):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
        payloads[chunk_id] = payload

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [(cid, payloads[cid], sc) for cid, sc in ranked]


class HybridSearcher:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        collection_name: str = "chunks",
    ) -> None:
        self._qdrant = qdrant_client
        self._collection = collection_name

    async def search(
        self,
        query_embedding: list[float],
        query_text: str,
        source_filter: list[str] | None = None,
        top_k: int = 20,
    ) -> list[SearchResult]:
        """Hybrid search returning top_k fused results."""
        qdrant_filter = None
        if source_filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchAny(any=source_filter),
                    )
                ]
            )

        # ── Dense ANN via Qdrant ─────────────────────────────────────────────
        dense_hits: list[tuple[str, dict]] = []
        try:
            ann_limit = top_k * 2
            ann_results: list[ScoredPoint] = await self._qdrant.search(
                collection_name=self._collection,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=ann_limit,
                with_payload=True,
            )
            for hit in ann_results:
                payload = hit.payload or {}
                dense_hits.append((str(hit.id), payload))
        except Exception:
            logger.warning("Qdrant dense search failed", exc_info=True)

        # ── BM25 sparse ──────────────────────────────────────────────────────
        sparse_hits: list[tuple[str, dict]] = []
        try:
            from rank_bm25 import BM25Okapi  # soft import

            scroll_results, _ = await self._qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=qdrant_filter,
                limit=500,
                with_payload=True,
            )
            if scroll_results:
                corpus_ids = [str(p.id) for p in scroll_results]
                corpus_payloads = [p.payload or {} for p in scroll_results]
                corpus_texts = [cp.get("content", "") for cp in corpus_payloads]
                tokenized = [t.split() for t in corpus_texts]

                bm25 = BM25Okapi(tokenized)
                bm25_scores = bm25.get_scores(query_text.split())

                # Sort indices by score descending, keep top_k * 2
                indexed = sorted(
                    enumerate(bm25_scores), key=lambda x: x[1], reverse=True
                )[: top_k * 2]
                sparse_hits = [
                    (corpus_ids[i], corpus_payloads[i]) for i, _ in indexed
                ]
        except ImportError:
            logger.warning("rank_bm25 not installed; skipping BM25 leg")
        except Exception:
            logger.warning("BM25 search failed", exc_info=True)

        if not dense_hits and not sparse_hits:
            return []

        fused = _rrf_fusion(dense_hits, sparse_hits, top_k)

        return [
            SearchResult(
                chunk_id=chunk_id,
                content=payload.get("content", ""),
                title=payload.get("page_title") or payload.get("title", ""),
                url=payload.get("source_url") or payload.get("url", ""),
                section=payload.get("section_title") or payload.get("section", ""),
                source_id=payload.get("source_id", ""),
                score=rrf_score,
            )
            for chunk_id, payload, rrf_score in fused
        ]
