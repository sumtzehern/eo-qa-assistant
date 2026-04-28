"""Sources route — GET /sources only. Ingestion routes live in ingestion.py."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_api_key
from backend.api.schemas.common import SourceItem, SourcesResponse
from backend.db.models import Chunk
from backend.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Fallback catalogue used when the DB returns no rows yet.
_STUB_SOURCES: list[dict] = [
    {
        "source_id": "edgeone-docs",
        "display_name": "EdgeOne Public Docs",
        "source_type": "html",
        "url": "https://cloud.tencent.com/document/product/1552",
        "last_crawled": None,
        "chunk_count": 0,
        "status": "unknown",
    },
    {
        "source_id": "tccli-reference",
        "display_name": "tccli CLI Reference",
        "source_type": "cli_ref",
        "url": None,
        "last_crawled": None,
        "chunk_count": 0,
        "status": "unknown",
    },
    {
        "source_id": "edgeone-api-ref",
        "display_name": "EdgeOne API Reference",
        "source_type": "api_ref",
        "url": "https://cloud.tencent.com/document/product/1552/api",
        "last_crawled": None,
        "chunk_count": 0,
        "status": "unknown",
    },
    {
        "source_id": "kb-json",
        "display_name": "Migration Knowledge Base (JSON)",
        "source_type": "json_kb",
        "url": None,
        "last_crawled": None,
        "chunk_count": 0,
        "status": "unknown",
    },
]


@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    request: Request,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> SourcesResponse:
    """Return all ingested sources and their freshness status.

    Queries the chunks table grouped by source_id. Falls back to the stub
    catalogue if the DB is unreachable or contains no rows.
    """
    try:
        result = await db.execute(
            select(
                Chunk.source_id,
                func.count(Chunk.chunk_id).label("chunk_count"),
                func.max(Chunk.created_at).label("last_crawled"),
            ).group_by(Chunk.source_id)
        )
        rows = result.all()
    except Exception:
        logger.warning("Failed to query chunks table for sources; using stub", exc_info=True)
        rows = []

    if rows:
        items = [
            SourceItem(
                source_id=row.source_id,
                display_name=row.source_id,
                source_type="unknown",
                last_crawled=row.last_crawled,
                chunk_count=row.chunk_count,
                status="healthy",
            )
            for row in rows
        ]
    else:
        items = [SourceItem(**s) for s in _STUB_SOURCES]

    return SourcesResponse(
        sources=items,
        total=len(items),
        request_id=request.state.request_id,
    )
