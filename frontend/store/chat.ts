import { create } from "zustand";

export interface Citation {
  index: number;
  title: string;
  url: string;
  excerpt: string;
  relevance: number;
  source_id: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  confidence: number | null;
  no_answer: boolean;
  isStreaming: boolean;
  followUpQuestions: string[];
}

interface ChatStore {
  messages: Message[];
  isLoading: boolean;
  currentSessionId: string;
  activeCitationIndex: number | null;
  setActiveCitationIndex: (index: number | null) => void;
  addUserMessage: (query: string) => string;
  startAssistantMessage: (id: string) => void;
  appendToken: (id: string, token: string) => void;
  finalizeMessage: (
    id: string,
    citations: Citation[],
    confidence: number,
    followUpQuestions?: string[]
  ) => void;
  setNoAnswer: (id: string) => void;
  clearSession: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,
  currentSessionId: crypto.randomUUID(),
  activeCitationIndex: null,

  setActiveCitationIndex: (index) => set({ activeCitationIndex: index }),

  addUserMessage: (query: string) => {
    const id = crypto.randomUUID();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "user",
          content: query,
          citations: [],
          confidence: null,
          no_answer: false,
          isStreaming: false,
          followUpQuestions: [],
        },
      ],
      isLoading: true,
    }));
    return id;
  },

  startAssistantMessage: (id: string) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "assistant",
          content: "",
          citations: [],
          confidence: null,
          no_answer: false,
          isStreaming: true,
          followUpQuestions: [],
        },
      ],
    }));
  },

  appendToken: (id: string, token: string) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    }));
  },

  finalizeMessage: (
    id: string,
    citations: Citation[],
    confidence: number,
    followUpQuestions: string[] = []
  ) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id
          ? { ...m, citations, confidence, followUpQuestions, isStreaming: false }
          : m
      ),
      isLoading: false,
    }));
  },

  setNoAnswer: (id: string) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, no_answer: true, isStreaming: false } : m
      ),
      isLoading: false,
    }));
  },

  clearSession: () => {
    set({
      messages: [],
      isLoading: false,
      currentSessionId: crypto.randomUUID(),
      activeCitationIndex: null,
    });
  },
}));
