"use client";

import React, { useEffect, useState } from "react";

import { AppShell } from "../../components/layout/AppShell";
import { PageHeader } from "../../components/layout/PageHeader";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { dashboardApi, DashboardSummaryData } from "../../lib/dashboard-api";
import { MetricCard } from "../../components/dashboard/MetricCard";
import { PipelineOverview } from "../../components/dashboard/PipelineOverview";
import { RecentActivity } from "../../components/dashboard/RecentActivity";
import { DashboardOnboarding } from "../../components/dashboard/DashboardOnboarding";
import { EmbeddingStatusPanel } from "../../components/embeddings/EmbeddingStatusPanel";
import dynamic from "next/dynamic";

const ScoreDistributionChart = dynamic(
  () => import("../../components/dashboard/ScoreDistributionChart").then((mod) => mod.ScoreDistributionChart),
  {
    ssr: false,
    loading: () => (
      <div style={{
        padding: "1rem",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface)",
        height: "320px",
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

function DashboardContent(): React.ReactElement {
  const [summary, setSummary] = useState<DashboardSummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    dashboardApi.getDashboardSummary()
      .then(res => {
        if (isMounted) {
          setSummary(res.data);
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          console.error("Dashboard load failed", err);
          setErrorMsg("Failed to load dashboard data. Please try again.");
          setIsLoading(false);
        }
      });
    return () => { isMounted = false; };
  }, []);

  if (isLoading) {
    return (
      <AppShell>
        <PageHeader title="Dashboard" subtitle="Loading your recruiting overview..." />
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
          Loading dashboard metrics...
        </div>
      </AppShell>
    );
  }

  if (errorMsg) {
    return (
      <AppShell>
        <PageHeader title="Dashboard" />
        <div style={{ padding: "1rem", backgroundColor: "var(--color-danger)", color: "white", borderRadius: "var(--radius-md)", marginBottom: "2rem" }}>
          {errorMsg}
        </div>
      </AppShell>
    );
  }

  if (!summary) {
    return (
      <AppShell>
        <PageHeader title="Dashboard" />
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
          No data available.
        </div>
      </AppShell>
    );
  }

  const { metrics, pipelineOverview, recentActivity, scoreDistribution } = summary;

  // Empty state logic: if no open jobs and no candidates, show onboarding wizard
  if (metrics.openJobsCount === 0 && metrics.totalCandidatesCount === 0) {
    return (
      <AppShell>
        <PageHeader title="Dashboard" subtitle="Welcome to your workspace" />
        <DashboardOnboarding />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        subtitle="Recruiting intelligence overview and pipeline health."
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1.25rem",
          marginBottom: "2rem",
        }}
      >
        <MetricCard
          label="Open Jobs"
          value={metrics.openJobsCount}
          icon="💼"
        />
        <MetricCard
          label="Total Candidates"
          value={metrics.totalCandidatesCount}
          icon="👥"
        />
        <MetricCard
          label="AI Scored"
          value={metrics.scoredCandidatesCount}
          icon="✨"
        />
        <MetricCard
          label="Hired"
          value={metrics.hiredCandidatesCount}
          icon="🎉"
        />
      </div>

      <div style={{ marginBottom: "2rem" }}>
        <EmbeddingStatusPanel />
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr",
        gap: "1.5rem",
        marginBottom: "2rem"
      }}>
        {/* Responsive layout: 2 columns on tablet/desktop */}
        <style dangerouslySetInnerHTML={{__html: `
          @media (min-width: 900px) {
            .dashboard-layout {
              display: grid;
              grid-template-columns: 2fr 1fr;
              gap: 1.5rem;
              align-items: start;
            }
            .charts-column {
              display: flex;
              flex-direction: column;
              gap: 1.5rem;
            }
          }
        `}} />

        <div className="dashboard-layout">
          <div>
            <h2 style={{ margin: "0 0 1rem", fontSize: "1.25rem", fontWeight: 700 }}>Pipeline Overview</h2>
            <PipelineOverview pipelines={pipelineOverview} />
          </div>
          <div className="charts-column">
            <div>
              <ScoreDistributionChart data={scoreDistribution} />
            </div>
            <div>
              <h2 style={{ margin: "0 0 1rem", fontSize: "1.25rem", fontWeight: 700 }}>Recent Activity</h2>
              <RecentActivity activities={recentActivity} />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function Home(): React.ReactElement {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
