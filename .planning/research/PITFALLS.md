# PITFALLS.md — Research: RAG QA Assistant Common Failures

## 1. RAG Quality Pitfalls

### 1.1 Chunking Destroys Context
**Pitfall:** Splitting at fixed token counts cuts mid-sentence, mid-table, or mid-code-block. Retrieval returns broken fragments that confuse the LLM.

**Warning signs:**
- LLM answers with "I don't have enough information" even when docs clearly cover the topic
- Retrieved chunks end/start with partial sentences
- Code examples split across two chunks

**Prevention:**
- Chunk by semantic structure (h2/h3 headings), not token count
- Apply token limit as a MAX, not a target — short sections stay intact
- Never split inside code blocks or tables
- Store section_title in metadata so LLM knows the heading context

**Phase:** Phase 2a (Ingestion pipeline)

---

### 1.2 Embedding Model Domain Mismatch
**Pitfall:** Using a general-purpose embedding model for highly technical CDN/API documentation. Terms like "origin pull", "edge node", "WAF rule" may not cluster correctly.

**Warning signs:**
- Semantically similar EdgeOne concepts retrieve unrelated results
- "How do I set a redirect rule?" retrieves firewall docs instead

**Prevention:**
- Use `text-embedding-3-small` (strong general + technical coverage)
- For Mandarin queries: use Hunyuan embedding (trained on CN technical content)
- Run embedding quality check: embed 10 known question-answer pairs, verify correct docs are in top-5
- Do NOT mix embedding models across the same index (all chunks and queries must use same model)

**Phase:** Phase 2a (Ingestion) + Phase 3 (Query)

---

### 1.3 Context Stuffing (More Chunks ≠ Better Answers)
**Pitfall:** Sending 15-20 chunks to Claude instead of 5 high-quality ones. LLM attention dilutes, answer quality drops, latency increases, cost increases.

**Warning signs:**
- Answers get longer but less accurate
- Citations reference irrelevant chunks
- Hallucination rate increases with more chunks

**Prevention:**
- Hard cap: 5 chunks maximum in prompt
- Reranking is mandatory before prompt assembly — not optional
- Monitor: if reranker confidence < 0.5 for top chunk, consider returning "I don't know"

**Phase:** Phase 3 (Query pipeline)

---

### 1.4 BM25 Weight Tuning Mistakes
**Pitfall:** Setting BM25 weight too high makes it keyword-search only (misses paraphrased questions). Too low and exact API action names get buried.

**Warning signs:**
- "CreateRule" retrieves nothing even though docs mention it (dense too high)
- "How do I redirect traffic?" retrieves docs containing only "redirect" keyword with no semantic match (BM25 too high)

**Prevention:**
- Default RRF weights: BM25 k=0.5, dense k=0.5 (equal fusion)
- Test with 20 known queries: split between keyword-style and natural-language-style
- Tune separately: technical queries (error codes, API actions) benefit from higher BM25 weight

**Phase:** Phase 3

---

## 2. Caching Pitfalls

### 2.1 String Match Cache (Near-Duplicate Miss)
**Pitfall:** Using exact string hash for semantic cache lookup. "How do I force HTTPS?" and "How to redirect HTTP to HTTPS?" return different cache misses even though the answer is identical.

**Warning signs:**
- Cache hit rate < 20% despite many repeat topics
- Same question phrased differently always costs a full LLM call

**Prevention:**
- Cache key = embedding vector similarity, not string hash
- Cosine similarity threshold: 0.95 = cache hit (tune for precision vs recall)
- Store query vector + response in Redis; lookup by nearest neighbor in recent cache

**Phase:** Phase 5 (Caching)

---

### 2.2 Stale Cache After Re-ingestion
**Pitfall:** Docs are updated and re-ingested, but old cached responses still reference stale content. Users get outdated answers confidently.

**Warning signs:**
- Admin triggers re-ingest but users still see old answers
- Cached response cites a URL that 404s after doc restructure

