import React from "react";

export interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
}

export function MetricCard({ label, value, icon, trend, trendDirection }: MetricCardProps): React.ReactElement {
  const trendColor = 
    trendDirection === "up" ? "var(--color-success, #10b981)" : 
    trendDirection === "down" ? "var(--color-danger, #ef4444)" : 
    "var(--text-muted)";

  return (
    <div
      style={{
        padding: "1.25rem",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: "1.25rem" }}>{icon}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
        <span style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
          {value}
        </span>
        {trend && (
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: trendColor }}>
            {trendDirection === "up" ? "↑" : trendDirection === "down" ? "↓" : ""} {trend}
          </span>
        )}
      </div>
    </div>
  );
}
