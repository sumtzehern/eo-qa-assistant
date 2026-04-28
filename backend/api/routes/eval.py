"""Eval and admin eval routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Float, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_admin, require_api_key
from backend.api.schemas.common import (
    EvalSummaryResponse,
    FlaggedQueriesResponse,
    FlaggedQueryItem,
    ReviewUpdateRequest,
)
from backend.db.models import EvalResult, Query
from backend.db.session import get_db

router = APIRouter()


@router.get("/eval/summary", response_model=EvalSummaryResponse)
async def get_eval_summary(
    request: Request,
    period_days: int = 7,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> EvalSummaryResponse:
    """Return aggregate eval stats for the given period."""
    try:
        since = datetime.now(tz=timezone.utc) - timedelta(days=period_days)

        # Total queries in period
        total_result = await db.execute(
            select(func.count()).where(Query.created_at > since)
        )
        total_queries = total_result.scalar() or 0

        # No-answer count
        no_ans_result = await db.execute(
            select(func.count())
            .where(Query.created_at > since)
            .where(Query.no_answer == True)  # noqa: E712
        )
        no_answer_count = no_ans_result.scalar() or 0
        no_answer_rate = (no_answer_count / total_queries) if total_queries > 0 else None

        # Avg eval scores
        scores_result = await db.execute(
            select(
                func.avg(EvalResult.groundedness),
                func.avg(EvalResult.retrieval_relevance),
                func.avg(EvalResult.citation_accuracy),
                func.avg(EvalResult.completeness),
                func.avg(EvalResult.overall_score),
                func.avg(cast(EvalResult.hallucination, Float)),
                func.count(EvalResult.eval_id).filter(EvalResult.flagged == True),  # noqa: E712
            )
            .join(Query, Query.query_id == EvalResult.query_id)
            .where(Query.created_at > since)
        )
        row = scores_result.one_or_none()

        if row and row[0] is not None:
            avg_g, avg_rr, avg_ca, avg_co, avg_overall, hall_rate, flagged_count = row
        else:
            avg_g = avg_rr = avg_ca = avg_co = avg_overall = hall_rate = None
            flagged_count = 0

        return EvalSummaryResponse(
            period_days=period_days,
            total_queries=total_queries,
            avg_groundedness=float(avg_g) if avg_g is not None else None,
            avg_retrieval_relevance=float(avg_rr) if avg_rr is not None else None,
            avg_citation_accuracy=float(avg_ca) if avg_ca is not None else None,
            avg_completeness=float(avg_co) if avg_co is not None else None,
            avg_overall_score=float(avg_overall) if avg_overall is not None else None,
            hallucination_rate=float(hall_rate) if hall_rate is not None else None,
            no_answer_rate=no_answer_rate,
            flagged_count=int(flagged_count) if flagged_count else 0,
            cache_hit_rate=None,
            request_id=request.state.request_id,
        )
    except Exception:
        # DB unavailable or schema missing — return zeroed stub
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
    """Return flagged queries pending human review."""
    try:
        # Build base query
        stmt = (
            select(
                EvalResult.eval_id,
                EvalResult.query_id,
                EvalResult.flag_reason,
                EvalResult.groundedness,
                EvalResult.overall_score,
                EvalResult.hallucination,
                EvalResult.reviewed,
                EvalResult.completed_at,
                Query.query_text,
            )
            .join(Query, Query.query_id == EvalResult.query_id)
            .where(EvalResult.flagged == True)  # noqa: E712
            .order_by(EvalResult.completed_at.desc())
        )

        if reviewed is not None:
            stmt = stmt.where(EvalResult.reviewed == reviewed)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        stmt = stmt.limit(limit).offset(offset)
        rows_result = await db.execute(stmt)
        rows = rows_result.all()

        items = [
            FlaggedQueryItem(
                eval_id=r.eval_id,
                query_id=r.query_id,
                query_text=r.query_text,
                flag_reason=r.flag_reason,
                groundedness=r.groundedness,
                overall_score=r.overall_score,
                hallucination=r.hallucination,
                reviewed=r.reviewed,
                completed_at=r.completed_at,
            )
            for r in rows
        ]

        return FlaggedQueriesResponse(
            items=items,
            total=total,
            request_id=request.state.request_id,
        )
    except Exception:
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
    """Mark a flagged query as reviewed (or un-reviewed)."""
    # Fetch existing row
    result = await db.execute(
        select(EvalResult).where(EvalResult.eval_id == eval_id)
    )
    eval_row = result.scalar_one_or_none()
    if eval_row is None:
        raise HTTPException(status_code=404, detail=f"eval_id {eval_id!r} not found")

    # Update reviewed flag
    await db.execute(
        update(EvalResult)
        .where(EvalResult.eval_id == eval_id)
        .values(reviewed=body.reviewed)
    )
    await db.commit()

    # Fetch query_text for response
    q_result = await db.execute(
        select(Query.query_text).where(Query.query_id == eval_row.query_id)
    )
    query_text = q_result.scalar_one_or_none()

    return FlaggedQueryItem(
        eval_id=eval_row.eval_id,
        query_id=eval_row.query_id,
        query_text=query_text,
        flag_reason=eval_row.flag_reason,
        groundedness=eval_row.groundedness,
        overall_score=eval_row.overall_score,
        hallucination=eval_row.hallucination,
        reviewed=body.reviewed,
        completed_at=eval_row.completed_at,
        request_id=request.state.request_id,
    )

