"use client";

import React from "react";

interface UserStatusBadgeProps {
  isActive: boolean;
}

export function UserStatusBadge({ isActive }: UserStatusBadgeProps): React.ReactElement {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        padding: "0.25rem 0.625rem",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        backgroundColor: isActive ? "rgba(34, 197, 94, 0.12)" : "rgba(239, 68, 68, 0.12)",
        color: isActive ? "#4ade80" : "#f87171",
        border: `1px solid ${isActive ? "rgba(74, 222, 128, 0.3)" : "rgba(248, 113, 113, 0.3)"}`,
        whiteSpace: "nowrap",
      }}
      aria-label={`User status: ${isActive ? "Active" : "Deactivated"}`}
    >
      <span
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          backgroundColor: isActive ? "#4ade80" : "#f87171",
        }}
      />
      {isActive ? "Active" : "Inactive"}
    </span>
  );
}
