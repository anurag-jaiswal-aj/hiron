"use client";

import React, { useCallback, useEffect, useState } from "react";

import { AppShell } from "../../components/layout/AppShell";
import { PageHeader } from "../../components/layout/PageHeader";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useAuth } from "../../context/AuthContext";
import { ApiError, httpClient } from "../../lib/api";

export interface CandidateListItem {
  id: string;
  full_name: string;
  email: string | null;
  current_title: string | null;
  current_company: string | null;
  location: string | null;
  total_experience_years: number | null;
  skills: string[];
  source: string;
  is_archived: boolean;
  created_at: string;
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

function CandidatesListContent(): React.ReactElement {
  const { user } = useAuth();
  const canManageCandidates = user?.role === "org_admin" || user?.role === "recruiter";

  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    hasMore: false,
    nextCursor: null,
    totalCount: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filter / Search / Sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [skillsFilter, setSkillsFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [experienceMin, setExperienceMin] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [sortBy, setSortBy] = useState("createdAt:desc");
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const fetchCandidates = useCallback(async () => {
    setErrorMsg(null);
    setIsLoading(true);

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append("q", searchQuery.trim());
      if (skillsFilter.trim()) params.append("skills", skillsFilter.trim());
      if (locationFilter.trim()) params.append("location", locationFilter.trim());
      if (experienceMin.trim()) params.append("experienceMin", experienceMin.trim());
      if (sourceFilter.trim()) params.append("source", sourceFilter.trim());
      if (sortBy) params.append("sort", sortBy);
      if (cursor) params.append("cursor", cursor);
      params.append("limit", "20");

      const response = await httpClient.get<ResponseEnvelope<PaginatedData<CandidateListItem>>>(
        `/api/v1/candidates?${params.toString()}`
      );

      if (response && response.data) {
        setCandidates(response.data.data || []);
        setPagination(
          response.data.pagination || { hasMore: false, nextCursor: null, totalCount: 0 }
        );
      } else {
        setCandidates([]);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to load candidates list. Please check network connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, skillsFilter, locationFilter, experienceMin, sourceFilter, sortBy, cursor]);

  // Debounce effect for search typing
  useEffect(() => {
    const handler = setTimeout(() => {
      fetchCandidates();
    }, 300);
    return () => clearTimeout(handler);
  }, [fetchCandidates]);

  const handleClearFilters = (): void => {
    setSearchQuery("");
    setSkillsFilter("");
    setLocationFilter("");
    setExperienceMin("");
    setSourceFilter("");
    setSortBy("createdAt:desc");
    setCursor(undefined);
  };

  const isFiltered = Boolean(searchQuery || skillsFilter || locationFilter || experienceMin || sourceFilter);

  return (
    <AppShell>
      <PageHeader
        title="Candidates"
        subtitle="Manage your talent pool, view candidate profiles, and organize pipeline sourcing."
        actions={
          canManageCandidates ? (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <Button type="button" variant="secondary" disabled>
                Upload
              </Button>
              <Button type="button" disabled>
                + Add Candidate
              </Button>
            </div>
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
        <div style={{ flex: "1 1 200px", minWidth: "160px" }}>
          <Input
            placeholder="Search candidates..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCursor(undefined);
            }}
          />
        </div>

        <div style={{ width: "140px" }}>
          <Input
            placeholder="Skills (comma sep)"
            value={skillsFilter}
            onChange={(e) => {
              setSkillsFilter(e.target.value);
              setCursor(undefined);
            }}
          />
        </div>

        <div style={{ width: "120px" }}>
          <Select
            value={experienceMin}
            onChange={(e) => {
              setExperienceMin(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "", label: "Any Exp" },
              { value: "1", label: "1+ years" },
              { value: "3", label: "3+ years" },
              { value: "5", label: "5+ years" },
              { value: "10", label: "10+ years" },
            ]}
          />
        </div>

        <div style={{ width: "140px" }}>
          <Input
            placeholder="Location"
            value={locationFilter}
            onChange={(e) => {
              setLocationFilter(e.target.value);
              setCursor(undefined);
            }}
          />
        </div>

        <div style={{ width: "130px" }}>
          <Select
            value={sourceFilter}
            onChange={(e) => {
              setSourceFilter(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "", label: "All Sources" },
              { value: "upload", label: "Upload" },
              { value: "manual", label: "Manual" },
            ]}
          />
        </div>

        <div style={{ width: "150px" }}>
          <Select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setCursor(undefined);
            }}
            options={[
              { value: "createdAt:desc", label: "Newest First" },
              { value: "createdAt:asc", label: "Oldest First" },
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
          <Button type="button" variant="secondary" size="sm" onClick={fetchCandidates}>
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
            <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading candidates...</p>
          </div>
        ) : candidates.length === 0 ? (
          isFiltered ? (
            <EmptyState
              title="No candidates match your search"
              description="Try different keywords or clearing your filters."
              action={
                <Button type="button" variant="secondary" onClick={handleClearFilters}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              title="No candidates in your pool"
              description="Get started by uploading resumes or adding candidates manually."
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
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Name / Title</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Skills</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Exp</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Location</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600, textAlign: "right" }}>Added</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr
                  key={candidate.id}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background-color 0.15s ease",
                  }}
                >
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.9375rem" }}>
                      {candidate.full_name}
                    </div>
                    <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: "2px" }}>
                      {[candidate.current_title, candidate.current_company].filter(Boolean).join(" @ ") || "—"}
                    </div>
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {candidate.skills && candidate.skills.length > 0 ? (
                      <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                        {candidate.skills.slice(0, 3).map(skill => (
                          <span
                            key={skill}
                            style={{
                              backgroundColor: "var(--bg-surface-secondary)",
                              padding: "0.125rem 0.375rem",
                              borderRadius: "var(--radius-sm)",
                              border: "1px solid var(--border-subtle)",
                              fontSize: "0.75rem"
                            }}
                          >
                            {skill}
                          </span>
                        ))}
                        {candidate.skills.length > 3 && (
                          <span style={{ fontSize: "0.75rem", alignSelf: "center", color: "var(--text-muted)" }}>
                            +{candidate.skills.length - 3}
                          </span>
                        )}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {candidate.total_experience_years !== null ? `${candidate.total_experience_years}y` : "—"}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {candidate.location || "—"}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--text-muted)", fontSize: "0.875rem", textAlign: "right" }}>
                    {new Date(candidate.created_at).toLocaleDateString("en-US", {
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
            Showing {candidates.length} candidate(s)
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

export default function CandidatesPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <CandidatesListContent />
    </ProtectedRoute>
  );
}
