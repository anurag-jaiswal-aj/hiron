"use client";

import React from "react";

import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { useAuth } from "../context/AuthContext";
import { EmbeddingStatusPanel } from "../components/embeddings/EmbeddingStatusPanel";

function DashboardContent(): React.ReactElement {
  const { user } = useAuth();

  return (
    <AppShell>
      <PageHeader
        title="Overview"
        subtitle="Recruiting intelligence overview and active session parameters."
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1.25rem",
          marginBottom: "2rem",
        }}
      >
        <div
          style={{
            padding: "1.25rem",
            borderRadius: "var(--radius-lg)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            Organization Tenant ID
          </span>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", wordBreak: "break-all" }}>
            {user?.tenantId}
          </p>
        </div>

        <div
          style={{
            padding: "1.25rem",
            borderRadius: "var(--radius-lg)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            User Role
          </span>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize" }}>
            {user?.role ? user.role.replace("_", " ") : "—"}
          </p>
        </div>

        <div
          style={{
            padding: "1.25rem",
            borderRadius: "var(--radius-lg)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            Email Identity
          </span>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {user?.email}
          </p>
        </div>
      </div>

      <div
        style={{
          padding: "1.5rem",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
          Security & Session Status
        </h2>
        <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Authenticated Session Active. Multi-tenant row-level security (RLS) and role-based access control (RBAC) enforced.
        </p>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <EmbeddingStatusPanel />
      </div>
    </AppShell>
  );
}

export default function Home(): React.ReactElement {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
