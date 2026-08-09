import { httpClient } from "./api";

export interface StageInfo {
  id: string;
  name: string;
  position: number;
}

export interface UserInfo {
  id: string;
  fullName: string;
}

export interface KanbanCandidateCard {
  candidateId: string;
  jobCandidateId: string;
  fullName: string;
  currentTitle?: string | null;
  fitScore?: number | null;
  confidence?: number | null;
  isShortlisted: boolean;
  appliedAt: string;
}

export interface PipelineStageStats {
  stageId: string;
  stageName: string;
  position: number;
  candidateCount: number;
  candidates: KanbanCandidateCard[];
}

export interface MoveCandidateStageData {
  jobCandidateId: string;
  previousStage?: StageInfo | null;
  currentStage: StageInfo;
  movedBy?: UserInfo | null;
  note?: string | null;
  movedAt: string;
}

export interface StageHistoryItem {
  id: string;
  fromStage?: StageInfo | null;
  toStage: StageInfo;
  movedBy?: UserInfo | null;
  note?: string | null;
  createdAt: string;
}

export interface ShortlistCandidateData {
  jobCandidateId: string;
  isShortlisted: boolean;
  shortlistedAt: string;
}

export interface RejectCandidateData {
  jobCandidateId: string;
  status: string;
  rejectionReason?: string | null;
  rejectedAt: string;
}

export const pipelineApi = {
  /**
   * Get Kanban pipeline board with candidate cards, counts, and AI scores.
   */
  getPipelineBoard: (jobId: string) => {
    return httpClient.get<{ data: PipelineStageStats[] }>(
      `/api/v1/jobs/${jobId}/pipeline`
    );
  },

  /**
   * Move a candidate to a different stage in their job pipeline.
   */
  moveCandidateStage: (jobCandidateId: string, toStageId: string, note?: string) => {
    return httpClient.post<{ data: MoveCandidateStageData }>(
      "/api/v1/pipeline/move",
      { jobCandidateId, toStageId, note }
    );
  },

  /**
   * Get complete stage transition history for a candidate in a job.
   */
  getStageHistory: (jobId: string, candidateId: string) => {
    return httpClient.get<{ data: StageHistoryItem[] }>(
      `/api/v1/jobs/${jobId}/candidates/${candidateId}/stage-history`
    );
  },

  /**
   * Mark a candidate as shortlisted for hiring manager review.
   */
  shortlistCandidate: (jobId: string, candidateId: string) => {
    return httpClient.post<{ data: ShortlistCandidateData }>(
      `/api/v1/jobs/${jobId}/candidates/${candidateId}/shortlist`,
      {}
    );
  },

  /**
   * Move a candidate to the rejected stage with an optional reason.
   */
  rejectCandidate: (jobId: string, candidateId: string, reason?: string) => {
    return httpClient.post<{ data: RejectCandidateData }>(
      `/api/v1/jobs/${jobId}/candidates/${candidateId}/reject`,
      { reason }
    );
  }
};
