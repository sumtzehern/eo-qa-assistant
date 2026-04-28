"""Query expansion using Claude Haiku.

Rewrites the user query to maximise recall from vector search.
Gracefully returns the original query on any error.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a search query optimizer for EdgeOne CDN documentation. "
    "Given a user question, rewrite it to maximize recall from a vector search. "
    "Output only the rewritten query, nothing else."
)

# claude-haiku-4-5 is the newer alias; fall back to the dated ID at runtime if needed.
_MODEL = "claude-haiku-4-5"


class QueryExpander:
    def __init__(self, anthropic_client) -> None:
        self._client = anthropic_client

    async def expand(self, query: str) -> str:
        """Return an expanded query string, or the original on failure."""
        try:
            message = await self._client.messages.create(
                model=_MODEL,
                max_tokens=200,
                temperature=0,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": query}],
            )
            return message.content[0].text.strip()
        except Exception:
            logger.warning("Query expansion failed; using original query", exc_info=True)
            return query
