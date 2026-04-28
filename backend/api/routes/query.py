"""Query routes: POST /query and GET /query/{query_id}/eval."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

import anthropic
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_api_key
from backend.api.middleware.rate_limit import check_rate_limit
from backend.api.pipeline.cache import CacheLayer
from backend.api.pipeline.expander import QueryExpander
from backend.api.pipeline.generator import ClaudeGenerator
from backend.api.pipeline.reranker import CohereReranker
from backend.api.pipeline.searcher import HybridSearcher
from backend.api.schemas.common import EvalResponse
from backend.api.schemas.query import CitationItem, QueryRequest, QueryResponse
from backend.api.settings import settings
from backend.db.session import get_db
from backend.ingestion.embedder import Embedder

logger = logging.getLogger(__name__)

router = APIRouter()


async def _dispatch_eval(query_id: str, answer: str, citations: list) -> None:
    """Fire-and-forget eval task stub. Phase 4 wires real scoring."""
    logger.debug("Eval dispatch queued for query_id=%s", query_id)


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    request: Request,
    body: QueryRequest,
    tier: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Accept a natural-language query and return a streaming SSE response."""
    await check_rate_limit(body.caller_id, tier)

    query_id = str(uuid.uuid4())
    request_id: str = request.state.request_id
    start_ms = time.time()
    language = body.options.language

    # ── Instantiate pipeline deps ────────────────────────────────────────────
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
    embedder = Embedder()
    embedder.client = openai_client

    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY or None)
    qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
    reranker = CohereReranker(api_key=settings.COHERE_API_KEY or "")
    generator = ClaudeGenerator(anthropic_client=anthropic_client)
    searcher = HybridSearcher(qdrant_client=qdrant_client)

    cache: CacheLayer | None = None
    redis_client = getattr(getattr(request, "app", None), "state", None)
    if redis_client:
        redis_client = getattr(redis_client, "redis", None)
    if redis_client:
        cache = CacheLayer(redis_client=redis_client, embedder=embedder)

    async def _stream():
        nonlocal query_id, request_id, start_ms

        try:
            # 1. Embed query
            query_embedding = (await embedder.embed_batch([body.query]))[0]

            # 2. Cache lookup
            if cache:
                hit = await cache.get(query_embedding, query_id)
                if hit:
                    for token in hit.answer.split():
                        yield f"data: {json.dumps({'token': ' ' + token})}\n\n"
                        await asyncio.sleep(0)
                    latency_ms = int((time.time() - start_ms) * 1000)
                    citations_dicts = [
                        c if isinstance(c, dict) else vars(c) for c in hit.citations
                    ]
                    done_payload = {
                        "done": True,
                        "query_id": query_id,
                        "answer": hit.answer,
                        "citations": citations_dicts,
                        "confidence": hit.confidence,
                        "no_answer": False,
                        "latency_ms": latency_ms,
                        "eval_status": "pending",
                        "eval_id": None,
                        "request_id": request_id,
                        "cached": True,
                    }
                    yield f"data: {json.dumps(done_payload)}\n\n"
                    return

            # 3. Query expansion
            effective_query = body.query
            if body.options.query_expansion:
                expander = QueryExpander(anthropic_client=anthropic_client)
                effective_query = await expander.expand(body.query)

            # 4. Hybrid search
            source_filter = body.options.source_filter or None
            search_results = await searcher.search(
                query_embedding=query_embedding,
                query_text=effective_query,
                source_filter=source_filter,
                top_k=20,
            )

            # 5. Rerank
            top_chunks = await reranker.rerank(
                query=effective_query,
                candidates=search_results,
                top_n=body.options.max_citations,
            )

            # 6. Stream Claude response
            full_answer_parts: list[str] = []
            async for token in generator.stream(effective_query, top_chunks, language):
                full_answer_parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

            full_answer = "".join(full_answer_parts)

            # 7. Extract citations
            cleaned_answer, citations = generator.extract_citations(full_answer, top_chunks)
            no_answer = cleaned_answer == ""
            confidence = 0.0 if no_answer else (
                top_chunks[0].score if top_chunks else 0.0
            )

            citations_dicts = [
                {
                    "index": c.index,
                    "title": c.title,
                    "url": c.url,
                    "section": c.section,
                    "snippet": c.snippet,
                }
                for c in citations
            ]

            # 8. Fire-and-forget eval
            asyncio.create_task(_dispatch_eval(query_id, cleaned_answer, citations_dicts))

            # 9. Cache store
            if cache:
                await cache.set(
                    query_id=query_id,
                    source_ids=[c.source_id for c in top_chunks],
                    embedding=query_embedding,
                    answer=cleaned_answer,
                    citations=citations_dicts,
                    confidence=confidence,
                )

            latency_ms = int((time.time() - start_ms) * 1000)
            done_payload = {
                "done": True,
                "query_id": query_id,
                "answer": cleaned_answer,
                "citations": citations_dicts,
                "confidence": confidence,
                "no_answer": no_answer,
                "latency_ms": latency_ms,
                "eval_status": "pending",
                "eval_id": None,
                "request_id": request_id,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception:
            logger.exception("Pipeline error for query_id=%s", query_id)
            latency_ms = int((time.time() - start_ms) * 1000)
            yield f"data: {json.dumps({'done': True, 'no_answer': True, 'answer': '', 'citations': [], 'confidence': 0.0, 'query_id': query_id, 'latency_ms': latency_ms, 'eval_status': 'pending', 'eval_id': None, 'request_id': request_id})}\n\n"

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
    """Return eval scores for a past query. Phase 4 wires real eval scores."""
    return EvalResponse(
        eval_id=None,
        query_id=query_id,
        status="pending",
        request_id=request.state.request_id,
    )
