import React, { useEffect, useState } from "react";
import { pipelineApi, StageHistoryItem } from "../../lib/pipeline-api";

interface StageHistoryTimelineProps {
  jobId: string;
  candidateId: string;
}

export function StageHistoryTimeline({ jobId, candidateId }: StageHistoryTimelineProps): React.ReactElement {
  const [history, setHistory] = useState<StageHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async (): Promise<void> => {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const response = await pipelineApi.getStageHistory(jobId, candidateId);
        setHistory(response.data);
      } catch (err: unknown) {
        setErrorMsg((err as Error).message || "Failed to load stage history.");
      } finally {
        setIsLoading(false);
      }
    };

    if (jobId && candidateId) {
      fetchHistory();
    }
  }, [jobId, candidateId]);

  if (isLoading) {
    return <div style={{ padding: "1rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading history...</div>;
  }

  if (errorMsg) {
    return <div style={{ padding: "1rem", color: "var(--text-danger)", fontSize: "0.875rem" }}>{errorMsg}</div>;
  }

  if (history.length === 0) {
    return <div style={{ padding: "1rem", color: "var(--text-muted)", fontSize: "0.875rem" }}>No stage history found.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", padding: "1rem" }}>
      <h4 style={{ margin: 0, fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)" }}>Pipeline Timeline</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", position: "relative" }}>
        {/* Vertical line connecting timeline items */}
        <div style={{
          position: "absolute",
          top: "0.5rem",
          bottom: "0.5rem",
          left: "0.375rem",
          width: "2px",
          backgroundColor: "var(--border-subtle)",
          zIndex: 0
        }} />

        {history.map((item, index) => (
          <div key={item.id} style={{ display: "flex", gap: "1rem", position: "relative", zIndex: 1 }}>
            <div style={{
              width: "0.875rem",
              height: "0.875rem",
              borderRadius: "50%",
              backgroundColor: index === history.length - 1 ? "var(--accent-primary)" : "var(--bg-surface)",
              border: `2px solid ${index === history.length - 1 ? "var(--accent-primary)" : "var(--border-strong)"}`,
              marginTop: "0.25rem",
              flexShrink: 0
            }} />
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", fontWeight: 500 }}>
                {item.fromStage ? `Moved from ${item.fromStage.name} to ` : "Added to "}
                <strong>{item.toStage.name}</strong>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                {new Date(item.createdAt).toLocaleString()} {item.movedBy ? `by ${item.movedBy.fullName}` : ""}
              </div>
              {item.note && (
                <div style={{ 
                  marginTop: "0.25rem", 
                  padding: "0.5rem", 
                  backgroundColor: "var(--bg-surface-secondary)", 
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  color: "var(--text-secondary)",
                  fontStyle: "italic"
                }}>
                  &quot;{item.note}&quot;
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
