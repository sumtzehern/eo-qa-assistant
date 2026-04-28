"""Async crawlers for each source type.

Each crawler fetches raw pages from its source and returns a list of RawPage
objects. Crawlers are stateless — they don't write to any store.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from backend.ingestion.config import SourceConfig

logger = logging.getLogger(__name__)


@dataclass
class RawPage:
    url: str
    title: str
    content: str  # cleaned text content
    language: str
    source_id: str


class BaseCrawler:
    async def fetch_pages(self, source_config: SourceConfig) -> list[RawPage]:
        raise NotImplementedError


class HtmlDocsCrawler(BaseCrawler):
    """Crawls HTML documentation pages.

    Fetches the seed URL, discovers linked subpages within the same product
    path, and extracts text content using BeautifulSoup.
    """

    async def fetch_pages(self, source_config: SourceConfig) -> list[RawPage]:
        pages: list[RawPage] = []
        visited: set[str] = set()

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "EdgeOne-QA-Crawler/1.0"},
        ) as client:
            to_visit = list(source_config.urls)

            while to_visit:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning("Failed to fetch %s: %s", url, exc)
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                # Extract page title
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else url

                # Extract main content — prefer article/main containers
                main = (
                    soup.find("article")
                    or soup.find("main")
                    or soup.find(id="doc-content")
                    or soup.find(class_="doc-content")
                    or soup.body
                )
                if main is None:
                    continue

                # Remove nav, footer, scripts, styles
                for tag in main.find_all(
                    ["nav", "footer", "script", "style", "aside"]
                ):
                    tag.decompose()

                content = main.get_text(separator="\n", strip=True)
                if not content.strip():
                    continue

                pages.append(
                    RawPage(
                        url=url,
                        title=title,
                        content=content,
                        language=source_config.language,
                        source_id=source_config.source_id,
                    )
                )

                # Discover linked subpages within the same product path
                base_path = "/document/product/1552"
                for link in soup.find_all("a", href=True):
                    href: str = link["href"]
                    if not href.startswith("http"):
                        href = f"https://cloud.tencent.com{href}"
                    if (
                        base_path in href
                        and href not in visited
                        and href not in to_visit
                        # Limit to reasonable depth
                        and len(visited) < 500
                    ):
                        to_visit.append(href)

        logger.info(
            "HtmlDocsCrawler: fetched %d pages for source '%s'",
            len(pages),
            source_config.source_id,
        )
        return pages


class ApiRefCrawler(BaseCrawler):
    """Crawls API reference pages — one page per API endpoint group."""

    async def fetch_pages(self, source_config: SourceConfig) -> list[RawPage]:
        pages: list[RawPage] = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "EdgeOne-QA-Crawler/1.0"},
        ) as client:
            for url in source_config.urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning("ApiRefCrawler: failed to fetch %s: %s", url, exc)
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                # Extract each API endpoint section as a separate "page"
                # API reference pages typically use h2 per endpoint group
                title_tag = soup.find("h1") or soup.find("title")
                page_title = title_tag.get_text(strip=True) if title_tag else url

                main = (
                    soup.find("article")
                    or soup.find("main")
                    or soup.find(id="doc-content")
                    or soup.body
                )
                if main is None:
                    continue

                for tag in main.find_all(["nav", "footer", "script", "style"]):
                    tag.decompose()

                # Split into per-endpoint sections by h2
                current_section_title = page_title
                current_lines: list[str] = []

                for element in main.children:
                    if not hasattr(element, "name"):
                        continue
                    if element.name == "h2":
                        # Flush current section
                        if current_lines:
                            content = "\n".join(current_lines).strip()
                            if content:
                                pages.append(
                                    RawPage(
                                        url=url,
                                        title=current_section_title,
                                        content=content,
                                        language=source_config.language,
                                        source_id=source_config.source_id,
                                    )
                                )
                        current_section_title = element.get_text(strip=True)
                        current_lines = [current_section_title]
                    else:
                        current_lines.append(element.get_text(separator="\n", strip=True))

                # Flush final section
                if current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        pages.append(
                            RawPage(
                                url=url,
                                title=current_section_title,
                                content=content,
                                language=source_config.language,
                                source_id=source_config.source_id,
                            )
                        )

        logger.info(
            "ApiRefCrawler: extracted %d endpoint pages for source '%s'",
            len(pages),
            source_config.source_id,
        )
        return pages


class CliRefCrawler(BaseCrawler):
    """Crawls CLI reference pages — one page per tccli command."""

    async def fetch_pages(self, source_config: SourceConfig) -> list[RawPage]:
        pages: list[RawPage] = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "EdgeOne-QA-Crawler/1.0"},
        ) as client:
            for url in source_config.urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning("CliRefCrawler: failed to fetch %s: %s", url, exc)
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                title_tag = soup.find("h1") or soup.find("title")
                page_title = title_tag.get_text(strip=True) if title_tag else url

                main = (
                    soup.find("article")
                    or soup.find("main")
                    or soup.find(id="doc-content")
                    or soup.body
                )
                if main is None:
                    continue

                for tag in main.find_all(["nav", "footer", "script", "style"]):
                    tag.decompose()

                # CLI reference: split by h2/h3 command headings
                current_cmd = page_title
                current_lines: list[str] = []

                for element in main.children:
                    if not hasattr(element, "name"):
                        continue
                    if element.name in ("h2", "h3"):
                        if current_lines:
                            content = "\n".join(current_lines).strip()
                            if content:
                                pages.append(
                                    RawPage(
                                        url=url,
                                        title=current_cmd,
                                        content=content,
                                        language=source_config.language,
                                        source_id=source_config.source_id,
                                    )
                                )
                        current_cmd = element.get_text(strip=True)
                        current_lines = [current_cmd]
                    else:
                        current_lines.append(element.get_text(separator="\n", strip=True))

                if current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        pages.append(
                            RawPage(
                                url=url,
                                title=current_cmd,
                                content=content,
                                language=source_config.language,
                                source_id=source_config.source_id,
                            )
                        )

        logger.info(
            "CliRefCrawler: extracted %d command pages for source '%s'",
            len(pages),
            source_config.source_id,
        )
        return pages


class JsonKbCrawler(BaseCrawler):
    """Reads local JSON knowledge-base files.

    Each top-level entry in the JSON becomes one RawPage.
    Supports both list and dict top-level structures.
    """

    async def fetch_pages(self, source_config: SourceConfig) -> list[RawPage]:
        pages: list[RawPage] = []

        for file_path in source_config.file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning("JsonKbCrawler: file not found: %s", file_path)
                continue

            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("JsonKbCrawler: failed to read %s: %s", file_path, exc)
                continue

            file_title = path.stem

            if isinstance(data, list):
                for i, entry in enumerate(data):
                    content = json.dumps(entry, ensure_ascii=False, indent=2)
                    entry_title = (
                        entry.get("name") or entry.get("id") or f"{file_title}[{i}]"
                        if isinstance(entry, dict)
                        else f"{file_title}[{i}]"
                    )
                    pages.append(
                        RawPage(
                            url=f"file://{file_path}#{i}",
                            title=str(entry_title),
                            content=content,
                            language=source_config.language,
                            source_id=source_config.source_id,
                        )
                    )
            elif isinstance(data, dict):
                for key, value in data.items():
                    content = json.dumps({key: value}, ensure_ascii=False, indent=2)
                    pages.append(
                        RawPage(
                            url=f"file://{file_path}#{key}",
                            title=f"{file_title}: {key}",
                            content=content,
                            language=source_config.language,
                            source_id=source_config.source_id,
                        )
                    )
            else:
                # Scalar top-level — treat as single page
                pages.append(
                    RawPage(
                        url=f"file://{file_path}",
                        title=file_title,
                        content=json.dumps(data, ensure_ascii=False, indent=2),
                        language=source_config.language,
                        source_id=source_config.source_id,
                    )
                )

        logger.info(
            "JsonKbCrawler: extracted %d entries for source '%s'",
            len(pages),
            source_config.source_id,
        )
        return pages


_CRAWLER_MAP: dict[str, type[BaseCrawler]] = {
    "html_docs": HtmlDocsCrawler,
    "api_ref": ApiRefCrawler,
    "cli_ref": CliRefCrawler,
    "json_kb": JsonKbCrawler,
}


def get_crawler(source_type: str) -> BaseCrawler:
    """Return the appropriate crawler instance for a source type."""
    cls = _CRAWLER_MAP.get(source_type)
    if cls is None:
        raise ValueError(
            f"Unknown source_type '{source_type}'. "
            f"Valid options: {list(_CRAWLER_MAP.keys())}"
        )
    return cls()
