"use client";

import React, { useCallback, useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { httpClient } from "../../lib/api";
import { scoresApi, TaskStatusData } from "../../lib/scores-api";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { Badge } from "../ui/Badge";

interface KanbanCandidateCard {
  candidateId: string;
  jobCandidateId: string;
  fullName: string;
  currentTitle?: string | null;
  fitScore?: number | null;
  confidence?: number | null;
  isShortlisted: boolean;
  appliedAt: string;
}

interface PipelineStageStats {
  stageId: string;
  stageName: string;
  position: number;
  candidateCount: number;
  candidates: KanbanCandidateCard[];
}

interface JobScoresListProps {
  jobId: string;
}

export function JobScoresList({ jobId }: JobScoresListProps): React.ReactElement {
  const { user } = useAuth();
  const [candidates, setCandidates] = useState<KanbanCandidateCard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Batch scoring state
  const [isBatchScoring, setIsBatchScoring] = useState(false);
  const [_batchTaskId, setBatchTaskId] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<TaskStatusData | null>(null);

  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const POLLING_INTERVAL = 2000;
  const MAX_POLLING_TIME = 5 * 60 * 1000; // 5 minutes
  const pollingStartRef = useRef<number>(0);

  const canManageScores = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchCandidates = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await httpClient.get<{ data: PipelineStageStats[] }>(
        `/api/v1/jobs/${jobId}/pipeline`
      );
      if (resp && resp.data) {
        // Flatten candidates from all stages
        const allCandidates = resp.data.flatMap((stage) => stage.candidates);
        // Sort by fitScore descending, then appliedAt
        allCandidates.sort((a, b) => {
          if (a.fitScore !== b.fitScore) {
            return (b.fitScore || 0) - (a.fitScore || 0);
          }
          return new Date(b.appliedAt).getTime() - new Date(a.appliedAt).getTime();
        });
        setCandidates(allCandidates);
      }
    } catch (_err: unknown) {
      setErrorMsg("Failed to load candidates for scoring.");
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchCandidates();
    return () => {
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
      }
    };
  }, [fetchCandidates]);

  const pollTaskStatus = useCallback(async (taskId: string) => {
    if (Date.now() - pollingStartRef.current > MAX_POLLING_TIME) {
      setErrorMsg("Batch scoring timed out.");
      setIsBatchScoring(false);
      setBatchTaskId(null);
      return;
    }

    try {
      const resp = await scoresApi.getTaskStatus(taskId);
      if (resp && resp.data) {
        setBatchProgress(resp.data);
        if (resp.data.status === "completed") {
          setIsBatchScoring(false);
          setBatchTaskId(null);
          await fetchCandidates();
        } else if (resp.data.status === "failed") {
          setIsBatchScoring(false);
          setBatchTaskId(null);
          setErrorMsg("Batch scoring failed.");
        } else {
          pollingTimerRef.current = setTimeout(() => pollTaskStatus(taskId), POLLING_INTERVAL);
        }
      }
    } catch (err) {
      setIsBatchScoring(false);
      setBatchTaskId(null);
      setErrorMsg("Failed to fetch batch scoring progress.");
    }
  }, [fetchCandidates, MAX_POLLING_TIME]);

  const handleScoreAll = async (): Promise<void> => {
    if (isBatchScoring) return;
    setIsBatchScoring(true);
    setErrorMsg(null);
    setBatchProgress({ taskId: "", status: "pending" });

    try {
      const resp = await scoresApi.scoreBatch(jobId, false);
      if (resp && resp.data && resp.data.taskId) {
        setBatchTaskId(resp.data.taskId);
        pollingStartRef.current = Date.now();
        pollTaskStatus(resp.data.taskId);
      } else {
        setIsBatchScoring(false);
        setErrorMsg("Failed to start batch scoring.");
      }
    } catch (err: unknown) {
      setIsBatchScoring(false);
      setErrorMsg((err as Error).message || "Failed to start batch scoring.");
    }
  };

  const unscoredCount = candidates.filter((c) => c.fitScore === null).length;
  const showScoreAllButton = canManageScores && unscoredCount > 0;

  if (isLoading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading candidates...</p>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <EmptyState
        title="No Candidates Found"
        description="There are currently no candidates in this job's pipeline."
      />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Candidate AI Fit Scores
          </h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: "0.25rem 0 0 0" }}>
            Review candidate match scores based on the job requirements.
          </p>
        </div>
        
        {showScoreAllButton && (
          <Button onClick={handleScoreAll} disabled={isBatchScoring}>
            {isBatchScoring ? "Starting Batch..." : `Score All Candidates (${unscoredCount})`}
          </Button>
        )}
      </div>

      {errorMsg && (
        <div style={{ padding: "0.75rem 1rem", backgroundColor: "#451A03", border: "1px solid #78350F", color: "#FDE68A", borderRadius: "var(--radius-md)", fontSize: "0.875rem" }}>
          {errorMsg}
        </div>
      )}

      {/* Progress Indicator */}
      {isBatchScoring && batchProgress && batchProgress.status === "progress" && batchProgress.progress && (
        <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
              Scoring Candidates...
            </span>
            <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
              {batchProgress.progress.current} of {batchProgress.progress.total}
            </span>
          </div>
          <div style={{ width: "100%", height: "8px", backgroundColor: "var(--bg-surface-secondary)", borderRadius: "4px", overflow: "hidden" }}>
            <div style={{ height: "100%", backgroundColor: "var(--accent-primary)", width: `${batchProgress.progress.percent}%`, transition: "width 0.3s ease" }} />
          </div>
        </div>
      )}

      {isBatchScoring && batchProgress && batchProgress.status === "pending" && (
        <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", padding: "1.25rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ width: "16px", height: "16px", border: "2px solid var(--accent-primary)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>Waiting for AI scoring engine to start...</span>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {candidates.map((candidate) => (
          <div key={candidate.candidateId} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <h4 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 0.25rem 0", color: "var(--text-primary)" }}>
                  {candidate.fullName}
                  {candidate.isShortlisted && (
                    <Badge variant="active" style={{ marginLeft: "0.75rem" }}>Shortlisted</Badge>
                  )}
                </h4>
                <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                  {candidate.currentTitle || "No title"}
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.5rem" }}>
                {candidate.fitScore !== null ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent-primary)", lineHeight: 1 }}>
                        {candidate.fitScore}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                        Confidence: {(candidate.confidence || 0) * 100}%
                      </div>
                    </div>
                    <Link href={`/jobs/${jobId}/candidates/${candidate.candidateId}`} style={{ textDecoration: "none" }}>
                      <Button variant="secondary" size="sm">View Details</Button>
                    </Link>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <Badge variant="neutral">Not Scored</Badge>
                    {canManageScores && (
                      <Link href={`/jobs/${jobId}/candidates/${candidate.candidateId}`} style={{ textDecoration: "none" }}>
                        <Button variant="secondary" size="sm" disabled={isBatchScoring}>Score Candidate</Button>
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
