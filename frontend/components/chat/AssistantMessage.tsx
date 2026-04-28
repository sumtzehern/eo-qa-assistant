"use client";

import type { Message } from "@/store/chat";
import { useChatStore } from "@/store/chat";
import { useStrings } from "@/lib/i18n";
import CodeBlock from "./CodeBlock";

interface AssistantMessageProps {
  message: Message;
}

// Parse content and inject citation badges
function renderContent(
  content: string,
  onCitationHover: (index: number | null) => void
) {
  // Split on citation patterns like [1], [2], etc.
  const parts = content.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const citMatch = part.match(/^\[(\d+)\]$/);
    if (citMatch) {
      const idx = parseInt(citMatch[1], 10);
      return (
        <CitationBadge
          key={i}
          index={idx}
          onHover={onCitationHover}
        />
      );
    }
    // Check for code blocks
    if (part.includes("```")) {
      return <InlineCode key={i} text={part} />;
    }
    return <span key={i}>{part}</span>;
  });
}

function InlineCode({ text }: { text: string }) {
  const segments = text.split(/(```[\s\S]*?```)/g);
  return (
    <>
      {segments.map((seg, i) => {
        const codeMatch = seg.match(/^```(\w*)\n?([\s\S]*?)```$/);
        if (codeMatch) {
          return (
            <CodeBlock key={i} language={codeMatch[1] || "text"} code={codeMatch[2]} />
          );
        }
        return <span key={i}>{seg}</span>;
      })}
    </>
  );
}

function CitationBadge({
  index,
  onHover,
}: {
  index: number;
  onHover: (idx: number | null) => void;
}) {
  return (
    <sup
      className="inline-flex items-center justify-center cursor-pointer mx-0.5 transition-colors"
      style={{
        backgroundColor: "#2A2A2A",
        color: "#94A3B8",
        borderRadius: "3px",
        padding: "1px 4px",
        fontSize: "10px",
        lineHeight: "14px",
        verticalAlign: "super",
      }}
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
    >
      {index}
    </sup>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="inline-block w-1.5 h-1.5 rounded-full animate-bounce"
          style={{
            backgroundColor: "#94A3B8",
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function AssistantMessage({ message }: AssistantMessageProps) {
  const t = useStrings();
  const setActiveCitationIndex = useChatStore((s) => s.setActiveCitationIndex);

  if (message.isStreaming && !message.content) {
    return (
      <div className="flex justify-start">
        <div className="text-sm">
          <TypingIndicator />
        </div>
      </div>
    );
  }

  if (message.no_answer) {
    return (
      <div className="flex justify-start">
        <p className="text-sm italic" style={{ color: "#94A3B8" }}>
          {t.noAnswer}
        </p>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full text-sm text-white leading-relaxed">
        <div className="prose prose-invert max-w-none">
          {renderContent(message.content, setActiveCitationIndex)}
          {message.isStreaming && <TypingIndicator />}
        </div>

        {/* Confidence badge */}
        {message.confidence !== null && message.confidence > 0 && (
          <div className="flex justify-end mt-2">
            <span
              className="text-xs"
              style={{ color: "#6EE7B7" }}
            >
              {t.score}: {message.confidence.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
