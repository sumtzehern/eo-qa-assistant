# 05 — API Design

**Status:** Draft  
**Last Updated:** 2026-04-16

---

## Base URL

```
https://api.edgeone-qa.internal/v1
```

---

## Endpoints

### POST /query

Submit a question. Returns answer + citations + eval scores (async eval attached to query_id).

**Request:**
```json
{
  "query": "How do I redirect HTTP to HTTPS on EdgeOne?",
  "options": {
    "language": "en",
    "source_filter": ["edgeone-docs", "cli-reference"],
    "query_expansion": true,
    "max_citations": 5
  },
  "session_id": "optional-for-conversation-history",
  "caller_id": "customer-portal | internal-tool | api"
}
```

**Response:**
```json
{
  "query_id": "q_abc123",
  "answer": "To redirect HTTP to HTTPS, configure a redirect rule with `scheme: https` [1]. You can also use the CLI [2].",
  "citations": [
    {
      "index": 1,
      "title": "Configure Redirect Rules",
      "url": "https://cloud.tencent.com/document/product/1552/...",
      "section": "HTTP to HTTPS Redirect",
      "snippet": "Set scheme to https in the action block..."
    }
  ],
  "confidence": 0.91,
  "no_answer": false,
  "latency_ms": 1240,
  "eval_status": "pending",
  "eval_id": "e_xyz789"
}
```

**Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid query (empty, too long) |
| 429 | Rate limited |
| 503 | Vector DB or Claude unavailable |

---

### GET /query/{query_id}/eval

Retrieve the eval scores for a past query (available ~2-3 seconds after the query).

**Response:**
```json
{
  "eval_id": "e_xyz789",
  "query_id": "q_abc123",
  "scores": {
    "groundedness": 0.94,
    "retrieval_relevance": 0.88,
    "citation_accuracy": 1.0,
    "completeness": 0.81,
    "hallucination_detected": false,
    "overall": 0.91
  },
  "flagged_for_review": false,
  "completed_at": "2026-04-16T10:23:03Z"
}
```

---

### GET /sources

List all ingested sources and their freshness status.

**Response:**
```json
{
  "sources": [
    {
      "source_id": "edgeone-docs",
      "display_name": "EdgeOne Documentation",
      "url": "https://cloud.tencent.com/document/product/1552",
      "chunk_count": 842,
      "last_ingested": "2026-04-14T02:00:00Z",
      "status": "healthy"
    },
    {
      "source_id": "error-patterns",
      "display_name": "Internal Error Patterns",
      "url": "file://knowledge-base/error-patterns.json",
      "chunk_count": 94,
      "last_ingested": "2026-04-15T09:12:00Z",
      "status": "healthy"
    }
  ]
}
```

---

### POST /ingestion/trigger

Manually trigger re-ingestion for a source (admin only).

**Request:**
```json
{
  "source_id": "edgeone-docs",
  "force_reembed": false
}
```

**Response:**
```json
{
  "job_id": "job_abc",
  "source_id": "edgeone-docs",
  "status": "queued",
  "created_at": "2026-04-16T10:00:00Z"
}
```

---

### GET /ingestion/jobs/{job_id}

Check ingestion job status.

**Response:**
```json
{
  "job_id": "job_abc",
  "source_id": "edgeone-docs",
  "status": "running | completed | failed",
  "chunks_processed": 612,
  "chunks_skipped": 230,
  "chunks_failed": 0,
  "started_at": "2026-04-16T10:00:05Z",
  "completed_at": null
}
```

---

### GET /eval/summary

Aggregate eval stats (enterprise dashboard feed).

**Query Params:** `?period=7d&category=migration`

**Response:**
```json
{
  "period": "7d",
  "total_queries": 1847,
  "avg_scores": {
    "groundedness": 0.92,
    "retrieval_relevance": 0.87,
    "overall": 0.90
  },
  "hallucination_rate": 0.021,
  "no_answer_rate": 0.084,
  "flagged_count": 38,
  "coverage_gaps": [
    "EdgeOne WAF custom rules",
    "tccli batch operations"
  ]
}
```

---

## Rate Limits

| Tier | Requests/min | Notes |
|------|-------------|-------|
| Internal tools | 200 | No limit in practice |
| Customer portal | 60 | Per authenticated user |
| Public API | 10 | Per IP, unauthenticated |

---

## Auth

- Internal: API key in `X-API-Key` header
- Customer portal: JWT (from Tencent auth system)
- Admin endpoints (`/ingestion/*`): separate admin API key

---

## Versioning

All endpoints under `/v1`. Breaking changes increment to `/v2`. Non-breaking additions are backwards compatible within `/v1`.
