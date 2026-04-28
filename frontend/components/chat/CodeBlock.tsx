"use client";

import { useState } from "react";
import { useStrings } from "@/lib/i18n";

interface CodeBlockProps {
  language: string;
  code: string;
}

export default function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const t = useStrings();

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable — silently ignore
    }
  }

  return (
    <div
      className="relative rounded-lg my-3 overflow-hidden"
      style={{ backgroundColor: "#0A0A0A", border: "1px solid #2A2A2A" }}
    >
      {/* Header bar */}
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: "1px solid #2A2A2A" }}
      >
        <span className="text-xs font-mono" style={{ color: "#94A3B8" }}>
          {language || "text"}
        </span>
        <button
          onClick={handleCopy}
          className="text-xs transition-colors"
          style={{ color: copied ? "#6EE7B7" : "#94A3B8" }}
        >
          {copied ? t.copied : t.copyCode}
        </button>
      </div>

      {/* Code content */}
      <pre className="overflow-x-auto px-4 py-3">
        <code
          className="text-xs font-mono leading-relaxed text-white"
          style={{ whiteSpace: "pre" }}
        >
          {code}
        </code>
      </pre>
    </div>
  );
}
