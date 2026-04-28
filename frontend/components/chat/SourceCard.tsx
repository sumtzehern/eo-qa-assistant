"use client";

import type { Citation } from "@/store/chat";
import { useChatStore } from "@/store/chat";

interface SourceCardProps {
  citation: Citation;
  highlighted: boolean;
}

export default function SourceCard({ citation, highlighted }: SourceCardProps) {
  const setActiveCitationIndex = useChatStore((s) => s.setActiveCitationIndex);

  return (
    <div
      className="relative rounded-lg p-3 transition-all"
      style={{
        backgroundColor: "#1C1C1C",
        border: `1px solid ${highlighted ? "#6EE7B7" : "#2A2A2A"}`,
      }}
      onMouseEnter={() => setActiveCitationIndex(citation.index)}
      onMouseLeave={() => setActiveCitationIndex(null)}
    >
      {/* Citation index badge */}
      <span
        className="absolute top-2 right-2 text-xs font-medium"
        style={{
          backgroundColor: "#2A2A2A",
          color: "#94A3B8",
          borderRadius: "3px",
          padding: "1px 5px",
          fontSize: "11px",
        }}
      >
        [{citation.index}]
      </span>

      {/* Title */}
      <p className="text-sm font-semibold text-white pr-8 mb-1 leading-snug">
        {citation.title}
      </p>

      {/* URL */}
      <p
        className="text-xs mb-2 truncate"
        style={{ color: "#94A3B8" }}
        title={citation.url}
      >
        {citation.url}
      </p>

      {/* Excerpt */}
      <p
        className="text-xs leading-relaxed"
        style={{
          color: "#94A3B8",
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {citation.excerpt}
      </p>

      {/* Relevance score bar */}
      <div className="mt-2">
        <div
          className="h-0.5 rounded-full"
          style={{ backgroundColor: "#2A2A2A" }}
        >
          <div
            className="h-0.5 rounded-full transition-all"
            style={{
              backgroundColor: "#6EE7B7",
              width: `${Math.round(citation.relevance * 100)}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
