"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

import { JobStatusBadge } from "../../../components/jobs/JobStatusBadge";
import { AppShell } from "../../../components/layout/AppShell";
import { PageHeader } from "../../../components/layout/PageHeader";
import { ProtectedRoute } from "../../../components/ProtectedRoute";
import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/EmptyState";
import { Modal } from "../../../components/ui/Modal";
import { useAuth } from "../../../context/AuthContext";
import { ApiError, httpClient } from "../../../lib/api";
import { EmbeddingStatusBadge } from "../../../components/embeddings/EmbeddingStatusBadge";
import { JobScoresList } from "../../../components/scoring/JobScoresList";

export interface PipelineStage {
  id: string;
  name: string;
  position: number;
  candidateCount: number;
}

export interface JobDetail {
  id: string;
  title: string;
  description: string;
  department?: string | null;
  location?: string | null;
  employmentType?: string | null;
  experienceYearsMin?: number | null;
  experienceYearsMax?: number | null;
  requiredSkills?: string[] | null;
  preferredSkills?: string[] | null;
  extractedRequirements?: {
    skills?: string[];
    education?: string;
    experienceSummary?: string;
  } | null;
  status: string;
  candidateCount: number;
  pipelineStages?: PipelineStage[] | null;
  createdBy?: {
    id: string;
    fullName?: string;
    email?: string;
  } | null;
  openedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

type TabType = "details" | "kanban" | "candidates" | "scores";

function JobDetailContent(): React.ReactElement {
  const params = useParams();
  const jobId = params.id as string;
  const { user } = useAuth();
  const router = useRouter();

  const [job, setJob] = useState<JobDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("details");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Lifecycle Mutation State
  const [isMutating, setIsMutating] = useState<boolean>(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [showArchiveModal, setShowArchiveModal] = useState<boolean>(false);

  const canManageJobs = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchJob = useCallback(async () => {
    if (!jobId) return;

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const response = await httpClient.get<ResponseEnvelope<JobDetail>>(`/api/v1/jobs/${jobId}`);
      if (response && response.data) {
        setJob(response.data);
      } else {
        setErrorMsg("Job description not found.");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setErrorMsg("The requested job description was not found or may have been deleted.");
        } else {
          setErrorMsg(err.message);
        }
      } else {
        setErrorMsg("Failed to load job details. Please check network connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  const handleOpenJob = async (): Promise<void> => {
    if (!jobId || isMutating) return;
    setIsMutating(true);
    setMutationError(null);
    try {
      const resp = await httpClient.post<ResponseEnvelope<JobDetail>>(`/api/v1/jobs/${jobId}/open`, {});
      if (resp?.data) setJob(resp.data);
    } catch (err) {
      if (err instanceof ApiError) setMutationError(err.message);
      else setMutationError("Failed to open job.");
    } finally {
      setIsMutating(false);
    }
  };

  const handlePauseJob = async (): Promise<void> => {
    if (!jobId || isMutating) return;
    setIsMutating(true);
    setMutationError(null);
    try {
      const resp = await httpClient.post<ResponseEnvelope<JobDetail>>(`/api/v1/jobs/${jobId}/pause`, {});
      if (resp?.data) setJob(resp.data);
    } catch (err) {
      if (err instanceof ApiError) setMutationError(err.message);
      else setMutationError("Failed to pause job.");
    } finally {
      setIsMutating(false);
    }
  };

  const handleCloseJob = async (): Promise<void> => {
    if (!jobId || isMutating) return;
    setIsMutating(true);
    setMutationError(null);
    try {
      const resp = await httpClient.post<ResponseEnvelope<JobDetail>>(`/api/v1/jobs/${jobId}/close`, {});
      if (resp?.data) setJob(resp.data);
    } catch (err) {
      if (err instanceof ApiError) setMutationError(err.message);
      else setMutationError("Failed to close job.");
    } finally {
      setIsMutating(false);
    }
  };

  const handleArchiveJob = async (): Promise<void> => {
    if (!jobId || isMutating) return;
    setIsMutating(true);
    setMutationError(null);
    try {
      await httpClient.post<ResponseEnvelope<JobDetail>>(`/api/v1/jobs/${jobId}/archive`, {});
      setShowArchiveModal(false);
      router.push("/jobs");
    } catch (err) {
      setShowArchiveModal(false);
      if (err instanceof ApiError) setMutationError(err.message);
      else setMutationError("Failed to archive job.");
    } finally {
      setIsMutating(false);
    }
  };

  return (
    <AppShell>
      {/* Loading Skeleton */}
      {isLoading && (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading job details...</p>
        </div>
      )}

      {/* Error State */}
      {!isLoading && errorMsg && (
        <EmptyState
          title="Job Not Found"
          description={errorMsg}
          action={
            <Link href="/jobs" style={{ textDecoration: "none" }}>
              <Button type="button" variant="secondary">
                Return to Jobs List
              </Button>
            </Link>
          }
        />
      )}

      {/* Main Job Content */}
      {!isLoading && job && (
        <>
          <PageHeader
            title={job.title}
            subtitle={`${job.department || "General"} • ${job.location || "Remote"} • ${
              job.employmentType ? job.employmentType.replace("_", "-") : "Full-time"
            }`}
            backHref="/jobs"
            backLabel="Back to Jobs"
            actions={
              canManageJobs ? (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                  <Link href={`/jobs/${job.id}/edit`} style={{ textDecoration: "none" }}>
                    <Button type="button" variant="secondary" size="sm">
                      Edit Job
                    </Button>
                  </Link>

                  {(job.status === "draft" || job.status === "paused" || job.status === "closed") && (
                    <Button type="button" size="sm" disabled={isMutating} onClick={handleOpenJob}>
                      {isMutating ? "Updating..." : job.status === "draft" ? "Open Job" : "Reopen Job"}
                    </Button>
                  )}

                  {job.status === "open" && (
                    <Button type="button" variant="secondary" size="sm" disabled={isMutating} onClick={handlePauseJob}>
                      {isMutating ? "Updating..." : "Pause Job"}
                    </Button>
                  )}

                  {(job.status === "open" || job.status === "paused") && (
                    <Button type="button" variant="secondary" size="sm" disabled={isMutating} onClick={handleCloseJob}>
                      {isMutating ? "Updating..." : "Close Job"}
                    </Button>
                  )}

                  <Button type="button" variant="destructive" size="sm" disabled={isMutating} onClick={() => setShowArchiveModal(true)}>
                    Archive
                  </Button>
                </div>
              ) : undefined
            }
          />

          {/* Job Overview Banner Info */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "1.25rem 1.5rem",
              marginBottom: "1.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
              <JobStatusBadge status={job.status} />
              <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                <strong style={{ color: "var(--text-primary)" }}>{job.candidateCount}</strong> candidates in pipeline
              </span>
              <div style={{ width: "1px", height: "24px", backgroundColor: "var(--border-subtle)" }}></div>
              <EmbeddingStatusBadge entityType="job" entityId={job.id} />
            </div>

            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Created{" "}
              {new Date(job.createdAt).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </div>
          </div>

          {/* Mutation Error Notification */}
          {mutationError && (
            <div
              style={{
                backgroundColor: "#451A03",
                border: "1px solid #78350F",
                color: "#FDE68A",
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-md)",
                marginBottom: "1.5rem",
                fontSize: "0.875rem",
              }}
            >
              {mutationError}
            </div>
          )}

          {/* Tab Bar */}
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              borderBottom: "1px solid var(--border-subtle)",
              marginBottom: "1.5rem",
              overflowX: "auto",
            }}
          >
            {(
              [
                { id: "details", label: "Details" },
                { id: "kanban", label: "Kanban" },
                { id: "candidates", label: "Candidates" },
                { id: "scores", label: "Scores" },
              ] as const
            ).map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    backgroundColor: "transparent",
                    border: "none",
                    borderBottom: isActive ? "2px solid var(--text-primary)" : "2px solid transparent",
                    color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                    fontSize: "0.875rem",
                    fontWeight: isActive ? 600 : 500,
                    padding: "0.75rem 1.25rem",
                    cursor: "pointer",
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content: Details */}
          {activeTab === "details" && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "1.5rem",
                alignItems: "start",
              }}
            >
              {/* Left Panel: Description & Skills */}
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-lg)",
                  padding: "1.75rem",
                }}
              >
                <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
                  Job Description
                </h3>
                <div
                  style={{
                    fontSize: "0.875rem",
                    color: "var(--text-secondary)",
                    lineHeight: "1.6",
                    whiteSpace: "pre-wrap",
                    marginBottom: "1.75rem",
                  }}
                >
                  {job.description}
                </div>

                {job.requiredSkills && job.requiredSkills.length > 0 && (
                  <div style={{ marginBottom: "1.25rem" }}>
                    <h4 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 0.5rem 0" }}>
                      Required Skills
                    </h4>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                      {job.requiredSkills.map((skill, idx) => (
                        <Badge key={idx} variant="active">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {job.preferredSkills && job.preferredSkills.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 0.5rem 0" }}>
                      Preferred Skills
                    </h4>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                      {job.preferredSkills.map((skill, idx) => (
                        <Badge key={idx} variant="muted">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Panel: Pipeline Stages & Metadata */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                <div
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-lg)",
                    padding: "1.5rem",
                  }}
                >
                  <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
                    Pipeline Stages
                  </h3>

                  {job.pipelineStages && job.pipelineStages.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {job.pipelineStages
                        .sort((a, b) => a.position - b.position)
                        .map((stage) => (
                          <div
                            key={stage.id}
                            style={{
                              backgroundColor: "var(--bg-surface-secondary)",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: "var(--radius-md)",
                              padding: "0.625rem 0.875rem",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              fontSize: "0.875rem",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 700 }}>
                                #{stage.position}
                              </span>
                              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{stage.name}</span>
                            </div>
                            <Badge variant="neutral">{stage.candidateCount}</Badge>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>
                      Default pipeline stages generated.
                    </p>
                  )}
                </div>

                <div
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-lg)",
                    padding: "1.5rem",
                    fontSize: "0.875rem",
                    color: "var(--text-secondary)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.75rem",
                  }}
                >
                  <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    Audit Details
                  </h3>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Created By:</span>
                    <strong style={{ color: "var(--text-primary)" }}>{job.createdBy?.fullName || "Org Admin"}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Created At:</span>
                    <strong style={{ color: "var(--text-primary)" }}>
                      {new Date(job.createdAt).toLocaleDateString("en-US")}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Status:</span>
                    <strong style={{ color: "var(--text-primary)", textTransform: "capitalize" }}>{job.status}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Placeholders for Kanban, Candidates, Scores */}
          {activeTab === "kanban" && (
            <EmptyState
              title="Pipeline Kanban Board"
              description="Interactive pipeline Kanban board for candidate stage progression is deferred to Phase 10."
            />
          )}

          {activeTab === "candidates" && (
            <EmptyState
              title="Candidate Pool"
              description="Candidate list and application filtering for this job will be available in Phase 4 Candidate Management."
            />
          )}

          {activeTab === "scores" && (
            <JobScoresList jobId={jobId} />
          )}

          {/* Archive Confirmation Modal */}
          <Modal
            isOpen={showArchiveModal}
            onClose={() => setShowArchiveModal(false)}
            title="Archive Job Description?"
            actions={
              <>
                <Button type="button" variant="secondary" onClick={() => setShowArchiveModal(false)} disabled={isMutating}>
                  Cancel
                </Button>
                <Button type="button" variant="destructive" onClick={handleArchiveJob} disabled={isMutating}>
                  {isMutating ? "Archiving..." : "Archive Job"}
                </Button>
              </>
            }
          >
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: "1.5", margin: 0 }}>
              Are you sure you want to archive <strong>{job.title}</strong>? Archived jobs are excluded from active job lists but preserve historical candidates and evaluation records.
            </p>
          </Modal>
        </>
      )}
    </AppShell>
  );
}

export default function JobDetailPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <JobDetailContent />
    </ProtectedRoute>
  );
}
