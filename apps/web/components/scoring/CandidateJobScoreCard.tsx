import React from "react";
import { useScore } from "../../hooks/useScore";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface CandidateJobScoreCardProps {
  candidateId: string;
  jobId: string;
  jobTitle: string;
}

export function CandidateJobScoreCard({ candidateId, jobId, jobTitle }: CandidateJobScoreCardProps): React.ReactElement {
  const { score, isLoading, isScoring, error, canScore, scoreCandidate } = useScore(jobId, candidateId);

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: "1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
          {jobTitle}
        </h3>
        
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
    </div>
  );
}
