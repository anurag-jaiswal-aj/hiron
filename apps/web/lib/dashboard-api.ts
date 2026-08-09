import { httpClient } from "./api";

export interface DashboardMetrics {
  openJobsCount: number;
  totalCandidatesCount: number;
  scoredCandidatesCount: number;
  shortlistedCandidatesCount: number;
  hiredCandidatesCount: number;
}

export interface JobStageOverview {
  stageId: string;
  stageName: string;
  position: number;
  candidateCount: number;
}

export interface JobPipelineOverview {
  jobId: string;
  jobTitle: string;
  status: string;
  totalCandidates: number;
  stages: JobStageOverview[];
}

export interface ScoreDistributionData {
  highFitCount: number;
  mediumFitCount: number;
  lowFitCount: number;
  totalScored: number;
  averageFitScore?: number | null;
}

export interface ActivityFeedItem {
  id: string;
  activityType: string;
  description: string;
  actorName?: string | null;
  timestamp: string;
}

export interface DashboardSummaryData {
  metrics: DashboardMetrics;
  pipelineOverview: JobPipelineOverview[];
  scoreDistribution: ScoreDistributionData;
  recentActivity: ActivityFeedItem[];
}

export interface TimeSeriesPoint {
  date: string;
  applicationsCount: number;
  scoresCount: number;
}

export const dashboardApi = {
  /**
   * Get complete dashboard overview metrics, pipelines, score distribution, and activity
   */
  getDashboardSummary: () => {
    return httpClient.get<{ data: DashboardSummaryData }>("/api/v1/dashboard/summary");
  },

  /**
   * Get time-series analytics aggregations
   */
  getAnalyticsAggregation: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append("startDate", startDate);
    if (endDate) params.append("endDate", endDate);
    const queryString = params.toString();
    const url = `/api/v1/dashboard/analytics${queryString ? `?${queryString}` : ""}`;
    return httpClient.get<{ data: TimeSeriesPoint[] }>(url);
  },

  /**
   * Get pipeline overview only
   */
  getPipelineOverview: () => {
    return httpClient.get<{ data: JobPipelineOverview[] }>("/api/v1/dashboard/pipeline-overview");
  },

  /**
   * Get score distribution only
   */
  getScoreDistribution: () => {
    return httpClient.get<{ data: ScoreDistributionData }>("/api/v1/dashboard/scoring-distribution");
  }
};
