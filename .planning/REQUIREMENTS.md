# REQUIREMENTS.md — EdgeOne QA Assistant

*Last updated: 2026-04-27*

---

## v1 Requirements

### INGEST — Ingestion Pipeline

- [ ] **INGEST-01** — Operator can trigger a full crawl of EdgeOne public docs (HTML) via POST /ingestion/trigger and see job status
- [ ] **INGEST-02** — Operator can trigger crawl of tccli CLI reference; each CLI command produces exactly one chunk
- [ ] **INGEST-03** — Operator can trigger crawl of EdgeOne API reference (HTML + OpenAPI JSON); each endpoint produces exactly one chunk
- [ ] **INGEST-04** — Operator can ingest internal knowledge base JSON files from `teo-psa-aiagents`; each top-level entry produces one chunk
- [ ] **INGEST-05** — HTML docs are chunked by h2/h3 section boundaries at ~800 tokens with 100-token overlap
- [ ] **INGEST-06** — Each chunk is embedded and stored in vector DB with metadata: source_id, source_url, page_title, section_title, language, content_hash, token_count
- [ ] **INGEST-07** — On re-ingest, chunks whose content_hash is unchanged are skipped (no re-embedding API call)
- [ ] **INGEST-08** — Each ingestion job has a trackable status (queued / running / complete / failed) visible via GET /ingestion/jobs/{job_id}
- [ ] **INGEST-09** — Ingestion runs in a separate worker process (Celery/RQ) so query latency is not affected during ingestion
- [ ] **INGEST-10** — On re-ingest of a source, all Redis cache entries tagged with that source_id are invalidated

### QUERY — Retrieval & Generation Pipeline

- [ ] **QUERY-01** — User can submit a natural language question in English or Chinese and receive a streamed answer
- [ ] **QUERY-02** — System returns first token to client within 3 seconds of receiving request (p95)
- [ ] **QUERY-03** — Every answer includes inline citation markers `[1][2]` that map to specific retrieved source chunks
- [ ] **QUERY-04** — When the system cannot answer confidently, it returns an explicit "I don't know" rather than hallucinating
- [ ] **QUERY-05** — Query pipeline performs hybrid search: BM25 (rank_bm25) + dense vector ANN, fused via RRF, top-30 candidates
- [ ] **QUERY-06** — Top-30 candidates are reranked (Cohere Rerank or cross-encoder); top-5 are passed to the prompt
- [ ] **QUERY-07** — Optional query expansion: system generates 2-3 sub-queries via Claude Haiku for ambiguous queries
- [ ] **QUERY-08** — System checks semantic cache before retrieval; a cache hit returns response in under 100ms
- [ ] **QUERY-09** — Each query response includes a confidence score (0.0–1.0)
- [ ] **QUERY-10** — Conversation history is maintained per session; prior turns are available in subsequent queries

### API — Backend API Endpoints

- [ ] **API-01** — POST /query returns: answer (streamed SSE), citations array, confidence score, eval_id
- [ ] **API-02** — GET /query/{query_id}/eval returns per-call eval scores for a completed query
- [ ] **API-03** — GET /sources returns list of all ingestion sources with last_crawled timestamp and health status
- [ ] **API-04** — POST /ingestion/trigger enqueues an ingestion job and returns job_id (admin only)
- [ ] **API-05** — GET /ingestion/jobs/{job_id} returns job status and error details if failed
- [ ] **API-06** — GET /eval/summary returns aggregate eval stats (groundedness, hallucination rate, cache hit rate, 7-day trend)
- [ ] **API-07** — GET /admin/eval/flagged returns paginated list of flagged queries awaiting review
- [ ] **API-08** — PATCH /admin/eval/flagged/{id} marks a flagged query as reviewed
- [ ] **API-09** — All public endpoints require a valid API key via `X-API-Key` header; invalid key returns 401
- [ ] **API-10** — Rate limiting enforced: 200 rpm (standard), 60 rpm (free), 10 rpm (trial); exceeded returns 429
- [ ] **API-11** — Customer portal endpoints support JWT auth in addition to API key
- [ ] **API-12** — All API responses follow a consistent JSON envelope schema with request_id and error codes

### FRONT — Frontend Chat UI

- [ ] **FRONT-01** — User sees a split-panel layout: 60% answer panel on left, 40% sources panel on right
- [ ] **FRONT-02** — Answer streams token-by-token in the answer panel as it is generated
- [ ] **FRONT-03** — Inline citation markers `[1][2]` are rendered as clickable badges that highlight the corresponding source card
- [ ] **FRONT-04** — Source panel shows cards with: page title, section title, source URL, relevance score bar, and snippet preview
- [ ] **FRONT-05** — Each answer displays a confidence score badge (color-coded: green ≥ 0.8, yellow 0.6–0.8, red < 0.6)
- [ ] **FRONT-06** — Three follow-up question suggestion pills appear below each answer; clicking one submits that question
- [ ] **FRONT-07** — UI defaults to English; user can toggle to 中文 via a language switcher; preference persists for the session
- [ ] **FRONT-08** — Conversation history is visible in a left sidebar or scroll history; user can start a new session
- [ ] **FRONT-09** — Code blocks in answers render in monospace with a copy-to-clipboard button
- [ ] **FRONT-10** — Chat input supports multi-line entry and submit on Ctrl+Enter or button click

