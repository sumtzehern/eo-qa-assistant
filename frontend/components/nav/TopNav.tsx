"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguageStore } from "@/store/language";

const NAV_LINKS = [
  { label: "Chat", href: "/" },
  { label: "History", href: "/history" },
  { label: "Sources", href: "/sources" },
  { label: "Admin", href: "/admin" },
];

export default function TopNav() {
  const pathname = usePathname();
  const { language, setLanguage } = useLanguageStore();

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center px-6"
      style={{
        height: "56px",
        backgroundColor: "#111111",
        borderBottom: "1px solid #2A2A2A",
      }}
    >
      {/* Logo */}
      <div className="flex-none mr-8">
        <span className="text-white font-semibold text-base tracking-tight">
          EdgeOne QA
        </span>
      </div>

      {/* Center nav links */}
      <div className="flex items-center gap-6 flex-1">
        {NAV_LINKS.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm transition-colors"
              style={{ color: isActive ? "#ffffff" : "#94A3B8" }}
            >
              {link.label}
            </Link>
          );
        })}
      </div>

      {/* Right: language toggle + avatar */}
      <div className="flex items-center gap-3">
        <div
          className="flex items-center rounded"
          style={{ border: "1px solid #2A2A2A", overflow: "hidden" }}
        >
          <button
            onClick={() => setLanguage("en")}
            className="px-3 py-1 text-xs transition-colors"
            style={{
              backgroundColor: language === "en" ? "#2A2A2A" : "transparent",
              color: language === "en" ? "#ffffff" : "#94A3B8",
            }}
          >
            EN
          </button>
          <button
            onClick={() => setLanguage("zh")}
            className="px-3 py-1 text-xs transition-colors"
            style={{
              backgroundColor: language === "zh" ? "#2A2A2A" : "transparent",
              color: language === "zh" ? "#ffffff" : "#94A3B8",
            }}
          >
            中文
          </button>
        </div>

        {/* User avatar placeholder */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium"
          style={{ backgroundColor: "#2A2A2A", color: "#94A3B8" }}
        >
          U
        </div>
      </div>
    </nav>
  );
}
