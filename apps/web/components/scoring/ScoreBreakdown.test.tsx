import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ScoreBreakdown } from "./ScoreBreakdown";
import type { ScoreBreakdown as ScoreBreakdownType } from "../../lib/scores-api";

const mockBreakdown: ScoreBreakdownType = {
  skills: { score: 92, weight: 0.4, details: "Strong match on Python, FastAPI, Docker" },
  experience: { score: 78, weight: 0.35, details: "5 years relevant experience, slightly below target" },
  education: { score: 60, weight: 0.25, details: "Bachelor's degree, no advanced degree" },
};

describe("ScoreBreakdown", () => {
  it("renders the Score Breakdown heading", () => {
    render(<ScoreBreakdown breakdown={mockBreakdown} />);
    expect(screen.getByText("Score Breakdown")).toBeInTheDocument();
  });

  it("renders all three dimension titles", () => {
    render(<ScoreBreakdown breakdown={mockBreakdown} />);
    expect(screen.getByText("Skills")).toBeInTheDocument();
    expect(screen.getByText("Experience")).toBeInTheDocument();
    expect(screen.getByText("Education")).toBeInTheDocument();
  });

  it("renders numeric scores for each dimension", () => {
    render(<ScoreBreakdown breakdown={mockBreakdown} />);
    expect(screen.getByText("92/100")).toBeInTheDocument();
    expect(screen.getByText("78/100")).toBeInTheDocument();
    expect(screen.getByText("60/100")).toBeInTheDocument();
  });

  it("renders detail text for each dimension", () => {
    render(<ScoreBreakdown breakdown={mockBreakdown} />);
    expect(screen.getByText("Strong match on Python, FastAPI, Docker")).toBeInTheDocument();
    expect(screen.getByText("5 years relevant experience, slightly below target")).toBeInTheDocument();
    expect(screen.getByText("Bachelor's degree, no advanced degree")).toBeInTheDocument();
  });

  it("renders progress bars with correct width percentages", () => {
    const { container } = render(<ScoreBreakdown breakdown={mockBreakdown} />);
    // Progress bar inner divs should have width matching the score
    const progressBars = container.querySelectorAll(".rounded-full.h-2:not(.w-full)");
    const widths = Array.from(progressBars).map((el) => (el as HTMLElement).style.width);
    expect(widths).toContain("92%");
    expect(widths).toContain("78%");
    expect(widths).toContain("60%");
  });

  it("handles edge case scores", () => {
    const edgeBreakdown: ScoreBreakdownType = {
      skills: { score: 100, weight: 0.4, details: "Perfect match" },
      experience: { score: 0, weight: 0.35, details: "No relevant experience" },
      education: { score: 50, weight: 0.25, details: "Some education" },
    };
    render(<ScoreBreakdown breakdown={edgeBreakdown} />);
    expect(screen.getByText("100/100")).toBeInTheDocument();
    expect(screen.getByText("0/100")).toBeInTheDocument();
    expect(screen.getByText("50/100")).toBeInTheDocument();
  });
});
