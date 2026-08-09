import React from "react";
import { Badge } from "../ui/Badge";
import type { KanbanCandidateCard as KanbanCandidateCardType } from "../../lib/pipeline-api";

interface Props {
  candidate: KanbanCandidateCardType;
}

export function KanbanCandidateCard({ candidate }: Props): React.ReactElement {
  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "0.75rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        cursor: "grab",
        boxShadow: "0 1px 2px rgba(0, 0, 0, 0.05)",
        position: "relative",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
        <h4 style={{ fontSize: "0.875rem", fontWeight: 600, margin: 0, color: "var(--text-primary)", wordBreak: "break-word" }}>
          {candidate.fullName}
        </h4>
        {candidate.isShortlisted && (
          <Badge variant="active">Shortlisted</Badge>
        )}
      </div>

      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", minHeight: "1.125rem" }}>
        {candidate.currentTitle || "No title provided"}
      </div>

      {(candidate.fitScore !== null || candidate.confidence !== null) && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.25rem" }}>
          {candidate.fitScore !== null && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <span style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent-primary)", lineHeight: 1 }}>
                {candidate.fitScore}
              </span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Fit</span>
            </div>
          )}
          {candidate.confidence !== null && (
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", borderLeft: "1px solid var(--border-subtle)", paddingLeft: "0.5rem" }}>
              Conf: {Math.round(candidate.confidence * 100)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}
