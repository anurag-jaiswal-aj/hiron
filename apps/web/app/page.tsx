"use client";

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
        padding: "2rem",
      }}
    >
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700 }}>Recruiting Dashboard</h1>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
              Welcome back, {user?.fullName || "Recruiter"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => logout()}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "8px",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#f8fafc",
              fontSize: "0.875rem",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Sign Out
          </button>
        </div>

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
