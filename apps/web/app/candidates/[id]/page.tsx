"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

import { AppShell } from "../../../components/layout/AppShell";
import { PageHeader } from "../../../components/layout/PageHeader";
import { ProtectedRoute } from "../../../components/ProtectedRoute";
import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/EmptyState";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { useAuth } from "../../../context/AuthContext";
import { ApiError, httpClient } from "../../../lib/api";

export interface CandidateAssociatedJob {
  jobId: string;
  jobTitle: string;
  currentStage: string;
  isShortlisted: boolean;
}

export interface CandidateDetail {
  id: string;
  fullName: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  linkedinUrl?: string | null;
  summary?: string | null;
  skills: string[];
  totalExperienceYears?: number | null;
  currentTitle?: string | null;
  currentCompany?: string | null;
  source: string;
  isArchived: boolean;
  jobs: CandidateAssociatedJob[];
  createdAt: string;
  updatedAt: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

interface JobsListResponse {
  data: { id: string; title: string }[];
}

type TabType = "profile" | "scores" | "notes" | "tags";

function CandidateDetailContent(): React.ReactElement {
  const params = useParams();
  const candidateId = params.id as string;
  const { user } = useAuth();

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("profile");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Add to Job Modal State
  const [isAddJobModalOpen, setIsAddJobModalOpen] = useState(false);
  const [availableJobs, setAvailableJobs] = useState<{ id: string; title: string }[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [isAddingToJob, setIsAddingToJob] = useState(false);
  const [addJobError, setAddJobError] = useState<string | null>(null);

  const canManageCandidates = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchCandidate = useCallback(async () => {
    if (!candidateId) return;

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const response = await httpClient.get<ResponseEnvelope<CandidateDetail>>(`/api/v1/candidates/${candidateId}`);
      if (response && response.data) {
        setCandidate(response.data);
      } else {
        setErrorMsg("Candidate not found.");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setErrorMsg("The requested candidate was not found or may have been deleted.");
        } else {
          setErrorMsg(err.message);
        }
      } else {
        setErrorMsg("Failed to load candidate details. Please check network connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [candidateId]);

  useEffect(() => {
    fetchCandidate();
  }, [fetchCandidate]);

  const handleOpenAddJobModal = async (): Promise<void> => {
    setIsAddJobModalOpen(true);
    setAddJobError(null);
    setSelectedJobId("");
    try {
      const res = await httpClient.get<ResponseEnvelope<JobsListResponse>>("/api/v1/jobs");
      if (res && res.data && res.data.data) {
        // filter out jobs the candidate is already in
        const existingJobIds = new Set(candidate?.jobs.map((j) => j.jobId) || []);
        setAvailableJobs(res.data.data.filter((j) => !existingJobIds.has(j.id)));
      }
    } catch (err) {
      setAddJobError("Failed to load available jobs.");
    }
  };

  const handleAddJobSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!selectedJobId || !candidateId) return;

    setIsAddingToJob(true);
    setAddJobError(null);
    try {
      await httpClient.post(`/api/v1/jobs/${selectedJobId}/candidates`, {
        candidateId: candidateId,
      });
      setIsAddJobModalOpen(false);
      // Refresh candidate details to show new job
      fetchCandidate();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setAddJobError("Candidate is already associated with this job.");
      } else {
        setAddJobError(err instanceof ApiError ? err.message : "Failed to add candidate to job.");
      }
    } finally {
      setIsAddingToJob(false);
    }
  };

  return (
    <AppShell>
      {/* Loading Skeleton */}
      {isLoading && (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading candidate details...</p>
        </div>
      )}

      {/* Error State */}
      {!isLoading && errorMsg && (
        <EmptyState
          title="Candidate Not Found"
          description={errorMsg}
          action={
            <Link href="/candidates" style={{ textDecoration: "none" }}>
              <Button type="button" variant="secondary">
                Return to Candidates List
              </Button>
            </Link>
          }
        />
      )}

      {/* Main Candidate Content */}
      {!isLoading && candidate && (
        <>
          <PageHeader
            title={candidate.fullName}
            subtitle={[candidate.currentTitle, candidate.currentCompany].filter(Boolean).join(" @ ") || "No title provided"}
            backHref="/candidates"
            backLabel="Back to Candidates"
            actions={
              canManageCandidates ? (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                  <Button type="button" variant="primary" size="sm" onClick={handleOpenAddJobModal}>
                    Add to Job
                  </Button>
                  <Button type="button" variant="secondary" size="sm" disabled>
                    Edit Profile
                  </Button>
                  <Button type="button" variant="destructive" size="sm" disabled>
                    Archive
                  </Button>
                </div>
              ) : undefined
            }
          />

          <div
            style={{
              display: "flex",
              flexDirection: "row",
              flexWrap: "wrap",
              gap: "1.5rem",
              alignItems: "flex-start",
            }}
          >
            {/* Sidebar Summary */}
            <div
              style={{
                flex: "1 1 300px",
                maxWidth: "350px",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "1.5rem",
                display: "flex",
                flexDirection: "column",
                gap: "1.25rem",
              }}
            >
              <div>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>Contact</h3>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                  {candidate.email ? <a href={`mailto:${candidate.email}`} style={{ color: "var(--text-primary)" }}>{candidate.email}</a> : <span>—</span>}
                  {candidate.phone ? <span>{candidate.phone}</span> : <span>—</span>}
                  {candidate.location ? <span>{candidate.location}</span> : <span>—</span>}
                  {candidate.linkedinUrl ? <a href={candidate.linkedinUrl} target="_blank" rel="noreferrer" style={{ color: "var(--text-primary)" }}>LinkedIn Profile ↗</a> : null}
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>Experience</h3>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                  {candidate.totalExperienceYears !== null ? `${candidate.totalExperienceYears} years` : "—"}
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>Skills</h3>
                {candidate.skills && candidate.skills.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                    {candidate.skills.map((skill, idx) => (
                      <Badge key={idx} variant="active">{skill}</Badge>
                    ))}
                  </div>
                ) : (
                  <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No skills listed</span>
                )}
              </div>

              <div>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>Jobs</h3>
                {candidate.jobs && candidate.jobs.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {candidate.jobs.map((job) => (
                      <div key={job.jobId} style={{ fontSize: "0.8125rem", display: "flex", flexDirection: "column" }}>
                        <Link href={`/jobs/${job.jobId}`} style={{ fontWeight: 600, color: "var(--text-primary)", textDecoration: "none" }}>
                          {job.jobTitle}
                        </Link>
                        <span style={{ color: "var(--text-secondary)" }}>→ {job.currentStage} {job.isShortlisted && "⭐"}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Not assigned to any jobs</span>
                )}
              </div>

              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem", fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <span>Source: {candidate.source}</span>
                <span>Added: {new Date(candidate.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
              </div>
            </div>

            {/* Tabbed Content Area */}
            <div style={{ flex: "2 1 500px", minWidth: 0 }}>
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
                    { id: "profile", label: "Profile" },
                    { id: "scores", label: "Scores" },
                    { id: "notes", label: "Notes" },
                    { id: "tags", label: "Tags" },
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
                        whiteSpace: "nowrap",
                      }}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab Content: Profile */}
              {activeTab === "profile" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                  {candidate.summary && (
                    <div
                      style={{
                        backgroundColor: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-lg)",
                        padding: "1.75rem",
                      }}
                    >
                      <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
                        Summary
                      </h3>
                      <div
                        style={{
                          fontSize: "0.875rem",
                          color: "var(--text-secondary)",
                          lineHeight: "1.6",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {candidate.summary}
                      </div>
                    </div>
                  )}

                  <EmptyState
                    title="Parsed Resume Data"
                    description="Detailed parsing of work experience, education, and certifications will be available in Phase 6 Resume Parsing."
                  />
                </div>
              )}

              {/* Placeholders for deferred tabs */}
              {activeTab === "scores" && (
                <EmptyState
                  title="Candidate Scores"
                  description="Automated candidate fit score rankings across associated jobs will be available in Phase 8 Automated Scoring."
                />
              )}

              {activeTab === "notes" && (
                <EmptyState
                  title="Candidate Notes"
                  description="Collaborative evaluation notes for candidates will be available in Phase 11 Notes & Tags."
                />
              )}

              {activeTab === "tags" && (
                <EmptyState
                  title="Candidate Tags"
                  description="Custom taxonomy tagging for candidates will be available in Phase 11 Notes & Tags."
                />
              )}
            </div>
          </div>
        </>
      )}

      <Modal
        isOpen={isAddJobModalOpen}
        onClose={() => setIsAddJobModalOpen(false)}
        title="Add to Job"
      >
        <form onSubmit={handleAddJobSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: 0 }}>
            Select a job to add {candidate?.fullName} to its pipeline. They will be placed in the first stage automatically.
          </p>

          {addJobError && (
            <div style={{ color: "var(--text-error)", fontSize: "0.875rem" }}>{addJobError}</div>
          )}

          <div>
            <Select
              id="jobSelect"
              label="Job"
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              required
              options={[
                { value: "", label: "Select a job..." },
                ...availableJobs.map((job) => ({ value: job.id, label: job.title }))
              ]}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddJobModalOpen(false)}
              disabled={isAddingToJob}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!selectedJobId || isAddingToJob}>
              {isAddingToJob ? "Adding..." : "Add Candidate"}
            </Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}

export default function CandidateDetailPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <CandidateDetailContent />
    </ProtectedRoute>
  );
}
