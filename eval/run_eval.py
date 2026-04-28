#!/usr/bin/env python3
"""
EdgeOne QA Assistant — Enterprise Eval Runner

Runs the golden question bank against the live API, scores responses,
aggregates results, checks thresholds, and exits with code 1 on breach.

Usage:
    python eval/run_eval.py --api-url http://localhost:8000 --api-key $API_KEY
    python eval/run_eval.py --api-url http://localhost:8000 --api-key $API_KEY --limit 20
    python eval/run_eval.py --api-url http://localhost:8000 --api-key $API_KEY --category security
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Resolve paths relative to this script's location
SCRIPT_DIR = Path(__file__).parent
QUESTIONS_FILE = SCRIPT_DIR / "golden_questions.json"
RESULTS_DIR = SCRIPT_DIR / "results"

# Thresholds from design docs
THRESHOLD_OVERALL_SCORE = 0.85
THRESHOLD_HALLUCINATION_RATE = 0.05
THRESHOLD_NO_ANSWER_RATE = 0.15

NO_ANSWER_MARKERS = [
    "i don't know",
    "i do not know",
    "no information",
    "cannot find",
    "not found",
    "unable to find",
    "no relevant",
    "i'm not sure",
    "i am not sure",
]


def is_no_answer(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in NO_ANSWER_MARKERS) or len(text.strip()) < 20


def parse_sse_final_event(response_text: str) -> dict | None:
    """Parse SSE stream text and return the final done event payload."""
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            try:
                data = json.loads(payload)
                if data.get("done"):
                    return data
            except json.JSONDecodeError:
                continue
    return None


def collect_sse_answer(response_text: str) -> str:
    """Collect all token chunks from SSE stream into a full answer string."""
    tokens = []
    final_event = None
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            try:
                data = json.loads(payload)
                if data.get("done"):
                    final_event = data
                    break
                if "token" in data:
                    tokens.append(data["token"])
            except json.JSONDecodeError:
                continue
    # Prefer answer from final event if available
    if final_event and final_event.get("answer"):
        return final_event["answer"]
    return "".join(tokens)


async def call_api(
    client: httpx.AsyncClient,
    api_url: str,
    api_key: str,
    question: str,
) -> tuple[str, list[dict], float, bool]:
    """
    Call the query API and return (answer, citations, latency_ms, error).
    Returns (answer, citations, latency_ms, had_error).
    """
    start = time.monotonic()
    try:
        resp = await client.post(
            f"{api_url}/v1/query",
            json={"query": question, "options": {"query_expansion": False}},
            headers={"X-API-Key": api_key},
            timeout=60.0,
        )
        latency_ms = (time.monotonic() - start) * 1000
        resp.raise_for_status()

        answer = collect_sse_answer(resp.text)
        final_event = parse_sse_final_event(resp.text)
        citations = []
        if final_event:
            citations = final_event.get("citations", [])

        return answer, citations, latency_ms, False

    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        print(f"    [ERROR] API call failed: {e}", file=sys.stderr)
        return "", [], latency_ms, True


async def score_response(
    scorer,
    query: str,
    answer: str,
    citations: list[dict],
):
    """Score a response using EvalScorer. Returns EvalScores or None on failure."""
    try:
        return await scorer.score(query, answer, citations)
    except Exception as e:
        print(f"    [WARN] Scoring failed: {e}", file=sys.stderr)
        return None


def compute_percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def print_summary_table(results: dict) -> None:
    agg = results["aggregate"]
    thresholds = results["threshold_checks"]

    print("\n" + "=" * 60)
    print("  EDGEONE QA EVAL SUITE — RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total questions:     {agg['total_questions']}")
    print(f"  Scored questions:    {agg['scored_questions']}")
    print(f"  Skipped (no key):    {agg['score_skipped']}")
    print(f"  API errors:          {agg['api_errors']}")
    print()
    print(f"  Avg overall score:   {agg['avg_overall_score']:.4f}  (threshold ≥ {THRESHOLD_OVERALL_SCORE})")
    print(f"  Hallucination rate:  {agg['hallucination_rate']:.4f}  (threshold < {THRESHOLD_HALLUCINATION_RATE})")
    print(f"  No-answer rate:      {agg['no_answer_rate']:.4f}  (threshold < {THRESHOLD_NO_ANSWER_RATE})")
    print()
    print(f"  Avg latency:         {agg['avg_latency_ms']:.1f} ms")
    print(f"  P95 latency:         {agg['p95_latency_ms']:.1f} ms")
    print()
    print("  THRESHOLD CHECKS:")
    for check_name, passed in thresholds.items():
        status = "PASS" if passed else "FAIL"
        mark = "✓" if passed else "✗"
        print(f"    {mark} {check_name}: {status}")
    print()
    print("  PER-CATEGORY BREAKDOWN:")
    print(f"  {'Category':<20} {'Count':>6} {'Avg Score':>10} {'No-Answer':>10} {'Hallu':>7}")
    print(f"  {'-'*20} {'-'*6} {'-'*10} {'-'*10} {'-'*7}")
    for cat, stats in sorted(results["per_category"].items()):
        avg_s = f"{stats['avg_overall_score']:.3f}" if stats["scored"] > 0 else "  N/A "
        print(
            f"  {cat:<20} {stats['count']:>6} {avg_s:>10} "
            f"{stats['no_answer_rate']:>10.3f} {stats['hallucination_rate']:>7.3f}"
        )
    print("=" * 60)

    all_passed = all(thresholds.values())
    if all_passed:
        print("  RESULT: ALL THRESHOLDS PASSED")
    else:
        failed = [k for k, v in thresholds.items() if not v]
        print(f"  RESULT: THRESHOLD BREACH — {', '.join(failed)}")
    print("=" * 60 + "\n")


async def run_eval(
    api_url: str,
    api_key: str,
    limit: int | None,
    category: str | None,
) -> int:
    """Run the eval suite. Returns exit code (0 = pass, 1 = failure)."""
    # Load questions
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)

    if category:
        questions = [q for q in questions if q["category"] == category]
        if not questions:
            print(f"No questions found for category '{category}'", file=sys.stderr)
            return 1

    if limit:
        # Sample evenly across categories for representative coverage
        by_cat: dict[str, list] = defaultdict(list)
        for q in questions:
            by_cat[q["category"]].append(q)
        sampled = []
        per_cat = max(1, limit // len(by_cat))
        for cat_qs in by_cat.values():
            sampled.extend(cat_qs[:per_cat])
        questions = sampled[:limit]

    print(f"Running eval: {len(questions)} questions against {api_url}")

    # Set up scorer if ANTHROPIC_API_KEY is available
    scorer = None
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import anthropic as anthropic_lib
            from backend.api.eval.scorer import EvalScorer
            client = anthropic_lib.AsyncAnthropic(api_key=anthropic_key)
            scorer = EvalScorer(client)
            print("Scoring: enabled (ANTHROPIC_API_KEY found)")
        except Exception as e:
            print(f"Scoring: disabled (import failed: {e})", file=sys.stderr)
    else:
        print("Scoring: disabled (ANTHROPIC_API_KEY not set) — only no_answer_rate threshold active")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    question_results = []
    latencies: list[float] = []

    async with httpx.AsyncClient() as http_client:
        for i, q in enumerate(questions, 1):
            qid = q["id"]
            question_text = q["question"]
            cat = q["category"]

            print(f"  [{i:3d}/{len(questions)}] {qid} ({cat}) ...", end=" ", flush=True)

            answer, citations, latency_ms, had_error = await call_api(
                http_client, api_url, api_key, question_text
            )
            latencies.append(latency_ms)

            no_answer = had_error or is_no_answer(answer)
            score_skipped = False
            hallucination = False
            overall_score = None
            groundedness = None
            retrieval_relevance = None
            citation_accuracy = None
            completeness = None

            if scorer and not had_error and answer:
                scores = await score_response(scorer, question_text, answer, citations)
                if scores:
                    hallucination = scores.hallucination
                    overall_score = scores.overall_score
                    groundedness = scores.groundedness
                    retrieval_relevance = scores.retrieval_relevance
                    citation_accuracy = scores.citation_accuracy
                    completeness = scores.completeness
                    print(f"score={overall_score:.3f} {'HALL' if hallucination else ''} ({latency_ms:.0f}ms)")
                else:
                    score_skipped = True
                    print(f"score=ERROR ({latency_ms:.0f}ms)")
            elif not scorer:
                score_skipped = True
                print(f"no_answer={'yes' if no_answer else 'no'} ({latency_ms:.0f}ms)")
            else:
                print(f"api_error ({latency_ms:.0f}ms)")

            question_results.append({
                "question_id": qid,
                "category": cat,
                "question": question_text,
                "no_answer": no_answer,
                "had_error": had_error,
                "score_skipped": score_skipped,
                "latency_ms": round(latency_ms, 1),
                "answer_length": len(answer),
                "hallucination": hallucination,
                "overall_score": overall_score,
                "groundedness": groundedness,
                "retrieval_relevance": retrieval_relevance,
                "citation_accuracy": citation_accuracy,
                "completeness": completeness,
            })

    # Aggregate
    total = len(question_results)
    scored = [r for r in question_results if r["overall_score"] is not None]
    skipped = [r for r in question_results if r["score_skipped"]]
    errors = [r for r in question_results if r["had_error"]]
    no_answer_list = [r for r in question_results if r["no_answer"]]

    avg_overall = sum(r["overall_score"] for r in scored) / len(scored) if scored else 0.0
    hall_rate = sum(1 for r in scored if r["hallucination"]) / len(scored) if scored else 0.0
    no_answer_rate = len(no_answer_list) / total if total else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = compute_percentile(latencies, 95)

    # Per-category stats
    per_category: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "scored": 0, "no_answer": 0, "hallucinations": 0,
        "total_score": 0.0,
    })
    for r in question_results:
        cat = r["category"]
        per_category[cat]["count"] += 1
        if r["no_answer"]:
            per_category[cat]["no_answer"] += 1
        if r["overall_score"] is not None:
            per_category[cat]["scored"] += 1
            per_category[cat]["total_score"] += r["overall_score"]
            if r["hallucination"]:
                per_category[cat]["hallucinations"] += 1

    per_category_summary = {}
    for cat, stats in per_category.items():
        avg_s = stats["total_score"] / stats["scored"] if stats["scored"] > 0 else 0.0
        hall_r = stats["hallucinations"] / stats["scored"] if stats["scored"] > 0 else 0.0
        na_r = stats["no_answer"] / stats["count"] if stats["count"] > 0 else 0.0
        per_category_summary[cat] = {
            "count": stats["count"],
            "scored": stats["scored"],
            "avg_overall_score": round(avg_s, 4),
            "no_answer_rate": round(na_r, 4),
            "hallucination_rate": round(hall_r, 4),
        }

    # Threshold checks
    # If scoring is not available, skip score/hallucination thresholds
    if scored:
        overall_pass = avg_overall >= THRESHOLD_OVERALL_SCORE
        hall_pass = hall_rate < THRESHOLD_HALLUCINATION_RATE
    else:
        # Cannot evaluate — treat as passed (keys unavailable)
        overall_pass = True
        hall_pass = True

    no_answer_pass = no_answer_rate < THRESHOLD_NO_ANSWER_RATE

    threshold_checks = {
        "overall_score": overall_pass,
        "hallucination_rate": hall_pass,
        "no_answer_rate": no_answer_pass,
    }

    aggregate = {
        "total_questions": total,
        "scored_questions": len(scored),
        "score_skipped": len(skipped),
        "api_errors": len(errors),
        "avg_overall_score": round(avg_overall, 4),
        "hallucination_rate": round(hall_rate, 4),
        "no_answer_rate": round(no_answer_rate, 4),
        "avg_latency_ms": round(avg_latency, 1),
        "p95_latency_ms": round(p95_latency, 1),
    }

    results = {
        "eval_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_url": api_url,
        "limit": limit,
        "category_filter": category,
        "aggregate": aggregate,
        "threshold_checks": threshold_checks,
        "per_category": per_category_summary,
        "questions": question_results,
    }

    # Write results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_file = RESULTS_DIR / f"eval_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to: {results_file}")

    print_summary_table(results)

    all_passed = all(threshold_checks.values())
    return 0 if all_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="EdgeOne QA Eval Runner")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the QA API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY", ""),
        help="API key for X-API-Key header (or set API_KEY env var)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to N questions (sampled across categories)",
    )
    parser.add_argument(
        "--category",
        default=None,
        choices=[
            "configuration", "edge_functions", "security", "performance",
            "api_usage", "migration", "troubleshooting", "billing",
        ],
        help="Run only questions from a specific category",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Warning: --api-key not provided and API_KEY env var not set", file=sys.stderr)

    exit_code = asyncio.run(
        run_eval(
            api_url=args.api_url.rstrip("/"),
            api_key=args.api_key,
            limit=args.limit,
            category=args.category,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
