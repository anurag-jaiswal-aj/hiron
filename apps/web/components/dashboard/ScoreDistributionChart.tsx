import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { ScoreDistributionData } from "../../lib/dashboard-api";

interface Props {
  data: ScoreDistributionData;
}

export function ScoreDistributionChart({ data }: Props): React.ReactElement {
  if (!data || data.totalScored === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)", height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        No candidate scores available yet.
      </div>
    );
  }

  const chartData = [
    { name: "High Fit (80+)", value: data.highFitCount, color: "#10b981" },
    { name: "Medium Fit (60-79)", value: data.mediumFitCount, color: "#f59e0b" },
    { name: "Low Fit (<60)", value: data.lowFitCount, color: "#ef4444" }
  ].filter(item => item.value > 0);

  return (
    <div style={{ 
      padding: "1rem", 
      border: "1px solid var(--border-subtle)", 
      borderRadius: "var(--radius-md)",
      backgroundColor: "var(--bg-surface)",
      height: "320px",
      display: "flex",
      flexDirection: "column"
    }}>
      <h3 style={{ margin: "0 0 1rem", fontSize: "1rem", fontWeight: 600 }}>AI Score Distribution</h3>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              formatter={(value: number) => [`${value} candidates`, "Count"]}
              contentStyle={{ borderRadius: "8px", border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)" }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: "0.875rem" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {data.averageFitScore !== null && data.averageFitScore !== undefined && (
        <div style={{ textAlign: "center", marginTop: "0.5rem", fontSize: "0.875rem", color: "var(--text-muted)" }}>
          Average Score: <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{data.averageFitScore.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}