### ADMIN — Admin Dashboard

- [ ] **ADMIN-01** — Admin can view 5 metric cards: avg groundedness, hallucination rate, cache hit rate, queries/day, avg latency
- [ ] **ADMIN-02** — Admin can see a 7-day eval scores line chart showing groundedness and hallucination rate trends
- [ ] **ADMIN-03** — Admin can see a flagged queries table with query text, flag reason, and Review/Resolved status pills
- [ ] **ADMIN-04** — Admin can mark a flagged query as reviewed directly from the dashboard table
- [ ] **ADMIN-05** — Admin can see source health cards showing each source's last_crawled timestamp and Healthy/Failed status
- [ ] **ADMIN-06** — Admin can trigger a re-ingestion job from the source health card and see job status update in real time
- [ ] **ADMIN-07** — Admin dashboard is accessible at /admin and protected by admin JWT check

### EVAL — Evaluation Pipeline

- [ ] **EVAL-01** — Every query response triggers an async eval task (non-blocking to user; fire-and-forget)
- [ ] **EVAL-02** — Per-call eval scores: groundedness, retrieval_relevance, citation_accuracy, completeness, hallucination flag
- [ ] **EVAL-03** — Responses are auto-flagged when: groundedness < 0.7, hallucination = true, or overall_score < 0.65
- [ ] **EVAL-04** — Flagged responses are added to the human review queue with flag_reason populated
- [ ] **EVAL-05** — All eval scores and flags are persisted to PostgreSQL eval_results table
- [ ] **EVAL-06** — Enterprise eval suite: 142 curated golden Q&A pairs can be run via CLI or CI trigger
- [ ] **EVAL-07** — Enterprise eval suite reports pass/fail against targets: >0.85 overall, <5% hallucination, <15% no-answer

### INFRA — Infrastructure & CI/CD

- [ ] **INFRA-01** — `docker compose up` starts the full local dev stack: FastAPI, Next.js, PostgreSQL, Redis, Qdrant, RQ worker
- [ ] **INFRA-02** — PostgreSQL schema is managed via Alembic migrations; `alembic upgrade head` applies all migrations cleanly
- [ ] **INFRA-03** — GitHub Actions PR gate runs: ruff lint, mypy typecheck, pytest backend suite on every PR
- [ ] **INFRA-04** — GitHub Actions PR gate runs: ESLint, TypeScript typecheck, Vitest unit tests on every PR
- [ ] **INFRA-05** — GitHub Actions optionally runs Playwright e2e tests against a test environment
- [ ] **INFRA-06** — All secrets (API keys, DB passwords) are managed via environment variables; no secrets in code or `.env` committed

---

## v2 Requirements (Deferred)

These are validated as desirable but intentionally deferred to avoid scope creep in v1.

- **Multi-tenant SaaS** — Tenant isolation at DB and vector DB layer; per-tenant rate limits and eval visibility
- **Voting / thumbs up on answers** — User feedback signals wired into eval; useful but complex training loop
- **Answer export (PDF/Word)** — Useful for enterprise reports but not core Q&A value
- **Slack / Teams integration** — Bot that responds to @mentions in internal channels
- **Voice input / TTS output** — Not an enterprise documentation workflow
- **Document upload by users** — Opens RAG poisoning attack surface; requires moderation pipeline first
- **Auto-learn from flagged queries** — Automatically ingest new sources when eval scores degrade; deferred until eval scoring is calibrated
- **Chat personas / tone settings** — Enterprise users want consistent professional answers
- **Source editing by admin** — Free-text modification of ingested chunks; breaks audit trail without versioning
- **Mobile-optimized UI** — Split-panel layout doesn't translate to mobile without redesign
- **LangSmith / Braintrust integration** — Full observability platform integration; manual eval sufficient for v1
- **pgvector as vector DB** — Consolidate on PostgreSQL for lower ops overhead; revisit if Chroma causes issues
- **Version-aware metadata filtering** — Filter by EdgeOne API version in query; needs version tagging in chunks first
- **Source freshness alerts** — Email/Slack alert when source not re-ingested in 14+ days
- **Ingestion webhook on git commit** — Auto-trigger ingestion when teo-psa-aiagents repo changes

---

## Out of Scope

| Item | Reason |
|------|--------|
| **Topic-based vector shard selection** | Causes cross-shard misses on multi-topic queries; metadata filters solve this without the downside |
| **WebSocket for streaming** | SSE is unidirectional, simpler, no connection state; WebSocket overhead not justified |
| **LangChain / LlamaIndex** | Abstraction overhead; direct library calls are easier to debug and more stable |
| **Auto-ingestion without human approval** | Eval scores are imperfect; auto-ingestion based on them degrades quality; human review queue is the right pattern |
| **Free-form user content upload** | RAG poisoning risk; moderation pipeline not in scope |
| **Consumer UX features** (share, vote, persona) | This is enterprise B2B; reliability and audit trail over novelty |
| **Voting / feedback loops to training** | Requires MLOps pipeline; not a v1 need |
| **Mobile UI** | Split-panel UX doesn't work on mobile without a redesign pass |
