# SUMMARY.md — Research Synthesis: EdgeOne QA Assistant

## Recommended Stack

**Backend:** FastAPI 0.115 + Python 3.11 + asyncpg + SQLAlchemy 2.x + Alembic  
**Frontend:** Next.js 14 (App Router) + Tailwind CSS 3.4 + Zustand + Recharts  
**Vector DB:** Chroma (dev) → Qdrant or Tencent VectorDB (prod)  
**Embeddings:** OpenAI `text-embedding-3-small` (EN) + Hunyuan (ZH fallback)  
**LLM:** `claude-3-5-sonnet-20241022` (generation) + `claude-3-haiku` (eval judge)  
**Reranker:** Cohere Rerank v3 (prod) / cross-encoder (dev)  
**Cache:** Redis (semantic cache + retrieval cache + embedding cache)  
**Queue:** Celery or RQ (ingestion + eval workers — separate from API process)  
**Search:** `rank_bm25` + vector ANN → Reciprocal Rank Fusion  
**No RAG framework:** Write pipeline directly. LangChain/LlamaIndex add abstraction overhead.

---

## Table Stakes Features (Must Ship v1)

1. Streaming response with SSE (< 3s to first token)
2. Inline citations `[1][2]` with source URL + snippet
3. Confidence score per response
4. "I don't know" handling (no hallucination preferred over wrong answer)
5. Conversation history (session continuity)
6. EN primary / 中文 toggle
7. API key auth + rate limiting
8. Admin dashboard with eval metrics + source health

---

## Differentiators Worth Building (v1)

1. **Hybrid search** — BM25 + dense via RRF fusion (exact CDN term matching + semantic)
2. **Reranking** — Cohere Rerank; top differentiator vs naive RAG
3. **Semantic cache** — Embedding similarity lookup, not string match; 40-70% expected hit rate
4. **Per-call async eval** — Every response scored; hallucination flag; human review queue
5. **Split-panel UI** — Sources always visible; relevance score bars
6. **Follow-up suggestions** — 3 suggested questions per answer

---

## Critical Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Ingestion worker separate from API process | Prevents ingestion from degrading query latency |
| Semantic cache with invalidation on re-ingest | Stale cache is worse than no cache |
| 5 chunks max in prompt (not 15-20) | More chunks hurts answer quality; reranker enforces quality |
| Human-in-the-loop for source additions | Auto-ingestion based on flawed eval scores degrades quality |
| SSE not WebSocket for streaming | Unidirectional; simpler; no connection state |
| No LangChain/LlamaIndex | Direct library calls; easier to debug; stable |
| pgvector as fallback vector DB option | If avoiding extra services in prod, PostgreSQL extension works |

---

## Watch Out For

1. **Chunking destroys context** — Chunk by heading structure, not token count
2. **Stale cache after re-ingest** — Tag cache entries with source_id; DEL on re-ingest
3. **Citation index mismatch** — Parse citations server-side; include citation_map in response
4. **Streaming partial citations** — Stream tokens first; send citation metadata as final SSE event
5. **Ingestion blocking queries** — Ingestion MUST be in separate worker process from day one
6. **LLM-as-judge overconfidence** — Calibrate Haiku judge against hand-scored samples
7. **Auto-remediation from bad eval** — Never auto-ingest; always human review queue
8. **Redis eviction policy** — Set `allkeys-lru` before going to production

---

## Build Order

```
Phase 1  → Infra (Docker Compose, PostgreSQL, Redis, Chroma, GitHub Actions CI)
Phase 2a → Ingestion pipeline [parallel with 2b, 2c]
Phase 2b → FastAPI skeleton + auth + rate limiting [parallel]
Phase 2c → Next.js frontend shell + chat UI [parallel]
Phase 3  → Wire query pipeline end-to-end (search → rerank → Claude → stream)
Phase 4  → Eval pipeline + admin dashboard
Phase 5  → Semantic cache + invalidation
Phase 6  → Enterprise eval suite + CI integration
```
