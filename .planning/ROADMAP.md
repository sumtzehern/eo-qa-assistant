# ROADMAP.md — EdgeOne QA Assistant

*Last updated: 2026-04-27*

---

## Overview

```
Phase 1  ──── Infrastructure & CI/CD
              ↓
Phase 2a ──┐
Phase 2b ──┤  WAVE 1 (parallel)
Phase 2c ──┘
              ↓
Phase 3  ──── Integration (wire end-to-end query pipeline)  ←── WAVE 2
              ↓
Phase 4  ──── Eval Pipeline + Admin Dashboard               ←── WAVE 3
              ↓
Phase 5  ──── Semantic Cache + Cache Invalidation           ←── WAVE 4
              ↓
Phase 6  ──── Enterprise Eval Suite + CI Integration        ←── WAVE 5
```

---

## Phase 1 — Infrastructure & CI/CD

**Wave:** Foundation (sequential prerequisite for all phases)

**Goal:** Stand up the complete local dev stack and CI/CD pipeline so every subsequent phase has a stable environment to build on.

**Requirements Covered:**
- INFRA-01 — Docker Compose local dev stack
- INFRA-02 — PostgreSQL + Alembic migrations
- INFRA-03 — GitHub Actions backend CI (lint, typecheck, pytest)
- INFRA-04 — GitHub Actions frontend CI (ESLint, TypeScript, Vitest)
- INFRA-06 — Secrets management via environment variables

**Deliverables:**
- `docker-compose.yml` starts: FastAPI (placeholder), Next.js (placeholder), PostgreSQL, Redis, Chroma, Celery worker
- `alembic/` with initial migrations for `chunks`, `queries`, `eval_results`, `ingestion_jobs` tables
- `.github/workflows/ci.yml` runs lint + typecheck + pytest on PR
- `.env.example` with all required variables; `.env` in `.gitignore`

**Success Criteria:**
1. `docker compose up` starts all 6 services with no errors; `docker compose ps` shows all healthy
2. `alembic upgrade head` applies all migrations against a fresh PostgreSQL instance with no errors
3. A GitHub Actions run on a test PR shows green for lint, typecheck, and a placeholder pytest suite
4. No API keys or secrets appear in any committed file; all are read from environment

---

## Phase 2a — Ingestion Pipeline

**Wave:** WAVE 1 (parallel with 2b and 2c)

**Goal:** Build the complete offline ingestion pipeline — crawl sources, chunk by type, embed, write to vector DB and PostgreSQL, with diff-based skipping and cache invalidation.

**Requirements Covered:**
- INGEST-01 — Crawl EdgeOne public docs (HTML, crawl4ai)
- INGEST-02 — Crawl tccli CLI reference (one chunk per command)
- INGEST-03 — Crawl EdgeOne API reference HTML + OpenAPI JSON (one chunk per endpoint)
- INGEST-04 — Ingest internal KB JSON files (one chunk per top-level entry)
- INGEST-05 — Source-type-aware chunking strategy
- INGEST-06 — Embed + store with full metadata in vector DB
- INGEST-07 — Diff-based re-embedding (skip unchanged content_hash)
- INGEST-08 — Ingestion job status tracking in PostgreSQL
- INGEST-09 — Ingestion runs in separate Celery/RQ worker process
- INGEST-10 — Redis cache invalidation on source re-ingest
- API-04 — POST /ingestion/trigger endpoint
- API-05 — GET /ingestion/jobs/{job_id} endpoint

**Deliverables:**
- `ingestion/crawler.py` — crawl4ai + BeautifulSoup4 crawlers per source type
- `ingestion/chunker.py` — source-type-aware chunking (HTML by h2/h3, API per endpoint, CLI per command, JSON per entry)
- `ingestion/embedder.py` — OpenAI text-embedding-3-small (EN) + Hunyuan fallback (ZH)
- `ingestion/writer.py` — VectorWriter (Chroma) + MetadataWriter (PostgreSQL)
- `ingestion/worker.py` — Celery/RQ task definitions; content_hash diff logic
- `ingestion/invalidator.py` — Redis DEL on source_id cache entries

