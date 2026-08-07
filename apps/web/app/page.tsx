"use client";

import Link from "next/link";
import React from "react";

import { ProtectedRoute } from "../components/ProtectedRoute";
import { useAuth } from "../context/AuthContext";

function DashboardContent(): React.ReactElement {
  const { user, logout } = useAuth();

  return (
    <main
      style={{
        minHeight: "100vh",
        backgroundColor: "#090d16",
        color: "#f8fafc",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Navigation Header */}
      <header
        style={{
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
          padding: "1rem 2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "2rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
          <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "#a5b4fc" }}>Hiron</span>
          <nav style={{ display: "flex", gap: "1rem" }}>
            <Link
              href="/"
              style={{
                color: "#f8fafc",
                backgroundColor: "#1e293b",
                textDecoration: "none",
                fontSize: "0.875rem",
                fontWeight: 600,
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
              }}
            >
              Dashboard
            </Link>
            <Link
              href="/users"
              style={{
                color: "#94a3b8",
                textDecoration: "none",
                fontSize: "0.875rem",
                fontWeight: 500,
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
              }}
            >
              Team Management
            </Link>
          </nav>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
            {user?.fullName || user?.email} ({user?.role})
          </span>
          <button
            type="button"
            onClick={() => logout()}
            style={{
              padding: "0.4rem 0.875rem",
              borderRadius: "6px",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#cbd5e1",
              fontSize: "0.8125rem",
              cursor: "pointer",
            }}
          >
            Sign Out
          </button>
        </div>
      </header>

      <div
        style={{
          maxWidth: "800px",
          margin: "0 auto",
          backgroundColor: "#0f172a",
          borderRadius: "16px",
          border: "1px solid #1e293b",
          padding: "2rem",
        }}
      >

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "1rem",
            marginBottom: "2rem",
          }}
        >
          <div style={{ padding: "1.25rem", borderRadius: "12px", backgroundColor: "#1e293b" }}>
            <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>Organization Tenant</span>
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "#a5b4fc" }}>
              {user?.tenantId}
            </p>
          </div>

          <div style={{ padding: "1.25rem", borderRadius: "12px", backgroundColor: "#1e293b" }}>
            <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>Role</span>
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "#38bdf8" }}>
              {user?.role}
            </p>
          </div>

          <div style={{ padding: "1.25rem", borderRadius: "12px", backgroundColor: "#1e293b" }}>
            <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>Email</span>
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.9375rem", fontWeight: 600, color: "#34d399" }}>
              {user?.email}
            </p>
          </div>
        </div>

        <div style={{ padding: "1.5rem", borderRadius: "12px", backgroundColor: "#1e293b", border: "1px solid #334155" }}>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.125rem", fontWeight: 600 }}>System Status</h2>
          <p style={{ margin: 0, fontSize: "0.875rem", color: "#cbd5e1" }}>
            ✓ Authenticated Session Active. Multi-tenant security isolation enforced.
          </p>
        </div>
      </div>
    </main>
  );
}

export default function Home(): React.ReactElement {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
