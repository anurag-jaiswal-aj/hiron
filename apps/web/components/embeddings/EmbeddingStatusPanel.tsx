"use client";

import React, { useEffect, useState, useCallback } from "react";
import { embeddingsApi, EmbeddingStatusData } from "../../lib/embeddings-api";
import { Badge } from "../ui/Badge";

export function EmbeddingStatusPanel(): React.ReactElement {
  const [data, setData] = useState<EmbeddingStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await embeddingsApi.getTenantStatus();
      setData(response.data);
    } catch (err) {
      setError("Failed to load embedding coverage statistics.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem", backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)" }}>
        <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Loading AI embedding statistics...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)" }}>
        <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1rem" }}>{error || "Failed to load data"}</span>
        <button type="button" onClick={fetchData} style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-primary)", background: "transparent", border: "none", cursor: "pointer", textDecoration: "underline" }}>
          Retry
        </button>
      </div>
    );
  }

  const renderMetric = (label: string, coverage: number, total: number, stale: number, missing: number): React.ReactElement => {
    const percentage = total > 0 ? Math.round((coverage / total) * 100) : 0;
    const isComplete = coverage === total && total > 0;
    
    return (
      <div style={{ display: "flex", flexDirection: "column", padding: "1.25rem", backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.05em", textTransform: "uppercase", margin: 0 }}>
            {label} Coverage
          </h3>
          {coverage === total && total > 0 ? (
            <Badge variant="active" style={{ backgroundColor: "#166534", color: "white", borderColor: "#14532d" }}>
              Fully Indexed
            </Badge>
          ) : (
            <Badge variant="warning" style={{ color: "#d97706", borderColor: "#d97706", backgroundColor: "transparent" }}>
              ⚠️ Action Needed
            </Badge>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", gap: "0.5rem", marginBottom: "1rem" }}>
          <span style={{ fontSize: "1.875rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>{percentage}%</span>
          <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>embedded</span>
        </div>

        {/* Progress Bar */}
        <div style={{ width: "100%", height: "0.5rem", backgroundColor: "var(--bg-app)", borderRadius: "9999px", marginBottom: "1rem", display: "flex", overflow: "hidden" }}>
          <div 
            style={{ height: "100%", backgroundColor: "var(--text-primary)", transition: "all 0.3s ease", width: `${percentage}%` }}
          />
          {total > 0 && stale > 0 && (
            <div 
              style={{ height: "100%", backgroundColor: "#fbbf24", transition: "all 0.3s ease", width: `${Math.round((stale / total) * 100)}%` }}
            />
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginTop: "auto" }}>
          <div style={{ display: "flex", flexDirection: "column", padding: "0.5rem", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-md)" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>Ready</span>
            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#22c55e" }}>{coverage} / {total}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", padding: "0.5rem", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-md)" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>Stale / Missing</span>
            <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#d97706" }}>{stale + missing}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
          ✨ AI Embedding Status
        </h2>
      </div>
      
      <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: "0 0 1rem 0", lineHeight: 1.6 }}>
        Embeddings are vector representations used by the AI engine to semantically score candidate fit against job requirements.
        Missing or stale embeddings may reduce AI scoring accuracy. Model version: <code style={{ fontSize: "0.75rem", backgroundColor: "var(--bg-app)", padding: "0.125rem 0.25rem", borderRadius: "var(--radius-sm)" }}>{data.candidates.modelVersion}</code>
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem" }}>
        {renderMetric("Candidates", data.candidates.withEmbedding, data.candidates.total, data.candidates.stale, data.candidates.missing)}
        {renderMetric("Jobs", data.jobs.withEmbedding, data.jobs.total, data.jobs.stale, data.jobs.missing)}
      </div>
    </div>
  );
}
