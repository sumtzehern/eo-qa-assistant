"use client";

import { useEffect, useState } from "react";
import { useStrings } from "@/lib/i18n";
import { getFlaggedQueries, reviewFlaggedQuery, type FlaggedQuery } from "@/lib/api";

function ScorePill({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs font-mono" style={{ color: "#94A3B8" }}>—</span>;
  const color = score >= 0.85 ? "#6EE7B7" : score < 0.7 ? "#F87171" : "#FBBF24";
  return (
    <span className="text-xs font-mono" style={{ color }}>
      {score.toFixed(2)}
    </span>
  );
}

function StatusPill({
  reviewed,
  evalId,
  onToggle,
}: {
  reviewed: boolean;
  evalId: string;
  onToggle: (evalId: string, reviewed: boolean) => void;
}) {
  const isReview = !reviewed;
  return (
    <button
      onClick={() => onToggle(evalId, !reviewed)}
      className="text-xs px-2 py-0.5 rounded-sm font-medium cursor-pointer"
      style={{
        backgroundColor: isReview ? "rgba(251,191,36,0.1)" : "rgba(110,231,183,0.1)",
        color: isReview ? "#FBBF24" : "#6EE7B7",
        border: `1px solid ${isReview ? "rgba(251,191,36,0.3)" : "rgba(110,231,183,0.3)"}`,
      }}
    >
      {isReview ? "Review" : "Resolved"}
    </button>
  );
}

export default function FlaggedTable() {
  const t = useStrings();
  const [rows, setRows] = useState<FlaggedQuery[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFlaggedQueries()
      .then((res) => setRows(res.items))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const handleToggleReview = async (evalId: string, reviewed: boolean) => {
    try {
      const updated = await reviewFlaggedQuery(evalId, reviewed);
      setRows((prev) =>
        prev.map((r) => (r.eval_id === evalId ? { ...r, reviewed: updated.reviewed } : r))
      );
    } catch {
      // silently ignore toggle errors
    }
  };

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        backgroundColor: "#1C1C1C",
        border: "1px solid #2A2A2A",
      }}
    >
      {loading ? (
        <div
          className="flex items-center justify-center py-8 text-xs"
          style={{ color: "#94A3B8" }}
        >
          Loading...
        </div>
      ) : (
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
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-xs" style={{ color: "#94A3B8" }}>
                  No flagged queries
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr
                  key={row.eval_id}
                  style={{
                    borderBottom: i < rows.length - 1 ? "1px solid #2A2A2A" : "none",
                  }}
                >
                  <td className="px-4 py-3 text-white max-w-xs">
                    <span className="truncate block" title={row.query_text ?? ""}>
                      {row.query_text ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ScorePill score={row.overall_score} />
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: "#94A3B8" }}>
                    {row.flag_reason ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill
                      reviewed={row.reviewed}
                      evalId={row.eval_id}
                      onToggle={handleToggleReview}
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
