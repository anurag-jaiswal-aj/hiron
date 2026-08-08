import { httpClient, ResponseEnvelope } from "./api";

export interface BreakdownDimension {
  score: number;
  weight: number;
  details: string;
}

export interface ScoreBreakdown {
  skills: BreakdownDimension;
  experience: BreakdownDimension;
  education: BreakdownDimension;
}

export interface ScoreData {
  id: string;
  fitScore: number;
  confidence: number;
  breakdown: ScoreBreakdown;
  explanation: string;
  skillsMatched: string[];
  skillsMissing: string[];
  warnings: string[];
  promptVersion: string;
  modelVersion: string;
  isCurrent: boolean;
  createdAt: string;
}

export const scoresApi = {
  /**
   * Fetch current active score for candidate-job pair.
   */
  getScore: (jobId: string, candidateId: string): Promise<ResponseEnvelope<ScoreData>> => {
    return httpClient.get<ResponseEnvelope<ScoreData>>(`/api/v1/jobs/${jobId}/candidates/${candidateId}/score`);
  },

  /**
   * Trigger AI fit scoring for candidate against a job.
   */
  scoreCandidate: (jobId: string, candidateId: string): Promise<ResponseEnvelope<ScoreData>> => {
    return httpClient.post<ResponseEnvelope<ScoreData>>(`/api/v1/jobs/${jobId}/candidates/${candidateId}/score`);
  },
};
