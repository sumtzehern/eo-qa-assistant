import type { Citation } from "@/store/chat";
import { readSSEStream, type SSEToken } from "./stream";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  };
}

export interface QueryRequest {
  query: string;
  session_id: string;
  language?: "en" | "zh";
}

export interface QueryResponse {
  query_id: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  no_answer: boolean;
  follow_up_questions: string[];
}

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    throw new Error(`Query failed: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<QueryResponse>;
}

export async function* streamQuery(
  request: QueryRequest
): AsyncGenerator<SSEToken> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: {
      ...headers(),
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!res.ok) {
    throw new Error(`Stream query failed: ${res.status} ${res.statusText}`);
  }

  yield* readSSEStream(res);
}

export interface SourceRecord {
  source_id: string;
  name: string;
  url: string;
  chunk_count: number;
  last_ingested: string;
  status: "healthy" | "failed" | "stale";
}

export async function getSources(): Promise<SourceRecord[]> {
  const res = await fetch(`${API_BASE}/sources`, { headers: headers() });
  if (!res.ok) throw new Error(`getSources failed: ${res.status}`);
  return res.json() as Promise<SourceRecord[]>;
}

export interface EvalSummary {
  period_days: number;
  total_queries: number;
  avg_groundedness: number | null;
  avg_retrieval_relevance: number | null;
  avg_citation_accuracy: number | null;
  avg_completeness: number | null;
  avg_overall_score: number | null;
  hallucination_rate: number | null;
  no_answer_rate: number | null;
  flagged_count: number;
  cache_hit_rate: number | null;
}

export async function getEvalSummary(): Promise<EvalSummary> {
  const res = await fetch(`${API_BASE}/eval/summary`, { headers: headers() });
  if (!res.ok) throw new Error(`getEvalSummary failed: ${res.status}`);
  return res.json() as Promise<EvalSummary>;
}

export interface FlaggedQuery {
  eval_id: string;
  query_id: string;
  query_text: string | null;
  flag_reason: string | null;
  groundedness: number | null;
  overall_score: number | null;
  hallucination: boolean | null;
  reviewed: boolean;
  completed_at: string | null;
}

export interface FlaggedQueriesResponse {
  items: FlaggedQuery[];
  total: number;
}

export async function getFlaggedQueries(
  reviewed?: boolean,
  limit: number = 50,
  offset: number = 0
): Promise<FlaggedQueriesResponse> {
  const params = new URLSearchParams();
  if (reviewed !== undefined) params.set("reviewed", String(reviewed));
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const res = await fetch(`${API_BASE}/admin/eval/flagged?${params}`, { headers: headers() });
  if (!res.ok) throw new Error(`getFlaggedQueries failed: ${res.status}`);
  return res.json() as Promise<FlaggedQueriesResponse>;
}

export async function reviewFlaggedQuery(
  evalId: string,
  reviewed: boolean
): Promise<FlaggedQuery> {
  const res = await fetch(`${API_BASE}/admin/eval/flagged/${evalId}`, {
    method: "PATCH",
    headers: headers(),
    body: JSON.stringify({ reviewed }),
  });
  if (!res.ok) throw new Error(`reviewFlaggedQuery failed: ${res.status}`);
  return res.json() as Promise<FlaggedQuery>;
}
