"use client";

import React, { useState } from "react";
import { AuditLogData } from "../../lib/audit-api";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { AuditLogDetailModal } from "./AuditLogDetailModal";

interface AuditLogsTableProps {
  logs: AuditLogData[];
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export function AuditLogsTable({
  logs,
  onLoadMore,
  hasMore,
}: AuditLogsTableProps): React.ReactElement {
  const [selectedLog, setSelectedLog] = useState<AuditLogData | null>(null);

  const renderActionBadge = (action: string): React.ReactElement => {
    switch (action) {
      case "created":
      case "login_success":
        return <Badge variant="active">{action}</Badge>;
      case "deleted":
      case "login_failed":
        return <Badge variant="error">{action}</Badge>;
      case "updated":
      case "stage_changed":
      case "scored":
        return <Badge variant="warning">{action}</Badge>;
      default:
        return <Badge variant="neutral">{action}</Badge>;
    }
  };

  const formatDate = (dateString: string): string => {
    const d = new Date(dateString);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div
        style={{
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          overflow: "hidden",
        }}
      >
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr
                style={{
                  backgroundColor: "var(--bg-surface-secondary)",
                  borderBottom: "1px solid var(--border-subtle)",
                }}
              >
                <th style={thStyle}>Timestamp</th>
                <th style={thStyle}>Action</th>
                <th style={thStyle}>Entity</th>
                <th style={thStyle}>Actor</th>
                <th style={thStyle}>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={tdStyle}>
                    <div style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                      {formatDate(log.createdAt)}
                    </div>
                  </td>
                  <td style={tdStyle}>{renderActionBadge(log.action)}</td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                      <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                        {log.entityType}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          fontFamily: "monospace",
                        }}
                      >
                        {log.entityId}
                      </span>
                    </div>
                  </td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                      {log.actor ? (
                        <>
                          <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                            {log.actor.fullName}
                          </span>
                          <span
                            style={{
                              fontSize: "0.75rem",
                              color: "var(--text-muted)",
                              fontFamily: "monospace",
                            }}
                          >
                            {log.actor.id}
                          </span>
                        </>
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                          System
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={tdStyle}>
                    {log.changes ? (
                      <Button variant="secondary" onClick={() => setSelectedLog(log)}>
                        View Changes
                      </Button>
                    ) : (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "2rem", textAlign: "center" }}>
                    <div style={{ color: "var(--text-muted)" }}>No audit logs found.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {hasMore && onLoadMore && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: "1rem" }}>
          <Button variant="secondary" onClick={onLoadMore}>
            Load More
          </Button>
        </div>
      )}

      {selectedLog && (
        <AuditLogDetailModal
          isOpen={true}
          onClose={() => setSelectedLog(null)}
          action={selectedLog.action}
          changes={selectedLog.changes}
        />
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "1rem",
  fontWeight: 600,
  fontSize: "0.875rem",
  color: "var(--text-secondary)",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "1rem",
  verticalAlign: "top",
};
