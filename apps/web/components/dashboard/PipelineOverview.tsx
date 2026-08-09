import React from "react";
import Link from "next/link";
import { JobPipelineOverview } from "../../lib/dashboard-api";
import { Badge } from "../ui/Badge";

interface Props {
  pipelines: JobPipelineOverview[];
}

export function PipelineOverview({ pipelines }: Props): React.ReactElement {
  if (!pipelines || pipelines.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)" }}>
        No open jobs to show in pipeline.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {pipelines.map(job => (
        <div key={job.jobId} style={{ 
          padding: "1rem", 
          border: "1px solid var(--border-subtle)", 
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--bg-surface)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <Link href={`/jobs/${job.jobId}`} style={{ fontWeight: 600, color: "var(--text-primary)", textDecoration: "none", fontSize: "1rem" }}>
              {job.jobTitle}
            </Link>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>
                {job.totalCandidates} cands
              </span>
              <Badge variant={job.status === "open" ? "active" : "neutral"}>
                {job.status}
              </Badge>
            </div>
          </div>
          
          <div style={{ display: "flex", height: "8px", borderRadius: "4px", overflow: "hidden", gap: "2px" }}>
            {[...job.stages].sort((a, b) => a.position - b.position).map((stage, idx) => {
              const percentage = job.totalCandidates > 0 ? (stage.candidateCount / job.totalCandidates) * 100 : 0;
              const colors = ["#e0e7ff", "#c7d2fe", "#a5b4fc", "#818cf8", "#6366f1", "#4f46e5", "#4338ca"];
              const color = colors[idx % colors.length];
              return (
                <div 
                  key={stage.stageId} 
                  style={{ 
                    width: `${percentage}%`, 
                    backgroundColor: color,
                    minWidth: percentage > 0 ? "4px" : "0"
                  }} 
                  title={`${stage.stageName}: ${stage.candidateCount}`}
                />
              );
            })}
            {job.totalCandidates === 0 && (
              <div style={{ width: "100%", backgroundColor: "var(--bg-subtle)" }} title="No candidates yet" />
            )}
          </div>
        </div>
      ))}
      <div style={{ textAlign: "right" }}>
        <Link href="/jobs" style={{ fontSize: "0.875rem", color: "var(--color-primary)", textDecoration: "none", fontWeight: 500 }}>
          View all jobs →
        </Link>
      </div>
    </div>
  );
}
