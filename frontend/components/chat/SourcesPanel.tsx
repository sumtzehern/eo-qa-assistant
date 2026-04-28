"use client";

import type { Citation } from "@/store/chat";
import { useChatStore } from "@/store/chat";
import { useStrings } from "@/lib/i18n";
import SourceCard from "./SourceCard";

interface SourcesPanelProps {
  citations: Citation[];
}

export default function SourcesPanel({ citations }: SourcesPanelProps) {
  const t = useStrings();
  const activeCitationIndex = useChatStore((s) => s.activeCitationIndex);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Sticky title */}
      <div
        className="px-4 py-3 flex-none"
        style={{ borderBottom: "1px solid #2A2A2A" }}
      >
        <span
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "#94A3B8" }}
        >
          {t.sources}
        </span>
      </div>

      {/* Source cards list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {citations.length === 0 ? (
          <p className="text-sm text-center mt-8" style={{ color: "#94A3B8" }}>
            {t.emptySources}
          </p>
        ) : (
          citations.map((citation) => (
            <SourceCard
              key={citation.index}
              citation={citation}
              highlighted={activeCitationIndex === citation.index}
            />
          ))
        )}
      </div>
    </div>
  );
}
