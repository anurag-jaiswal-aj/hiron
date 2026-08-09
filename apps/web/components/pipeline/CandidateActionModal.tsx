import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import type { KanbanCandidateCard as KanbanCandidateCardType } from "../../lib/pipeline-api";
import { pipelineApi } from "../../lib/pipeline-api";
import Link from "next/link";
import { RejectionModal } from "./RejectionModal";

interface CandidateActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: KanbanCandidateCardType;
  jobId: string;
  canManage: boolean;
  onUpdated: () => void;
}

export function CandidateActionModal({
  isOpen,
  onClose,
  candidate,
  jobId,
  canManage,
  onUpdated,
}: CandidateActionModalProps): React.ReactElement {
  const [isRejecting, setIsRejecting] = useState(false);
  const [isShortlisting, setIsShortlisting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleShortlist = async (): Promise<void> => {
    setIsShortlisting(true);
    setErrorMsg(null);
    try {
      await pipelineApi.shortlistCandidate(jobId, candidate.candidateId);
      onUpdated();
      onClose();
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || "Failed to shortlist candidate.");
      setIsShortlisting(false);
    }
  };

  const handleReject = async (reason: string): Promise<void> => {
    await pipelineApi.rejectCandidate(jobId, candidate.candidateId, reason);
    onUpdated();
    setIsRejecting(false);
    onClose();
  };

  if (isRejecting) {
    return (
      <RejectionModal
        isOpen={true}
        onClose={() => setIsRejecting(false)}
        onConfirm={handleReject}
        candidateName={candidate.fullName}
      />
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Candidate Actions">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "1rem" }}>
        
        {errorMsg && (
          <div style={{ padding: "0.75rem", backgroundColor: "#FEE2E2", color: "#991B1B", borderRadius: "0.25rem", fontSize: "0.875rem" }}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.125rem", color: "var(--text-primary)" }}>{candidate.fullName}</h3>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-secondary)" }}>{candidate.currentTitle || "No title"}</p>
          </div>
          {candidate.isShortlisted && <Badge variant="active">Shortlisted</Badge>}
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          {candidate.fitScore !== null && (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Fit Score</span>
              <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent-primary)" }}>{candidate.fitScore}</span>
            </div>
          )}
          {candidate.confidence !== null && (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Confidence</span>
              <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}>{Math.round(candidate.confidence * 100)}%</span>
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", borderTop: "1px solid var(--border-subtle)", paddingTop: "1rem" }}>
          <Link href={`/candidates/${candidate.candidateId}`} style={{ width: "100%", textDecoration: "none" }}>
            <Button variant="secondary" style={{ width: "100%" }}>View Full Profile</Button>
          </Link>
          
          {canManage && (
            <div style={{ display: "flex", gap: "0.75rem" }}>
              {!candidate.isShortlisted && (
                <Button 
                  variant="primary" 
                  style={{ flex: 1 }} 
                  onClick={handleShortlist}
                  disabled={isShortlisting}
                >
                  {isShortlisting ? "Shortlisting..." : "Shortlist"}
                </Button>
              )}
              <Button 
                variant="destructive" 
                style={{ flex: 1 }} 
                onClick={() => setIsRejecting(true)}
              >
                Reject
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
