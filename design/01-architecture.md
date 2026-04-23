# 01 — System Architecture

**Status:** Draft  
**Last Updated:** 2026-04-16

---

## Overview

The EdgeOne QA Assistant is a RAG-based question-answering system. It is split into two fully independent planes:

- **Ingestion Plane** — offline, async, scheduled. Crawls sources, chunks, embeds, writes to vector DB.
- **Query Plane** — real-time, stateless. Embeds user query, retrieves chunks, calls Claude, returns answer + citations + eval scores.

These planes share only the **Vector DB** and the **Chunk Metadata Store**.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION PLANE (Offline)                │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │ Crawler/ │→  │  Chunker │→  │ Embedder │→  │ Vector DB  │  │
│  │ Scraper  │   │          │   │          │   │ (+ Metadata│  │
│  └──────────┘   └──────────┘   └──────────┘   │  Store)    │  │
│       ↑                                        └────────────┘  │
│  Job Queue (cron / manual trigger)                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        QUERY PLANE (Real-time)                  │
│                                                                 │
│  User → Query API → Embed Query → Vector Search → Reranker      │
│                          ↓                                      │
│                     Claude (RAG) → Response + Citations          │
│                          ↓                                      │
│                     Eval Pipeline → Eval Store → Dashboard      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector DB | Tencent VectorDB or Chroma (local dev) | Stays in Tencent ecosystem; Chroma for local iteration |
| Embeddings | OpenAI `text-embedding-3-small` or Hunyuan | Hunyuan preferred for bilingual CN/EN content |
| LLM | Claude (Anthropic API) | Instruction-following, citation format, long context |
| Reranker | Cohere Rerank or cross-encoder | Improves retrieval precision significantly |
| Job Queue | Redis Queue (RQ) or Celery | Async ingestion jobs |
| Metadata Store | PostgreSQL | Chunk metadata, source tracking, eval logs |
| API Layer | FastAPI (Python) | Consistent with existing Python skills |
| Eval Framework | Custom + LangSmith or Braintrust | Per-call scoring + enterprise dashboards |

---

## Data Flow — Detailed

### Ingestion (Offline)
```
1. Cron triggers CrawlJob for each source
2. Crawler fetches raw HTML/JSON/Markdown
3. Chunker splits by section, adds metadata:
   { source_url, title, section, last_crawled, content_hash }
4. Diff check: skip if content_hash unchanged
5. Embedder generates vector for each chunk
6. Upsert into Vector DB (by chunk_id)
7. Write metadata to Postgres
8. Job status logged → Ingestion Dashboard
```

### Query (Request Time)
```
1. User submits query via API
2. Query expanded into 2-3 sub-queries (optional, improves recall)
3. Each sub-query embedded
4. Hybrid search: vector similarity + BM25 keyword
5. Top-20 candidates fetched
6. Reranker scores candidates, selects top-5
7. Prompt assembled: system prompt + chunks + user query
8. Claude generates answer with inline citations [1][2]
9. Citations resolved to source URLs
10. Response returned: { answer, citations, query_id }
11. Eval pipeline runs async on response → scores logged
```

---

## Scalability Notes

- Ingestion is fully decoupled — can run parallel crawl workers
- Query plane is stateless — horizontally scalable
- Vector DB is the shared bottleneck — Tencent VectorDB handles this at scale
- Eval runs async (non-blocking) — does not add latency to user response
