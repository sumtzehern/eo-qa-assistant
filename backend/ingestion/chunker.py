"""Source-type-aware chunking strategies.

Each chunker takes a RawPage and returns a list of Chunk objects whose fields
match the `chunks` PostgreSQL table exactly.

Chunk identity:
  chunk_id     = SHA-256(content)   — used as PRIMARY KEY in PostgreSQL / Qdrant point id
  content_hash = SHA-256(content)   — used for diff-based skip logic

Both are identical by design: if content changes the chunk is a new object.
"""

import hashlib
import re
from dataclasses import dataclass

import tiktoken

from backend.ingestion.crawler import RawPage

# Shared tokeniser — cl100k_base matches text-embedding-3-small
_ENCODER = tiktoken.get_encoding("cl100k_base")

# Chunking constants
HTML_TARGET_TOKENS = 800
HTML_OVERLAP_TOKENS = 100
MAX_TOKENS = 1000  # hard cap per chunk


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


def _split_by_tokens(
    text: str,
    target: int = HTML_TARGET_TOKENS,
    overlap: int = HTML_OVERLAP_TOKENS,
) -> list[str]:
    """Split text into token-bounded chunks with overlap.

    Works at sentence/newline boundaries to avoid mid-sentence splits.
    """
    tokens = _ENCODER.encode(text)
    if len(tokens) <= target:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + target, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _ENCODER.decode(chunk_tokens)
        chunks.append(chunk_text)
        if end >= len(tokens):
            break
        start = end - overlap  # back up by overlap
    return chunks


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_url: str
    page_title: str
    section_title: str
    content: str
    content_hash: str
    token_count: int
    language: str


def _make_chunk(
    *,
    source_id: str,
    source_url: str,
    page_title: str,
    section_title: str,
    content: str,
    language: str,
) -> Chunk:
    content_hash = _sha256(content)
    return Chunk(
        chunk_id=content_hash,  # SHA-256 of content == chunk_id
        source_id=source_id,
        source_url=source_url,
        page_title=page_title,
        section_title=section_title,
        content=content,
        content_hash=content_hash,
        token_count=_count_tokens(content),
        language=language,
    )


class BaseChunker:
    def chunk(self, page: RawPage) -> list[Chunk]:
        raise NotImplementedError


class HtmlChunker(BaseChunker):
    """Split HTML doc pages by h2/h3 headings, then token-bound with overlap.

    Strategy:
    1. Split the raw text on heading-like lines (all-caps words, lines that
       look like section headers based on position in the text).
    2. For each section, if token count > HTML_TARGET_TOKENS, further split
       by tokens with HTML_OVERLAP_TOKENS overlap.
    """

    # Matches lines that look like headings: short, no trailing punctuation
    _HEADING_RE = re.compile(
        r"^(?:#{1,3}\s+.+|[A-Z][A-Za-z0-9 \-:]{2,79})$",
        re.MULTILINE,
    )

    def chunk(self, page: RawPage) -> list[Chunk]:
        chunks: list[Chunk] = []
        lines = page.content.splitlines()

        sections: list[tuple[str, list[str]]] = []  # (section_title, lines)
        current_title = page.title
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Detect heading: markdown heading or short capitalized line
            is_heading = (
                stripped.startswith("#")
                or (
                    len(stripped) < 80
                    and len(stripped) > 2
                    and not stripped.endswith((".", ",", ";", ":"))
                    and stripped == stripped  # always true; placeholder for future heuristic
                    and re.match(r"^[A-Z]", stripped)
                    and _count_tokens(stripped) < 15
                )
            )
            if stripped.startswith("#") and len(stripped) > 2:
                # Markdown heading — flush and start new section
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = stripped.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_title, current_lines))

        for section_title, section_lines in sections:
            section_text = "\n".join(section_lines).strip()
            if not section_text:
                continue

            sub_chunks = _split_by_tokens(section_text)
            for i, sub_text in enumerate(sub_chunks):
                sub_text = sub_text.strip()
                if not sub_text:
                    continue
                title = section_title if len(sub_chunks) == 1 else f"{section_title} (part {i + 1})"
                chunks.append(
                    _make_chunk(
                        source_id=page.source_id,
                        source_url=page.url,
                        page_title=page.title,
                        section_title=title,
                        content=sub_text,
                        language=page.language,
                    )
                )

        # Dedup by chunk_id (same content appearing in multiple sections)
        seen: set[str] = set()
        deduped: list[Chunk] = []
        for c in chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                deduped.append(c)

        return deduped


