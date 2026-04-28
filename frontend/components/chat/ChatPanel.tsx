"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/store/chat";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";

interface ChatPanelProps {
  messages: Message[];
}

export default function ChatPanel({ messages }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center overflow-y-auto p-6">
        <div className="text-center">
          <p className="text-2xl font-semibold text-white mb-2">EdgeOne QA</p>
          <p className="text-sm" style={{ color: "#94A3B8" }}>
            Ask anything about EdgeOne documentation
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} content={message.content} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
