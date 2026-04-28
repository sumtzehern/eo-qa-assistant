"""RQ worker task: full ingestion pipeline for one source.

The `run_ingestion_job` function is the RQ job entry point.  It is designed
to be synchronous (RQ runs tasks in a thread pool) but calls async helpers
via asyncio.run() where needed.

Pipeline steps:
  1. Mark job 'running' in PostgreSQL
  2. Get crawler + chunker for the source type
  3. Fetch raw pages
  4. Chunk pages
  5. Load existing content_hashes from PostgreSQL
  6. Filter: skip unchanged chunks (unless force_reembed=True)
  7. Embed new/changed chunks in batches
  8. Upsert vectors to Qdrant + metadata to PostgreSQL
  9. Invalidate Redis cache for this source_id
  10. Mark job 'complete' (or 'failed' on exception)
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import IngestionJob
from backend.ingestion.chunker import Chunk, get_chunker
from backend.ingestion.config import SOURCE_CONFIG_MAP
from backend.ingestion.crawler import get_crawler
from backend.ingestion.embedder import Embedder
from backend.ingestion.invalidator import CacheInvalidator
from backend.ingestion.settings import settings
from backend.ingestion.writer import MetadataWriter, VectorWriter

logger = logging.getLogger(__name__)


def run_ingestion_job(
    job_id: str,
    source_id: str,
    force_reembed: bool = False,
) -> None:
    """RQ task entry point — runs the full ingestion pipeline for one source."""
    asyncio.run(_async_ingestion_job(job_id, source_id, force_reembed))


async def _async_ingestion_job(
    job_id: str,
    source_id: str,
    force_reembed: bool,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore[type-arg]
        engine, class_=AsyncSession, expire_on_commit=False
    )

    chunks_processed = 0
    chunks_skipped = 0
    chunks_failed = 0

    async with async_session() as session:
        # Step 1: Mark job as running
        await _update_job_status(session, job_id, "running", started_at=datetime.now(tz=timezone.utc))

    try:
        source_config = SOURCE_CONFIG_MAP.get(source_id)
        if source_config is None:
            raise ValueError(f"Unknown source_id: '{source_id}'")

        # Step 2: Get crawler + chunker
        crawler = get_crawler(source_config.source_type)
        chunker = get_chunker(source_config.source_type)

        # Step 3: Fetch raw pages
        logger.info("Job %s: fetching pages for source '%s'", job_id, source_id)
        pages = await crawler.fetch_pages(source_config)
        logger.info("Job %s: fetched %d pages", job_id, len(pages))

        # Step 4: Chunk pages
        all_chunks: list[Chunk] = []
        for page in pages:
            try:
                page_chunks = chunker.chunk(page)
                all_chunks.extend(page_chunks)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Job %s: chunking failed for page '%s'",
                    job_id,
                    page.url,
                    exc_info=True,
                )
                chunks_failed += 1

        logger.info("Job %s: produced %d total chunks", job_id, len(all_chunks))

        # Step 5: Load existing content hashes
        async with async_session() as session:
            existing_hashes: dict[str, str] = {}
            if not force_reembed:
                meta_writer = MetadataWriter()
                existing_hashes = await meta_writer.get_content_hashes(source_id, session)

        # Step 6: Filter unchanged chunks
        new_chunks: list[Chunk] = []
        for chunk in all_chunks:
            existing_hash = existing_hashes.get(chunk.chunk_id)
            if existing_hash == chunk.content_hash and not force_reembed:
                chunks_skipped += 1
            else:
                new_chunks.append(chunk)

        logger.info(
            "Job %s: %d new/changed chunks, %d skipped",
            job_id,
            len(new_chunks),
            chunks_skipped,
        )

        if new_chunks:
            # Step 7: Embed new/changed chunks
            embedder = Embedder()
            texts = [c.content for c in new_chunks]
            logger.info("Job %s: embedding %d chunks", job_id, len(texts))
            vectors = await embedder.embed_batch(texts)

            # Step 8: Upsert to Qdrant + PostgreSQL
            vector_writer = VectorWriter()
            await vector_writer.ensure_collection()
            await vector_writer.upsert_chunks(new_chunks, vectors)

            async with async_session() as session:
                meta_writer = MetadataWriter()
                await meta_writer.upsert_chunks(new_chunks, session)

            chunks_processed = len(new_chunks)

        # Step 9: Invalidate Redis cache
        invalidator = CacheInvalidator()
        try:
            deleted_keys = await invalidator.invalidate_source(source_id)
            logger.info("Job %s: invalidated %d Redis cache keys", job_id, deleted_keys)
        finally:
            await invalidator.close()

        # Step 10: Mark job complete
        async with async_session() as session:
            await _update_job_status(
                session,
                job_id,
                "complete",
                completed_at=datetime.now(tz=timezone.utc),
                chunks_processed=chunks_processed,
                chunks_skipped=chunks_skipped,
                chunks_failed=chunks_failed,
            )

        logger.info(
            "Job %s: complete — processed=%d skipped=%d failed=%d",
            job_id,
            chunks_processed,
            chunks_skipped,
            chunks_failed,
        )

    except Exception as exc:  # noqa: BLE001
        error_msg = traceback.format_exc()
        logger.error("Job %s: FAILED — %s", job_id, exc, exc_info=True)
        async with async_session() as session:
            await _update_job_status(
                session,
                job_id,
                "failed",
                completed_at=datetime.now(tz=timezone.utc),
                chunks_processed=chunks_processed,
                chunks_skipped=chunks_skipped,
                chunks_failed=chunks_failed,
                error_message=error_msg[:2000],  # truncate to fit column
            )
        raise

    finally:
        await engine.dispose()


async def _update_job_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    chunks_processed: int = 0,
    chunks_skipped: int = 0,
    chunks_failed: int = 0,
    error_message: str | None = None,
) -> None:
    values: dict[str, object] = {"status": status}
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at
    if chunks_processed:
        values["chunks_processed"] = chunks_processed
    if chunks_skipped:
        values["chunks_skipped"] = chunks_skipped
    if chunks_failed:
        values["chunks_failed"] = chunks_failed
    if error_message is not None:
        values["error_message"] = error_message

    await session.execute(
        update(IngestionJob).where(IngestionJob.job_id == job_id).values(**values)
    )
    await session.commit()
