"use client";

import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, style, ...props }: InputProps): React.ReactElement {
  return (
    <div style={{ width: "100%" }}>
      {label && (
        <label
          htmlFor={id}
          style={{
            display: "block",
            fontSize: "0.875rem",
            fontWeight: 600,
            color: "var(--text-secondary)",
            marginBottom: "0.375rem",
          }}
        >
          {label}
        </label>
      )}
      <input
        id={id}
        style={{
          width: "100%",
          backgroundColor: "var(--bg-surface-secondary)",
          border: error ? "1px solid #7F1D1D" : "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          color: "var(--text-primary)",
          padding: "0.625rem 0.75rem",
          fontSize: "0.875rem",
          outline: "none",
          transition: "border-color 0.15s ease",
          ...style,
        }}
        {...props}
      />
      {error && (
        <div style={{ fontSize: "0.8125rem", color: "#F87171", marginTop: "0.25rem" }}>
          {error}
        </div>
      )}
    </div>
  );
}
