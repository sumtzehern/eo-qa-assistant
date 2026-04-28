"""Eval and admin eval routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_admin, require_api_key
from backend.api.schemas.common import (
    EvalSummaryResponse,
    FlaggedQueriesResponse,
    FlaggedQueryItem,
    ReviewUpdateRequest,
)
from backend.db.session import get_db

router = APIRouter()


@router.get("/eval/summary", response_model=EvalSummaryResponse)
async def get_eval_summary(
    request: Request,
    period_days: int = 7,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> EvalSummaryResponse:
    """Return aggregate eval stats for the given period.

    Phase 2b: returns stub zeroed-out metrics. Phase 4 queries PostgreSQL.
    """
    return EvalSummaryResponse(
        period_days=period_days,
        total_queries=0,
        avg_groundedness=None,
        avg_retrieval_relevance=None,
        avg_citation_accuracy=None,
        avg_completeness=None,
        avg_overall_score=None,
        hallucination_rate=None,
        no_answer_rate=None,
        flagged_count=0,
        cache_hit_rate=None,
        request_id=request.state.request_id,
    )


@router.get("/admin/eval/flagged", response_model=FlaggedQueriesResponse)
async def list_flagged_queries(
    request: Request,
    reviewed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FlaggedQueriesResponse:
    """Return flagged queries pending human review.

    Phase 2b: returns empty list. Phase 4 reads from PostgreSQL.
    """
    return FlaggedQueriesResponse(
        items=[],
        total=0,
        request_id=request.state.request_id,
    )


@router.patch("/admin/eval/flagged/{eval_id}", response_model=FlaggedQueryItem)
async def update_flagged_query(
    eval_id: str,
    body: ReviewUpdateRequest,
    request: Request,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FlaggedQueryItem:
    """Mark a flagged query as reviewed (or un-reviewed).

    Phase 2b: returns stub response. Phase 4 persists to PostgreSQL.
    """
    return FlaggedQueryItem(
        eval_id=eval_id,
        query_id="stub",
        reviewed=body.reviewed,
        request_id=request.state.request_id,
    )
