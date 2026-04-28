import { create } from "zustand";

interface LanguageStore {
  language: "en" | "zh";
  setLanguage: (lang: "en" | "zh") => void;
}

export const useLanguageStore = create<LanguageStore>((set) => ({
  language: "en",
  setLanguage: (lang) => set({ language: lang }),
}));
