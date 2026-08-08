"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

import { useAuth } from "../../context/AuthContext";

export function Sidebar(): React.ReactElement {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { label: "Overview", href: "/" },
    { label: "Jobs", href: "/jobs" },
    { label: "Candidates", href: "/candidates" },
    { label: "Team", href: "/users" },
  ];

  return (
    <aside
      className="sidebar"
      style={{
        width: "240px",
        minWidth: "240px",
        backgroundColor: "var(--bg-surface)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "1.5rem 1rem",
        height: "100vh",
        position: "sticky",
        top: 0,
      }}
    >
      <div>
        {/* Brand Header */}
        <div style={{ padding: "0.5rem 0.75rem", marginBottom: "2rem" }}>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
            HIRON
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            Recruiting Intelligence
          </div>
        </div>

        {/* Navigation Section */}
        <nav style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "block",
                  padding: "0.5rem 0.75rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                  backgroundColor: isActive ? "var(--bg-surface-secondary)" : "transparent",
                  transition: "background-color 0.15s ease",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User Session Footer */}
      <div
        style={{
          borderTop: "1px solid var(--border-subtle)",
          paddingTop: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
        }}
      >
        <div style={{ padding: "0 0.5rem" }}>
          <div
            style={{
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "var(--text-primary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {user?.fullName || user?.email}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
            {user?.role ? user.role.replace("_", " ") : "Member"}
          </div>
        </div>

        <button
          type="button"
          onClick={logout}
          style={{
            width: "100%",
            backgroundColor: "transparent",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-secondary)",
            fontSize: "0.8125rem",
            fontWeight: 500,
            padding: "0.5rem",
            cursor: "pointer",
            textAlign: "center",
          }}
        >
          Sign Out
        </button>
      </div>
    </aside>
  );
}
