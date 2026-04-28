"""Pydantic v2 schemas for eval, sources, ingestion, and admin endpoints."""

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------


class EvalResponse(BaseModel):
    eval_id: str | None
    query_id: str
    groundedness: float | None = None
    retrieval_relevance: float | None = None
    citation_accuracy: float | None = None
    completeness: float | None = None
    hallucination: bool | None = None
    overall_score: float | None = None
    flagged: bool = False
    flag_reason: str | None = None
    reviewed: bool = False
    status: str = "pending"
    request_id: str | None = None


class EvalSummaryResponse(BaseModel):
    period_days: int
    total_queries: int
    avg_groundedness: float | None
    avg_retrieval_relevance: float | None
    avg_citation_accuracy: float | None
    avg_completeness: float | None
    avg_overall_score: float | None
    hallucination_rate: float | None
    no_answer_rate: float | None
    flagged_count: int
    cache_hit_rate: float | None = None
    request_id: str | None = None


class FlaggedQueryItem(BaseModel):
    eval_id: str
    query_id: str
    query_text: str | None = None
    flag_reason: str | None = None
    groundedness: float | None = None
    overall_score: float | None = None
    hallucination: bool | None = None
    reviewed: bool = False
    completed_at: datetime | None = None
    request_id: str | None = None


class FlaggedQueriesResponse(BaseModel):
    items: list[FlaggedQueryItem]
    total: int
    request_id: str | None = None


class ReviewUpdateRequest(BaseModel):
    reviewed: bool = True
    review_note: str | None = None


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class SourceItem(BaseModel):
    source_id: str
    display_name: str
    source_type: str  # html | api_ref | cli_ref | json_kb | markdown
    url: str | None = None
    last_crawled: datetime | None = None
    chunk_count: int = 0
    status: str = "unknown"  # healthy | stale | error | unknown


class SourcesResponse(BaseModel):
    sources: list[SourceItem]
    total: int
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class IngestionTriggerRequest(BaseModel):
    source_ids: list[str] | None = None  # None = re-ingest all
    force: bool = False  # ignore content_hash diff


class IngestionTriggerResponse(BaseModel):
    job_ids: list[str]
    queued_count: int
    request_id: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    source_id: str
    status: str  # queued | running | complete | failed
    chunks_processed: int = 0
    chunks_skipped: int = 0
    chunks_failed: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    request_id: str | None = None
