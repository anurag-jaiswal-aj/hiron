import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";

interface RejectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  candidateName: string;
}

export function RejectionModal({ isOpen, onClose, onConfirm, candidateName }: RejectionModalProps): React.ReactElement {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!reason.trim()) {
      setErrorMsg("Please provide a reason for rejection.");
      return;
    }
    
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onConfirm(reason);
      setReason("");
      onClose();
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || "Failed to reject candidate");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Reject Candidate">
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: 0 }}>
          You are about to reject <strong>{candidateName}</strong>. Please provide a reason.
        </p>
        
        {errorMsg && (
          <div style={{ padding: "0.75rem", backgroundColor: "#FEE2E2", color: "#991B1B", borderRadius: "0.25rem", fontSize: "0.875rem" }}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <label htmlFor="reason" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-primary)" }}>
            Reason
          </label>
          <textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isSubmitting}
            placeholder="e.g. Insufficient experience with distributed systems"
            style={{
              width: "100%",
              minHeight: "100px",
              padding: "0.5rem",
              borderRadius: "0.25rem",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--bg-surface)",
              color: "var(--text-primary)",
              fontFamily: "inherit",
              resize: "vertical"
            }}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="destructive" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Rejecting..." : "Reject Candidate"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
