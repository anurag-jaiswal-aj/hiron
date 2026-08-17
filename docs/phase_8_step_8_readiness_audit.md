# Phase 8 Step 8: Readiness Audit

## 1. Roadmap Requirement
**Phase 8: AI Scoring**
- Implement `POST /jobs/{jobId}/score-batch` (async via QStash/Celery)
- Acceptance Criteria: "Batch scoring processes all candidates with progress reporting"

## 2. Existing Implementation
The architectural scaffolding for Batch Scoring is fully implemented in the repository:
- **API Endpoint:** `POST /jobs/{job_id}/score-batch` is exposed in `apps/api/hiron/scores/router.py`.
- **Database Layer:** The `batch_score_jobs` table exists and the schema (`queued_count`, `completed_count`, `failed_count`, `status`) is defined in `scores.models.py`.
- **Service Layer:** `ScoreService.batch_score_async` successfully instantiates the batch job and publishes the initial message to QStash.
- **Webhook Layer (Coordinator):** `POST /qstash/scores/batch/coordinator` accepts the batch payload, transitions the database state to `processing`, and fans out messages to the worker.
- **Webhook Layer (Worker):** `POST /qstash/scores/batch/worker` scores a single candidate using `ScoreService.score_candidate_sync()` (the exact path verified in Step 7) and atomically updates the completion status via `claim_batch_score_worker_success()`.

## 3. Missing Implementation
There is **NO code implementation missing**. The entire batch scoring pipeline is written.

However, the batch scoring infrastructure has **never been invoked or tested in the production environment**. We do not know if the QStash fan-out topology will hit transaction deadlocks, timeout constraints, or connection limits when executed in the real production environment against live Gemini APIs.

## 4. Dependencies
- **Phase 8 Step 7 (Completed):** Single synchronous scoring with telemetry has been proven to work.
- **Production Configuration:** QStash environment variables (`QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, `QSTASH_WEBHOOK_URL`) must be correctly configured in the production Vercel environment.

## 5. Test Coverage
- Comprehensive unit and integration tests exist in `test_scores_webhook.py` and `test_scores_coordinator.py`.
- Tests mock the QStash publisher and the AI engine, verifying the atomicity of the `batch_score_jobs` state machine (e.g., zero-candidate behavior, duplicate delivery, terminal failures).

## 6. Production/E2E Requirements
We must perform a tightly controlled, programmatic end-to-end test in production:
1. Provision 1 Job and multiple (e.g., 2 or 3) unscored Candidates under a safe test tenant.
2. Trigger the `POST /api/v1/jobs/{job_id}/score-batch` endpoint via an authenticated script.
3. Monitor the database for `BatchScoreJob` state transitions (`pending` → `processing` → `completed`).
4. Ensure exactly N `scores` and N `ai_usage_logs` are generated safely.

## 7. Risks/Blockers
- **Concurrency / Deadlocks:** If multiple QStash workers fire simultaneously, they may cause PostgreSQL transaction deadlocks when attempting to update the `batch_score_jobs` row, though the `claim_batch_score_worker_success` function uses optimistic locking / precise row updates to mitigate this.
- **Vercel Execution Timeouts:** The worker webhook runs within Vercel serverless bounds (max 10–15s). While `httpx` to Gemini is capped at 7.5s, any combined latency (DB overhead + Network + Gemini) could cause 504 Gateway Timeouts on the webhook. QStash's retry semantics must handle this gracefully.

## 8. Recommended Smallest Implementation/Validation Slice
**Phase 8 Step 8: Execute ONE controlled Production Batch Scoring E2E Test.**
Do not modify any application code. Build an E2E script similar to Step 7 that generates 2 candidates, triggers the batch API, polls the database until the batch job completes, and validates the resulting records.

## 9. Acceptance Criteria
- [ ] 2 Candidates are scored asynchronously via the QStash webhook worker.
- [ ] The `batch_score_jobs` record successfully transitions from `pending` to `completed` with `completed_count=2`.
- [ ] Exactly 2 AI scores and 2 `ai_usage_logs` entries are persisted.
- [ ] No PostgreSQL deadlocks or orphaned transactions occur during the fan-out.
