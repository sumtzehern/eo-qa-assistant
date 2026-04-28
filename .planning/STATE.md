# STATE.md — EdgeOne QA Assistant

*Last updated: 2026-04-27*

---

## Current Phase

**Phase 0 — Pre-Implementation**

No code exists. Design and planning complete. Ready to begin Phase 1.

---

## Phase History

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 — Planning | Complete | All design docs written; requirements, roadmap, and state initialized |
| Phase 1 — Infrastructure | Not started | — |
| Phase 2a — Ingestion | Not started | — |
| Phase 2b — Backend API | Not started | — |
| Phase 2c — Frontend Shell | Not started | — |
| Phase 3 — Integration | Not started | — |
| Phase 4 — Eval + Admin | Not started | — |
| Phase 5 — Semantic Cache | Not started | — |
| Phase 6 — Enterprise Eval | Not started | — |

---

## Key Decisions (Locked)

These decisions are confirmed and should not be revisited without explicit justification.

| Decision | Outcome | Rationale |
|----------|---------|-----------|
| Split-panel UI (Option C) | Approved | Shows RAG retrieval quality visibly; follow-up suggestions show context awareness |
| FastAPI backend | Approved | Consistent with existing teo-psa Python skills |
| Next.js 14 (App Router) | Approved | SSR + streaming support; best for AI chat UIs |
| Standard granularity (5-8 phases) | Approved | Right size for solo dev scope |
| YOLO execution mode | Approved | Solo dev, high trust, fast iteration |
| Sharding by language/tenant (not topic) | Decided | Topic sharding causes cross-shard misses on multi-topic queries |
| Human-in-the-loop for source additions | Decided | Auto-ingestion risks degrading quality if eval scores are wrong |
| SSE not WebSocket for streaming | Decided | Unidirectional, simpler, no connection state |
| No LangChain / LlamaIndex | Decided | Direct library calls; easier to debug; stable |
| Ingestion worker separate from API process | Decided | Prevents ingestion from degrading query latency |
| Semantic cache with invalidation on re-ingest | Decided | Stale cache is worse than no cache |
| 5 chunks max in prompt | Decided | More chunks hurts answer quality; reranker enforces quality |
| Vector DB: Chroma (dev) / Tencent VectorDB (prod) | Decided | pgvector as fallback option if extra services are an issue |
| LLM: claude-3-5-sonnet (generation) + claude-3-haiku (eval judge) | Decided | Sonnet for quality, Haiku for cost on eval |
| Reranker: Cohere Rerank v3 (prod) / cross-encoder (dev) | Decided | Top differentiator vs naive RAG |
| Embeddings: text-embedding-3-small (EN) + Hunyuan (ZH fallback) | Decided | Bilingual support; CN data residency option |

---

## Blockers

None.

---

## Open Questions

None currently. All major architecture questions resolved in research phase.

---

## Next Action

Run `/gsd-discuss-phase 1` to discuss and finalize the Phase 1 implementation plan before coding begins.

---

## Planning Artifacts

| File | Purpose | Status |
|------|---------|--------|
| `.planning/PROJECT.md` | Project brief, decisions, high-level requirements | Complete |
| `.planning/research/ARCHITECTURE.md` | System architecture, data models, build order | Complete |
| `.planning/research/FEATURES.md` | Feature list, complexity notes, anti-features | Complete |
| `.planning/research/SUMMARY.md` | Stack recommendations, critical decisions, watch-outs | Complete |
| `.planning/REQUIREMENTS.md` | Full requirement list with REQ-IDs, v1/v2/out-of-scope | Complete |
| `.planning/ROADMAP.md` | 6-phase roadmap with success criteria and coverage matrix | Complete |
| `.planning/STATE.md` | This file — current phase, decisions, blockers | Complete |
| `design/01-architecture.md` | Original architecture spec | Superseded by research |
| `design/02-ingestion-pipeline.md` | Original ingestion spec | Reference |
| `design/03-rag-retrieval.md` | Original retrieval spec | Reference |
| `design/04-eval-framework.md` | Original eval spec | Reference |
| `design/05-api-design.md` | Original API spec | Reference |
