"""Tests for the query pipeline modules.

Run with: pytest backend/tests/api/test_pipeline.py -v
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.pipeline.cache import CacheHit, CacheLayer
from backend.api.pipeline.generator import CitationItem, ClaudeGenerator
from backend.api.pipeline.searcher import SearchResult, _rrf_fusion


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_result(chunk_id: str, content: str = "some content", score: float = 0.5) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        content=content,
        title=f"Title {chunk_id}",
        url=f"https://example.com/{chunk_id}",
        section="Overview",
        source_id="edgeone-docs",
        score=score,
    )


# ---------------------------------------------------------------------------
# Unit test: RRF fusion
# ---------------------------------------------------------------------------


class TestRrfFusion:
    def test_both_lists_contribute(self):
        dense = [("a", {"content": "a"}), ("b", {"content": "b"})]
        sparse = [("b", {"content": "b"}), ("c", {"content": "c"})]
        fused = _rrf_fusion(dense, sparse, top_k=3)
        ids = [f[0] for f in fused]
        # "b" appears in both lists → should have highest score
        assert ids[0] == "b"
        assert len(fused) == 3

    def test_top_k_truncates(self):
        dense = [("a", {}), ("b", {}), ("c", {}), ("d", {})]
        sparse = [("e", {}), ("f", {}), ("g", {}), ("h", {})]
        fused = _rrf_fusion(dense, sparse, top_k=2)
        assert len(fused) == 2

    def test_single_list(self):
        dense = [("x", {"content": "x"}), ("y", {"content": "y"})]
        fused = _rrf_fusion(dense, [], top_k=5)
        ids = [f[0] for f in fused]
        # x ranked higher in dense → should appear first
        assert ids[0] == "x"
        assert len(fused) == 2

    def test_empty_lists(self):
        assert _rrf_fusion([], [], top_k=10) == []


# ---------------------------------------------------------------------------
# Unit test: extract_citations
# ---------------------------------------------------------------------------


class TestExtractCitations:
    def setup_method(self):
        mock_client = MagicMock()
        self.gen = ClaudeGenerator(anthropic_client=mock_client)

    def test_parses_single_citation(self):
        chunks = [_make_result("c1", content="EdgeOne is a CDN platform.")]
        answer = "EdgeOne provides CDN services [1]."
        cleaned, citations = self.gen.extract_citations(answer, chunks)
        assert len(citations) == 1
        assert citations[0].index == 1
        assert citations[0].title == "Title c1"
        assert cleaned == answer

    def test_parses_multiple_citations(self):
        chunks = [
            _make_result("c1", content="Content one."),
            _make_result("c2", content="Content two."),
        ]
        answer = "First point [1] and second point [2]."
        cleaned, citations = self.gen.extract_citations(answer, chunks)
        assert len(citations) == 2
        assert {c.index for c in citations} == {1, 2}

    def test_deduplicates_citations(self):
        chunks = [_make_result("c1", content="Repeated.")]
        answer = "Claim [1] and again [1]."
        _, citations = self.gen.extract_citations(answer, chunks)
        assert len(citations) == 1

    def test_no_answer_returns_empty(self):
        chunks = [_make_result("c1")]
        cleaned, citations = self.gen.extract_citations("NO_ANSWER", chunks)
        assert cleaned == ""
        assert citations == []

    def test_out_of_range_index_skipped(self):
        chunks = [_make_result("c1")]
        answer = "Claim [5]."  # only 1 chunk exists
        _, citations = self.gen.extract_citations(answer, chunks)
        assert citations == []


# ---------------------------------------------------------------------------
# Cache: miss path
# ---------------------------------------------------------------------------


class TestCacheMiss:
    @pytest.mark.asyncio
    async def test_returns_none_on_miss(self):
        redis_mock = AsyncMock()
        redis_mock.keys = AsyncMock(return_value=[])
        embedder_mock = MagicMock()
        cache = CacheLayer(redis_client=redis_mock, embedder=embedder_mock, threshold=0.92)

        result = await cache.get([0.1, 0.2, 0.3], "qid-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_below_threshold(self):
        # Store an embedding that is orthogonal → similarity = 0.0
        stored_emb = [1.0, 0.0, 0.0]
        query_emb = [0.0, 1.0, 0.0]

        redis_mock = AsyncMock()
        redis_mock.keys = AsyncMock(return_value=["cache:query:old"])
        redis_mock.hgetall = AsyncMock(return_value={
            "embedding": json.dumps(stored_emb),
            "answer": "cached answer",
            "citations": "[]",
            "confidence": "0.8",
        })

        cache = CacheLayer(redis_client=redis_mock, embedder=MagicMock(), threshold=0.92)
        result = await cache.get(query_emb, "new-qid")
        assert result is None


# ---------------------------------------------------------------------------
# Cache: hit path
# ---------------------------------------------------------------------------


class TestCacheHit:
    @pytest.mark.asyncio
    async def test_returns_hit_above_threshold(self):
        # Nearly identical embeddings → high cosine similarity
        emb = [1.0, 0.0, 0.0]

        redis_mock = AsyncMock()
        redis_mock.keys = AsyncMock(return_value=["cache:query:old"])
        redis_mock.hgetall = AsyncMock(return_value={
            "embedding": json.dumps(emb),
            "answer": "cached answer",
            "citations": json.dumps([{"index": 1, "title": "T", "url": "u", "section": "s", "snippet": "snip"}]),
            "confidence": "0.9",
        })

        cache = CacheLayer(redis_client=redis_mock, embedder=MagicMock(), threshold=0.92)
        result = await cache.get(emb, "new-qid")
        assert result is not None
        assert isinstance(result, CacheHit)
        assert result.answer == "cached answer"
        assert result.cached is True


# ---------------------------------------------------------------------------
# Graceful degradation: Qdrant raises → empty results
# ---------------------------------------------------------------------------


class TestSearcherDegradation:
    @pytest.mark.asyncio
    async def test_qdrant_error_returns_empty(self):
        from backend.api.pipeline.searcher import HybridSearcher

        qdrant_mock = AsyncMock()
        qdrant_mock.search = AsyncMock(side_effect=RuntimeError("Qdrant unavailable"))
        qdrant_mock.scroll = AsyncMock(side_effect=RuntimeError("Qdrant unavailable"))

        searcher = HybridSearcher(qdrant_client=qdrant_mock)
        results = await searcher.search(
            query_embedding=[0.1, 0.2],
            query_text="test query",
        )
        assert results == []
