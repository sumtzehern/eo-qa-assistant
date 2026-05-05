# CODEBUDDY.md

Guidance for CodeBuddy Code (and any LLM coding agent) working in this repository.

---

## Project Status

**Implementation complete.** All 6 phases are built and committed. This is a production-grade
enterprise RAG QA assistant for Tencent EdgeOne CDN.

Git log (newest first):
```
4c87a38  Phase 6 — enterprise eval suite + CI gate
0342302  Phase 5 — semantic cache hardening + source-scoped invalidation
a1bbbdf  Phase 4 — eval pipeline, live admin dashboard
bbd2ad0  Phase 3 — live end-to-end query pipeline wired
0384c70  Wave 1 complete — ingestion pipeline, API skeleton, frontend shell
60e135c  Phase 1 — complete infrastructure scaffold
```

---

## Coding Rules (follow always)

### General
- No LangChain, no LangGraph, no LangSmith wrappers. Use direct SDK calls:
  `openai`, `anthropic`, `cohere`, `qdrant-client`, `asyncpg`.
- Python 3.11+. Use `async`/`await` throughout — no blocking I/O on the event loop.
- All settings via `pydantic-settings` (`backend/api/settings.py`,
  `backend/ingestion/settings.py`). Never hardcode secrets or URLs.
- `ruff` for linting, `mypy --strict` for type checking. Both must pass clean.
- Raise `HTTPException` with explicit status codes. Never return bare 500s from routes.

### FastAPI conventions
- Route files live in `backend/api/routes/`. One file per resource group.
- No business logic in route files — delegate to pipeline modules or ingestion modules.
- Auth via `backend/api/middleware/auth.py` (API key) and JWT. Never skip auth on
  non-health endpoints.
- Rate limiting via `backend/api/middleware/rate_limit.py`.

### Database
- ORM: SQLAlchemy 2.x async (`backend/db/models.py`, `backend/db/session.py`).
- Session factory: `async_session_factory` (not `AsyncSessionLocal`).
- All schema changes via Alembic migrations in `backend/db/alembic/versions/`.
  Never mutate tables directly.
- Use `func.avg()`, `func.count()` for aggregates — not Python-side loops.

### Redis / Cache
- Client always initialized with `decode_responses=True`. No byte-string handling needed.
- Key schema (never deviate):
  - `cache:query:{query_id}` — main semantic cache entry
  - `cache:src_idx:{source_id}:{query_id}` — secondary index for source-scoped invalidation
  - `cache:stats` — HASH with `hits` / `misses` counters
- Use `scan_iter()` for all key iteration. Never use `KEYS` (blocks Redis event loop).

### Streaming (SSE)
- The `/v1/query` route returns `StreamingResponse` (SSE).
- The inner `_stream()` generator must **never raise** — wrap in `try/except`, emit
  `{"done": true, "no_answer": true}` on any error. Never let exceptions escape to 500.
- `proxy_buffering off` and `proxy_read_timeout 120s` are set in `nginx/nginx.conf`
  for this route. Do not change the route path without updating nginx.

### Eval (fire-and-forget)
- Scoring runs via `asyncio.create_task(dispatch_eval(...))` — non-blocking.
- Scorer: `backend/api/eval/scorer.py` using `claude-haiku-4-5`.
- Dispatcher: `backend/api/eval/dispatcher.py` — owns its own DB session, full try/except.
- Auto-flag thresholds: `groundedness < 0.7`, `overall_score < 0.65`, `hallucination = True`.
- Never change flag thresholds without updating `eval/run_eval.py` CI gate thresholds too.

### RRF Fusion (hybrid search)
- Formula: `score += 1 / (60 + rank + 1)` for both dense and sparse legs.
- Constant `_RRF_K = 60` in `backend/api/pipeline/searcher.py`.
- `_rrf_fusion()` is public (no underscore suppression) for unit testing.

### Frontend
- Next.js 14 App Router. Files under `frontend/app/` and `frontend/components/`.
- Dark enterprise UI: background `#111111`, flat, no gradients.
- Tailwind CSS only — no inline styles.
- API calls via `frontend/lib/api.ts`. Never call `fetch()` directly from components.
- Chat UI: `frontend/components/chat/`. Admin dashboard: `frontend/components/admin/`.

### Testing
- Backend tests: `pytest` in `backend/tests/`. Use `fakeredis` for Redis, mock Qdrant
  and LLM clients. Fixture: `qdrant_available` (session-scoped, skips live Qdrant tests).
- Frontend tests: Vitest in `frontend/`. Mock `frontend/lib/api.ts`.
- CI runs `ruff`, `mypy --strict`, `pytest --cov`, ESLint, `tsc`, Vitest on every push.
- Eval gate runs on PRs to `main` only (`eval/run_eval.py --limit 20`).

---

## Repository Layout

