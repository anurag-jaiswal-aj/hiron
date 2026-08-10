import { apiFetch, PaginatedResponseEnvelope } from "./api";

export interface AuditActor {
  id: string;
  fullName: string;
}

export interface AuditLogData {
  id: string;
  action: string;
  entityType: string;
  entityId: string;
  actor: AuditActor | null;
  changes: Record<string, unknown> | null;
  ipAddress: string | null;
  createdAt: string;
}

export interface AuditListParams {
  entityType?: string;
  entityId?: string;
  actorId?: string;
  action?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  cursor?: string;
}

export const auditApi = {
  listAuditLogs: async (params?: AuditListParams) => {
    return apiFetch<PaginatedResponseEnvelope<AuditLogData>>(`/api/v1/audit-logs`, {
      params: params as Record<string, string | number | boolean | null | undefined>,
    });
  },

  getEntityAuditLogs: async (entityType: string, entityId: string, limit?: number) => {
    return apiFetch<PaginatedResponseEnvelope<AuditLogData>>(
      `/api/v1/audit-logs/entity/${entityType}/${entityId}`,
      {
        params: limit ? { limit } : undefined,
      }
    );
  },
};
