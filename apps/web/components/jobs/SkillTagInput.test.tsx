import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { SkillTagInput } from "./SkillTagInput";

describe("SkillTagInput", () => {
  it("renders existing skills as tag chips", () => {
    render(
      <SkillTagInput skills={["Python", "React"]} onChange={vi.fn()} />
    );
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
  });

  it("adds a skill on Enter key press", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={[]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("Add a skill (press Enter or comma)");
    await user.type(input, "TypeScript{Enter}");

    expect(onChange).toHaveBeenCalledWith(["TypeScript"]);
  });

  it("adds a skill on comma key press", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={[]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("Add a skill (press Enter or comma)");
    await user.type(input, "Docker,");

    expect(onChange).toHaveBeenCalledWith(["Docker"]);
  });

  it("prevents duplicate skills (case-insensitive)", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={["Python"]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("+ Add skill");
    await user.type(input, "python{Enter}");

    // onChange should still be called (it clears input), but skills array should not include duplicate
    // The component calls onChange only if the skill doesn't exist, so it should NOT be called
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes a skill when the × button is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={["Python", "React", "Docker"]} onChange={onChange} />
    );

    const removeButtons = screen.getAllByRole("button", { name: /Remove/ });
    // Remove "React" (second skill)
    await user.click(removeButtons[1]);

    expect(onChange).toHaveBeenCalledWith(["Python", "Docker"]);
  });

  it("removes last skill on Backspace when input is empty", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={["Python", "React"]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("+ Add skill");
    await user.click(input);
    await user.keyboard("{Backspace}");

    expect(onChange).toHaveBeenCalledWith(["Python"]);
  });

  it("does not add skill when input is empty", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={[]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("Add a skill (press Enter or comma)");
    await user.type(input, "{Enter}");

    expect(onChange).not.toHaveBeenCalled();
  });

  it("respects maxSkills limit", () => {
    const skills = ["A", "B", "C"];
    const { container } = render(
      <SkillTagInput skills={skills} onChange={vi.fn()} maxSkills={3} />
    );

    // When skills.length >= maxSkills, the input should not be rendered
    const input = container.querySelector("input");
    expect(input).toBeNull();
  });

  it("adds skill on blur when input has content", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={[]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("Add a skill (press Enter or comma)");
    await user.type(input, "FastAPI");
    // Blur by tabbing away
    await user.tab();

    expect(onChange).toHaveBeenCalledWith(["FastAPI"]);
  });

  it("renders remove buttons with accessible aria-label", () => {
    render(
      <SkillTagInput skills={["Python"]} onChange={vi.fn()} />
    );
    expect(screen.getByRole("button", { name: "Remove Python" })).toBeInTheDocument();
  });

  it("trims whitespace from skill input", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SkillTagInput skills={[]} onChange={onChange} />
    );

    const input = screen.getByPlaceholderText("Add a skill (press Enter or comma)");
    await user.type(input, "  Go  {Enter}");

    expect(onChange).toHaveBeenCalledWith(["Go"]);
  });
});
