import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "enterprise-bg": "#111111",
        "enterprise-card": "#1C1C1C",
        "enterprise-border": "#2A2A2A",
        "enterprise-secondary": "#94A3B8",
        "enterprise-green": "#6EE7B7",
        "enterprise-red": "#F87171",
        "enterprise-amber": "#FBBF24",
        "enterprise-blue": "#60A5FA",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
