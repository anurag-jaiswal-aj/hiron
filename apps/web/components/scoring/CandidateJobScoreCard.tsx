import React from "react";
import { useScore } from "../../hooks/useScore";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { SkillsAnalysis } from "./SkillsAnalysis";
import { ScoreExplanationPanel } from "./ScoreExplanationPanel";
import { ScoreHistory } from "./ScoreHistory";

interface CandidateJobScoreCardProps {
  candidateId: string;
  jobId: string;
  jobTitle: string;
}

export function CandidateJobScoreCard({ candidateId, jobId, jobTitle }: CandidateJobScoreCardProps): React.ReactElement {
  const {
    score,
    history,
    explanation,
    isLoading,
    isHistoryLoading,
    isExplanationLoading,
    isScoring,
    error,
    historyError,
    explanationError,
    canScore,
    scoreCandidate
  } = useScore(jobId, candidateId);

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: "1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
            {jobTitle}
          </h3>
          {score?.confidence && (
            <p className="text-sm text-gray-500 mt-1">
              Confidence: {Math.round(score.confidence * 100)}%
            </p>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {isLoading ? (
            <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Loading score...</span>
          ) : score ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Badge variant={score.fitScore >= 80 ? "active" : score.fitScore >= 50 ? "warning" : "neutral"} style={{ fontSize: "1rem", padding: "0.25rem 0.5rem" }}>
                {score.fitScore}/100
              </Badge>
              {canScore && (
                <Button variant="secondary" size="sm" onClick={scoreCandidate} disabled={isScoring}>
                  {isScoring ? "Scoring..." : "Re-score"}
                </Button>
              )}
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Badge variant="neutral">Not Scored</Badge>
              {canScore && (
                <Button variant="primary" size="sm" onClick={scoreCandidate} disabled={isScoring}>
                  {isScoring ? "Scoring..." : "Score Now"}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div style={{ color: "var(--text-error)", fontSize: "0.875rem", marginTop: "0.5rem" }}>
          Error: {error.message}
        </div>
      )}

      {score && !isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
          <div className="flex flex-col gap-4">
            <ScoreBreakdown breakdown={score.breakdown} />
            <SkillsAnalysis skillsMatched={score.skillsMatched} skillsMissing={score.skillsMissing} />
          </div>
          <div className="flex flex-col gap-4">
            <ScoreExplanationPanel explanation={explanation} isLoading={isExplanationLoading} error={explanationError} />
            <ScoreHistory history={history} isLoading={isHistoryLoading} error={historyError} />
          </div>
        </div>
      )}
    </div>
  );
}
