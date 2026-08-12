import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Input } from "./Input";

describe("Input", () => {
  it("renders a text input element", () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter text").tagName).toBe("INPUT");
  });

  it("renders label when provided", () => {
    render(<Input id="test-input" label="Email Address" />);
    expect(screen.getByText("Email Address")).toBeInTheDocument();
  });

  it("associates label with input via htmlFor", () => {
    render(<Input id="email" label="Email" />);
    const label = screen.getByText("Email");
    expect(label).toHaveAttribute("for", "email");
    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("id", "email");
  });

  it("does not render label when not provided", () => {
    const { container } = render(<Input id="no-label" />);
    expect(container.querySelector("label")).toBeNull();
  });

  it("displays error message when error prop is set", () => {
    render(<Input error="This field is required" />);
    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("applies error border style when error prop is set", () => {
    render(<Input error="Invalid" placeholder="test" />);
    const input = screen.getByPlaceholderText("test");
    expect(input.style.border).toContain("rgb(127, 29, 29)");
  });

  it("applies normal border when no error", () => {
    render(<Input placeholder="test" />);
    const input = screen.getByPlaceholderText("test");
    expect(input.style.border).toContain("var(--border-subtle)");
  });

  it("passes through HTML input attributes", () => {
    render(
      <Input
        type="email"
        required
        maxLength={100}
        placeholder="email@example.com"
      />
    );
    const input = screen.getByPlaceholderText("email@example.com");
    expect(input).toHaveAttribute("type", "email");
    expect(input).toBeRequired();
    expect(input).toHaveAttribute("maxlength", "100");
  });

  it("merges custom style prop on the input element", () => {
    render(<Input style={{ marginTop: "2rem" }} placeholder="styled" />);
    const input = screen.getByPlaceholderText("styled");
    expect(input.style.marginTop).toBe("2rem");
  });
});
