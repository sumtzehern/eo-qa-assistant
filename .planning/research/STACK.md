# STACK.md — Research: Standard 2025 Stack for Enterprise RAG QA Assistant

## Recommended Stack

### Backend API
| Component | Recommendation | Version | Confidence |
|-----------|---------------|---------|-----------|
| Framework | **FastAPI** | 0.115.x | HIGH — async-native, best Python streaming support, OpenAPI auto-docs |
| Python | 3.11+ | 3.11/3.12 | HIGH — 3.11 for stability, 3.12 for perf gains |
| ASGI Server | **uvicorn** + gunicorn | 0.30.x | HIGH |
| Task Queue | **Celery** or **RQ** | Celery 5.x | MEDIUM — Celery for complex DAGs, RQ for simplicity |

**NOT**: Flask (sync-only), Django (too heavy), LangServe (opinionated, harder to customize)

---

### Embeddings
| Choice | Recommendation | Notes |
|--------|---------------|-------|
| **Primary** | `text-embedding-3-small` (OpenAI) | Best cost/quality ratio for English; 1536-dim |
| **Bilingual fallback** | Hunyuan embedding (Tencent) | Better EN/ZH bilingual; required for Mandarin queries |
| **Local/offline** | `sentence-transformers/all-MiniLM-L6-v2` | Dev/testing only; lower quality |

**Confidence:** HIGH — `text-embedding-3-small` is the 2025 standard for production RAG.  
**NOT**: `text-embedding-ada-002` (deprecated), BGE models (good but operational complexity)

---

### Vector Database
| Choice | Use Case | Notes |
|--------|---------|-------|
| **Chroma** | Local dev | Zero-ops, runs in-process or as server, Python-native |
| **Qdrant** | Production (recommended upgrade path) | Better filtering, payload indexes, HNSW tuning, Rust-based (fast) |
| **Tencent VectorDB** | Production on Tencent Cloud | Ecosystem fit; required if data residency matters |
| **pgvector** | Lightweight production | Postgres extension; good if already running PG, avoids extra service |

**Recommendation:** Chroma for dev → Qdrant for prod (unless Tencent Cloud lock-in required, then VectorDB).  
**NOT**: Pinecone (expensive, US-only), Weaviate (heavy ops), Milvus (overkill for this scale)

---

### Hybrid Search (BM25 + Dense)
| Component | Library | Notes |
|-----------|---------|-------|
| BM25 | **rank_bm25** (Python) | Simple, fast, no infra needed |
| Dense | Vector DB native ANN search | Built into Chroma/Qdrant |
| Fusion | **Reciprocal Rank Fusion (RRF)** | Standard fusion method; better than weighted sum |

**NOT**: Elasticsearch for BM25 (adds too much infra); use rank_bm25 in-process instead.

---

### Reranker
| Choice | Notes |
|--------|-------|
| **Cohere Rerank v3** | Best quality, API-based, no GPU needed. ~$1/1000 queries |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Local, free, slightly lower quality. Good for dev |
| **BGE-Reranker** | Strong multilingual, local, requires GPU for production throughput |

**Recommendation:** Cohere for production (quality + no ops). Cross-encoder for dev/staging.

---

### LLM (Generation)
| Choice | Notes |
|--------|-------|
| **claude-3-5-sonnet-20241022** | Main generation model. Best instruction-following + citation format |
| **claude-3-haiku-20240307** | Eval scoring (LLM-as-judge). Fast + cheap |

Use Anthropic SDK directly — no LangChain wrapper needed for this use case.

---

### Chunking
| Library | Use Case |
|---------|---------|
| **BeautifulSoup4** | HTML parsing (EdgeOne docs) |
| **tiktoken** | Token counting for chunk size validation |
| **markdown-it-py** | Markdown parsing |
| Custom logic | Per-source chunking strategy (API ref = per endpoint, CLI = per command) |

**NOT**: LangChain's text splitters (too generic; loses structural metadata)

---

### RAG Orchestration — No Framework Recommended
**Recommendation: Write it yourself.** The pipeline is simple enough:

```
embed → search → rerank → prompt_assembly → generate → parse_citations
```

LangChain and LlamaIndex add abstraction overhead, make debugging harder, and their updates break production. For a purpose-built system this focused, direct library calls are better.

**Use if needed:** `anthropic` SDK, `openai` SDK, `cohere` SDK, `chromadb`, `rank_bm25` — all direct.

---

### Metadata Store
| Component | Choice | Notes |
|-----------|--------|-------|
| DB | **PostgreSQL 15+** | Chunk metadata, eval logs, source registry |
| ORM | **SQLAlchemy 2.x** + **Alembic** | Async support, migrations |
| Async driver | **asyncpg** | Required for FastAPI async routes |

---

### Caching
| Layer | Technology | Notes |
|-------|-----------|-------|
| Semantic cache | **Redis** + custom embedding index | Store (query_vector, response) pairs; lookup by cosine similarity |
| Retrieval cache | **Redis** with TTL | Cache chunk_ids for a query hash |
| Embedding cache | **Redis** | Cache query vectors by exact string hash |

**Pattern:** Small Redis sorted set for semantic cache (cosine sim lookup on ~1000 recent vectors is fast). Not a full vector DB — just Redis ZADD with hash.

---

### Frontend
| Component | Choice | Version | Notes |
|-----------|--------|---------|-------|
| Framework | **Next.js 14** (App Router) | 14.x | SSR + streaming; `useOptimistic` for instant response feel |
| Styling | **Tailwind CSS** | 3.4.x | Dark theme; enterprise design system |
| Streaming | **Server-Sent Events (SSE)** via `fetch` + ReadableStream | — | Better than WebSocket for unidirectional AI stream |
| State | **Zustand** | 4.x | Lightweight; no Redux overhead for chat state |
| Charts (admin) | **Recharts** | 2.x | Lightweight, composable, works with Tailwind |
| Tables (admin) | **TanStack Table** | 8.x | Headless, fully customizable |

**NOT**: WebSockets for streaming (bidirectional overhead not needed), tRPC (adds complexity), Redux (too heavy)

---

### CI/CD
| Component | Choice |
|-----------|--------|
| CI | **GitHub Actions** |
| Python testing | **pytest** + **pytest-asyncio** |
| Frontend testing | **Vitest** (unit) + **Playwright** (e2e) |
| Linting | **ruff** (Python) + **ESLint** + **Prettier** |
| Type checking | **mypy** (Python) + **TypeScript strict mode** |
| Containerization | **Docker Compose** (dev) + **Dockerfile** per service |

---

### Eval
| Component | Choice | Notes |
|-----------|--------|-------|
| Per-call scoring | Custom (Claude Haiku as judge) | ~500ms async, non-blocking |
| Observability | **LangSmith** (optional) | Session tracing, eval dashboards |
| Enterprise eval suite | Custom pytest fixtures | 142 golden questions as JSON test cases |

---

## What NOT to Use (and Why)

| Skip | Reason |
|------|--------|
| LangChain | Abstraction rot; breaks on updates; harder to debug streaming |
| LlamaIndex | Similar issues; better for document QA than this architecture |
| Pinecone | US-only, expensive, not needed at this scale |
| Elasticsearch | Overkill for BM25; adds ops burden |
| GraphQL | REST is fine here; no complex query graphs |
| Next.js Pages Router | App Router is 2025 standard; better streaming support |
