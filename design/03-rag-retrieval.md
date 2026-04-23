# 03 — RAG Retrieval Design

**Status:** Draft  
**Last Updated:** 2026-04-16

---

## Retrieval Pipeline

```
User Query
    ↓
[1] Query Expansion (optional)     → 2-3 sub-queries via Claude
    ↓
[2] Embedding                      → vector per query
    ↓
[3] Hybrid Search                  → vector similarity + BM25 keyword
    ↓
[4] Merge + Deduplicate            → combine results from all sub-queries
    ↓
[5] Rerank                         → cross-encoder scores top-20 → select top-5
    ↓
[6] Prompt Assembly                → system prompt + chunks + user query
    ↓
[7] Claude Generation              → answer with inline citations
    ↓
[8] Citation Resolution            → map [1][2] to source URLs + titles
    ↓
Response: { answer, citations[], query_id }
```

---

## Hybrid Search

Vector search alone misses exact matches (e.g. "error code 1005", "SureRoute", CLI flag `--config`).
BM25 alone misses semantic similarity.

We run both and merge:

```python
# Pseudocode
vector_results = vector_db.search(query_embedding, top_k=20)
bm25_results   = bm25_index.search(query_text, top_k=20)
merged         = reciprocal_rank_fusion(vector_results, bm25_results)
reranked       = reranker.score(query, merged[:20])
top_chunks     = reranked[:5]
```

**Reciprocal Rank Fusion (RRF)** combines scores without needing to normalize:
```
score(chunk) = Σ 1 / (k + rank_in_list)   # k=60 standard
```

---

## Prompt Design

```
System:
You are an EdgeOne technical assistant. Answer using ONLY the provided context.
If the context does not contain the answer, say "I don't have enough information on this."
Always cite the source chunk numbers inline as [1], [2], etc.
Be concise and technical. Prefer showing config examples over prose.

Context:
[1] {chunk_1_content}
Source: {chunk_1_title} — {chunk_1_url}

[2] {chunk_2_content}
Source: {chunk_2_title} — {chunk_2_url}

... (up to 5 chunks)

User Question:
{user_query}
```

---

## Citation Format (Perplexity-style)

Response object:

```json
{
  "query_id": "uuid",
  "answer": "To redirect HTTP to HTTPS, configure a redirect rule with `scheme: https` [1]. You can also set this via the CLI using `tccli edgeone rule create --type redirect` [2].",
  "citations": [
    {
      "index": 1,
      "title": "Configure Redirect Rules",
      "url": "https://cloud.tencent.com/document/product/1552/...",
      "section": "HTTP to HTTPS Redirect",
      "snippet": "Set scheme to https in the action block..."
    },
    {
      "index": 2,
      "title": "tccli edgeone rule create",
      "url": "https://cloud.tencent.com/document/product/1552/cli/...",
      "section": "CLI Reference",
      "snippet": "tccli edgeone rule create --type redirect --scheme https"
    }
  ],
  "retrieval_score": 0.87,
  "latency_ms": 1240
}
```

---

## Query Expansion (Optional — improves recall)

For ambiguous queries, Claude rewrites the question before retrieval:

```
Input:  "SureRoute equivalent?"
Output: [
  "EdgeOne performance optimization equivalent to Akamai SureRoute",
  "Akamai SureRoute mapping EdgeOne",
  "origin connectivity optimization EdgeOne"
]
```

Run retrieval for all 3, merge results. Adds ~200ms latency but significantly improves recall for migration queries.

**Enable by default for queries under 10 words (likely under-specified).**

---

## Metadata Filtering

Allow callers to scope retrieval to specific source types:

```json
{
  "query": "how do I configure a redirect?",
  "filters": {
    "source_id": ["edgeone-docs", "cli-reference"],
    "language": "en"
  }
}
```

Useful for building focused sub-assistants (e.g., "CLI assistant only").

---

## Fallback Behavior

| Situation | Behavior |
|-----------|---------|
| No relevant chunks found (low score) | Return: "I don't have documentation on this. Please check [EdgeOne docs](url)." |
| Claude refuses to answer | Pass through Claude's response, log for review |
| Retrieval latency > 2s | Return partial results with warning |
| All sources stale (>30 days) | Prepend staleness warning to answer |
