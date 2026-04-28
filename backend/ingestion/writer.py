"""Persistence layer for ingested chunks.

VectorWriter  — writes chunk vectors to Qdrant.
MetadataWriter — writes chunk metadata to PostgreSQL via SQLAlchemy async.
"""

import logging
from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Chunk as ChunkModel
from backend.ingestion.chunker import Chunk
from backend.ingestion.settings import settings

logger = logging.getLogger(__name__)

_VECTOR_DIMS = 1536  # text-embedding-3-small output dimensionality
_COLLECTION = "chunks"


class VectorWriter:
    """Writes chunk vectors to Qdrant."""

    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = _COLLECTION

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""
        existing = self.client.get_collections().collections
        names = {c.name for c in existing}
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=_VECTOR_DIMS,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info("VectorWriter: created Qdrant collection '%s'", self.collection_name)
        else:
            logger.debug("VectorWriter: collection '%s' already exists", self.collection_name)

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        """Upsert chunks and their vectors into Qdrant.

        Uses chunk_id as the Qdrant point id (stored as payload key too).
        Metadata is stored as Qdrant payload for filtered search.
        """
        if not chunks:
            return

        points = [
            qdrant_models.PointStruct(
                id=_chunk_id_to_int(chunk.chunk_id),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "source_id": chunk.source_id,
                    "source_url": chunk.source_url,
                    "page_title": chunk.page_title,
                    "section_title": chunk.section_title,
                    "language": chunk.language,
                    "token_count": chunk.token_count,
                    # Store truncated content for reranker fallback
                    "content_preview": chunk.content[:500],
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.debug("VectorWriter: upserted %d points", len(points))

    async def delete_by_source(self, source_id: str) -> None:
        """Delete all Qdrant points belonging to a source."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="source_id",
                            match=qdrant_models.MatchValue(value=source_id),
                        )
                    ]
                )
            ),
        )
        logger.info("VectorWriter: deleted all points for source_id='%s'", source_id)


def _chunk_id_to_int(chunk_id: str) -> int:
    """Convert a hex SHA-256 string to an integer for Qdrant point id."""
    # Qdrant supports both UUID and unsigned 64-bit integer ids.
    # We take the first 16 hex chars (64 bits) of the SHA-256 as an int.
    return int(chunk_id[:16], 16)


class MetadataWriter:
    """Writes chunk metadata to PostgreSQL."""

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        session: AsyncSession,
    ) -> None:
        """Upsert chunk metadata rows using PostgreSQL ON CONFLICT DO UPDATE."""
        if not chunks:
            return

        now = datetime.now(tz=timezone.utc)
        rows = [
            {
                "chunk_id": c.chunk_id,
                "source_id": c.source_id,
                "source_url": c.source_url,
                "page_title": c.page_title,
                "section_title": c.section_title,
                "content": c.content,
                "content_hash": c.content_hash,
                "token_count": c.token_count,
                "language": c.language,
                "last_crawled": now,
            }
            for c in chunks
        ]

        stmt = pg_insert(ChunkModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["chunk_id"],
            set_={
                "content": stmt.excluded.content,
                "content_hash": stmt.excluded.content_hash,
                "token_count": stmt.excluded.token_count,
                "last_crawled": stmt.excluded.last_crawled,
            },
        )
        await session.execute(stmt)
        await session.commit()
        logger.debug("MetadataWriter: upserted %d chunk rows", len(rows))

    async def get_content_hashes(
        self,
        source_id: str,
        session: AsyncSession,
    ) -> dict[str, str]:
        """Return {chunk_id: content_hash} for all existing chunks from source_id."""
        result = await session.execute(
            select(ChunkModel.chunk_id, ChunkModel.content_hash).where(
                ChunkModel.source_id == source_id
            )
        )
        return {row.chunk_id: row.content_hash for row in result}
