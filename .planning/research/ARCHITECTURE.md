# ARCHITECTURE.md — Research: Enterprise RAG QA Assistant Architecture

## System Overview

Two independent planes with shared infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│  INGESTION PLANE (Offline, Async)                           │
│                                                             │
│  Sources → Crawler → Chunker → Embedder → Vector DB        │
│               ↓                               ↓            │
│           PostgreSQL (chunk metadata)    Redis (cache       │
│                                          invalidation)      │
└─────────────────────────────────────────────────────────────┘
                           ↕ shared infra
┌─────────────────────────────────────────────────────────────┐
│  QUERY PLANE (Real-time, Stateless)                         │
│                                                             │
│  Request → Cache? → Embed → BM25+Dense → Rerank →          │
│  Prompt → Claude → Response + Citations → Async Eval       │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### 1. Ingestion Service (`/ingestion/`)
**Owns:** Source crawling, chunking, embedding, vector DB writes
**Does NOT own:** Query processing, caching, eval

```
IngestionWorker
├── SourceCrawler        # crawl4ai + BeautifulSoup4, per source type
├── Chunker              # Source-type-aware chunking strategies
├── Embedder             # OpenAI / Hunyuan embedding calls
├── VectorWriter         # Writes chunks + vectors to Chroma/Qdrant
├── MetadataWriter       # Writes chunk metadata to PostgreSQL
└── CacheInvalidator     # Signals Redis to clear stale cache entries
```

Input: Source config (URL, type, schedule)
Output: Chunks in vector DB + metadata in PostgreSQL
Triggered by: Cron job OR POST /ingestion/trigger (admin API)
Run in: Celery/RQ worker (NOT in the FastAPI app process)

---

### 2. Query Service (`/api/`)
**Owns:** Query processing pipeline, cache, response formatting
**Does NOT own:** Ingestion, source management, eval scoring

```
QueryPipeline
├── CacheLayer           # Check semantic cache first
├── QueryExpander        # Optional: Claude Haiku generates sub-queries
├── QueryEmbedder        # Embed query → vector
├── HybridSearcher       # BM25 (rank_bm25) + Dense (vector DB) → merge via RRF
├── Reranker             # Cohere Rerank or cross-encoder → top-5
├── PromptAssembler      # System prompt + chunks + query → Claude prompt
├── Generator            # Claude API call with streaming
├── CitationResolver     # Map [1][2] to source metadata
└── EvalDispatcher       # Fire-and-forget async eval task
```

Input: POST /query request
Output: Streamed response + citations + eval_id
Stateless: No session state in the query path (session history in PostgreSQL if needed)

---

### 3. Eval Service (`/eval/`)
**Owns:** Per-call scoring, flag logic, enterprise eval suite
**Does NOT own:** Query processing, ingestion

```
EvalService
├── PerCallEvaluator     # Claude Haiku judge: groundedness, relevance, citations, completeness
├── HallucinationDetector # Claims outside retrieved chunks?
├── FlagRouter           # Auto-flag rules → review queue
└── EvalStore            # PostgreSQL: eval logs, scores, flags
```

Input: query_id, answer, retrieved_chunks (passed from QueryPipeline)
Output: Eval scores written to PostgreSQL
Runs: Async Celery task, ~500ms, non-blocking to user response

---

### 4. Admin API (`/admin/`)
**Owns:** Source management, eval summary, ingestion controls
**Does NOT own:** Query processing

Routes:
- GET /sources — Source health from PostgreSQL
- POST /ingestion/trigger — Enqueue ingestion job
- GET /ingestion/jobs/{id} — Job status from Celery/RQ
- GET /eval/summary — Aggregate scores from PostgreSQL
- GET /eval/flagged — Flagged query review queue
- PATCH /eval/flagged/{id} — Mark reviewed

---

### 5. Semantic Cache (`/cache/`)

```
SemanticCache
├── EmbeddingCache       # Redis HSET: query_hash → vector (exact match lookup)
├── SemanticLookup       # Redis: cosine similarity on recent query vectors
├── ResponseCache        # Redis: query_hash → full response JSON
└── InvalidationHandler  # On source re-ingest: clear affected cache entries
```

**Critical design:** Cache uses embedding similarity for lookup, NOT string match.
- Store last ~1000 query vectors in Redis sorted set
- On new query: embed → cosine sim against cache → threshold 0.95 = hit
- On cache hit: return cached response (sub-100ms)
- On re-ingest: flush all cache entries tagged with that source_id

---

## Data Flow: Query Path (Detailed)

```
1. POST /query arrives at FastAPI
         ↓
2. CacheLayer: embed query → cosine sim lookup in Redis
   → HIT: return cached response immediately (< 100ms)
   → MISS: continue
         ↓
3. QueryExpander (optional): Claude Haiku → 2-3 sub-queries
         ↓
4. HybridSearcher:
   a. BM25: rank_bm25 against in-memory BM25 index → top-20
   b. Dense: vector DB ANN search → top-20
   c. RRF fusion: merge + deduplicate → top-30
         ↓
5. Reranker: Cohere Rerank top-30 → score → select top-5
         ↓
6. PromptAssembler: system_prompt + chunks[1-5] + query → Claude prompt
         ↓
7. Generator: Claude API stream → token-by-token SSE to client
         ↓
8. CitationResolver: parse [1][2] markers → map to source metadata
         ↓
9. Store: full response + citations → PostgreSQL (query_id)
         ↓
10. EvalDispatcher: fire-and-forget → Celery task → async eval
         ↓
11. Response complete: {answer, citations, confidence, eval_id}
```

