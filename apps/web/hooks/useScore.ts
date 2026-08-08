import { useState, useEffect, useCallback } from "react";
import { scoresApi, ScoreData } from "../lib/scores-api";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";


export interface UseScoreResult {
  score: ScoreData | null;
  isLoading: boolean;
  isScoring: boolean;
  error: Error | null;
  canScore: boolean;
  fetchScore: () => Promise<void>;
  scoreCandidate: () => Promise<void>;
}

export function useScore(jobId: string, candidateId: string): UseScoreResult {
  const { user } = useAuth();
  
  const [score, setScore] = useState<ScoreData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScoring, setIsScoring] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const canScore = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchScore = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await scoresApi.getScore(jobId, candidateId);
      setScore(response.data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setScore(null);
      } else {
        setError(err instanceof Error ? err : new Error("Failed to fetch score"));
      }
    } finally {
      setIsLoading(false);
    }
  }, [jobId, candidateId]);

  const scoreCandidate = useCallback(async () => {
    if (isScoring || !canScore) return;

    setIsScoring(true);
    setError(null);
    try {
      const response = await scoresApi.scoreCandidate(jobId, candidateId);
      setScore(response.data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to score candidate"));
    } finally {
      setIsScoring(false);
    }
  }, [jobId, candidateId, isScoring, canScore]);

  useEffect(() => {
    if (jobId && candidateId) {
      fetchScore();
    }
  }, [fetchScore, jobId, candidateId]);

  return {
    score,
    isLoading,
    isScoring,
    error,
    canScore,
    fetchScore,
    scoreCandidate,
  };
}