**Success Criteria:**
1. Running the ingestion pipeline against all 4 source types produces chunks in Chroma and metadata rows in PostgreSQL with correct fields
2. Re-running ingestion on an unchanged source skips embedding (verified by zero OpenAI API calls)
3. `GET /ingestion/jobs/{job_id}` returns correct status transitions: queued → running → complete
4. Ingesting a source during a simulated query load does not increase query p95 latency (worker isolation confirmed)

---

## Phase 2b — Backend API Skeleton

**Wave:** WAVE 1 (parallel with 2a and 2c)

**Goal:** Build the FastAPI application with all route stubs, auth middleware, rate limiting, and the query pipeline skeleton (no live LLM yet — returns mock responses).

**Requirements Covered:**
- API-01 — POST /query (stub: returns mock SSE stream)
- API-02 — GET /query/{query_id}/eval
- API-03 — GET /sources
- API-06 — GET /eval/summary
- API-07 — GET /admin/eval/flagged
- API-08 — PATCH /admin/eval/flagged/{id}
- API-09 — API key auth via X-API-Key header
- API-10 — Rate limiting (200/60/10 rpm by tier)
- API-11 — JWT auth for customer portal endpoints
- API-12 — Consistent JSON envelope schema with request_id

**Deliverables:**
- `api/main.py` — FastAPI app factory with all routers registered
- `api/routes/query.py` — POST /query stub with SSE streaming scaffold
- `api/routes/sources.py` — GET /sources, POST /ingestion/trigger, GET /ingestion/jobs/{id}
- `api/routes/eval.py` — GET /eval/summary, GET/PATCH /admin/eval/flagged
- `api/middleware/auth.py` — API key validation + JWT verification
- `api/middleware/rate_limit.py` — Redis-backed sliding window rate limiter
- `api/schemas/` — Pydantic request/response models for all endpoints

**Success Criteria:**
1. All routes return correct HTTP status codes (200/201/401/429/422) for valid and invalid inputs
2. An invalid API key returns 401; a valid key at rate limit returns 429 with Retry-After header
3. `pytest api/` passes with ≥ 80% coverage on route handlers and auth middleware
4. POST /query returns a valid SSE stream (mock tokens) that the Next.js client can consume

---

## Phase 2c — Frontend Shell

**Wave:** WAVE 1 (parallel with 2a and 2b)

**Goal:** Build the complete Next.js UI shell — split-panel chat layout, streaming rendering, source cards, confidence badge, follow-up pills, EN/ZH toggle, and admin dashboard scaffolding (no live data yet).

**Requirements Covered:**
- FRONT-01 — Split-panel layout (60% answer / 40% sources)
- FRONT-02 — Streaming token-by-token answer rendering
- FRONT-03 — Inline citation badges [1][2] with source card highlight
- FRONT-04 — Source cards (title, URL, relevance score bar, snippet)
- FRONT-05 — Confidence score badge (color-coded)
- FRONT-06 — Follow-up question suggestion pills (3 per answer)
- FRONT-07 — EN/中文 language toggle; session-persistent
- FRONT-08 — Conversation history sidebar + new session button
- FRONT-09 — Code block rendering with copy-to-clipboard button
- FRONT-10 — Multi-line chat input with Ctrl+Enter submit
- ADMIN-01 — Admin metric cards (layout + mock data)
- ADMIN-02 — 7-day eval line chart (Recharts + mock data)
- ADMIN-03 — Flagged queries table (layout + mock data)
- ADMIN-05 — Source health cards (layout + mock data)
- ADMIN-07 — /admin route protected by admin JWT check

**Deliverables:**
- `frontend/app/page.tsx` — Chat UI page with split-panel layout
- `frontend/components/chat/` — MessageBubble, CitationBadge, SourceCard, ConfidenceBadge, FollowUpPills, CodeBlock components
- `frontend/components/admin/` — MetricCard, EvalChart, FlaggedTable, SourceHealthCard components
- `frontend/app/admin/page.tsx` — Admin dashboard shell
- `frontend/lib/stream.ts` — SSE reader utility for streaming responses
- `frontend/lib/i18n.ts` — EN/ZH string tables + toggle hook
- `frontend/store/chat.ts` — Zustand store for conversation state

