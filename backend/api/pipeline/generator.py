"""Claude streaming generator with citation injection."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator

import anthropic

if TYPE_CHECKING:
    from backend.api.pipeline.searcher import SearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert assistant for Tencent EdgeOne CDN platform.
Answer questions using ONLY the provided context chunks.
For every factual claim, cite the chunk number inline as [N] (e.g., "EdgeOne supports HTTP/3 [1]").
If the context does not contain enough information to answer, respond with exactly: NO_ANSWER
Be concise but complete. Do not hallucinate."""


@dataclass
class CitationItem:
    index: int
    title: str
    url: str
    section: str
    snippet: str


class ClaudeGenerator:
    def __init__(
        self,
        anthropic_client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-5",
    ) -> None:
        self._client = anthropic_client
        self._model = model

    async def stream(
        self,
        query: str,
        chunks: list[SearchResult],
        language: str = "en",
    ) -> AsyncIterator[str]:
        """Yield raw token strings from Claude's streaming response."""
        context_parts = [
            f"[{i + 1}] {chunk.title} — {chunk.section}\n{chunk.content}\n"
            for i, chunk in enumerate(chunks)
        ]
        context = "\n".join(context_parts)

        user_message = f"Context:\n{context}\n\nQuestion: {query}"
        if language == "zh":
            user_message += " Please answer in Chinese."

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def extract_citations(
        self,
        answer: str,
        chunks: list[SearchResult],
    ) -> tuple[str, list[CitationItem]]:
        """Parse [N] references in the answer and map to CitationItems.

        Returns (cleaned_answer, citations). For NO_ANSWER returns ("", []).
        """
        if answer.strip() == "NO_ANSWER":
            return ("", [])

        citation_indices = [int(m) for m in re.findall(r"\[(\d+)\]", answer)]
        seen: set[int] = set()
        citations: list[CitationItem] = []

        for idx in citation_indices:
            if idx in seen:
                continue
            seen.add(idx)
            chunk_pos = idx - 1  # [1]-indexed
            if 0 <= chunk_pos < len(chunks):
                chunk = chunks[chunk_pos]
                citations.append(
                    CitationItem(
                        index=idx,
                        title=chunk.title,
                        url=chunk.url,
                        section=chunk.section,
                        snippet=chunk.content[:200],
                    )
                )

        return (answer, citations)
