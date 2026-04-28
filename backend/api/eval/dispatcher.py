"""Fire-and-forget eval dispatcher — persists query + scores to PostgreSQL."""

import logging
import uuid
from datetime import datetime, timezone

import anthropic

from backend.api.eval.scorer import EvalScorer
from backend.db.models import EvalResult, Query
from backend.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def dispatch_eval(
    query_id: str,
    query_text: str,
    answer: str,
    citations: list[dict],
    confidence: float,
    no_answer: bool,
    latency_ms: int,
    caller_id: str,
    session_id: str | None,
    language: str,
    anthropic_api_key: str | None,
) -> None:
    """Persist query row and eval scores. Called as asyncio.create_task()."""
    try:
        # Own a fresh DB session — cannot reuse the request session (already closed)
        async with async_session_factory() as db:
            # 1. Persist Query row
            query_row = Query(
                query_id=query_id,
                query_text=query_text,
                answer=answer,
                citations=citations,
                confidence=confidence,
                no_answer=no_answer,
                latency_ms=latency_ms,
                caller_id=caller_id,
                session_id=session_id,
                language=language,
            )
            db.add(query_row)
            await db.flush()

            # 2. Run eval scorer (skip if no answer or no API key)
            if no_answer or not anthropic_api_key or not answer:
                await db.commit()
                return

            client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
            scorer = EvalScorer(anthropic_client=client)
            scores = await scorer.score(query=query_text, answer=answer, citations=citations)

            # 3. Persist EvalResult row
            eval_row = EvalResult(
                eval_id=str(uuid.uuid4()),
                query_id=query_id,
                groundedness=scores.groundedness,
                retrieval_relevance=scores.retrieval_relevance,
                citation_accuracy=scores.citation_accuracy,
                completeness=scores.completeness,
                hallucination=scores.hallucination,
                overall_score=scores.overall_score,
                flagged=scores.flagged,
                flag_reason=scores.flag_reason,
                reviewed=False,
                completed_at=datetime.now(tz=timezone.utc),
            )
            db.add(eval_row)
            await db.commit()

    except Exception:
        logger.exception("dispatch_eval failed for query_id=%s", query_id)
