"""Async eval scorer — Claude Haiku as judge.

Scores a single QA response on 5 dimensions asynchronously.
Designed to be called as a fire-and-forget asyncio.Task.
"""

import json
from dataclasses import dataclass

import anthropic

EVAL_PROMPT_TEMPLATE = """You are evaluating a RAG QA system response. Score it on these dimensions:

Query: {query}

Answer: {answer}

Retrieved chunks used:
{context}

Respond with ONLY valid JSON:
{{
  "groundedness": <0.0-1.0, fraction of claims supported by chunks>,
  "retrieval_relevance": <0.0-1.0, how relevant the chunks are to the query>,
  "citation_accuracy": <0.0-1.0, citations map correctly to claims>,
  "completeness": <0.0-1.0, query fully answered>,
  "hallucination": <true/false, any claim NOT in chunks>
}}"""

AUTO_FLAG_THRESHOLDS = {
    "groundedness": 0.7,    # flag if below
    "overall_score": 0.65,  # flag if below
    "hallucination": True,  # flag if hallucination detected
}


@dataclass
class EvalScores:
    groundedness: float
    retrieval_relevance: float
    citation_accuracy: float
    completeness: float
    hallucination: bool
    overall_score: float
    flagged: bool
    flag_reason: str | None


class EvalScorer:
    def __init__(
        self,
        anthropic_client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5",
    ):
        self._client = anthropic_client
        self._model = model

    async def score(
        self,
        query: str,
        answer: str,
        citations: list[dict],  # list of CitationItem dicts
    ) -> EvalScores:
        # Build context string from citations (snippet field)
        context = "\n".join(
            f"[{c.get('index', i + 1)}] {c.get('snippet', '')}"
            for i, c in enumerate(citations)
        )

        prompt = EVAL_PROMPT_TEMPLATE.format(query=query, answer=answer, context=context)

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
        except Exception:
            # On any LLM/parse failure, return neutral scores rather than crashing
            data = {
                "groundedness": 0.5,
                "retrieval_relevance": 0.5,
                "citation_accuracy": 0.5,
                "completeness": 0.5,
                "hallucination": False,
            }

        g = float(data.get("groundedness", 0.5))
        rr = float(data.get("retrieval_relevance", 0.5))
        ca = float(data.get("citation_accuracy", 0.5))
        co = float(data.get("completeness", 0.5))
        hall = bool(data.get("hallucination", False))
        overall = round((g + rr + ca + co) / 4, 4)

        # Auto-flag logic
        flagged = False
        flag_reason: str | None = None
        if g < AUTO_FLAG_THRESHOLDS["groundedness"]:
            flagged = True
            flag_reason = f"groundedness={g:.2f} below threshold"
        elif overall < AUTO_FLAG_THRESHOLDS["overall_score"]:
            flagged = True
            flag_reason = f"overall_score={overall:.2f} below threshold"
        elif hall:
            flagged = True
            flag_reason = "hallucination detected"

        return EvalScores(
            groundedness=g,
            retrieval_relevance=rr,
            citation_accuracy=ca,
            completeness=co,
            hallucination=hall,
            overall_score=overall,
            flagged=flagged,
            flag_reason=flag_reason,
        )
