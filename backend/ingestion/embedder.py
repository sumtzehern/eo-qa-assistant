"""OpenAI embedding client with batching and retry logic."""

import logging

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100  # max texts per OpenAI embedding API call


class Embedder:
    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self.client = AsyncOpenAI()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _embed_batch_raw(self, texts: list[str]) -> list[list[float]]:
        """Single API call for up to _BATCH_SIZE texts."""
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        # Response data is ordered the same as input
        return [item.embedding for item in response.data]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, batching into groups of _BATCH_SIZE.

        Returns a flat list of embedding vectors in the same order as input.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            logger.debug(
                "Embedder: embedding batch %d-%d of %d",
                i,
                i + len(batch),
                len(texts),
            )
            batch_results = await self._embed_batch_raw(batch)
            results.extend(batch_results)

        return results

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        results = await self.embed_batch([text])
        return results[0]
