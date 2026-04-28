"use client";

import { useStrings } from "@/lib/i18n";

interface FollowUpPillsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export default function FollowUpPills({ questions, onSelect }: FollowUpPillsProps) {
  const t = useStrings();

  if (questions.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="text-xs mb-2" style={{ color: "#94A3B8" }}>
        {t.followUpLabel}
      </p>
      <div className="flex flex-wrap gap-2">
        {questions.slice(0, 3).map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="text-xs rounded-md px-3 py-1.5 transition-colors text-left"
            style={{
              backgroundColor: "#1C1C1C",
              border: "1px solid #2A2A2A",
              color: "#94A3B8",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "#ffffff";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "#94A3B8";
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
