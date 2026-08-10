import React from "react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";

interface AuditLogDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  changes: Record<string, unknown> | null;
  action: string;
}

export function AuditLogDetailModal({
  isOpen,
  onClose,
  changes,
  action,
}: AuditLogDetailModalProps): React.ReactElement | null {
  if (!isOpen) return null;

  const renderJson = (data: unknown): string => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  const before = changes?.before;
  const after = changes?.after;

  const hasBefore = before && Object.keys(before as object).length > 0;
  const hasAfter = after && Object.keys(after as object).length > 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Audit Event Details: ${action}`}>
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {!changes ? (
          <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            No detailed changes recorded for this event.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {/* Before State */}
            {hasBefore && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface-secondary)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "0.5rem 1rem",
                    borderBottom: "1px solid var(--border-subtle)",
                    backgroundColor: "rgba(239, 68, 68, 0.1)", // Red tinted for "before"
                    color: "var(--text-primary)",
                    fontWeight: 600,
                    fontSize: "0.875rem",
                  }}
                >
                  Before
                </div>
                <pre
                  style={{
                    margin: 0,
                    padding: "1rem",
                    fontSize: "0.875rem",
                    overflowX: "auto",
                    color: "var(--text-secondary)",
                    maxHeight: "300px",
                    overflowY: "auto",
                  }}
                >
                  {renderJson(before)}
                </pre>
              </div>
            )}

            {/* After State */}
            {hasAfter && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface-secondary)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "0.5rem 1rem",
                    borderBottom: "1px solid var(--border-subtle)",
                    backgroundColor: "rgba(34, 197, 94, 0.1)", // Green tinted for "after"
                    color: "var(--text-primary)",
                    fontWeight: 600,
                    fontSize: "0.875rem",
                  }}
                >
                  After
                </div>
                <pre
                  style={{
                    margin: 0,
                    padding: "1rem",
                    fontSize: "0.875rem",
                    overflowX: "auto",
                    color: "var(--text-secondary)",
                    maxHeight: "300px",
                    overflowY: "auto",
                  }}
                >
                  {renderJson(after)}
                </pre>
              </div>
            )}

            {/* If neither before nor after, but changes exists */}
            {!hasBefore && !hasAfter && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface-secondary)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "0.5rem 1rem",
                    borderBottom: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontWeight: 600,
                    fontSize: "0.875rem",
                  }}
                >
                  Payload
                </div>
                <pre
                  style={{
                    margin: 0,
                    padding: "1rem",
                    fontSize: "0.875rem",
                    overflowX: "auto",
                    color: "var(--text-secondary)",
                    maxHeight: "300px",
                    overflowY: "auto",
                  }}
                >
                  {renderJson(changes)}
                </pre>
              </div>
            )}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
