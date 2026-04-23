# 02 — Ingestion Pipeline

**Status:** Draft  
**Last Updated:** 2026-04-16

---

## Design Principle

> Ingestion is **entirely offline**. No scraping, chunking, or embedding happens at query time. The vector DB is always pre-populated and ready.

---

## Sources to Ingest

| Source | Format | Crawl Method | Priority |
|--------|--------|-------------|----------|
| EdgeOne public docs | HTML | Web crawler (crawl4ai) | P0 |
| Tencent CLI reference (`tccli`) | HTML / Markdown | Web crawler | P0 |
| EdgeOne API reference | HTML / OpenAPI JSON | Web crawler + JSON parser | P0 |
| Internal migration guides | Markdown / Confluence | Direct file read / Confluence API | P0 |
| `mappings.json` | JSON | Direct file ingest | P0 |
| `error-patterns.json` | JSON | Direct file ingest | P0 |
| `edge-functions.json` | JSON | Direct file ingest | P0 |
| `ignore-list.json` | JSON | Direct file ingest | P1 |
| Code examples / Edge Functions | JS / Python | Git repo crawler | P1 |

---

## Pipeline Stages

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  Job Queue │ →  │  Crawler   │ →  │  Chunker   │ →  │  Embedder  │ →  │ Vector DB  │
│  (Redis)   │    │            │    │            │    │            │    │            │
└────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘
      ↑                  ↓                ↓                  ↓                 ↓
 Cron Trigger      Raw Content      Chunk + Meta       Vectors           Upsert by
 Manual Trigger    + HTML/JSON      + Hash Check       (1536-dim)        chunk_id
```

---

## Job Queue Design

Each ingestion job is a message:

```json
{
  "job_id": "uuid",
  "source_type": "web | file | json | git",
  "source_id": "edgeone-docs",
  "url_or_path": "https://cloud.tencent.com/document/product/1552",
  "triggered_by": "cron | manual | webhook",
  "priority": 1,
  "created_at": "2026-04-16T00:00:00Z"
}
```

Workers pull jobs from queue, process, report status back.

---

## Chunking Strategy

Different sources need different chunking:

| Source Type | Strategy | Chunk Size | Overlap |
|-------------|----------|-----------|---------|
| HTML docs | Split by `<h2>` / `<h3>` sections | ~800 tokens | 100 tokens |
| API reference | One chunk per endpoint | Variable | None |
| CLI reference | One chunk per command | ~500 tokens | None |
| JSON knowledge files | One chunk per top-level key/entry | Variable | None |
| Markdown | Split by `##` headings | ~800 tokens | 100 tokens |

### Chunk Metadata Schema

```json
{
  "chunk_id": "sha256_of_content",
  "source_id": "edgeone-docs",
  "source_url": "https://...",
  "page_title": "Configure Redirect Rules",
  "section_title": "HTTP to HTTPS Redirect",
  "content": "...",
  "content_hash": "sha256",
  "token_count": 312,
  "language": "en | zh",
  "last_crawled": "2026-04-16T00:00:00Z",
  "last_modified": "2026-03-01T00:00:00Z"
}
```

---

## Diff / Freshness Check

Before re-embedding, check if content changed:

```
1. Fetch page
2. Hash the cleaned text content
3. Compare with stored content_hash in Postgres
4. If unchanged → skip embedding (save cost)
5. If changed → re-chunk → re-embed → upsert
6. If new → chunk → embed → insert
7. If deleted (404) → mark chunk as stale in DB
```

This makes weekly re-crawls cheap — only changed pages are re-embedded.

---

## Schedule

| Job | Frequency | Notes |
|-----|-----------|-------|
| EdgeOne public docs | Weekly (Mon 2am) | Full re-crawl |
| CLI reference | Weekly (Mon 2am) | Full re-crawl |
| API reference | Weekly (Mon 2am) | Full re-crawl |
| Internal JSON files | On git commit (webhook) | Event-driven |
| Internal Markdown guides | On git commit (webhook) | Event-driven |

---

## Error Handling

| Failure | Action |
|---------|--------|
| Crawler 404/timeout | Retry 3x, then mark source as failed, alert |
| Embedding API error | Retry with exponential backoff |
| Vector DB write fail | Retry, dead-letter queue if persistent |
| Partial crawl | Log which URLs succeeded/failed, continue |

---

## Ingestion Monitoring

Track per-job:
- `chunks_processed`, `chunks_skipped` (unchanged), `chunks_failed`
- `embedding_cost` (token count × price)
- `duration_seconds`
- `last_successful_run`

Expose via internal dashboard. Alert if a source hasn't successfully ingested in 14 days.
