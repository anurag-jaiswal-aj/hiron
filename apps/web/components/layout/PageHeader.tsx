"use client";

import Link from "next/link";
import React from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  backHref?: string;
  backLabel?: string;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  backHref,
  backLabel,
  actions,
}: PageHeaderProps): React.ReactElement {
  return (
    <div style={{ marginBottom: "2rem" }}>
      {backHref && (
        <div style={{ marginBottom: "0.75rem" }}>
          <Link
            href={backHref}
            style={{
              color: "var(--text-secondary)",
              fontSize: "0.875rem",
              fontWeight: 500,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.375rem",
            }}
          >
            ← {backLabel || "Back"}
          </Link>
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
              {subtitle}
            </p>
          )}
        </div>

        {actions && <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>{actions}</div>}
      </div>
    </div>
  );
}
