"use client";

import React from "react";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Array<{ value: string; label: string }>;
}

export function Select({ label, options, id, style, ...props }: SelectProps): React.ReactElement {
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
      <select
        id={id}
        style={{
          width: "100%",
          backgroundColor: "var(--bg-surface-secondary)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          color: "var(--text-primary)",
          padding: "0.625rem 0.75rem",
          fontSize: "0.875rem",
          outline: "none",
          cursor: "pointer",
          ...style,
        }}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
