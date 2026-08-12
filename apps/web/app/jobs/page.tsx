"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

import { JobStatusBadge } from "../../components/jobs/JobStatusBadge";
import { AppShell } from "../../components/layout/AppShell";
import { PageHeader } from "../../components/layout/PageHeader";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useAuth } from "../../context/AuthContext";
import { ApiError, httpClient } from "../../lib/api";

export interface JobListItem {
  id: string;
  title: string;
  department: string | null;
  location: string | null;
  status: string;
  employmentType: string | null;
  candidateCount: number;
  openedAt: string | null;
  createdAt: string;
}

export interface PaginationMeta {
  hasMore: boolean;
  nextCursor: string | null;
  totalCount: number | null;
}

export interface PaginatedData<T> {
  data: T[];
  pagination: PaginationMeta;
}

export interface ResponseEnvelope<T> {
  data: T;
}

function JobsListContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();
  const canManageJobs = user?.role === "org_admin" || user?.role === "recruiter";

  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    hasMore: false,
    nextCursor: null,
    totalCount: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filter / Search / Sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [sortBy, setSortBy] = useState("createdAt:desc");
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const fetchJobs = useCallback(async () => {
    setErrorMsg(null);

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append("q", searchQuery.trim());
      if (statusFilter) params.append("status", statusFilter);
      if (departmentFilter) params.append("department", departmentFilter);
      if (sortBy) params.append("sort", sortBy);
      if (cursor) params.append("cursor", cursor);
      params.append("limit", "20");

      const response = await httpClient.get<ResponseEnvelope<PaginatedData<JobListItem>>>(
        `/api/v1/jobs?${params.toString()}`
      );

      if (response && response.data) {
        setJobs(response.data.data || []);
        setPagination(
          response.data.pagination || { hasMore: false, nextCursor: null, totalCount: 0 }
        );
      } else {
        setJobs([]);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to load jobs list. Please check network connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, statusFilter, departmentFilter, sortBy, cursor]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleClearFilters = (): void => {
    setSearchQuery("");
    setStatusFilter("");
    setDepartmentFilter("");
    setSortBy("createdAt:desc");
    setCursor(undefined);
  };

  const isFiltered = Boolean(searchQuery || statusFilter || departmentFilter);

  return (
    <AppShell>
      <PageHeader
        title="Jobs"
        subtitle="Manage open positions, pipeline configurations, and candidate sourcing."
        actions={
          canManageJobs ? (
            <Button type="button" onClick={() => router.push("/jobs/new")}>
              + Create Job
            </Button>
          ) : undefined
        }
      />

      {/* Filter / Control Bar */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <div style={{ flex: "1 1 240px", minWidth: "200px" }}>
          <Input
            placeholder="Search jobs by title..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCursor(undefined);
            }}
          />
        </div>

        <div style={{ width: "160px" }}>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "", label: "All Statuses" },
              { value: "open", label: "Open" },
              { value: "draft", label: "Draft" },
              { value: "paused", label: "Paused" },
              { value: "closed", label: "Closed" },
            ]}
          />
        </div>

        <div style={{ width: "160px" }}>
          <Select
            value={departmentFilter}
            onChange={(e) => {
              setDepartmentFilter(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "", label: "All Departments" },
              { value: "Engineering", label: "Engineering" },
              { value: "Product", label: "Product" },
              { value: "Design", label: "Design" },
              { value: "Sales", label: "Sales" },
              { value: "Marketing", label: "Marketing" },
              { value: "Operations", label: "Operations" },
              { value: "HR", label: "HR" },
            ]}
          />
        </div>

        <div style={{ width: "160px" }}>
          <Select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "createdAt:desc", label: "Newest First" },
              { value: "createdAt:asc", label: "Oldest First" },
              { value: "title:asc", label: "Title (A-Z)" },
              { value: "title:desc", label: "Title (Z-A)" },
              { value: "status:asc", label: "Status" },
            ]}
          />
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div
          style={{
            backgroundColor: "#451A03",
            border: "1px solid #78350F",
            color: "#FDE68A",
            padding: "0.875rem 1.25rem",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "0.875rem",
          }}
        >
          <span>{errorMsg}</span>
          <Button type="button" variant="secondary" size="sm" onClick={fetchJobs}>
            Retry
          </Button>
        </div>
      )}

      {/* Table Container */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
        }}
      >
        {isLoading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading jobs...</p>
          </div>
        ) : jobs.length === 0 ? (
          isFiltered ? (
            <EmptyState
              title="No jobs match your filters"
              description="Try adjusting or clearing your search term, department, or status filters."
              action={
                <Button type="button" variant="secondary" onClick={handleClearFilters}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              title="No jobs created yet"
              description="Get started by creating your organization's first job description using the button above."
            />
          )
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-subtle)",
                  color: "var(--text-muted)",
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Job Title</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Department</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Location / Type</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Candidates</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600, textAlign: "right" }}>Posted Date</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background-color 0.15s ease",
                  }}
                >
                  {/* Job Title */}
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <Link
                      href={`/jobs/${job.id}`}
                      style={{
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        fontSize: "0.9375rem",
                        textDecoration: "none",
                      }}
                    >
                      {job.title}
                    </Link>
                  </td>

                  {/* Department */}
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {job.department || "—"}
                  </td>

                  {/* Location & Employment Type */}
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {[job.location, job.employmentType ? job.employmentType.replace("_", "-") : null]
                      .filter(Boolean)
                      .join(" • ") || "—"}
                  </td>

                  {/* Candidates Count */}
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <span
                      style={{
                        backgroundColor: "var(--bg-surface-secondary)",
                        color: "var(--text-secondary)",
                        padding: "0.25rem 0.625rem",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.8125rem",
                        fontWeight: 600,
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      {job.candidateCount}
                    </span>
                  </td>

                  {/* Status Badge */}
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <JobStatusBadge status={job.status} />
                  </td>

                  {/* Created Date */}
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-muted)", fontSize: "0.875rem", textAlign: "right" }}>
                    {new Date(job.createdAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Footer / Pagination */}
        <div
          style={{
            padding: "0.875rem 1.25rem",
            backgroundColor: "var(--bg-surface-secondary)",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "0.8125rem",
            color: "var(--text-secondary)",
          }}
        >
          <span>
            Showing {jobs.length} job(s)
            {pagination.totalCount !== null ? ` of ${pagination.totalCount}` : ""}
          </span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setCursor(undefined)}
              disabled={!cursor || isLoading}
            >
              Reset Page
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setCursor(pagination.nextCursor || undefined)}
              disabled={!pagination.hasMore || isLoading}
            >
              Next Page
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function JobsPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <JobsListContent />
    </ProtectedRoute>
  );
}
