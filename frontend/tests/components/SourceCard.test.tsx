import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SourceCard from "@/components/chat/SourceCard";
import type { Citation } from "@/store/chat";

// Mock zustand store
vi.mock("@/store/chat", async () => {
  const actual = await vi.importActual<typeof import("@/store/chat")>("@/store/chat");
  return {
    ...actual,
    useChatStore: (selector: (s: { setActiveCitationIndex: () => void; activeCitationIndex: null }) => unknown) =>
      selector({
        setActiveCitationIndex: () => {},
        activeCitationIndex: null,
      }),
  };
});

const mockCitation: Citation = {
  index: 1,
  title: "EdgeOne CDN Configuration",
  url: "https://docs.edgeone.io/en/configuration",
  excerpt: "This guide covers the core configuration options for EdgeOne CDN, including cache rules, routing policies, and security settings.",
  relevance: 0.87,
  source_id: "edgeone-docs",
};

describe("SourceCard", () => {
  it("renders title and URL", () => {
    render(<SourceCard citation={mockCitation} highlighted={false} />);
    expect(screen.getByText("EdgeOne CDN Configuration")).toBeDefined();
    expect(screen.getByText("https://docs.edgeone.io/en/configuration")).toBeDefined();
  });

  it("renders citation index badge", () => {
    render(<SourceCard citation={mockCitation} highlighted={false} />);
    expect(screen.getByText("[1]")).toBeDefined();
  });

  it("renders relevance bar with correct width", () => {
    const { container } = render(
      <SourceCard citation={mockCitation} highlighted={false} />
    );
    // Relevance bar is a div with width = relevance * 100%
    const bars = container.querySelectorAll("div[style*='width: 87%']");
    expect(bars.length).toBeGreaterThan(0);
  });

  it("shows highlighted border when highlighted=true", () => {
    const { container } = render(
      <SourceCard citation={mockCitation} highlighted={true} />
    );
    const card = container.firstChild as HTMLElement;
    // jsdom normalizes hex to rgb
    expect(card.style.border).toContain("rgb(110, 231, 183)");
  });

  it("shows un-highlighted border when highlighted=false", () => {
    const { container } = render(
      <SourceCard citation={mockCitation} highlighted={false} />
    );
    const card = container.firstChild as HTMLElement;
    // jsdom normalizes hex to rgb
    expect(card.style.border).toContain("rgb(42, 42, 42)");
  });

  it("truncates excerpt to 3 lines", () => {
    const { container } = render(
      <SourceCard citation={mockCitation} highlighted={false} />
    );
    const excerpt = container.querySelector("p:nth-child(4)");
    expect((excerpt as HTMLElement)?.style.webkitLineClamp).toBe("3");
  });
});
