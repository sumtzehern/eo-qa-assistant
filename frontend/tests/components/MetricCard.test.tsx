import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricCard from "@/components/admin/MetricCard";

describe("MetricCard", () => {
  it("renders label and value", () => {
    render(
      <MetricCard
        label="Overall Score"
        value="0.87"
        delta={2.3}
        deltaPositive={true}
      />
    );
    expect(screen.getByText("Overall Score")).toBeDefined();
    expect(screen.getByText("0.87")).toBeDefined();
  });

  it("shows positive delta with green color text", () => {
    const { container } = render(
      <MetricCard
        label="Score"
        value="0.9"
        delta={5.0}
        deltaPositive={true}
      />
    );
    const deltaEl = container.querySelector("p:last-child");
    expect(deltaEl?.textContent).toContain("+5%");
    expect((deltaEl as HTMLElement)?.style.color).toBe("rgb(110, 231, 183)");
  });

  it("shows negative delta with red color text", () => {
    const { container } = render(
      <MetricCard
        label="Error Rate"
        value="12%"
        delta={-3.1}
        deltaPositive={false}
      />
    );
    const deltaEl = container.querySelector("p:last-child");
    expect(deltaEl?.textContent).toContain("-3.1%");
    expect((deltaEl as HTMLElement)?.style.color).toBe("rgb(248, 113, 113)");
  });

  it("renders icon when provided", () => {
    render(
      <MetricCard label="Cache" value="42%" delta={0} deltaPositive={true} icon="⚡" />
    );
    expect(screen.getByText("⚡")).toBeDefined();
  });
});
