"use client";

import React from "react";
import { OperationUsageBreakdown } from "../../lib/ai-usage-api";

interface Props {
  data: OperationUsageBreakdown[];
}

export function OperationBreakdownTable({ data }: Props): React.ReactElement {
  if (!data || data.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)", height: "360px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        No operation data available for this period.
      </div>
    );
  }

  return (
    <div style={{ 
      border: "1px solid var(--border-subtle)", 
      borderRadius: "var(--radius-lg)",
      backgroundColor: "var(--bg-surface)",
      display: "flex",
      flexDirection: "column",
      height: "360px",
      minWidth: 0
    }}>
      <div style={{ padding: "1.25rem", borderBottom: "1px solid var(--border-subtle)" }}>
        <h3 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600 }}>Operation Breakdown</h3>
        <p style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Note: Token usage and cache hit rate per-operation are not currently provided by the API.
        </p>
      </div>
      <div style={{ flex: 1, overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
          <thead style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-surface-secondary)", zIndex: 1 }}>
            <tr>
              <th style={{ padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, color: "var(--text-secondary)" }}>Operation</th>
              <th style={{ padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, color: "var(--text-secondary)", textAlign: "right" }}>Count</th>
              <th style={{ padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, color: "var(--text-secondary)", textAlign: "right" }}>Cost (USD)</th>
              <th style={{ padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, color: "var(--text-secondary)", textAlign: "right" }}>Avg Latency</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr key={item.operation} style={{ borderBottom: index < data.length - 1 ? "1px solid var(--border-subtle)" : "none" }}>
                <td style={{ padding: "0.75rem 1.25rem", color: "var(--text-primary)", fontWeight: 500 }}>
                  {item.operation}
                </td>
                <td style={{ padding: "0.75rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>
                  {item.count.toLocaleString()}
                </td>
                <td style={{ padding: "0.75rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>
                  ${item.costUsd.toFixed(4)}
                </td>
                <td style={{ padding: "0.75rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>
                  {item.avgLatencyMs.toLocaleString()} ms
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