---

## Data Flow: Ingestion Path

```
1. Trigger: cron OR POST /ingestion/trigger
         ↓
2. Enqueue: Celery/RQ job per source
         ↓
3. Crawler: fetch pages → raw HTML/Markdown/JSON
         ↓
4. ContentHasher: SHA-256 of content → compare vs stored hash
   → UNCHANGED: skip (cost saving)
   → CHANGED or NEW: continue
         ↓
5. Chunker: source-type-aware strategy
   - HTML: split by h2/h3, ~800 tokens, 100-token overlap
   - API ref: one chunk per endpoint
   - CLI ref: one chunk per command
   - JSON: one chunk per top-level entry
         ↓
6. Embedder: batch embed → OpenAI / Hunyuan API
         ↓
7. VectorWriter: upsert chunks to Chroma/Qdrant
         ↓
8. MetadataWriter: upsert chunk metadata to PostgreSQL
         ↓
9. CacheInvalidator: Redis DEL all entries tagged source_id
         ↓
10. JobUpdate: mark job complete in PostgreSQL
```

---

## Data Model

### PostgreSQL: chunks table
```sql
CREATE TABLE chunks (
  chunk_id      TEXT PRIMARY KEY,   -- SHA-256 of content
  source_id     TEXT NOT NULL,
  source_url    TEXT,
  page_title    TEXT,
  section_title TEXT,
  content       TEXT NOT NULL,
  content_hash  TEXT NOT NULL,
  token_count   INT,
  language      TEXT DEFAULT 'en',
  last_crawled  TIMESTAMPTZ,
  last_modified TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### PostgreSQL: eval_results table
```sql
CREATE TABLE eval_results (
  eval_id              TEXT PRIMARY KEY,
  query_id             TEXT NOT NULL,
  groundedness         FLOAT,
  retrieval_relevance  FLOAT,
  citation_accuracy    FLOAT,
  completeness         FLOAT,
  hallucination        BOOLEAN,
  overall_score        FLOAT,
  flagged              BOOLEAN DEFAULT FALSE,
  flag_reason          TEXT,
  reviewed             BOOLEAN DEFAULT FALSE,
  completed_at         TIMESTAMPTZ
);
```

### PostgreSQL: queries table
```sql
CREATE TABLE queries (
  query_id    TEXT PRIMARY KEY,
  query_text  TEXT NOT NULL,
  answer      TEXT,
  citations   JSONB,
  confidence  FLOAT,
  no_answer   BOOLEAN,
  latency_ms  INT,
  caller_id   TEXT,
  session_id  TEXT,
  language    TEXT DEFAULT 'en',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Streaming: FastAPI → Next.js

**Protocol:** Server-Sent Events (SSE) — unidirectional stream, no WebSocket overhead

```python
# FastAPI
from fastapi.responses import StreamingResponse

async def generate_stream(query: str):
    async with anthropic_client.messages.stream(...) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'token': text})}\n\n"
    yield f"data: {json.dumps({'done': True, 'citations': citations})}\n\n"

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    return StreamingResponse(generate_stream(request.query), media_type="text/event-stream")
```

```typescript
// Next.js App Router
const response = await fetch('/api/query', { method: 'POST', body: ... })
const reader = response.body!.getReader()
// Read tokens, update React state incrementally
```

---

## Build Order (Phase Dependencies)

```
Phase 1: Infrastructure (Docker Compose, PostgreSQL, Redis, Chroma)
         ↓
Phase 2a: Ingestion pipeline (crawlers → chunker → embedder → vector DB) [parallel]
Phase 2b: Backend API skeleton (FastAPI routes, auth, rate limiting)       [parallel]
Phase 2c: Frontend shell (Next.js, layout, chat UI components)             [parallel]
         ↓
Phase 3: Wire query pipeline (embed → search → rerank → Claude → stream to frontend)
         ↓
Phase 4: Eval pipeline (per-call scoring, flag routing, admin dashboard)
         ↓
Phase 5: Semantic cache (Redis cosine sim + invalidation)
         ↓
Phase 6: Enterprise eval suite (golden questions, CI integration)
```

Phase 2a/2b/2c are independent and can run in parallel.
Phase 3 requires all of Phase 2.
Phase 5 requires Phase 3 (needs working query pipeline to cache).

---

## Admin Dashboard Architecture

Same FastAPI backend — admin routes under `/admin/` prefix with separate admin API key auth.

Next.js serves both chat UI and admin dashboard as separate routes:
- `/` — Chat UI
- `/admin` — Admin dashboard (protected by admin JWT check)

Admin dashboard polls `/admin/eval/summary` every 30s for live metrics. No WebSocket needed — polling is fine for dashboard refresh rates.
