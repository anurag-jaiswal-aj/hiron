import { apiFetch, ResponseEnvelope, PaginatedResponseEnvelope } from "./api";

export interface OperationUsageBreakdown {
  operation: string;
  count: number;
  costUsd: number;
  avgLatencyMs: number;
}

export interface DailyUsagePoint {
  date: string;
  costUsd: number;
  operations: number;
}

export interface AIUsageSummaryData {
  totalCostUsd: number;
  totalTokens: number;
  totalOperations: number;
  cacheHitRate: number;
  byOperation: OperationUsageBreakdown[];
  byDay: DailyUsagePoint[];
}

export interface AIUsageLogItem {
  id: string;
  operation: string;
  modelVersion: string;
  promptName: string | null;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
  latencyMs: number;
  status: string;
  isCacheHit: boolean;
  createdAt: string;
}

export interface AIUsageSummaryParams {
  period?: string;
  groupBy?: string;
}

export interface AIUsageLogsParams {
  operation?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  cursor?: string;
}

export const aiUsageApi = {
  getSummary: async (params?: AIUsageSummaryParams) => {
    return apiFetch<ResponseEnvelope<AIUsageSummaryData>>(`/api/v1/ai-usage/summary`, {
      params: params as Record<string, string | number | boolean | null | undefined>,
    });
  },

  listLogs: async (params?: AIUsageLogsParams) => {
    return apiFetch<PaginatedResponseEnvelope<AIUsageLogItem>>(`/api/v1/ai-usage/logs`, {
      params: params as Record<string, string | number | boolean | null | undefined>,
    });
  },
};
