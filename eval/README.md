# EdgeOne QA Eval Suite

The golden eval suite provides automated quality gates for the EdgeOne QA Assistant.

## What It Is

A bank of 142 realistic engineer questions across 8 categories, paired with a batch runner that:
- Calls the live `/v1/query` API for each question
- Scores each response on 5 dimensions using Claude Haiku as judge
- Checks aggregate metrics against quality thresholds
- Exits with code 1 if any threshold is breached (CI gate)

## Running Locally

Start the API server first, then:

```bash
# Full suite (142 questions)
python eval/run_eval.py --api-url http://localhost:8000 --api-key $INTERNAL_API_KEY

# Sample 20 questions (faster)
python eval/run_eval.py --api-url http://localhost:8000 --api-key $INTERNAL_API_KEY --limit 20

# Single category
python eval/run_eval.py --api-url http://localhost:8000 --api-key $INTERNAL_API_KEY --category security
```

Set `ANTHROPIC_API_KEY` in your environment to enable per-question scoring. Without it, only the `no_answer_rate` threshold is checked.

## Thresholds

| Metric | Threshold | Behavior when breached |
|--------|-----------|----------------------|
| `avg_overall_score` | ≥ 0.85 | Exit code 1 |
| `hallucination_rate` | < 5% | Exit code 1 |
| `no_answer_rate` | < 15% | Exit code 1 |

When `ANTHROPIC_API_KEY` is absent (e.g. on fork PRs), only `no_answer_rate` is enforced.

## Question Schema

Each question in `golden_questions.json` has:

```json
{
  "id": "GQ-001",
  "category": "configuration",
  "question": "How do I configure HTTP/3 support in EdgeOne?",
  "expected_topics": ["http3", "quic", "protocol", "enable"],
  "difficulty": "easy"
}
```

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (GQ-NNN) |
| `category` | One of 8 categories (see below) |
| `question` | The question text sent to the API |
| `expected_topics` | 3–5 keywords the answer should cover |
| `difficulty` | `easy`, `medium`, or `hard` |

## Categories

| Category | Count | Description |
|----------|-------|-------------|
| `configuration` | 25 | Cache TTL, headers, redirects, HTTPS, HTTP/2/3 |
| `edge_functions` | 20 | JS Edge Functions, PMUSER variables, deployment |
| `security` | 20 | WAF, DDoS, IP blocklists, rate limiting |
| `performance` | 20 | Cache optimization, compression, purge, prefetch |
| `api_usage` | 20 | API auth, SDK, tccli, API errors |
| `migration` | 15 | Akamai-to-EdgeOne migration concepts |
| `troubleshooting` | 12 | 5xx errors, cache misses, latency spikes |
| `billing` | 10 | Traffic billing, cost optimization, usage reports |

## Adding New Questions

Append to `golden_questions.json`, incrementing the numeric ID:

```json
{
  "id": "GQ-143",
  "category": "configuration",
  "question": "Your question here?",
  "expected_topics": ["keyword1", "keyword2", "keyword3"],
  "difficulty": "medium"
}
```

Keep `expected_topics` to 3–5 relevant keywords. The runner does not currently validate coverage against these; they serve as documentation.

## Viewing Past Results

Results are written to `eval/results/eval_YYYYMMDDTHHMMSSZ.json`. Each file contains:

- `aggregate` — overall metrics and threshold check results
- `per_category` — breakdown by category
- `questions` — per-question scores, latencies, and no-answer flags

```bash
# List past runs
ls eval/results/

# View the latest summary (requires jq)
cat eval/results/$(ls eval/results/ | tail -1) | jq '.aggregate'
```

## CI Integration

The `eval-gate` job in `.github/workflows/ci.yml` runs automatically on every PR to `main`. It:

1. Spins up Qdrant, Postgres, and Redis services
2. Starts the FastAPI server
3. Runs `run_eval.py --limit 20` (sample for speed)
4. Uploads results as a GitHub Actions artifact
5. Fails the PR check if any threshold is breached
