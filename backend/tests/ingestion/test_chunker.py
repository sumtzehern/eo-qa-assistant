"""Unit tests for backend/ingestion/chunker.py"""

import hashlib

import pytest

from backend.ingestion.chunker import (
    HtmlChunker,
    JsonChunker,
    _count_tokens,
    _sha256,
)
from backend.ingestion.crawler import RawPage


def _make_page(content: str, source_type: str = "html_docs") -> RawPage:
    return RawPage(
        url="https://example.com/test",
        title="Test Page",
        content=content,
        language="en",
        source_id="test-source",
    )


# ---------------------------------------------------------------------------
# SHA-256 helpers
# ---------------------------------------------------------------------------


def test_sha256_matches_stdlib() -> None:
    text = "hello world"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert _sha256(text) == expected


def test_sha256_empty_string() -> None:
    assert _sha256("") == hashlib.sha256(b"").hexdigest()


# ---------------------------------------------------------------------------
# HtmlChunker
# ---------------------------------------------------------------------------


def test_html_chunker_splits_by_heading() -> None:
    content = "Intro paragraph text.\n# Section One\nContent of section one.\n# Section Two\nContent of section two."
    page = _make_page(content)
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    # Should produce at least 2 chunks (one per markdown heading section)
    assert len(chunks) >= 2

    full_text = " ".join(c.content for c in chunks)
    assert "section one" in full_text.lower() or "Section One" in full_text
    assert "section two" in full_text.lower() or "Section Two" in full_text


def test_html_chunker_returns_correct_source_id() -> None:
    page = _make_page("Some content here.")
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    for chunk in chunks:
        assert chunk.source_id == "test-source"
        assert chunk.source_url == "https://example.com/test"
        assert chunk.page_title == "Test Page"
        assert chunk.language == "en"


def test_chunk_id_is_sha256_of_content() -> None:
    page = _make_page("Deterministic content string.")
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    for chunk in chunks:
        expected_id = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        assert chunk.chunk_id == expected_id, (
            f"chunk_id {chunk.chunk_id!r} != SHA-256({chunk.content[:40]!r})"
        )


def test_content_hash_is_sha256_of_content() -> None:
    page = _make_page("Another deterministic string for hashing.")
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    for chunk in chunks:
        expected_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        assert chunk.content_hash == expected_hash


def test_chunk_id_equals_content_hash() -> None:
    """chunk_id and content_hash must be identical (both are SHA-256 of content)."""
    page = _make_page("Sample text for identity check.")
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    for chunk in chunks:
        assert chunk.chunk_id == chunk.content_hash


def test_token_count_uses_tiktoken() -> None:
    content = "The quick brown fox jumps over the lazy dog."
    page = _make_page(content)
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    # Verify each chunk's token_count matches what tiktoken reports
    for chunk in chunks:
        expected = _count_tokens(chunk.content)
        assert chunk.token_count == expected, (
            f"token_count {chunk.token_count} != tiktoken count {expected}"
        )


def test_token_count_positive() -> None:
    page = _make_page("This has tokens.")
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)
    for chunk in chunks:
        assert chunk.token_count > 0


# ---------------------------------------------------------------------------
# JsonChunker
# ---------------------------------------------------------------------------


def test_json_chunker_single_chunk_for_short_content() -> None:
    import json

    data = {"name": "test-behavior", "edgeone_action": "cache", "confidence": 0.9}
    content = json.dumps(data, indent=2)
    page = RawPage(
        url="file:///kb/mappings.json#test-behavior",
        title="mappings: test-behavior",
        content=content,
        language="en",
        source_id="error-patterns",
    )
    chunker = JsonChunker()
    chunks = chunker.chunk(page)

    assert len(chunks) == 1
    assert chunks[0].source_id == "error-patterns"
    assert chunks[0].content == content


def test_json_chunker_chunk_id_sha256() -> None:
    import json

    content = json.dumps({"key": "value"}, indent=2)
    page = RawPage(
        url="file:///kb/test.json#0",
        title="test: key",
        content=content,
        language="en",
        source_id="test-source",
    )
    chunker = JsonChunker()
    chunks = chunker.chunk(page)

    for chunk in chunks:
        assert chunk.chunk_id == hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_html_chunker_deduplicates_identical_content() -> None:
    """If two sections have identical text, only one chunk should appear."""
    repeated = "Same content appears here."
    content = f"# Section A\n{repeated}\n# Section B\n{repeated}"
    page = _make_page(content)
    chunker = HtmlChunker()
    chunks = chunker.chunk(page)

    chunk_ids = [c.chunk_id for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk_ids found after dedup"
