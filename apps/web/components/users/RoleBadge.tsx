"use client";

import React from "react";

interface RoleBadgeProps {
  role: string;
}

const ROLE_CONFIG: Record<string, { label: string; bg: string; color: string; border: string }> = {
  org_admin: {
    label: "Org Admin",
    bg: "rgba(99, 102, 241, 0.15)",
    color: "#a5b4fc",
    border: "rgba(129, 140, 248, 0.3)",
  },
  recruiter: {
    label: "Recruiter",
    bg: "rgba(14, 165, 233, 0.15)",
    color: "#38bdf8",
    border: "rgba(56, 189, 248, 0.3)",
  },
  hiring_manager: {
    label: "Hiring Manager",
    bg: "rgba(16, 185, 129, 0.15)",
    color: "#34d399",
    border: "rgba(52, 211, 153, 0.3)",
  },
  read_only: {
    label: "Read Only",
    bg: "rgba(148, 163, 184, 0.15)",
    color: "#cbd5e1",
    border: "rgba(203, 213, 225, 0.3)",
  },
};

export function RoleBadge({ role }: RoleBadgeProps): React.ReactElement {
  const normalizedRole = role.toLowerCase();
  const config = ROLE_CONFIG[normalizedRole] || {
    label: role,
    bg: "rgba(148, 163, 184, 0.15)",
    color: "#cbd5e1",
    border: "rgba(203, 213, 225, 0.3)",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "0.25rem 0.625rem",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
        whiteSpace: "nowrap",
      }}
    >
      {config.label}
    </span>
  );
}
