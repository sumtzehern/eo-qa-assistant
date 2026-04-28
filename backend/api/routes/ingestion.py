"""Ingestion API routes — real RQ-backed implementation.

POST /ingestion/trigger  → enqueue RQ jobs, create IngestionJob rows, return job_ids
GET  /ingestion/jobs/{job_id} → read job status from PostgreSQL
"""

import uuid
from datetime import datetime, timezone

import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_admin, require_api_key
from backend.api.schemas.common import (
    IngestionTriggerRequest,
    IngestionTriggerResponse,
    JobStatusResponse,
)
from backend.db.models import IngestionJob
from backend.db.session import get_db
from backend.ingestion.config import SOURCE_CONFIG_MAP, SOURCE_CONFIGS

router = APIRouter()


def _get_rq_queue() -> Queue:
    """Create a synchronous Redis connection for RQ (RQ requires sync redis)."""
    import os

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    conn = redis.from_url(redis_url)
    return Queue("ingestion", connection=conn)


@router.post(
    "/ingestion/trigger",
    response_model=IngestionTriggerResponse,
    status_code=202,
    summary="Trigger ingestion job(s)",
    description=(
        "Enqueue one RQ ingestion job per requested source. "
        "If source_ids is omitted, all configured sources are re-ingested."
    ),
)
async def trigger_ingestion(
    body: IngestionTriggerRequest,
    request: Request,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionTriggerResponse:
    source_ids = body.source_ids or [cfg.source_id for cfg in SOURCE_CONFIGS]

    # Validate all requested source_ids up front
    unknown = [sid for sid in source_ids if sid not in SOURCE_CONFIG_MAP]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown source_id(s): {unknown}. "
            f"Valid: {list(SOURCE_CONFIG_MAP.keys())}",
        )

    queue = _get_rq_queue()
    now = datetime.now(tz=timezone.utc)
    job_ids: list[str] = []

    for source_id in source_ids:
        job_id = str(uuid.uuid4())

        # Persist job row with status='queued'
        db_job = IngestionJob(
            job_id=job_id,
            source_id=source_id,
            status="queued",
            chunks_processed=0,
            chunks_skipped=0,
            chunks_failed=0,
            created_at=now,
        )
        db.add(db_job)

        # Enqueue RQ task.
        # RQ keyword args to the task function are passed via kwargs dict.
        # job_timeout and job_id are RQ-level options, not function args.
        queue.enqueue(
            "backend.ingestion.worker.run_ingestion_job",
            kwargs={
                "job_id": job_id,
                "source_id": source_id,
                "force_reembed": body.force,
            },
            job_id=job_id,
            job_timeout=3600,  # 1 hour max per source
        )

        job_ids.append(job_id)

    await db.commit()

    return IngestionTriggerResponse(
        job_ids=job_ids,
        queued_count=len(job_ids),
        request_id=request.state.request_id,
    )


@router.get(
    "/ingestion/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get ingestion job status",
    description="Read status and progress of an ingestion job from PostgreSQL.",
)
async def get_job_status(
    job_id: str,
    request: Request,
    _tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    result = await db.execute(
        select(IngestionJob).where(IngestionJob.job_id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        source_id=job.source_id,
        status=job.status,
        chunks_processed=job.chunks_processed,
        chunks_skipped=job.chunks_skipped,
        chunks_failed=job.chunks_failed,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        created_at=job.created_at,
        request_id=request.state.request_id,
    )
