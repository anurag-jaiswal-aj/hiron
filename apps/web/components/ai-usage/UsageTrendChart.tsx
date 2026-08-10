"use client";

import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { DailyUsagePoint } from "../../lib/ai-usage-api";

interface Props {
  data: DailyUsagePoint[];
}

export function UsageTrendChart({ data }: Props): React.ReactElement {
  if (!data || data.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)", height: "360px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        No trend data available for this period.
      </div>
    );
  }

  // Ensure data is sorted chronologically
  const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));

  const chartData = sortedData.map(d => {
    // Parse 'YYYY-MM-DD' correctly ignoring timezones
    const [year, month, day] = d.date.split('-');
    const dateObj = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const formattedDate = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    return {
      ...d,
      formattedDate
    };
  });

  return (
    <div style={{ 
      padding: "1.25rem", 
      border: "1px solid var(--border-subtle)", 
      borderRadius: "var(--radius-lg)",
      backgroundColor: "var(--bg-surface)",
      height: "360px",
      display: "flex",
      flexDirection: "column",
      minWidth: 0
    }}>
      <h3 style={{ margin: "0 0 1rem", fontSize: "1.125rem", fontWeight: 600 }}>Daily Cost Trend (USD)</h3>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
            <XAxis 
              dataKey="formattedDate" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 12, fill: "var(--text-muted)" }} 
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 12, fill: "var(--text-muted)" }}
              tickFormatter={(value) => `$${value}`}
              dx={-10}
            />
            <Tooltip
              contentStyle={{ borderRadius: "8px", border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)", backgroundColor: "var(--bg-surface)" }}
              formatter={(value: number) => [`$${value.toFixed(2)}`, "Cost"]}
              labelStyle={{ color: "var(--text-primary)", fontWeight: 600, marginBottom: "0.25rem" }}
            />
            <Line 
              type="monotone" 
              dataKey="costUsd" 
              stroke="#3b82f6" 
              strokeWidth={3}
              dot={{ r: 4, fill: "var(--bg-surface)", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
