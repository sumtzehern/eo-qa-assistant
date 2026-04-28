"""Cohere rerank wrapper.

Uses the v2 async client (cohere >= 5.x). Falls back gracefully to
returning the first top_n candidates unchanged on any error.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.api.pipeline.searcher import SearchResult

logger = logging.getLogger(__name__)


class CohereReranker:
    def __init__(self, api_key: str, model: str = "rerank-english-v3.0") -> None:
        self._api_key = api_key
        self._model = model

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int = 5,
    ) -> list[SearchResult]:
        """Return candidates reordered by Cohere relevance scores.

        Falls back to the original order (sliced to top_n) on any error.
        """
        if not candidates:
            return []

        try:
            import cohere  # soft import — not available in all envs

            # cohere >= 5.x exposes AsyncClientV2
            client = cohere.AsyncClientV2(api_key=self._api_key)
            documents = [c.content for c in candidates]
            response = await client.rerank(
                model=self._model,
                query=query,
                documents=documents,
                top_n=top_n,
            )
            reranked = [candidates[r.index] for r in response.results]
            return reranked
        except ImportError:
            logger.warning("cohere package not installed; skipping rerank")
        except Exception:
            logger.warning("Cohere rerank failed; using original order", exc_info=True)

        return candidates[:top_n]