**Prevention:**
- Tag every cache entry with source_id(s) it was built from
- On re-ingest completion: `DEL` all Redis cache entries tagged with that source_id
- Never set cache TTL longer than ingestion schedule (weekly ingest → cache TTL max 7 days)

**Phase:** Phase 5 (Caching) — must be designed alongside ingestion pipeline

---

### 2.3 Redis Memory Explosion
**Pitfall:** No cache eviction policy. Redis fills up, starts evicting randomly, cache hit rate crashes silently.

**Warning signs:**
- Redis memory > 80% of configured limit
- Cache hit rate drops suddenly without traffic increase

**Prevention:**
- Set `maxmemory-policy allkeys-lru` in Redis config
- Cap semantic cache at 10,000 entries (ring buffer approach)
- Monitor `redis-cli INFO memory` in admin dashboard

**Phase:** Phase 1 (Infrastructure) — set eviction policy in Docker Compose config

---

## 3. Eval Pitfalls

### 3.1 LLM-as-Judge Overconfidence
**Pitfall:** Claude Haiku scores its own parent model's (Sonnet) outputs generously. Groundedness scores are systematically inflated.

**Warning signs:**
- Groundedness scores cluster at 0.9+ even on clearly bad answers
- Human spot-check reveals hallucinations that eval scored 0.95 groundedness

**Prevention:**
- Calibrate: hand-score 50 responses, compare vs Haiku judge scores
- Use explicit rubric in judge prompt: "A score of 1.0 requires EVERY claim to be directly supported..."
- Cross-validate: spot-check 5% of "not flagged" responses manually

**Phase:** Phase 4 (Eval pipeline)

---

### 3.2 Auto-Remediation Based on Flawed Eval
**Pitfall:** Low eval score triggers automatic ingestion of new content to "fix" the gap. If eval score is wrong (Haiku false positive), bad content gets ingested.

**Warning signs:**
- Source count grows without human review
- Answer quality degrades over time despite "improving" eval scores

**Prevention:** Never auto-ingest. Low eval score → flagged queue → human review → manual source addition.

**Phase:** Phase 4 (Eval) — hard rule, not a tuning issue

---

### 3.3 Golden Test Set Rot
**Pitfall:** 142 golden questions become too easy over time as the system learns them. Eval suite passes at 95% but real-world performance is 70%.

**Warning signs:**
- Enterprise eval suite score > 0.95 but user-reported accuracy < 0.80
- All golden questions are about the same 5 topics

**Prevention:**
- Rotate 10-15% of golden questions quarterly
- Include adversarial questions (edge cases, wrong-direction queries)
- Separate "known good" subset from "challenging" subset in reporting

**Phase:** Phase 6 (Enterprise eval suite)

---

## 4. Infrastructure Pitfalls

### 4.1 Ingestion Blocking Query Path
**Pitfall:** Running ingestion in the same process as the FastAPI query server. A large re-crawl saturates CPU/memory, degrading query latency.

**Warning signs:**
- Query latency spikes during scheduled ingestion window (Monday 2am)
- FastAPI returns 503s during large re-ingests

**Prevention:**
- Ingestion MUST run in a separate Celery/RQ worker process
- Use separate Redis queue for ingestion vs eval tasks
- Rate-limit embedding API calls in ingestion worker (not in query path)

**Phase:** Phase 1 (Infrastructure) — worker separation from day one

---

### 4.2 Streaming Response Timeout
**Pitfall:** Claude takes 15-20s for complex answers. Nginx/proxy default timeout (60s) cuts the connection mid-stream.

**Warning signs:**
- Long answers get cut off in production but work locally
- Client receives `ERR_INCOMPLETE_CHUNKED_ENCODING`

**Prevention:**
- Set `proxy_read_timeout 120s` in Nginx config
- Add `keepalive_timeout 65s`
- Implement heartbeat: send empty SSE comment `": ping\n\n"` every 5s to keep connection alive

