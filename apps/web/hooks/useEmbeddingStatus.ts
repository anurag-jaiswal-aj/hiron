import { useState, useEffect, useCallback, useRef } from "react";
import { embeddingsApi, IndividualEmbeddingStatusData } from "../lib/embeddings-api";
import { useAuth } from "../context/AuthContext";

export type EntityType = "candidate" | "job";

interface UseEmbeddingStatusResult {
  status: IndividualEmbeddingStatusData["status"] | "queued" | "loading";
  error: Error | null;
  modelVersion: string | null;
  isPolling: boolean;
  canRegenerate: boolean;
  regenerate: () => Promise<void>;
  fetchStatus: () => Promise<IndividualEmbeddingStatusData["status"] | null>;
}

export function useEmbeddingStatus(
  entityType: EntityType,
  entityId: string,
  initialPoll = true
): UseEmbeddingStatusResult {
  const { user } = useAuth();
  
  const [status, setStatus] = useState<IndividualEmbeddingStatusData["status"] | "queued" | "loading">("loading");
  const [error, setError] = useState<Error | null>(null);
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const isRegeneratingRef = useRef(false);
  const MAX_POLL_ATTEMPTS = 12;
  const POLL_INTERVAL_MS = 5000;

  const canRegenerate = user?.role === "org_admin" || user?.role === "recruiter";

  const fetchStatus = useCallback(async (): Promise<IndividualEmbeddingStatusData["status"] | null> => {
    try {
      const response =
        entityType === "candidate"
          ? await embeddingsApi.getCandidateStatus(entityId)
          : await embeddingsApi.getJobStatus(entityId);

      setStatus(response.data.status);
      setModelVersion(response.data.modelVersion);
      setError(null);
      return response.data.status;
    } catch (err) {
      if (err instanceof Error) {
        setError(err);
      } else {
        setError(new Error("Failed to fetch embedding status"));
      }
      return null;
    }
  }, [entityType, entityId]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(false);
    pollAttemptsRef.current = 0;
  }, []);

  const startPolling = useCallback(() => {
    // Guard: prevent duplicate polling loops
    if (pollIntervalRef.current) return;

    setIsPolling(true);
    pollAttemptsRef.current = 0;

    pollIntervalRef.current = setInterval(async () => {
      pollAttemptsRef.current += 1;

      if (pollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
        stopPolling();
        // Fetch final status so UI shows real state, not stuck on "queued"
        await fetchStatus();
        return;
      }

      const currentStatus = await fetchStatus();
      if (currentStatus === "current") {
        stopPolling();
      } else if (currentStatus === null) {
        // API error — stop polling, fetchStatus already set error state
        stopPolling();
      }
      // If stale/missing, keep polling (Celery task may still be running)
    }, POLL_INTERVAL_MS);
  }, [fetchStatus, stopPolling]);

  const regenerate = useCallback(async () => {
    // Guard: prevent double-submit
    if (isRegeneratingRef.current || isPolling) return;
    if (!canRegenerate) return;

    isRegeneratingRef.current = true;
    try {
      setStatus("queued");
      if (entityType === "candidate") {
        await embeddingsApi.generateCandidateEmbedding(entityId);
      } else {
        await embeddingsApi.generateJobEmbedding(entityId);
      }
      startPolling();
    } catch (err) {
      await fetchStatus(); // Revert to actual status
    } finally {
      isRegeneratingRef.current = false;
    }
  }, [canRegenerate, entityType, entityId, startPolling, fetchStatus, isPolling]);

  // Initial fetch + cleanup on unmount or entity change
  useEffect(() => {
    if (initialPoll) {
      fetchStatus();
    }
    return () => {
      // Clean up timers on unmount or when entityId/entityType changes
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [entityId, entityType, fetchStatus, initialPoll]);

  return {
    status,
    error,
    modelVersion,
    isPolling,
    canRegenerate,
    regenerate,
    fetchStatus,
  };
}
