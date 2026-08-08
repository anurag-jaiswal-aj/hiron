import { httpClient, ResponseEnvelope } from "./api";

export interface CoverageMetricData {
  total: number;
  withEmbedding: number;
  stale: number;
  missing: number;
  modelVersion: string;
}

export interface EmbeddingStatusData {
  candidates: CoverageMetricData;
  jobs: CoverageMetricData;
}

export interface IndividualEmbeddingStatusData {
  status: "current" | "stale" | "missing";
  modelVersion: string;
}

export interface GenerateCandidateEmbeddingData {
  candidateId: string;
  taskId: string;
  status: string;
  modelVersion: string;
}

export interface GenerateJobEmbeddingData {
  jobId: string;
  taskId: string;
  status: string;
  modelVersion: string;
}

export const embeddingsApi = {
  /**
   * Check tenant embedding coverage statistics.
   */
  getTenantStatus: (): Promise<ResponseEnvelope<EmbeddingStatusData>> => {
    return httpClient.get<ResponseEnvelope<EmbeddingStatusData>>("/api/v1/embeddings/status");
  },

  /**
   * Check individual candidate embedding status.
   */
  getCandidateStatus: (candidateId: string): Promise<ResponseEnvelope<IndividualEmbeddingStatusData>> => {
    return httpClient.get<ResponseEnvelope<IndividualEmbeddingStatusData>>(`/api/v1/embeddings/candidates/${candidateId}`);
  },

  /**
   * Check individual job embedding status.
   */
  getJobStatus: (jobId: string): Promise<ResponseEnvelope<IndividualEmbeddingStatusData>> => {
    return httpClient.get<ResponseEnvelope<IndividualEmbeddingStatusData>>(`/api/v1/embeddings/jobs/${jobId}`);
  },

  /**
   * Generate or regenerate a candidate's embedding.
   */
  generateCandidateEmbedding: (candidateId: string): Promise<ResponseEnvelope<GenerateCandidateEmbeddingData>> => {
    return httpClient.post<ResponseEnvelope<GenerateCandidateEmbeddingData>>(`/api/v1/candidates/${candidateId}/embedding`);
  },

  /**
   * Generate or regenerate a job's embedding.
   */
  generateJobEmbedding: (jobId: string): Promise<ResponseEnvelope<GenerateJobEmbeddingData>> => {
    return httpClient.post<ResponseEnvelope<GenerateJobEmbeddingData>>(`/api/v1/jobs/${jobId}/embedding`);
  },
};
