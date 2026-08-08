import { useState, useEffect, useCallback } from "react";
import { scoresApi, ScoreData, ScoreHistoryItem, ScoreExplanationData } from "../lib/scores-api";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";


export interface UseScoreResult {
  score: ScoreData | null;
  history: ScoreHistoryItem[] | null;
  explanation: ScoreExplanationData | null;
  isLoading: boolean;
  isHistoryLoading: boolean;
  isExplanationLoading: boolean;
  isScoring: boolean;
  error: Error | null;
  historyError: Error | null;
  explanationError: Error | null;
  canScore: boolean;
  fetchScore: () => Promise<void>;
  scoreCandidate: () => Promise<void>;
}

export function useScore(jobId: string, candidateId: string): UseScoreResult {
  const { user } = useAuth();

  const [score, setScore] = useState<ScoreData | null>(null);
  const [history, setHistory] = useState<ScoreHistoryItem[] | null>(null);
  const [explanation, setExplanation] = useState<ScoreExplanationData | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isExplanationLoading, setIsExplanationLoading] = useState(false);
  const [isScoring, setIsScoring] = useState(false);

  const [error, setError] = useState<Error | null>(null);
  const [historyError, setHistoryError] = useState<Error | null>(null);
  const [explanationError, setExplanationError] = useState<Error | null>(null);

  const canScore = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchHistoryAndExplanation = useCallback(async (scoreId: string) => {
    setIsHistoryLoading(true);
    setIsExplanationLoading(true);
    setHistoryError(null);
    setExplanationError(null);

    Promise.allSettled([
      scoresApi.getScoreHistory(jobId, candidateId).then((res) => setHistory(res.data)),
      scoresApi.getScoreExplanation(scoreId).then((res) => setExplanation(res.data))
    ]).then(([historyResult, explanationResult]) => {
      setIsHistoryLoading(false);
      setIsExplanationLoading(false);

      if (historyResult.status === "rejected") {
        setHistoryError(historyResult.reason instanceof Error ? historyResult.reason : new Error("Failed to fetch score history"));
      }
      if (explanationResult.status === "rejected") {
        setExplanationError(explanationResult.reason instanceof Error ? explanationResult.reason : new Error("Failed to fetch score explanation"));
      }
    });
  }, [jobId, candidateId]);

  const fetchScore = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await scoresApi.getScore(jobId, candidateId);
      setScore(response.data);
      if (response.data?.id) {
        fetchHistoryAndExplanation(response.data.id);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setScore(null);
      } else {
        setError(err instanceof Error ? err : new Error("Failed to fetch score"));
      }
    } finally {
      setIsLoading(false);
    }
  }, [jobId, candidateId, fetchHistoryAndExplanation]);

  const scoreCandidate = useCallback(async () => {
    if (isScoring || !canScore) return;

    setIsScoring(true);
    setError(null);
    try {
      const response = await scoresApi.scoreCandidate(jobId, candidateId);
      setScore(response.data);
      if (response.data?.id) {
        fetchHistoryAndExplanation(response.data.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to score candidate"));
    } finally {
      setIsScoring(false);
    }
  }, [jobId, candidateId, isScoring, canScore, fetchHistoryAndExplanation]);

  useEffect(() => {
    if (jobId && candidateId) {
      fetchScore();
    }
  }, [fetchScore, jobId, candidateId]);

  return {
    score,
    history,
    explanation,
    isLoading,
    isHistoryLoading,
    isExplanationLoading,
    isScoring,
    error,
    historyError,
    explanationError,
    canScore,
    fetchScore,
    scoreCandidate,
  };
}
