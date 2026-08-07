"use client";

import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "destructive" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  style,
  disabled,
  ...props
}: ButtonProps): React.ReactElement {
  let bg = "var(--btn-primary-bg)";
  let color = "var(--btn-primary-text)";
  let border = "none";

  if (variant === "secondary") {
    bg = "var(--btn-secondary-bg)";
    color = "var(--btn-secondary-text)";
    border = "1px solid var(--border-subtle)";
  } else if (variant === "destructive") {
    bg = "transparent";
    color = "#F87171";
    border = "1px solid #7F1D1D";
  } else if (variant === "ghost") {
    bg = "transparent";
    color = "var(--text-secondary)";
    border = "none";
  }

  let padding = "0.5rem 1rem";
  let fontSize = "0.875rem";

  if (size === "sm") {
    padding = "0.375rem 0.75rem";
    fontSize = "0.8125rem";
  } else if (size === "lg") {
    padding = "0.625rem 1.25rem";
    fontSize = "0.9375rem";
  }

  return (
    <button
      disabled={disabled}
      style={{
        backgroundColor: disabled ? "var(--bg-surface-secondary)" : bg,
        color: disabled ? "var(--text-muted)" : color,
        border,
        borderRadius: "var(--radius-md)",
        padding,
        fontSize,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.5rem",
        transition: "all 0.15s ease",
        opacity: disabled ? 0.6 : 1,
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}