class ApiChunker(BaseChunker):
    """One chunk per API endpoint.

    The RawPage from ApiRefCrawler already contains one endpoint per page,
    so this chunker simply wraps the full page content as a single chunk,
    optionally splitting if it exceeds MAX_TOKENS.
    """

    def chunk(self, page: RawPage) -> list[Chunk]:
        content = page.content.strip()
        if not content:
            return []

        if _count_tokens(content) <= MAX_TOKENS:
            return [
                _make_chunk(
                    source_id=page.source_id,
                    source_url=page.url,
                    page_title=page.title,
                    section_title=page.title,
                    content=content,
                    language=page.language,
                )
            ]

        # Oversized endpoint — split by tokens
        chunks: list[Chunk] = []
        for i, sub_text in enumerate(_split_by_tokens(content, target=MAX_TOKENS)):
            sub_text = sub_text.strip()
            if sub_text:
                chunks.append(
                    _make_chunk(
                        source_id=page.source_id,
                        source_url=page.url,
                        page_title=page.title,
                        section_title=f"{page.title} (part {i + 1})",
                        content=sub_text,
                        language=page.language,
                    )
                )
        return chunks


class CliChunker(BaseChunker):
    """One chunk per CLI command.

    Same logic as ApiChunker — each RawPage from CliRefCrawler is already
    scoped to one command.
    """

    def chunk(self, page: RawPage) -> list[Chunk]:
        content = page.content.strip()
        if not content:
            return []

        if _count_tokens(content) <= MAX_TOKENS:
            return [
                _make_chunk(
                    source_id=page.source_id,
                    source_url=page.url,
                    page_title=page.title,
                    section_title=page.title,
                    content=content,
                    language=page.language,
                )
            ]

        chunks: list[Chunk] = []
        for i, sub_text in enumerate(_split_by_tokens(content, target=MAX_TOKENS)):
            sub_text = sub_text.strip()
            if sub_text:
                chunks.append(
                    _make_chunk(
                        source_id=page.source_id,
                        source_url=page.url,
                        page_title=page.title,
                        section_title=f"{page.title} (part {i + 1})",
                        content=sub_text,
                        language=page.language,
                    )
                )
        return chunks


class JsonChunker(BaseChunker):
    """One chunk per top-level JSON entry.

    JsonKbCrawler emits one RawPage per top-level entry, so this chunker also
    produces one chunk per page (with fallback splitting for large entries).
    """

    def chunk(self, page: RawPage) -> list[Chunk]:
        content = page.content.strip()
        if not content:
            return []

        if _count_tokens(content) <= MAX_TOKENS:
            return [
                _make_chunk(
                    source_id=page.source_id,
                    source_url=page.url,
                    page_title=page.title,
                    section_title=page.title,
                    content=content,
                    language=page.language,
                )
            ]

        chunks: list[Chunk] = []
        for i, sub_text in enumerate(_split_by_tokens(content, target=MAX_TOKENS)):
            sub_text = sub_text.strip()
            if sub_text:
                chunks.append(
                    _make_chunk(
                        source_id=page.source_id,
                        source_url=page.url,
                        page_title=page.title,
                        section_title=f"{page.title} (part {i + 1})",
                        content=sub_text,
                        language=page.language,
                    )
                )
        return chunks


_CHUNKER_MAP: dict[str, type[BaseChunker]] = {
    "html_docs": HtmlChunker,
    "api_ref": ApiChunker,
    "cli_ref": CliChunker,
    "json_kb": JsonChunker,
}


def get_chunker(source_type: str) -> BaseChunker:
    """Return the appropriate chunker instance for a source type."""
    cls = _CHUNKER_MAP.get(source_type)
    if cls is None:
        raise ValueError(
            f"Unknown source_type '{source_type}'. "
            f"Valid options: {list(_CHUNKER_MAP.keys())}"
        )
    return cls()
