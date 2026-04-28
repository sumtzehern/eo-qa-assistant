"use client";

import { useState, useRef } from "react";
import ChatPanel from "./ChatPanel";
import SourcesPanel from "./SourcesPanel";
import ChatInput from "./ChatInput";
import { useChatStore } from "@/store/chat";
import { streamQuery } from "@/lib/api";

export default function ChatInterface() {
  const {
    messages,
    isLoading,
    currentSessionId,
    addUserMessage,
    startAssistantMessage,
    appendToken,
    finalizeMessage,
    setNoAnswer,
  } = useChatStore();

  const [inputValue, setInputValue] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(query: string) {
    if (!query.trim() || isLoading) return;
    setInputValue("");

    addUserMessage(query);

    const assistantId = crypto.randomUUID();
    startAssistantMessage(assistantId);

    try {
      abortRef.current = new AbortController();
      for await (const event of streamQuery({
        query,
        session_id: currentSessionId,
      })) {
        if (event.done) {
          break;
        }
        if (event.token) {
          appendToken(assistantId, event.token);
        }
        if (event.no_answer) {
          setNoAnswer(assistantId);
          return;
        }
        if (event.citations && event.confidence !== undefined) {
          finalizeMessage(
            assistantId,
            event.citations,
            event.confidence,
            event.follow_up_questions ?? []
          );
          return;
        }
      }
      // If stream ended without finalize, finalize with empty citations
      finalizeMessage(assistantId, [], 0);
    } catch {
      finalizeMessage(assistantId, [], 0);
    }
  }

  const lastAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && !m.isStreaming);

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 56px)" }}>
      {/* Split panel area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat panel 60% */}
        <div className="flex flex-col" style={{ width: "60%" }}>
          <ChatPanel messages={messages} />
        </div>

        {/* Divider */}
        <div style={{ width: "1px", backgroundColor: "#2A2A2A", flexShrink: 0 }} />

        {/* Sources panel 40% */}
        <div style={{ width: "40%" }}>
          <SourcesPanel
            citations={lastAssistantMessage?.citations ?? []}
          />
        </div>
      </div>

      {/* Sticky input bar */}
      <div style={{ borderTop: "1px solid #2A2A2A", backgroundColor: "#111111" }}>
        <div className="max-w-5xl mx-auto px-4 py-3">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            followUpQuestions={lastAssistantMessage?.followUpQuestions ?? []}
          />
        </div>
      </div>
    </div>
  );
}
