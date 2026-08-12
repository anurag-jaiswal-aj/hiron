import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByRole("button", { name: "Click Me" })).toBeInTheDocument();
  });

  it("calls onClick handler when clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Press</Button>);

    await user.click(screen.getByRole("button", { name: "Press" }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("does not call onClick when disabled", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <Button onClick={handleClick} disabled>
        Disabled
      </Button>
    );

    await user.click(screen.getByRole("button", { name: "Disabled" }));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("applies disabled visual styling", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByRole("button", { name: "Disabled" });
    expect(btn).toBeDisabled();
    expect(btn.style.cursor).toBe("not-allowed");
    expect(btn.style.opacity).toBe("0.6");
  });

  it("renders primary variant by default", () => {
    render(<Button>Primary</Button>);
    const btn = screen.getByRole("button", { name: "Primary" });
    expect(btn.style.backgroundColor).toContain("var(--btn-primary-bg)");
    expect(btn.style.color).toContain("var(--btn-primary-text)");
  });

  it("renders secondary variant styles", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const btn = screen.getByRole("button", { name: "Secondary" });
    expect(btn.style.backgroundColor).toContain("var(--btn-secondary-bg)");
    expect(btn.style.border).toContain("var(--border-subtle)");
  });

  it("renders destructive variant styles", () => {
    render(<Button variant="destructive">Delete</Button>);
    const btn = screen.getByRole("button", { name: "Delete" });
    expect(btn.style.backgroundColor).toBe("transparent");
    expect(btn.style.color).toBe("rgb(248, 113, 113)");
  });

  it("renders ghost variant styles", () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole("button", { name: "Ghost" });
    expect(btn.style.backgroundColor).toBe("transparent");
    expect(btn.style.border).toBe("");
  });

  it("applies small size padding", () => {
    render(<Button size="sm">Small</Button>);
    const btn = screen.getByRole("button", { name: "Small" });
    expect(btn.style.padding).toBe("0.375rem 0.75rem");
  });

  it("applies large size padding", () => {
    render(<Button size="lg">Large</Button>);
    const btn = screen.getByRole("button", { name: "Large" });
    expect(btn.style.padding).toBe("0.625rem 1.25rem");
  });

  it("forwards type attribute", () => {
    render(<Button type="submit">Submit</Button>);
    expect(screen.getByRole("button", { name: "Submit" })).toHaveAttribute("type", "submit");
  });
});
