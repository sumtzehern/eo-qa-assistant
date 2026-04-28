# FEATURES.md — Research: Enterprise RAG QA Assistant Features

## Table Stakes (Must Have — Absence Is a Dealbreaker)

### Query & Answer
- [ ] **Natural language question input** — Free-text, not keyword search
- [ ] **Streaming response** — Token-by-token output; waiting for full response feels broken
- [ ] **Source citations** — Every factual claim links to a source. Without this, enterprise users don't trust answers
- [ ] **"I don't know" handling** — System must gracefully decline rather than hallucinate
- [ ] **Response latency < 3s to first token** — Users abandon after 3s; streaming masks total latency
- [ ] **Conversation history** — Users refine questions; losing context mid-session is unusable

### Trust & Quality Signals
- [ ] **Confidence indicator** — Some signal that the system is sure vs uncertain
- [ ] **Source URL visibility** — Users must be able to verify answers themselves
- [ ] **Snippet preview** — Show the exact text from source that was cited
- [ ] **Hallucination detection** — Enterprise: any undetected hallucination is a support escalation

### Language
- [ ] **English UI** — Primary language for this product
- [ ] **Chinese query support** — Many EdgeOne customers are CN-based; Mandarin queries must work

### Access & Auth
- [ ] **API key authentication** — For internal/B2B programmatic access
- [ ] **Rate limiting** — Prevent abuse; different tiers for different callers
- [ ] **HTTPS** — Non-negotiable for enterprise

---

## Differentiators (Competitive Advantage)

### Retrieval Quality
- [ ] **Hybrid search (BM25 + dense)** — Pure vector search misses exact term matches (API action names, error codes)
- [ ] **Reranking** — Dramatically improves precision; most naive RAG systems skip this
- [ ] **Query expansion** — For ambiguous queries ("why is it slow?"), generates sub-queries to improve recall
- [ ] **Semantic cache** — Repeat questions return instantly; hit rate typically 40-70% for documentation QA

### UX Differentiation
- [ ] **Split-panel layout** (sources always visible) — Users stay in context without toggling
- [ ] **Follow-up question suggestions** — Guides users to related answers they didn't know to ask
- [ ] **Source relevance scores** — Shows users WHY a source was retrieved
- [ ] **Bilingual toggle (EN/中文)** — Rare in CDN documentation tools; strong differentiator for CN market

### Operational Excellence (Enterprise B2B Differentiator)
- [ ] **Per-call eval scoring** — Every response scored; enterprise customers want SLA guarantees
- [ ] **Flagged query review queue** — Human-in-the-loop for low-quality responses
- [ ] **Admin dashboard** — Ops team visibility into quality trends, source health, cache hit rate
- [ ] **Source freshness tracking** — Alert when documentation hasn't been re-ingested in 14+ days
- [ ] **Enterprise eval suite** — Pre-deployment regression testing against golden Q&A pairs

### Technical Documentation Specific
- [ ] **Code block rendering** — CLI commands, JSON configs must render in monospace with copy button
- [ ] **Multi-source retrieval** — Single answer may cite docs + CLI ref + API ref simultaneously
- [ ] **Error code lookup** — "What does error X mean?" must retrieve from error-patterns source specifically
- [ ] **Version awareness** — Questions about specific EdgeOne API versions need metadata filtering

---

## Anti-Features (Deliberately NOT Build in v1)

| Anti-Feature | Why |
|-------------|-----|
| **Document upload by users** | Opens RAG poisoning attack surface; adds moderation burden |
| **Auto-learn from low-score queries** | Eval scores are imperfect; auto-ingestion of new sources based on them degrades quality |
| **Free-text source editing** | Users modifying source content breaks audit trail |
| **Chat personas / tone settings** | Enterprise users want professional, consistent answers — not casual chat styles |
| **Export to PDF/Word** | Scope creep; not core to Q&A value |
| **Voice input** | Not enterprise workflow |
| **Voting/thumbs up on answers** | Useful signal but complex to wire into training; deferred |
| **Topic-based shard selection** | User-facing source filtering is fine; internal topic sharding causes cross-shard misses |

---

## Feature Complexity Notes

| Feature | Complexity | Dependencies |
|---------|-----------|-------------|
| Streaming response | Medium | FastAPI SSE + Next.js ReadableStream |
| Hybrid search | Medium | BM25 index + vector DB, RRF fusion |
| Reranking | Low | Cohere API call |
| Semantic cache | High | Redis + cosine similarity + invalidation on re-ingest |
| Query expansion | Low | One Claude Haiku call before retrieval |
| Per-call eval | Medium | Async task, Claude Haiku judge, PostgreSQL logging |
| Admin dashboard charts | Medium | Recharts + GET /eval/summary endpoint |
| Flagged review queue | Medium | PostgreSQL flag table + admin UI table |
| EN/ZH toggle | Low | i18n library + Hunyuan embedding fallback |
| Enterprise eval suite | High | 142 golden questions + CI integration + regression detection |
| Follow-up suggestions | Low | Append to LLM prompt: "suggest 3 follow-up questions" |

---

## Enterprise B2B vs Consumer Differences

Enterprise B2B requires:
1. **Audit trail** — Every query logged with eval scores, not just successful ones
2. **SLA monitoring** — Latency p95, availability, flagged rate dashboards
3. **Admin controls** — Source management, ingestion triggers, review queue
4. **Reliability over novelty** — Boring and correct beats clever and wrong
5. **Data residency** — Option to use Tencent VectorDB + Hunyuan for CN data residency
6. **No hallucinations in production** — Even one confident wrong answer destroys enterprise trust

Consumer products tolerate:
- Higher hallucination rates (users verify casually)
- Fun/casual tone
- Social features (share, vote)
- Personalization
