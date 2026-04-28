"""Pydantic v2 schemas for query endpoints."""

from pydantic import BaseModel, Field


class QueryOptions(BaseModel):
    language: str = "en"
    source_filter: list[str] = []
    query_expansion: bool = False
    max_citations: int = 5


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    options: QueryOptions = QueryOptions()
    session_id: str | None = None
    caller_id: str = "api"


class CitationItem(BaseModel):
    index: int
    title: str
    url: str
    section: str
    snippet: str


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    citations: list[CitationItem]
    confidence: float
    no_answer: bool
    latency_ms: int
    eval_status: str = "pending"
    eval_id: str | None = None
    request_id: str | None = None