```
edgeone-qa-assistant/
├── backend/
│   ├── api/
│   │   ├── eval/
│   │   │   ├── dispatcher.py       # fire-and-forget eval task
│   │   │   └── scorer.py           # Claude Haiku judge, 5-dim scoring
│   │   ├── middleware/
│   │   │   ├── auth.py             # API key + JWT verification
│   │   │   └── rate_limit.py       # per-key rate limiting
│   │   ├── pipeline/
│   │   │   ├── cache.py            # semantic cache (Redis cosine, 0.92 threshold)
│   │   │   ├── expander.py         # query expansion via Claude Haiku
│   │   │   ├── generator.py        # Claude streaming + citation extraction
│   │   │   ├── reranker.py         # Cohere Rerank v3 (soft import, fallback)
│   │   │   └── searcher.py         # HybridSearcher: ANN + BM25 → RRF fusion
│   │   ├── routes/
│   │   │   ├── cache.py            # DELETE /v1/cache/invalidate (admin)
│   │   │   ├── eval.py             # GET /v1/eval/summary, flagged queries
│   │   │   ├── ingestion.py        # POST /v1/ingestion/trigger, GET /v1/ingestion/jobs/{id}
│   │   │   ├── query.py            # POST /v1/query (SSE streaming)
│   │   │   └── sources.py          # GET /v1/sources
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   └── query.py
│   │   ├── main.py                 # FastAPI app, router registration, lifespan
│   │   └── settings.py             # Pydantic settings (reads from env)
│   ├── db/
│   │   ├── alembic/versions/       # migration scripts
│   │   ├── models.py               # SQLAlchemy ORM: Query, EvalResult, Source, IngestionJob
│   │   └── session.py              # async_session_factory, engine
│   ├── ingestion/
│   │   ├── chunker.py              # source-type-aware chunker (HTML/API/CLI/JSON/MD)
│   │   ├── config.py               # source definitions (URLs, types, schedules)
│   │   ├── crawler.py              # crawl4ai HTML crawler
│   │   ├── embedder.py             # Embedder class (OpenAI text-embedding-3-small)
│   │   ├── invalidator.py          # cache invalidation on re-ingestion
│   │   ├── settings.py             # ingestion-specific settings
│   │   ├── worker.py               # RQ job entrypoint
│   │   └── writer.py               # Qdrant + PostgreSQL writer
│   ├── tests/
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_cache.py       # 14 tests (fakeredis)
│   │   │   ├── test_eval.py        # 8 tests
│   │   │   ├── test_pipeline.py    # RRF, citations, cache hit/miss, Qdrant degradation
│   │   │   └── test_routes.py
│   │   ├── ingestion/
│   │   │   └── test_chunker.py
│   │   └── conftest.py             # qdrant_available fixture
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pyproject.toml              # ruff + mypy config
│   └── requirements.txt
├── eval/
│   ├── golden_questions.json       # 142 curated questions (8 categories)
│   ├── run_eval.py                 # CLI eval runner, SSE parser, threshold gates
│   ├── results/                    # gitignored JSON outputs
│   └── README.md
├── frontend/
│   ├── app/
│   │   ├── admin/page.tsx          # admin dashboard page
│   │   ├── layout.tsx
│   │   └── page.tsx                # main chat page
│   ├── components/
│   │   ├── admin/
│   │   │   ├── EvalChart.tsx       # Recharts score trends
│   │   │   ├── FlaggedTable.tsx    # flagged queries + inline review toggle
│   │   │   ├── MetricCard.tsx
│   │   │   └── SourceHealthCard.tsx
│   │   └── chat/
│   │       ├── AssistantMessage.tsx # renders [1][2] citation links
│   │       ├── ChatInput.tsx
│   │       ├── ChatInterface.tsx
│   │       └── ChatPanel.tsx
│   ├── lib/
│   │   └── api.ts                  # all API calls (query, eval, sources, cache)
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                  # prod reverse proxy (SSE-safe, TLS, gzip)
├── .github/
│   └── workflows/ci.yml            # backend-ci + frontend-ci + eval-gate jobs
├── docker-compose.yml              # local dev (bind mounts, ports exposed)
├── docker-compose.prod.yml         # production (built images, nginx entry, mem limits)
├── .env.example                    # all required env vars documented
└── .gitignore
```

---

## Tech Stack (actual, as built)

| Component      | Implementation                                   |
|----------------|--------------------------------------------------|
| API            | FastAPI 0.115, Python 3.11, uvicorn              |
| Vector DB      | Qdrant (local dev + CI), Tencent VectorDB (prod) |
| Embeddings     | OpenAI `text-embedding-3-small`                  |
| LLM            | Claude Sonnet (generation), Claude Haiku (eval + expand) |
| Reranker       | Cohere Rerank v3 (`cohere.AsyncClientV2`)        |
| Metadata Store | PostgreSQL 15 + asyncpg + SQLAlchemy 2.x async   |
| Job Queue      | Redis Queue (RQ)                                 |
| Cache          | Redis 7 — semantic cosine cache (0.92 threshold) |
| Frontend       | Next.js 14 App Router, Tailwind CSS, Recharts    |
| Testing        | pytest + fakeredis (backend), Vitest (frontend)  |
| Lint / Types   | ruff, mypy --strict (backend), ESLint + tsc (frontend) |
| CI             | GitHub Actions — 3 jobs: backend-ci, frontend-ci, eval-gate |

