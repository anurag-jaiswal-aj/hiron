"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { PageHeader } from "../../components/layout/PageHeader";
import { AppShell } from "../../components/layout/AppShell";
import { MetricCard } from "../../components/dashboard/MetricCard";
import dynamic from "next/dynamic";

const UsageTrendChart = dynamic(
  () => import("../../components/ai-usage/UsageTrendChart").then((mod) => mod.UsageTrendChart),
  {
    ssr: false,
    loading: () => (
      <div style={{
        padding: "1.25rem",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--bg-surface)",
        height: "360px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--text-muted)"
      }}>
        Loading chart...
      </div>
    )
  }
);
import { OperationBreakdownTable } from "../../components/ai-usage/OperationBreakdownTable";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";
import { aiUsageApi, AIUsageSummaryData } from "../../lib/ai-usage-api";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";

export default function AIUsagePage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <AIUsageContent />
    </ProtectedRoute>
  );
}

function AIUsageContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && user.role !== "org_admin") {
      router.replace("/");
    }
  }, [user, router]);

  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("30d");
  const [summary, setSummary] = useState<AIUsageSummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  const fetchSummary = useCallback(async (selectedPeriod: "7d" | "30d" | "90d") => {
    setIsLoading(true);
    setIsError(false);
    try {
      const response = await aiUsageApi.getSummary({ period: selectedPeriod });
      setSummary(response.data);
    } catch (error) {
      console.error("Failed to load AI usage summary", error);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role === "org_admin") {
      void fetchSummary(period);
    }
  }, [period, fetchSummary, user?.role]);

  // Don't render content until auth redirect happens for non-admins
  if (user && user.role !== "org_admin") {
    return (
      <AppShell>
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
          Redirecting...
        </div>
      </AppShell>
    );
  }

  const periodSelector = (
    <select
      aria-label="Time period"
      value={period}
      onChange={(e) => setPeriod(e.target.value as "7d" | "30d" | "90d")}
      style={{
        padding: "0.5rem 2rem 0.5rem 1rem",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        backgroundColor: "var(--bg-surface)",
        color: "var(--text-primary)",
        fontSize: "0.875rem",
        appearance: "none",
        backgroundImage: "url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23666%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 0.7rem top 50%",
        backgroundSize: "0.65rem auto",
        cursor: "pointer",
      }}
    >
      <option value="7d">Last 7 Days</option>
      <option value="30d">Last 30 Days</option>
      <option value="90d">Last 90 Days</option>
    </select>
  );

  let content: React.ReactNode;

  if (isLoading && !summary) {
    content = (
      <div style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
        Loading AI usage data...
      </div>
    );
  } else if (isError && !summary) {
    content = (
      <EmptyState
        title="Failed to load AI usage"
        description="There was a problem communicating with the server."
        action={
          <Button onClick={() => void fetchSummary(period)}>
            Retry
          </Button>
        }
      />
    );
  } else if (summary && summary.totalOperations === 0) {
    content = (
      <EmptyState
        title="No AI Usage Data"
        description={`No AI operations were performed in the selected period (${period}).`}
      />
    );
  } else if (summary) {
    content = (
      <div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1.25rem",
            marginBottom: "2rem",
          }}
        >
          <MetricCard
            label="Total Cost (USD)"
            value={`$${summary.totalCostUsd.toFixed(2)}`}
            icon="💵"
          />
          <MetricCard
            label="Total Tokens"
            value={summary.totalTokens.toLocaleString()}
            icon="🪙"
          />
          <MetricCard
            label="Total Operations"
            value={summary.totalOperations.toLocaleString()}
            icon="⚡"
          />
          <MetricCard
            label="Cache Hit Rate"
            value={`${(summary.cacheHitRate * 100).toFixed(1)}%`}
            icon="🎯"
          />
        </div>

        {/* Charts & Tables */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "1.5rem",
          marginBottom: "2rem"
        }}>
          <style dangerouslySetInnerHTML={{__html: `
            .ai-usage-layout {
              display: flex;
              flex-direction: column;
              gap: 1.5rem;
              min-width: 0;
            }
            .ai-usage-layout > * {
              min-width: 0;
            }
            @media (min-width: 900px) {
              .ai-usage-layout {
                display: grid;
                grid-template-columns: 2fr 1fr;
                align-items: start;
              }
            }
          `}} />
          <div className="ai-usage-layout">
            <UsageTrendChart data={summary.byDay} />
            <OperationBreakdownTable data={summary.byOperation} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <AppShell>
      <PageHeader
        title="AI Usage Analytics"
        subtitle="Monitor token usage, cost, and cache performance."
        actions={periodSelector}
      />
      {content}
    </AppShell>
  );
}