**Phase:** Phase 2b (Backend API) + deployment config

---

### 4.3 Vector DB Index Rebuild Cost
**Pitfall:** Rebuilding HNSW index from scratch after large re-ingest. Can take 10-30 minutes for 100k+ chunks, during which search quality degrades.

**Warning signs:**
- Search quality drops after bulk re-ingest
- Vector DB CPU spikes for extended periods after ingestion

**Prevention:**
- Use upsert (not delete+insert) for changed chunks
- Only re-embed changed chunks (content_hash diff check)
- Schedule large re-ingests during off-peak (2am, not business hours)

**Phase:** Phase 2a (Ingestion pipeline)

---

## 5. Frontend Pitfalls

### 5.1 Citation Index Mismatch
**Pitfall:** Claude outputs `[1][2]` but the mapping to actual source chunks is done by string parsing that breaks on edge cases (nested brackets, no space before bracket).

**Warning signs:**
- Citation `[1]` on frontend points to wrong source
- Some citations show as broken links

**Prevention:**
- Parse citations server-side before sending to frontend (never trust frontend parsing)
- Citation format: `[N]` where N is exactly the index in the ordered chunks list
- Include citation_map in API response: `{"1": chunk_id_1, "2": chunk_id_2}`

**Phase:** Phase 3 (Query pipeline + frontend wiring)

---

### 5.2 Streaming Partial Citations
**Pitfall:** Citations `[1]` appear mid-stream before the citation metadata arrives. Frontend renders `[1]` as plain text until the full response completes.

**Warning signs:**
- Citations flash as `[1]` then transform to links at end of stream
- UX feels broken

**Prevention:**
- Stream answer tokens first, send citations as final SSE event after `[DONE]`
- Frontend: render inline `[1]` as placeholder spans; replace with links when citation metadata arrives
- Or: stream with `__CIT_1__` placeholder, swap to rich citation on completion

**Phase:** Phase 3 (Streaming + frontend)

---

## 6. Production Pitfalls

### 6.1 Cold Start Latency
**Pitfall:** First query after deployment takes 10-15s because: BM25 index not loaded into memory, vector DB connection pooling not warmed up, embedding model cold.

**Warning signs:**
- First query always slow, subsequent queries normal

**Prevention:**
- Health check endpoint `/health` that warms BM25 index on startup
- PostgreSQL connection pool: min_size=2 (keep 2 connections alive)
- Celery worker pre-import: load all models at worker start, not on first task

**Phase:** Phase 2b (Backend API)

---

### 6.2 Source Freshness Staleness
**Pitfall:** Ingestion cron fails silently. EdgeOne docs update but the assistant answers from 3-week-old content. No alert fires.

**Warning signs:**
- `last_ingested` timestamp in /sources response > 14 days old
- Users report outdated answers

**Prevention:**
- Admin dashboard: red "Stale" badge on source cards if `last_ingested > 14 days`
- Alert: if source hasn't ingested in 14 days, write to flagged alerts table
- Cron failure monitoring: use `sentry-sdk` or similar to catch Celery task failures

**Phase:** Phase 2a (Ingestion) + Phase 4 (Admin dashboard)

---

### 6.3 Claude/Cohere API Rate Limit Handling
**Pitfall:** Under load, Anthropic or Cohere rate limits hit (429). Query fails with no retry logic.

**Warning signs:**
- 429 errors in logs during peak usage
- Queries silently fail instead of gracefully degrading

**Prevention:**
- Wrap all external API calls with exponential backoff retry (max 3 attempts)
- Use `tenacity` library for retry logic
- Circuit breaker: if reranker fails, fall back to vector search without reranking (don't fail the whole query)
- Log all 429s as metrics: if rate limit hits > 5% of queries, time to upgrade API tier

**Phase:** Phase 3 (Query pipeline)
