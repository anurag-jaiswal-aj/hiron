import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders children text content", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders as an inline span element", () => {
    render(<Badge>Status</Badge>);
    const el = screen.getByText("Status");
    expect(el.tagName).toBe("SPAN");
  });

  it("applies neutral variant styles by default", () => {
    render(<Badge>Default</Badge>);
    const el = screen.getByText("Default");
    expect(el.style.backgroundColor).toContain("var(--bg-surface-secondary)");
    expect(el.style.color).toContain("var(--text-secondary)");
  });

  it("applies active variant styles", () => {
    render(<Badge variant="active">Active</Badge>);
    const el = screen.getByText("Active");
    expect(el.style.backgroundColor).toContain("var(--bg-hover)");
    expect(el.style.color).toContain("var(--text-primary)");
    expect(el.style.border).toContain("var(--border-strong)");
  });

  it("applies muted variant styles", () => {
    render(<Badge variant="muted">Muted</Badge>);
    const el = screen.getByText("Muted");
    expect(el.style.backgroundColor).toContain("var(--bg-app)");
    expect(el.style.color).toContain("var(--text-muted)");
  });

  it("applies error variant styles with amber colors", () => {
    render(<Badge variant="error">Error</Badge>);
    const el = screen.getByText("Error");
    expect(el.style.backgroundColor).toBe("rgb(69, 26, 3)");
    expect(el.style.color).toBe("rgb(253, 230, 138)");
  });

  it("passes through title attribute", () => {
    render(<Badge title="tooltip text">Hover me</Badge>);
    const el = screen.getByText("Hover me");
    expect(el).toHaveAttribute("title", "tooltip text");
  });

  it("merges custom style prop", () => {
    render(<Badge style={{ marginLeft: "1rem" }}>Styled</Badge>);
    const el = screen.getByText("Styled");
    expect(el.style.marginLeft).toBe("1rem");
  });

  it("renders complex children (React nodes)", () => {
    render(
      <Badge>
        <strong>85</strong>/100
      </Badge>
    );
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("/100")).toBeInTheDocument();
  });
});
