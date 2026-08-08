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

export interface ScoreHistoryItem {
  id: string;
  fitScore: number;
  promptVersion: string;
  isCurrent: boolean;
  createdAt: string;
}

export interface ConfidenceFactorsData {
  resumeCompleteness: number;
  outputConsistency: number;
  explanationQuality: number;
  sanityCheckPassed: boolean;
}

export interface ScoreExplanationData {
  scoreId: string;
  fitScore: number;
  explanation: string;
  breakdown: ScoreBreakdown;
  skillsMatched: string[];
  skillsMissing: string[];
  warnings: string[];
  confidence: number;
  confidenceFactors: ConfidenceFactorsData;
}

export interface BatchScoreData {
  taskId: string;
  candidatesQueued: number;
  estimatedCompletionSeconds: number;
  statusUrl: string;
}

export interface TaskProgress {
  current: number;
  total: number;
  percent: number;
}

export interface TaskStatusData {
  taskId: string;
  status: "pending" | "progress" | "completed" | "failed";
  progress?: TaskProgress;
  createdAt?: string;
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

  /**
   * Trigger batch AI scoring for all unscored candidates for a job.
   */
  scoreBatch: (jobId: string, forceRescore = false): Promise<ResponseEnvelope<BatchScoreData>> => {
    return httpClient.post<ResponseEnvelope<BatchScoreData>>(`/api/v1/jobs/${jobId}/score-batch`, {
      forceRescore,
    });
  },

  /**
   * Get the full AI-generated explanation for a score.
   */
  getScoreExplanation: (scoreId: string): Promise<ResponseEnvelope<ScoreExplanationData>> => {
    return httpClient.get<ResponseEnvelope<ScoreExplanationData>>(`/api/v1/scores/${scoreId}/explanation`);
  },

  /**
   * Get all historical scores for a candidate-job pair.
   */
  getScoreHistory: (jobId: string, candidateId: string): Promise<ResponseEnvelope<ScoreHistoryItem[]>> => {
    return httpClient.get<ResponseEnvelope<ScoreHistoryItem[]>>(`/api/v1/jobs/${jobId}/candidates/${candidateId}/scores/history`);
  },

  /**
   * Poll for completion status of async background task.
   */
  getTaskStatus: (taskId: string): Promise<ResponseEnvelope<TaskStatusData>> => {
    return httpClient.get<ResponseEnvelope<TaskStatusData>>(`/api/v1/tasks/${taskId}`);
  },
};

