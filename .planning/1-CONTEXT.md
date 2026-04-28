# 1-CONTEXT.md — Phase 1: Infrastructure & CI/CD

*Created: 2026-04-27*

---

## Phase Goal

Stand up the complete local dev stack and CI/CD pipeline so every subsequent phase has a stable environment to build on.

---

## Locked Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo layout | **Monorepo** | Single repo with `/backend`, `/frontend`, `/ingestion` subdirs. One `docker-compose.yml` at root. |
| Worker queue | **RQ (Redis Queue)** | Simpler than Celery, Python-native, Redis-backed. Sufficient for ingestion + eval tasks at this scale. |
| Vector DB (dev) | **Qdrant** (Docker) | Better filtering/payload indexes than Chroma; closer to Tencent VectorDB API surface. Qdrant also runs as a Docker container. |
| CI gate | **Full gate** | lint (ruff + ESLint) + typecheck (mypy + tsc strict) + tests (pytest + Vitest) on every PR |
| Port layout | **Standard** | FastAPI :8000, Next.js :3000, PostgreSQL :5432, Redis :6379, Qdrant :6333, RQ worker (no port) |

---

## Directory Structure

```
edgeone-qa-assistant/
├── backend/                  # FastAPI app
│   ├── api/                  # Routes, middleware, schemas
│   ├── ingestion/            # Crawler, chunker, embedder, writer, worker
│   ├── eval/                 # Evaluator, detector, router, worker
│   ├── pipeline/             # Query pipeline (search, rerank, generate, cache)
│   ├── db/                   # SQLAlchemy models, alembic migrations
│   ├── tests/                # pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Next.js 14 app
│   ├── app/                  # App Router pages
│   ├── components/           # Chat UI + Admin components
│   ├── lib/                  # stream.ts, i18n.ts, api.ts
│   ├── store/                # Zustand stores
│   ├── tests/                # Vitest unit + Playwright e2e
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml        # Root compose file: all 6 services
├── .env.example              # All required env vars documented
├── .github/
│   └── workflows/
│       ├── ci.yml            # PR gate: lint + typecheck + tests
│       └── eval.yml          # Enterprise eval suite (Phase 6)
├── .planning/                # GSD planning artifacts
└── design/                   # Design docs + UI mockups
```

---

## Docker Compose Services

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| `api` | `./backend/Dockerfile` | 8000 | FastAPI + uvicorn |
| `frontend` | `./frontend/Dockerfile` | 3000 | Next.js dev server |
| `db` | `postgres:15` | 5432 | PostgreSQL |
| `redis` | `redis:7-alpine` | 6379 | Cache + RQ broker |
| `qdrant` | `qdrant/qdrant` | 6333 | Vector DB |
| `worker` | `./backend/Dockerfile` | — | RQ worker process |

All services in the same Docker network. Health checks on `db`, `redis`, `qdrant`.

---

## Environment Variables (.env.example)

```
# Anthropic
ANTHROPIC_API_KEY=

# OpenAI (embeddings)
OPENAI_API_KEY=

# Cohere (reranker)
COHERE_API_KEY=

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/edgeone_qa

# Redis
REDIS_URL=redis://redis:6379/0

# Qdrant
QDRANT_URL=http://qdrant:6333

# Auth
INTERNAL_API_KEY=
ADMIN_API_KEY=
JWT_SECRET=

# Tencent (optional, for Hunyuan embeddings)
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
```

---

## GitHub Actions CI (`.github/workflows/ci.yml`)

Triggers: `push` to any branch + `pull_request` to `main`

Jobs (run in parallel where possible):
1. **backend-ci**: `ruff check` + `mypy --strict` + `pytest backend/tests/ --cov=backend`
2. **frontend-ci**: `eslint` + `tsc --noEmit` + `vitest run`

Both jobs must pass for PR merge.

---

## PostgreSQL Schema (Alembic Migrations)

Four tables in initial migration:
- `chunks` — ingested content with metadata
- `queries` — query log with answer + citations
- `eval_results` — per-call eval scores + flags
- `ingestion_jobs` — job status tracking

Schema defined in ARCHITECTURE.md research file.

---

## Notes for Downstream Agents

- **Phase 2a/2b/2c** all run in parallel — they each need the docker-compose stack running
- **RQ worker** shares the same Dockerfile as the `api` service; started with `rq worker` entrypoint
- **Qdrant** collection setup happens in Phase 2a (ingestion pipeline); Phase 1 just starts the service
- **Alembic** migrations run via `alembic upgrade head` inside the `api` container on startup
- **No LangChain/LlamaIndex** — direct library calls only throughout all phases
