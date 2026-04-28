"""Sources and ingestion routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_admin, require_api_key
from backend.api.middleware.rate_limit import check_rate_limit
from backend.api.schemas.common import (
    IngestionTriggerRequest,
    IngestionTriggerResponse,
    JobStatusResponse,
    SourceItem,
    SourcesResponse,
)
from backend.db.session import get_db

router = APIRouter()

# Stub source catalogue — Phase 2a populates this from the ingestion pipeline.
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

# Stub job store — Phase 2a replaces with real RQ/PostgreSQL tracking.
_STUB_JOBS: dict[str, dict] = {}


@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    request: Request,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> SourcesResponse:
    """Return all ingested sources and their freshness status.

    Phase 2b: returns stub catalogue. Phase 3 reads live data from PostgreSQL.
    """
    items = [SourceItem(**s) for s in _STUB_SOURCES]
    return SourcesResponse(
        sources=items,
        total=len(items),
        request_id=request.state.request_id,
    )


@router.post("/ingestion/trigger", response_model=IngestionTriggerResponse, status_code=202)
async def trigger_ingestion(
    body: IngestionTriggerRequest,
    request: Request,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionTriggerResponse:
    """Enqueue ingestion job(s) for one or all sources.

    Phase 2b: creates stub job records. Phase 2a wires real RQ tasks.
    """
    source_ids = body.source_ids or [s["source_id"] for s in _STUB_SOURCES]
    job_ids = []
    for source_id in source_ids:
        job_id = str(uuid.uuid4())
        _STUB_JOBS[job_id] = {
            "job_id": job_id,
            "source_id": source_id,
            "status": "queued",
            "chunks_processed": 0,
            "chunks_skipped": 0,
            "chunks_failed": 0,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "created_at": datetime.now(tz=timezone.utc),
        }
        job_ids.append(job_id)

    return IngestionTriggerResponse(
        job_ids=job_ids,
        queued_count=len(job_ids),
        request_id=request.state.request_id,
    )


@router.get("/ingestion/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request: Request,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Return status of an ingestion job.

    Phase 2b: reads from in-memory stub store. Phase 2a stores in PostgreSQL.
    """
    from fastapi import HTTPException

    job = _STUB_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    return JobStatusResponse(**job, request_id=request.state.request_id)
