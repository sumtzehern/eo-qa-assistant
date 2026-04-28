"use client";

import { useStrings } from "@/lib/i18n";

interface FlaggedRow {
  id: string;
  query: string;
  score: number;
  reason: string;
  status: "review" | "resolved";
}

const MOCK_FLAGGED_DATA: FlaggedRow[] = [
  {
    id: "1",
    query: "How do I configure wildcard SSL for EdgeOne?",
    score: 0.61,
    reason: "Groundedness below threshold",
    status: "review",
  },
  {
    id: "2",
    query: "What are EdgeOne's rate limiting options?",
    score: 0.58,
    reason: "Hallucination detected",
    status: "review",
  },
  {
    id: "3",
    query: "Can EdgeOne handle WebSocket traffic?",
    score: 0.72,
    reason: "Completeness low",
    status: "resolved",
  },
  {
    id: "4",
    query: "How to migrate Akamai SureRoute to EdgeOne?",
    score: 0.60,
    reason: "Overall score below threshold",
    status: "review",
  },
];

function ScorePill({ score }: { score: number }) {
  const color = score >= 0.85 ? "#6EE7B7" : score < 0.7 ? "#F87171" : "#FBBF24";
  return (
    <span className="text-xs font-mono" style={{ color }}>
      {score.toFixed(2)}
    </span>
  );
}

function StatusPill({ status }: { status: "review" | "resolved" }) {
  const isReview = status === "review";
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-sm font-medium"
      style={{
        backgroundColor: isReview ? "rgba(251,191,36,0.1)" : "rgba(110,231,183,0.1)",
        color: isReview ? "#FBBF24" : "#6EE7B7",
        border: `1px solid ${isReview ? "rgba(251,191,36,0.3)" : "rgba(110,231,183,0.3)"}`,
      }}
    >
      {isReview ? "Review" : "Resolved"}
    </span>
  );
}

export default function FlaggedTable() {
  const t = useStrings();

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        backgroundColor: "#1C1C1C",
        border: "1px solid #2A2A2A",
      }}
    >
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: "1px solid #2A2A2A" }}>
            {[t.query, t.scoreLabel, t.reason, t.status].map((col) => (
              <th
                key={col}
                className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest"
                style={{ color: "#94A3B8" }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MOCK_FLAGGED_DATA.map((row, i) => (
            <tr
              key={row.id}
              style={{
                borderBottom:
                  i < MOCK_FLAGGED_DATA.length - 1 ? "1px solid #2A2A2A" : "none",
              }}
            >
              <td className="px-4 py-3 text-white max-w-xs">
                <span className="truncate block" title={row.query}>
                  {row.query}
                </span>
              </td>
              <td className="px-4 py-3">
                <ScorePill score={row.score} />
              </td>
              <td className="px-4 py-3 text-xs" style={{ color: "#94A3B8" }}>
                {row.reason}
              </td>
              <td className="px-4 py-3">
                <StatusPill status={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
