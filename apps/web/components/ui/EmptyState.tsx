"use client";

import React from "react";

export interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps): React.ReactElement {
  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: "3.5rem 2rem",
        textAlign: "center",
        color: "var(--text-secondary)",
      }}
    >
      <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
        {title}
      </h3>
      <p style={{ fontSize: "0.875rem", margin: "0 0 1.5rem 0" }}>{description}</p>
      {action}
    </div>
  );
}
