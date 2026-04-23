# 04 — Evaluation Framework

**Status:** Draft  
**Last Updated:** 2026-04-16

---

## Design Principle

> Every API call is evaluated. No response leaves the system without a score. Eval is async (non-blocking) but comprehensive.

This is enterprise-grade: you can prove answer quality to customers, catch regressions, and build SLA commitments around it.

---

## Two Eval Layers

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: Per-Call Eval (every production request)  │
│  Runs async, ~500ms, attached to every query_id     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  LAYER 2: Enterprise Eval Suite (scheduled / CI)    │
│  Runs against curated test set, produces reports    │
│  Used for: regression tests, model upgrades,        │
│  SLA reviews, customer trust reports                │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1 — Per-Call Eval

Runs **async after every response** is returned to the user. Does not block the response.

### Metrics Computed Per Call

| Metric | Method | Score |
|--------|--------|-------|
| **Groundedness** | Are claims in the answer supported by retrieved chunks? | 0.0–1.0 |
| **Retrieval Relevance** | Are the retrieved chunks actually relevant to the query? | 0.0–1.0 |
| **Citation Accuracy** | Do citations map to chunks that contain the cited claim? | 0.0–1.0 |
| **Answer Completeness** | Does the answer address all parts of the query? | 0.0–1.0 |
| **Hallucination Flag** | Does the answer contain claims NOT in any chunk? | bool |
| **No-Answer Rate** | Did Claude say "I don't know"? | bool |

### How Groundedness is Evaluated

Use a lightweight LLM-as-judge call (Claude Haiku / fast model):

```
System: You are an evaluator. Given a question, answer, and source chunks,
score how well the answer is grounded in the sources (0.0 to 1.0).
Return JSON: { "score": 0.92, "reason": "..." }

Input:
Question: {query}
Answer: {answer}
Sources: {chunks}
```

Cost: ~500 tokens per eval call. Run async, does not affect latency.

### Per-Call Eval Record (stored in Postgres)

```json
{
  "eval_id": "uuid",
  "query_id": "uuid",
  "timestamp": "2026-04-16T10:23:00Z",
  "query": "How do I redirect HTTP to HTTPS?",
  "answer": "...",
  "chunk_ids_used": ["chunk_abc", "chunk_def"],
  "scores": {
    "groundedness": 0.94,
    "retrieval_relevance": 0.88,
    "citation_accuracy": 1.0,
    "completeness": 0.81,
    "hallucination_detected": false,
    "no_answer": false
  },
  "overall_score": 0.91,
  "flagged_for_review": false,
  "latency_ms": 1240,
  "model": "claude-sonnet-4.6",
  "embedding_model": "text-embedding-3-small"
}
```

### Auto-Flag Rules

| Condition | Action |
|-----------|--------|
| `groundedness < 0.7` | Flag for human review |
| `hallucination_detected = true` | Flag + alert |
| `overall_score < 0.65` | Flag for review |
| `no_answer = true` AND query has >50 similar queries | Flag as coverage gap |
| `retrieval_relevance < 0.5` | Flag as retrieval failure |

---

## Layer 2 — Enterprise Eval Suite

A curated **golden test set** of question-answer pairs, run on a schedule or before any model/prompt change.

### Test Set Structure

```json
[
  {
    "test_id": "T001",
    "category": "setup",
    "question": "How do I redirect HTTP to HTTPS on EdgeOne?",
    "expected_topics": ["redirect rule", "scheme: https", "action block"],
    "should_cite_source": "edgeone-docs",
    "should_not_hallucinate": true,
    "difficulty": "easy"
  },
  {
    "test_id": "T002",
    "category": "debugging",
    "question": "What does API error 1005 mean?",
    "expected_topics": ["error 1005", "fix", "cause"],
    "should_cite_source": "error-patterns",
    "difficulty": "medium"
  },
  {
    "test_id": "T003",
    "category": "migration",
    "question": "What is the EdgeOne equivalent of Akamai SureRoute?",
    "expected_topics": ["SureRoute", "mapping", "EdgeOne equivalent"],
    "should_cite_source": "mappings",
    "difficulty": "hard"
  }
]
```

### Enterprise Eval Run Output

```
EdgeOne QA Assistant — Eval Report
Run Date: 2026-04-16
Model: claude-sonnet-4.6
Test Set: v1.2 (142 questions)

Overall Score:          0.89 / 1.00   ✓
Groundedness:           0.93 / 1.00   ✓
Retrieval Relevance:    0.87 / 1.00   ✓
Citation Accuracy:      0.95 / 1.00   ✓
Hallucination Rate:     2.1%          ✓ (threshold: <5%)
No-Answer Rate:         8.4%          ✓ (threshold: <15%)

By Category:
  setup:       0.94  ✓
  debugging:   0.91  ✓
  migration:   0.83  ⚠ (below 0.85 target)

Flagged for Review: 3 questions
Regressions vs last run: 0
```

### When to Run Enterprise Eval

| Trigger | Action |
|---------|--------|
| Before deploying new prompt version | Run full suite, require >0.85 to proceed |
| Before upgrading Claude model version | Run full suite, compare scores |
| Weekly scheduled run | Track trends, alert on degradation |
| New source ingested | Run category-relevant subset |
| Customer escalation | Run relevant category, share report |

---

## Eval Dashboard (Internal)

Real-time metrics visible to the team:

- **Daily average scores** (groundedness, relevance, accuracy)
- **Hallucination rate** over time
- **Top 10 flagged queries** (worst-performing)
- **Coverage gaps** — queries that consistently returned no-answer
- **Source contribution** — which sources are cited most/least
- **Latency percentiles** (p50, p95, p99)

---

## Human Review Workflow

Flagged queries enter a review queue:

```
Flagged Query → Review Queue → Human Reviewer
                                    ↓
                          [ Approve | Reject | Add to Test Set ]
                                    ↓
                    If rejected → identify root cause:
                      - Missing doc (add to ingestion sources)
                      - Bad chunking (tune chunker)
                      - Retrieval failure (tune reranker)
                      - Prompt issue (update system prompt)
                      - Model failure (escalate)
```

Human-reviewed examples feed back into the golden test set, making the eval suite richer over time.