---

## API Endpoints (live)

**Base URL (local dev):** `http://localhost:8000/v1`

| Method | Endpoint                     | Auth          | Notes                                      |
|--------|------------------------------|---------------|--------------------------------------------|
| POST   | `/query`                     | X-API-Key     | SSE stream, semantic cache, async eval     |
| GET    | `/query/{query_id}/eval`     | X-API-Key     | Retrieve eval scores for a query           |
| GET    | `/sources`                   | X-API-Key     | List ingested sources + freshness          |
| POST   | `/ingestion/trigger`         | X-API-Key     | Enqueue RQ ingestion job                   |
| GET    | `/ingestion/jobs/{job_id}`   | X-API-Key     | Poll job status                            |
| GET    | `/eval/summary`              | X-Admin-Key   | Aggregate scores + cache hit rate          |
| GET    | `/eval/flagged`              | X-Admin-Key   | Flagged queries pending review             |
| PATCH  | `/eval/{eval_id}/review`     | X-Admin-Key   | Mark flagged query as reviewed             |
| DELETE | `/cache/invalidate`          | X-Admin-Key   | Purge cache entries (per-source or full)   |
| GET    | `/health`                    | None          | Liveness probe                             |

---

## Eval System

### Per-call (async, every query)
- Judge model: `claude-haiku-4-5`
- Dimensions: groundedness, retrieval_relevance, citation_accuracy, completeness, hallucination
- Overall score: mean of first 4 dimensions
- Auto-flag if: `groundedness < 0.7` OR `overall_score < 0.65` OR `hallucination = True`

### Enterprise eval suite (CI gate, PRs to main only)
- 142 golden questions across 8 categories:
  `api_usage(20)`, `billing(10)`, `configuration(25)`, `edge_functions(20)`,
  `migration(15)`, `performance(20)`, `security(20)`, `troubleshooting(12)`
- CI samples 20 questions (`--limit 20`) to keep gate fast
- Pass gates: overall > 0.85, hallucination rate < 5%, no-answer rate < 15%
- Results uploaded as GitHub Actions artifact (30-day retention)

### CI secrets required (GitHub repo settings)
```
ANTHROPIC_API_KEY
OPENAI_API_KEY
COHERE_API_KEY
```
Without these, eval gate skips LLM scoring but still enforces no-answer rate.

---

## Key Algorithms

### Reciprocal Rank Fusion (RRF)
```python
# backend/api/pipeline/searcher.py
_RRF_K = 60
score += 1.0 / (_RRF_K + rank + 1)  # applied to both dense and sparse legs
```

### Semantic Cache Lookup
```python
# backend/api/pipeline/cache.py
threshold = 0.92  # cosine similarity
# Key: cache:query:{query_id}
# Secondary index: cache:src_idx:{source_id}:{query_id}  (TTL 86400)
# Stats: HINCRBY cache:stats hits/misses
```

### Cache Invalidation on Re-ingestion
```python
# backend/ingestion/invalidator.py
async for idx_key in redis.scan_iter(f"cache:src_idx:{source_id}:*"):
    query_id = await redis.get(idx_key)
    await redis.delete(f"cache:query:{query_id}")
    await redis.delete(idx_key)
```

---

## Environment Variables

See `.env.example` for the full list. Required for the system to start:

```
ANTHROPIC_API_KEY      # Claude generation + eval judge
OPENAI_API_KEY         # text-embedding-3-small
COHERE_API_KEY         # Cohere Rerank v3
DATABASE_URL           # postgresql+asyncpg://...
REDIS_URL              # redis://...
QDRANT_URL             # http://...
INTERNAL_API_KEY       # service-to-service auth
ADMIN_API_KEY          # admin dashboard auth
JWT_SECRET             # customer portal JWT signing
POSTGRES_PASSWORD      # used in docker-compose.prod.yml
```

---

## Running Locally

```bash
cp .env.example .env          # fill in all keys
docker compose up             # starts all 6 services
docker compose exec api alembic upgrade head   # first time only
```

## Running in Production

```bash
# on the server after git clone + .env filled
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

Replace `your-domain.com` in `nginx/nginx.conf` (lines 15, 23) and
`docker-compose.prod.yml` (line 102) before deploying.

---

## Related Repositories

Knowledge base JSONs sourced from `teo-psa-aiagents`:
- Path: `/Users/wesleysum/Projects/teo-psa-aiagents/accelerationConversionAgent/knowledge-base/`
- Files: `mappings.json`, `error-patterns.json`, `edge-functions.json`,
  `ignore-list.json`, `source-index.json`
