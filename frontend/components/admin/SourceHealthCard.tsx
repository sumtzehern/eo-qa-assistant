"use client";

import { useStrings } from "@/lib/i18n";

interface SourceData {
  id: string;
  name: string;
  chunkCount: number;
  lastIngested: string;
  status: "healthy" | "failed" | "stale";
}

const MOCK_SOURCE_DATA: SourceData[] = [
  {
    id: "1",
    name: "EdgeOne Public Docs",
    chunkCount: 1243,
    lastIngested: "2026-04-28T06:00:00Z",
    status: "healthy",
  },
  {
    id: "2",
    name: "EdgeOne API Reference",
    chunkCount: 587,
    lastIngested: "2026-04-28T06:00:00Z",
    status: "healthy",
  },
  {
    id: "3",
    name: "tccli CLI Reference",
    chunkCount: 312,
    lastIngested: "2026-04-21T06:00:00Z",
    status: "stale",
  },
  {
    id: "4",
    name: "Migration Knowledge Base",
    chunkCount: 89,
    lastIngested: "2026-04-15T06:00:00Z",
    status: "failed",
  },
];

function StatusPill({ status }: { status: SourceData["status"] }) {
  const config = {
    healthy: { color: "#6EE7B7", bg: "rgba(110,231,183,0.1)", border: "rgba(110,231,183,0.3)", label: "Healthy" },
    failed: { color: "#F87171", bg: "rgba(248,113,113,0.1)", border: "rgba(248,113,113,0.3)", label: "Failed" },
    stale: { color: "#FBBF24", bg: "rgba(251,191,36,0.1)", border: "rgba(251,191,36,0.3)", label: "Stale" },
  }[status];

  return (
    <span
      className="text-xs px-2 py-0.5 rounded-sm font-medium"
      style={{
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
      }}
    >
      {config.label}
    </span>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function SourceHealthCard() {
  const t = useStrings();

  return (
    <>
      {MOCK_SOURCE_DATA.map((source) => (
        <div
          key={source.id}
          className="rounded-lg p-4 flex items-center justify-between"
          style={{
            backgroundColor: "#1C1C1C",
            border: "1px solid #2A2A2A",
          }}
        >
          <div>
            <p className="text-sm font-semibold text-white mb-1">{source.name}</p>
            <p className="text-xs" style={{ color: "#94A3B8" }}>
              {source.chunkCount.toLocaleString()} {t.chunks} &middot; {t.lastIngested}: {formatDate(source.lastIngested)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusPill status={source.status} />
            <button
              className="text-xs px-3 py-1.5 rounded transition-colors"
              style={{
                backgroundColor: "#2A2A2A",
                color: "#94A3B8",
                border: "1px solid #3A3A3A",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = "#ffffff";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = "#94A3B8";
              }}
            >
              {t.reIngest}
            </button>
          </div>
        </div>
      ))}
    </>
  );
}
