"""SQLAlchemy 2.x ORM models for EdgeOne QA Assistant."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String, primary_key=True)  # SHA-256 of content
    source_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    page_title: Mapped[Optional[str]] = mapped_column(Text)
    section_title: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String, server_default="en")
    last_crawled: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    last_modified: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )


class Query(Base):
    __tablename__ = "queries"

    query_id: Mapped[str] = mapped_column(String, primary_key=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    citations: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    no_answer: Mapped[Optional[bool]] = mapped_column(Boolean)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    caller_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    language: Mapped[str] = mapped_column(String, server_default="en")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )


class EvalResult(Base):
    __tablename__ = "eval_results"

    eval_id: Mapped[str] = mapped_column(String, primary_key=True)
    query_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    groundedness: Mapped[Optional[float]] = mapped_column(Float)
    retrieval_relevance: Mapped[Optional[float]] = mapped_column(Float)
    citation_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    completeness: Mapped[Optional[float]] = mapped_column(Float)
    hallucination: Mapped[Optional[bool]] = mapped_column(Boolean)
    overall_score: Mapped[Optional[float]] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, server_default="false")
    flag_reason: Mapped[Optional[str]] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="queued"
    )  # queued | running | complete | failed
    chunks_processed: Mapped[int] = mapped_column(Integer, server_default="0")
    chunks_skipped: Mapped[int] = mapped_column(Integer, server_default="0")
    chunks_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now()
    )
