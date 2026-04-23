# EdgeOne QA Assistant — System Design

**Status:** In Progress  
**Owner:** Wesley Sum  
**Last Updated:** 2026-04-16

---

## Documents

| Doc | Description | Status |
|-----|-------------|--------|
| [01-architecture.md](./01-architecture.md) | High-level system architecture | Draft |
| [02-ingestion-pipeline.md](./02-ingestion-pipeline.md) | Offline async ingestion design | Draft |
| [03-rag-retrieval.md](./03-rag-retrieval.md) | Retrieval-augmented generation design | Draft |
| [04-eval-framework.md](./04-eval-framework.md) | Per-call evaluation + enterprise eval | Draft |
| [05-api-design.md](./05-api-design.md) | Query API + response schema | Draft |

---

## Design Principles

1. **Ingestion is offline** — no scraping or embedding at request time
2. **Eval on every call** — every API response is scored, logged, and traceable
3. **Citations are first-class** — every answer references a source chunk
4. **Async by default** — ingestion jobs are queued, not synchronous
5. **Enterprise-ready** — eval framework supports SLA monitoring, regression testing, and human review workflows

---

## High-Level Flow

```
[OFFLINE]                          [REQUEST TIME]
Sources → Scrape → Chunk →         User Query
Embed → Vector DB                       ↓
                                   Embed Query
                                        ↓
                                   Vector Search
                                        ↓
                                   Rerank Chunks
                                        ↓
                                   Claude (RAG)
                                        ↓
                                   Response + Citations
                                        ↓
                                   Eval Pipeline → Log
```
