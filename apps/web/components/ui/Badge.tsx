"use client";

import React from "react";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: "neutral" | "active" | "muted" | "warning" | "error";
  style?: React.CSSProperties;
  title?: string;
}

export function Badge({
  children,
  variant = "neutral",
  style,
  title,
}: BadgeProps): React.ReactElement {
  let bg = "var(--bg-surface-secondary)";
  let color = "var(--text-secondary)";
  let border = "1px solid var(--border-subtle)";

  if (variant === "active") {
    bg = "var(--bg-hover)";
    color = "var(--text-primary)";
    border = "1px solid var(--border-strong)";
  } else if (variant === "muted") {
    bg = "var(--bg-app)";
    color = "var(--text-muted)";
    border = "1px solid var(--border-subtle)";
  } else if (variant === "warning") {
    bg = "#422006"; // dark amber/orange background
    color = "#FCD34D"; // amber-300 text
    border = "1px solid #78350F"; // amber-900 border
  } else if (variant === "error") {
    bg = "#451A03";
    color = "#FDE68A";
    border = "1px solid #78350F";
  }

  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "0.1875rem 0.5rem",
        borderRadius: "var(--radius-sm)",
        fontSize: "0.75rem",
        fontWeight: 600,
        backgroundColor: bg,
        color,
        border,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </span>
  );
}
