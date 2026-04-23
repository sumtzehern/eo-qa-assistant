# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

---

## Project Status

**Design phase only** — no implementation code exists yet. All files under `design/` are specification documents. The implementation will use Python (FastAPI).

## Design Documents

| File | Purpose |
|------|---------|
| `design/01-architecture.md` | System architecture, two-plane design, tech stack |
| `design/02-ingestion-pipeline.md` | Offline ingestion: crawling, chunking, embedding, scheduling |
| `design/03-rag-retrieval.md` | Query-time retrieval: hybrid search, reranking, generation, citations |
| `design/04-eval-framework.md` | Quality evaluation: per-call scoring, enterprise eval suite |
| `design/05-api-design.md` | API endpoints, request/response schemas, auth, rate limits |

## Architecture

The system has **two independent planes**:

### Ingestion Plane (Offline, Async)
- Runs on schedule (weekly) or webhook-triggered on git commit
- Crawls sources → chunks → embeds → stores in vector DB
- Uses diff-based re-embedding (skip if `content_hash` unchanged)
- Job queue: Redis Queue (RQ) or Celery

### Query Plane (Real-time, Stateless)
1. Embed query
2. Hybrid search (vector similarity + BM25)
3. Rerank top-20 → select top-5
4. Assemble prompt + call Claude
5. Return answer with Perplexity-style inline citations `[1][2]`
6. Fire-and-forget async eval (non-blocking)

### Key Sources
- EdgeOne public docs (crawl4ai, HTML)
- Tencent CLI reference (tccli)
- EdgeOne API reference (HTML + OpenAPI JSON)
- Internal migration guides (Markdown/Confluence)
- Knowledge base JSON files from `teo-psa-aiagents` repo
- Edge Function code examples (Git crawler)

### Chunking Strategy (varies by source type)
- HTML docs: split by `<h2>`/`<h3>`, ~800 tokens, 100-token overlap
- API reference: one chunk per endpoint
- CLI reference: one chunk per command
- JSON knowledge files: one chunk per top-level entry
- Markdown: split by `##` headings

## Tech Stack

| Component | Choice |
|-----------|--------|
| API | FastAPI (Python) |
| Vector DB | Tencent VectorDB (prod) / Chroma (local dev) |
| Embeddings | OpenAI `text-embedding-3-small` or Hunyuan (bilingual) |
| LLM | Claude (Anthropic) |
| Reranker | Cohere Rerank or cross-encoder |
| Metadata Store | PostgreSQL |
| Job Queue | Redis Queue (RQ) or Celery |
| Eval | Custom + LangSmith/Braintrust |

## API Overview

**Base URL:** `https://api.edgeone-qa.internal/v1`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/query` | Submit question → answer + citations + eval |
| GET | `/query/{query_id}/eval` | Retrieve eval scores |
| GET | `/sources` | List ingested sources & freshness |
| POST | `/ingestion/trigger` | Trigger re-ingestion (admin) |
| GET | `/ingestion/jobs/{job_id}` | Check ingestion job status |
| GET | `/eval/summary` | Aggregate eval stats |

**Auth:** API key (`X-API-Key`) for internal, JWT for customer portal.

## Evaluation System

Every API response is scored asynchronously on:
- **Groundedness** — claims supported by retrieved chunks
- **Retrieval Relevance** — chunks relevant to query
- **Citation Accuracy** — citations map to claims
- **Completeness** — all parts of query addressed
- **Hallucination Flag** — claims outside retrieved chunks

**Auto-flag thresholds:** groundedness < 0.7, hallucination detected, overall score < 0.65.

**Enterprise eval suite:** 142 curated golden questions, run before deploying prompt/model changes. Targets: >0.85 overall, <5% hallucination rate, <15% no-answer rate.

## Related Repositories

Knowledge base JSON files are sourced from the `teo-psa-aiagents` repo:
- `/Users/wesleysum/Projects/teo-psa-aiagents/accelerationConversionAgent/knowledge-base/`
- Key files: `mappings.json`, `error-patterns.json`, `edge-functions.json`, `ignore-list.json`, `source-index.json`