**Success Criteria:**
1. Chat UI renders with correct split-panel proportions on 1280px+ viewport; source panel is always visible
2. Clicking a citation badge [1] scrolls to and highlights the corresponding source card in the right panel
3. Language toggle switches all UI strings to Chinese and back; preference survives page navigation within session
4. All 5 admin metric cards, chart, flagged table, and source health cards render with mock data; no TypeScript errors; Vitest passes

---

## Phase 3 — Integration

**Wave:** WAVE 2 (requires Phase 1 + all of Phase 2)

**Goal:** Wire the complete end-to-end query pipeline — embed → hybrid search → rerank → Claude → SSE stream → frontend with live citations — producing a fully working QA demo.

**Requirements Covered:**
- QUERY-01 — Natural language query → streamed answer
- QUERY-02 — First token within 3 seconds (p95)
- QUERY-03 — Inline citations mapping to retrieved chunks
- QUERY-04 — "I don't know" handling
- QUERY-05 — Hybrid search (BM25 + dense, RRF fusion, top-30)
- QUERY-06 — Reranking (Cohere or cross-encoder, top-5)
- QUERY-07 — Optional query expansion (Claude Haiku sub-queries)
- QUERY-09 — Confidence score per response
- QUERY-10 — Session conversation history
- EVAL-01 — Async eval dispatch on every query (fire-and-forget)

**Deliverables:**
- `api/pipeline/cache.py` — CacheLayer (semantic lookup placeholder wired to Redis miss for now)
- `api/pipeline/expander.py` — QueryExpander (Claude Haiku sub-query generation)
- `api/pipeline/searcher.py` — HybridSearcher (BM25 + Chroma ANN → RRF)
- `api/pipeline/reranker.py` — Reranker (Cohere API call or cross-encoder)
- `api/pipeline/generator.py` — Claude API streaming + citation parsing
- `api/pipeline/assembler.py` — PromptAssembler (system prompt + chunks + query)
- `api/pipeline/eval_dispatcher.py` — Fire-and-forget Celery eval task dispatch
- Updated `api/routes/query.py` — Full live pipeline replacing mock stub

**Success Criteria:**
1. `POST /query` with a real EdgeOne question returns a streamed answer with ≥ 1 inline citation backed by an ingested chunk
2. First token arrives at the Next.js client within 3s measured from request send (p95 over 20 manual tests)
3. Query for an out-of-scope question returns a response containing explicit "I don't know" language with no fabricated answer
4. GET /query/{query_id}/eval returns a non-null eval_id within 5 seconds of query completion (async eval dispatched)

---

## Phase 4 — Eval Pipeline + Admin Dashboard

**Wave:** WAVE 3 (requires Phase 3)

**Goal:** Build the complete async eval scoring pipeline (Claude Haiku judge) and wire the admin dashboard to live data.

**Requirements Covered:**
- EVAL-01 — Async eval on every query (confirmed working end-to-end)
- EVAL-02 — Per-call scores: groundedness, retrieval_relevance, citation_accuracy, completeness, hallucination flag
- EVAL-03 — Auto-flag rules (groundedness < 0.7, hallucination = true, overall < 0.65)
- EVAL-04 — Flagged responses added to human review queue with flag_reason
- EVAL-05 — Eval scores persisted to eval_results table
- ADMIN-01 — Admin metric cards wired to live GET /eval/summary
- ADMIN-02 — 7-day eval line chart wired to live data
- ADMIN-03 — Flagged queries table wired to live GET /admin/eval/flagged
- ADMIN-04 — Mark reviewed via PATCH /admin/eval/flagged/{id}
- ADMIN-05 — Source health cards wired to live GET /sources
- ADMIN-06 — Re-ingest trigger from source health card

**Deliverables:**
- `eval/evaluator.py` — PerCallEvaluator (Claude Haiku judge; 5 dimensions)
- `eval/detector.py` — HallucinationDetector (claims outside retrieved chunks)
- `eval/router.py` — FlagRouter (auto-flag threshold logic)
- `eval/worker.py` — Celery eval task consuming from eval queue
- Updated `frontend/app/admin/page.tsx` — Polls live API every 30s; all mock data replaced

