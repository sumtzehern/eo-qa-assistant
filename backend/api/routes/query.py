"""Query routes: POST /query and GET /query/{query_id}/eval."""

import json
import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_api_key
from backend.api.middleware.rate_limit import check_rate_limit
from backend.api.schemas.common import EvalResponse
from backend.api.schemas.query import QueryRequest, QueryResponse
from backend.db.session import get_db

router = APIRouter()

# Mock tokens returned by the stub while real pipeline is wired in Phase 3
_MOCK_ANSWER = (
    "EdgeOne is Tencent's global CDN and edge computing platform. "
    "It provides acceleration, security, and edge function capabilities. [1]"
)
_MOCK_CITATIONS = [
    {
        "index": 1,
        "title": "EdgeOne Overview",
        "url": "https://cloud.tencent.com/document/product/1552",
        "section": "Introduction",
        "snippet": "EdgeOne provides global CDN and edge computing services.",
    }
]


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    request: Request,
    body: QueryRequest,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Accept a natural-language query and return a streaming SSE response.

    Phase 2b: returns a mock SSE stream of tokens. Phase 3 wires the real
    embed → search → rerank → Claude pipeline.
    """
    await check_rate_limit(body.caller_id, tier)

    query_id = str(uuid.uuid4())
    request_id: str = request.state.request_id
    start_ms = time.time()

    async def _stream():
        tokens = _MOCK_ANSWER.split()
        for i, token in enumerate(tokens):
            chunk = token if i == 0 else " " + token
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            # Tiny yield to simulate async streaming without real I/O delay in tests
            import asyncio

            await asyncio.sleep(0)

        latency_ms = int((time.time() - start_ms) * 1000)
        done_payload = {
            "done": True,
            "query_id": query_id,
            "answer": _MOCK_ANSWER,
            "citations": _MOCK_CITATIONS,
            "confidence": 0.0,
            "no_answer": False,
            "latency_ms": latency_ms,
            "eval_status": "pending",
            "eval_id": None,
            "request_id": request_id,
        }
        yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Request-ID": request_id,
        },
    )


@router.get("/query/{query_id}/eval", response_model=EvalResponse)
async def get_query_eval(
    query_id: str,
    request: Request,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> EvalResponse:
    """Return eval scores for a past query.

    Phase 2b: returns a stub response. Phase 4 wires real eval scores.
    """
    return EvalResponse(
        eval_id=None,
        query_id=query_id,
        status="pending",
        request_id=request.state.request_id,
    )
