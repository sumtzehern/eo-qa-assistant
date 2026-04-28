# EdgeOne QA Assistant

## What This Is

A production-grade, enterprise B2B Retrieval-Augmented Generation (RAG) question-answering assistant for Tencent EdgeOne CDN. Helps customers and internal pre-sales engineers get accurate, cited answers about EdgeOne configuration, API usage, CLI reference, and Akamai-to-EdgeOne migration — without digging through documentation manually.

Built as a portfolio project targeting Anthropic-level production standards.

## Core Value

**Trustworthy, cited technical answers about EdgeOne — fast.**

Every answer references the exact source chunk. No hallucinations go undetected. Every response is scored and logged.

## Who Uses It

- **To B customers** — EdgeOne enterprise customers asking configuration and debugging questions via a web interface
- **Internal pre-sales engineers** — SA team members needing quick answers during customer calls
- **Admin/ops team** — Monitoring eval quality, managing ingestion sources, reviewing flagged responses

## What It Does

### User-Facing (Chat UI)
- Split-panel chat interface (60% answer / 40% sources panel)
- Inline Perplexity-style citations `[1][2]` with source cards
- Confidence score badge per response
- Follow-up question suggestions
- EN/中文 language toggle (English primary)
- Conversation history

### Admin Dashboard
- Real-time eval metrics (groundedness, hallucination rate, cache hit rate)
- Flagged queries review queue
- Source health monitoring
- Ingestion job management
- 7-day trend charts

### Backend Intelligence
- Hybrid search (BM25 + dense vector)
- Semantic cache (embedding similarity, not string match)
- Query expansion for ambiguous queries
- Per-call async eval scoring (non-blocking)
- Human-in-the-loop review queue for low-score responses

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 + Tailwind CSS |
| Backend API | FastAPI (Python) |
| Vector DB | Chroma (dev) / Tencent VectorDB (prod) |
| Embeddings | OpenAI text-embedding-3-small or Hunyuan |
| LLM | Claude (Anthropic) via API |
| Reranker | Cohere Rerank or cross-encoder |
| Metadata Store | PostgreSQL |
| Cache | Redis |
| Job Queue | Redis Queue (RQ) |
| Eval | Custom LLM-as-judge (Claude Haiku) + LangSmith |

## Key Constraints

- **English first, Mandarin second** — UI defaults to EN, toggle to 中文
- **Citations are non-negotiable** — every answer must cite source chunks
- **Eval on every call** — async but mandatory, never skipped
- **No auto-ingestion of new sources** — human review required before adding new sources
- **Cache invalidation tied to ingestion** — retrieval cache clears when source re-ingested
- **Semantic cache** — uses embedding similarity for cache lookups, not string match

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Split-panel UI (Option C) | Shows RAG retrieval quality visibly; follow-up suggestions show context awareness | Approved |
| FastAPI backend | Consistent with existing teo-psa Python skills | Approved |
| Next.js 14 frontend | SSR + streaming support; best for AI chat UIs | Approved |
| Standard granularity | 5-8 phases, balanced — right size for this scope | Approved |
| YOLO execution mode | Solo dev, high trust, fast iteration | Approved |
| Sharding by language/tenant, not topic | Topic sharding causes cross-shard misses on multi-topic queries | Decided |
| Human-in-the-loop for source additions | Auto-ingestion risks degrading quality if eval scores are wrong | Decided |

## Requirements

### Validated
(None yet — ship to validate)

### Active

**Ingestion**
- [ ] Crawl EdgeOne public docs (HTML, weekly schedule)
- [ ] Crawl tccli CLI reference
- [ ] Crawl EdgeOne API reference (HTML + OpenAPI JSON)
- [ ] Ingest internal knowledge base JSON files
- [ ] Chunk by source type (section-based HTML, per-endpoint API, per-command CLI)
- [ ] Embed chunks and store in vector DB with metadata
- [ ] Diff-based re-embedding (skip unchanged content_hash)
- [ ] Ingestion job queue with status tracking

**Retrieval & Generation**
- [ ] Query embedding
- [ ] Hybrid search (BM25 + dense vector)
- [ ] Rerank top-20 → select top-5
- [ ] Query expansion (optional, for ambiguous queries)
- [ ] Semantic cache (embedding similarity lookup)
- [ ] Claude generation with inline citations
- [ ] Streaming response support

**API**
- [ ] POST /query — answer + citations + eval_id
- [ ] GET /query/{id}/eval — retrieve scores
- [ ] GET /sources — source health + freshness
- [ ] POST /ingestion/trigger — admin re-ingest
- [ ] GET /eval/summary — aggregate stats
- [ ] API key auth (internal) + JWT (customer portal)
- [ ] Rate limiting (200/60/10 rpm by tier)

**Frontend — Chat UI**
- [ ] Split-panel layout (60% answer / 40% sources)
- [ ] Streaming response rendering
- [ ] Inline citation badges [1][2]
- [ ] Source cards with title, URL, relevance score bar
- [ ] Confidence score badge
- [ ] Follow-up question suggestions (3 pills)
- [ ] EN/中文 toggle (English default)
- [ ] Conversation history

**Frontend — Admin Dashboard**
- [ ] 5 metric cards with trend deltas
- [ ] Eval scores line chart (7-day)
- [ ] Flagged queries table with Review/Resolved pills
- [ ] Source health cards (Healthy/Failed)
- [ ] Ingestion job status

**Eval Pipeline**
- [ ] Per-call async eval (groundedness, retrieval relevance, citation accuracy, completeness, hallucination flag)
- [ ] Auto-flag rules (groundedness < 0.7, hallucination detected, overall < 0.65)
- [ ] Human review queue for flagged responses
- [ ] Enterprise eval suite (142 golden questions, CI-triggered)

**CI/CD**
- [ ] GitHub Actions PR gate (lint + typecheck)
- [ ] pytest backend test suite
- [ ] Vitest/Playwright frontend tests
- [ ] Docker Compose local dev setup

### Out of Scope (v1)

- Multi-tenant SaaS (single tenant for now)
- Auto-ingestion of new sources based on low eval scores (human review required)
- Topic-based sharding (use metadata filters instead)
- Mobile UI
- Slack/Teams integration

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-27 after initialization*
