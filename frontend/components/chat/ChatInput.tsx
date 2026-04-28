"use client";

import { useRef, KeyboardEvent } from "react";
import { useStrings } from "@/lib/i18n";
import FollowUpPills from "./FollowUpPills";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  isLoading: boolean;
  followUpQuestions: string[];
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading,
  followUpQuestions,
}: ChatInputProps) {
  const t = useStrings();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (!isLoading && value.trim()) {
        onSubmit(value);
      }
    }
  }

  function handleSubmitClick() {
    if (!isLoading && value.trim()) {
      onSubmit(value);
    }
  }

  function handleFollowUpSelect(question: string) {
    onChange(question);
    setTimeout(() => textareaRef.current?.focus(), 0);
  }

  return (
    <div>
      {followUpQuestions.length > 0 && (
        <FollowUpPills
          questions={followUpQuestions}
          onSelect={handleFollowUpSelect}
        />
      )}
      <div
        className="flex items-end gap-2 mt-2 rounded-lg px-3 py-2"
        style={{
          backgroundColor: "#1C1C1C",
          border: "1px solid #2A2A2A",
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t.askPlaceholder}
          disabled={isLoading}
          rows={1}
          className="flex-1 bg-transparent text-white text-sm resize-none outline-none placeholder:text-enterprise-secondary leading-relaxed"
          style={{
            minHeight: "24px",
            maxHeight: "120px",
          }}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
          }}
        />

        {/* Gear icon (no-op) */}
        <button
          className="flex-none text-enterprise-secondary hover:text-white transition-colors p-1"
          aria-label="Options"
          tabIndex={-1}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>

        {/* Submit button */}
        <button
          onClick={handleSubmitClick}
          disabled={isLoading || !value.trim()}
          className="flex-none rounded px-3 py-1.5 text-xs font-medium transition-colors"
          style={{
            backgroundColor: isLoading || !value.trim() ? "#2A2A2A" : "#ffffff",
            color: isLoading || !value.trim() ? "#94A3B8" : "#111111",
            cursor: isLoading || !value.trim() ? "not-allowed" : "pointer",
          }}
        >
          {isLoading ? (
            <span className="flex items-center gap-1.5">
              <svg
                className="animate-spin"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </span>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-xs mt-1 text-right" style={{ color: "#2A2A2A" }}>
        Ctrl+Enter to send
      </p>
    </div>
  );
}
