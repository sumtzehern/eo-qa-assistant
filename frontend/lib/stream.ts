import type { Citation } from "@/store/chat";

export interface SSEToken {
  token?: string;
  done?: boolean;
  citations?: Citation[];
  confidence?: number;
  no_answer?: boolean;
  follow_up_questions?: string[];
  error?: string;
}

export async function* readSSEStream(
  response: Response
): AsyncGenerator<SSEToken> {
  if (!response.body) {
    throw new Error("Response body is null");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep incomplete last line in buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(":")) continue; // skip comments/empty

        if (trimmed.startsWith("data: ")) {
          const data = trimmed.slice(6).trim();
          if (data === "[DONE]") {
            yield { done: true };
            return;
          }
          try {
            const parsed = JSON.parse(data) as SSEToken;
            yield parsed;
          } catch {
            // Malformed JSON — skip
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