**Success Criteria:**
1. Every query in PostgreSQL has a corresponding eval_result row within 10 seconds of query completion
2. A manually crafted response with a fabricated fact triggers hallucination = true and auto-flag = true
3. Admin dashboard shows live groundedness score and hallucination rate from the last 50 queries with no mock data
4. Clicking "Mark Reviewed" on a flagged query updates its status in PostgreSQL and reflects in the dashboard within 1 page refresh

---

## Phase 5 — Semantic Cache + Invalidation

**Wave:** WAVE 4 (requires Phase 3)

**Goal:** Implement Redis-based semantic cache with embedding-similarity lookup and source-aware invalidation on re-ingest.

**Requirements Covered:**
- QUERY-08 — Semantic cache hit returns response in < 100ms
- INGEST-10 — Redis cache invalidation on re-ingest (confirmed end-to-end)

**Deliverables:**
- `api/pipeline/cache.py` — Full SemanticCache implementation:
  - Store last ~1000 query vectors in Redis sorted set
  - On new query: embed → cosine similarity against cache → threshold 0.95 = HIT
  - On HIT: return cached response in < 100ms
  - On MISS: continue to full pipeline, write result to cache tagged with source_ids
- `ingestion/invalidator.py` — Updated to DEL all cache entries tagged with re-ingested source_id
- Cache hit rate metric surfaced in GET /eval/summary and admin dashboard ADMIN-01

**Success Criteria:**
1. A repeat query (exact text) returns a cached response in < 100ms (measured with curl timing)
2. A semantically equivalent query (paraphrase) above cosine similarity 0.95 also returns a cache hit
3. Re-ingesting a source clears all cache entries tagged with its source_id; subsequent queries to that source return fresh results
4. Cache hit rate is visible in the admin dashboard metric cards

---

## Phase 6 — Enterprise Eval Suite + CI Integration

**Wave:** WAVE 5 (requires Phase 4)

**Goal:** Build the 142-question golden eval suite with CI integration, regression detection, and pass/fail gates on model/prompt changes.

**Requirements Covered:**
- EVAL-06 — 142 curated golden Q&A pairs runnable via CLI or CI
- EVAL-07 — Pass/fail against targets: >0.85 overall, <5% hallucination, <15% no-answer
- INFRA-05 — Playwright e2e tests against test environment

**Deliverables:**
- `eval/golden/questions.json` — 142 curated (question, expected_answer, source_ids) golden pairs covering: EdgeOne config, API usage, CLI reference, Akamai migration, error codes
- `eval/suite.py` — CLI runner: `python -m eval.suite --env=staging` runs all 142 questions, scores with Claude Haiku judge, reports pass/fail
- `.github/workflows/eval.yml` — CI workflow triggered manually or on tag; runs eval suite against staging; fails build if targets not met
- `eval/report.py` — Generates eval run summary (overall score, hallucination rate, no-answer rate, per-question breakdown)
- Playwright e2e test: submit a question → verify answer renders with ≥ 1 citation and a confidence badge

**Success Criteria:**
1. `python -m eval.suite` runs all 142 questions without crashing; produces a JSON report with per-question scores
2. Eval suite correctly reports FAIL when a prompt change causes overall score to drop below 0.85
3. Eval CI workflow triggers on manual dispatch, runs to completion, and posts a summary comment to the triggering PR
4. Playwright e2e test passes: user submits a question, answer streams, citation badge [1] appears, source card is populated

---

## Requirement Coverage Matrix

| Phase | Requirements |
|-------|-------------|
| Phase 1 | INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-06 |
| Phase 2a | INGEST-01–10, API-04, API-05 |
| Phase 2b | API-01 (stub), API-02, API-03, API-06, API-07, API-08, API-09, API-10, API-11, API-12 |
| Phase 2c | FRONT-01–10, ADMIN-01 (mock), ADMIN-02 (mock), ADMIN-03 (mock), ADMIN-05 (mock), ADMIN-07 |
| Phase 3 | QUERY-01–07, QUERY-09–10, EVAL-01 (dispatch only) |
| Phase 4 | EVAL-01 (end-to-end), EVAL-02–05, ADMIN-01–06 (live) |
| Phase 5 | QUERY-08, INGEST-10 (end-to-end) |
| Phase 6 | EVAL-06, EVAL-07, INFRA-05 |

**Total v1 requirements: 56**
**Covered in roadmap: 56 (100%)**
