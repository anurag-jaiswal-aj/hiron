"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AuditFilters } from "../../components/audit-logs/AuditFilters";
import { AuditLogsTable } from "../../components/audit-logs/AuditLogsTable";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";
import { auditApi, AuditLogData, AuditListParams } from "../../lib/audit-api";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";

export default function AuditLogsPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <AuditLogsContent />
    </ProtectedRoute>
  );
}

function AuditLogsContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();
  
  useEffect(() => {
    if (user && user.role === "hiring_manager") {
      router.replace("/");
    }
  }, [user, router]);
  const [logs, setLogs] = useState<AuditLogData[]>([]);
  const [filters, setFilters] = useState<AuditListParams>({});
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchLogs = useCallback(async (currentFilters: AuditListParams, append = false) => {
    try {
      if (!append) {
        setIsLoading(true);
      } else {
        setIsLoadingMore(true);
      }
      setIsError(false);

      const res = await auditApi.listAuditLogs(currentFilters);
      
      setLogs((prev) => (append ? [...prev, ...res.data] : res.data));
      setNextCursor(res.pagination.nextCursor || null);
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
      setIsError(true);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  // Fetch when filters change
  useEffect(() => {
    fetchLogs(filters, false);
  }, [filters, fetchLogs]);

  const handleFiltersChange = useCallback((newFilters: AuditListParams): void => {
    // Reset cursor when filters change
    setFilters({ ...newFilters, cursor: undefined });
  }, []);

  const handleLoadMore = (): void => {
    if (nextCursor && !isLoadingMore) {
      const nextFilters = { ...filters, cursor: nextCursor };
      setFilters(nextFilters);
      fetchLogs(nextFilters, true);
    }
  };

  const hasActiveFilters = Object.keys(filters).some(
    (k) => k !== "cursor" && k !== "limit" && filters[k as keyof AuditListParams] !== undefined
  );

  if (user?.role === "hiring_manager") {
    return null;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      <header>
        <h1
          style={{
            fontSize: "1.875rem",
            fontWeight: 700,
            color: "var(--text-primary)",
            margin: "0 0 0.5rem 0",
          }}
        >
          Audit Logs
        </h1>
        <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "1rem" }}>
          Immutable record of system-wide data mutations.
          {user?.role === "recruiter" && (
            <span style={{ marginLeft: "0.5rem", fontStyle: "italic", color: "var(--text-muted)" }}>
              (Viewing only your own actions)
            </span>
          )}
        </p>
      </header>

      <AuditFilters initialFilters={filters} onFiltersChange={handleFiltersChange} />

      <div>
        {isLoading && logs.length === 0 ? (
          <div style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading audit logs...
          </div>
        ) : isError && logs.length === 0 ? (
          <EmptyState
            title="Failed to Load"
            description="We encountered an error while fetching the audit logs."
            action={
              <Button variant="primary" onClick={() => fetchLogs(filters, false)}>
                Retry
              </Button>
            }
          />
        ) : logs.length === 0 ? (
          <EmptyState
            title={hasActiveFilters ? "No matches found" : "No audit history"}
            description={
              hasActiveFilters
                ? "No audit events match your current filter criteria."
                : "No audit events have been recorded yet."
            }
          />
        ) : (
          <AuditLogsTable
            logs={logs}
            hasMore={!!nextCursor}
            onLoadMore={handleLoadMore}
          />
        )}

        {isLoadingMore && (
          <div style={{ padding: "1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Loading more logs...
          </div>
        )}
      </div>
    </div>
  );
}
