import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KanbanCandidateCard } from "./KanbanCandidateCard";
import type { KanbanCandidateCard as KanbanCandidateCardType } from "../../lib/pipeline-api";

function makeCandidate(overrides: Partial<KanbanCandidateCardType> = {}): KanbanCandidateCardType {
  return {
    candidateId: "cand-1",
    jobCandidateId: "jc-1",
    fullName: "Jane Smith",
    currentTitle: "Senior Engineer",
    fitScore: 87,
    confidence: 0.92,
    isShortlisted: false,
    appliedAt: "2026-01-15T10:00:00Z",
    ...overrides,
  };
}

describe("KanbanCandidateCard", () => {
  it("renders candidate full name", () => {
    render(<KanbanCandidateCard candidate={makeCandidate()} />);
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
  });

  it("renders candidate current title", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ currentTitle: "Staff Engineer" })} />);
    expect(screen.getByText("Staff Engineer")).toBeInTheDocument();
  });

  it("renders fallback when currentTitle is null", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ currentTitle: null })} />);
    expect(screen.getByText("No title provided")).toBeInTheDocument();
  });

  it("renders fallback when currentTitle is undefined", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ currentTitle: undefined })} />);
    expect(screen.getByText("No title provided")).toBeInTheDocument();
  });

  it("renders fit score when present", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ fitScore: 87 })} />);
    expect(screen.getByText("87")).toBeInTheDocument();
    expect(screen.getByText("Fit")).toBeInTheDocument();
  });

  it("renders confidence percentage when present", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ confidence: 0.92 })} />);
    expect(screen.getByText("Conf: 92%")).toBeInTheDocument();
  });

  it("does not render score section when both fitScore and confidence are null", () => {
    const { container } = render(
      <KanbanCandidateCard candidate={makeCandidate({ fitScore: null, confidence: null })} />
    );
    expect(screen.queryByText("Fit")).not.toBeInTheDocument();
    expect(container.textContent).not.toContain("Conf:");
  });

  it("renders Shortlisted badge when isShortlisted is true", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ isShortlisted: true })} />);
    expect(screen.getByText("Shortlisted")).toBeInTheDocument();
  });

  it("does not render Shortlisted badge when isShortlisted is false", () => {
    render(<KanbanCandidateCard candidate={makeCandidate({ isShortlisted: false })} />);
    expect(screen.queryByText("Shortlisted")).not.toBeInTheDocument();
  });

  it("renders fitScore without confidence when confidence is null", () => {
    render(
      <KanbanCandidateCard candidate={makeCandidate({ fitScore: 75, confidence: null })} />
    );
    expect(screen.getByText("75")).toBeInTheDocument();
    expect(screen.getByText("Fit")).toBeInTheDocument();
    expect(screen.queryByText(/Conf:/)).not.toBeInTheDocument();
  });

  it("renders confidence without fitScore when fitScore is null", () => {
    const { container } = render(
      <KanbanCandidateCard candidate={makeCandidate({ fitScore: null, confidence: 0.88 })} />
    );
    expect(screen.queryByText("Fit")).not.toBeInTheDocument();
    expect(container.textContent).toContain("Conf: 88%");
  });

  it("rounds confidence correctly", () => {
    render(
      <KanbanCandidateCard candidate={makeCandidate({ confidence: 0.856 })} />
    );
    expect(screen.getByText("Conf: 86%")).toBeInTheDocument();
  });
});
