# Phase 21.6 QStash Migration Implementation Plan

## Phase 21.6.1 — QStash client/configuration
1. **Dependencies:** Add `upstash-qstash` to `pyproject.toml`. Do NOT remove Celery or Redis.
2. **Environment Variables:** Introduce `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, and `BACKGROUND_TASK_ENGINE` (defaulting to `celery`) to `apps/api/hiron/core/config.py`.

## Phase 21.6.2 — webhook authentication
1. **Webhook Router:** Create `apps/api/hiron/webhooks/qstash_router.py` to house the new POST endpoints.
2. **Auth Dependency:** Create a FastAPI Dependency `verify_qstash_signature` utilizing the `Receiver` class from `upstash_qstash.fastapi` to authenticate incoming webhook requests.

## Phase 21.6.3 — resume webhook
1. Create `POST /webhooks/qstash/resumes/parse`.
2. Update `ResumeService._enqueue_parse_task` to check `BACKGROUND_TASK_ENGINE`. If `qstash`, use `Client.publish_json()`; if `celery`, use `.delay()`.
3. Implement `SELECT ... FOR UPDATE SKIP LOCKED` for atomic idempotency claim.

## Phase 21.6.4 — candidate embedding webhook
1. Create `POST /webhooks/qstash/embeddings/candidate`.
2. Update `EmbeddingService.generate_candidate_embedding` to respect the feature flag.

## Phase 21.6.5 — job embedding webhook
1. Create `POST /webhooks/qstash/embeddings/job`.
2. Update `JobService` auto-triggers to respect the feature flag.

## Phase 21.6.6 — candidate scoring webhook
1. Create `POST /webhooks/qstash/scores/batch/worker`.
2. Ensure individual candidate scoring relies on the `SCORE_CACHE_TTL_SECONDS` to prevent duplicate AI burns.

## Phase 21.6.7 — batch coordinator/fan-out
1. **Database Migration:** Create Alembic migration for the `BatchScoreJob` entity to track batch fan-out progress.
2. Create Coordinator (`POST /webhooks/qstash/scores/batch/coordinator`).
3. Update `ScoreService.batch_score_async` to insert a `BatchScoreJob` row, then check feature flag.

## Phase 21.6.8 — parallel Celery/QStash switch (GREEN/COMPLETED)
1. Provide documentation and tooling (e.g., `cloudflared`) for local dev tunneling.
2. Update all unit tests to mock `qstash.Client.publish_json`.

## Phase 21.6.9 — full lifecycle verification
1. Deploy to production with `BACKGROUND_TASK_ENGINE=celery`.
2. Toggle `BACKGROUND_TASK_ENGINE=qstash`.
3. Monitor Upstash dashboard for deliveries, retries, and DLQ. Monitor Gemini quota usage limits.

## Phase 21.6.10 — Celery Application Decommissioning
*Requires explicit operator approval before execution.*

STATUS: BLOCKED UNTIL PLAN APPROVAL

### 1. Scope
This phase strictly scopes the application and local-development removal of Celery. No AWS infrastructure destruction is permitted in this phase.

### 2. Application Code & Configurations to Remove
*   **Exact Python Files to Delete:**
    *   `apps/api/hiron/core/celery.py`
    *   `apps/api/hiron/embeddings/tasks.py`
    *   `apps/api/hiron/jobs/tasks.py`
    *   `apps/api/hiron/scores/tasks.py`
    *   `apps/api/hiron/resumes/tasks.py`
*   **Exact Tests to Delete/Update:**
    *   Delete: `apps/api/tests/test_embedding_tasks.py`, `apps/api/tests/test_resume_tasks.py`
    *   Update: Remove `BACKGROUND_TASK_ENGINE` mocking/fixtures from `conftest.py` and other test files.
*   **Exact Service/Configuration References to Remove:**
    *   Remove `.delay()` execution paths in `embeddings/service.py`, `jobs/service.py`, `scores/service.py`, `resumes/service.py`.
    *   Remove `_is_celery` initialization logic in `apps/api/hiron/core/database.py`.
    *   Remove `BACKGROUND_TASK_ENGINE` from `apps/api/hiron/core/config.py` **only after verifying all references**.
    *   Remove `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` from `config.py` **only after reference audit**.

### 3. Exact Dependencies to Remove
*   **Python:** Remove the `celery` package (and its extras) from `pyproject.toml`. Update `uv.lock`.

### 4. Docker/Local Orchestration to Remove
*   **Local Docker:** Remove the `worker` service block and `CELERY_*` environment variables from `docker-compose.yml` and `docker-compose.prod.yml`.

### 5. Architectural Shifts & Redis Preservation
*   **Task Engine:** Confirmation that QStash becomes the sole background-task engine.
*   **Redis Functionality:** 
    1. Redis is currently an application capability used by CacheManager, RateLimitMiddleware, and the dashboard.
    2. The free architecture audit says these components support in-memory fallback.
    3. Upstash Redis is an optional future provider if persistent Redis is required.
    4. Therefore Redis/ElastiCache should NOT be destroyed as part of the Celery cleanup.
    5. Whether Redis can eventually be removed entirely must be determined by a separate application/runtime audit.
    6. Ensure the preservation of any Redis functionality still required by the application.

### 6. Validation Requirements
*   **Static Validation Requirements:** Verify no imports of `celery` exist via codebase scan. Verify `.delay()` and `@celery_app.task` are entirely removed.
*   **Build/Test Requirements:** Build the API container successfully without Celery.
*   **Regression Test Requirements:** Run the full relevant regression test suite to ensure QStash webhook delivery, AI execution, rate limiting, and caching remain intact.

### 7. Acceptance Criteria
*   Zero production Celery imports.
*   Zero Celery task definitions.
*   Zero `.delay()` execution paths.
*   Zero Celery dependency.
*   Zero Celery worker in local orchestration.
*   QStash is the sole background task engine.
*   QStash E2E functionality remains intact.
*   Redis-dependent application features remain functional OR documented in-memory fallback is verified.
*   Full relevant regression suite passes.
*   No AWS infrastructure is modified by Phase 21.6.10.

## Phase 21.6.11 — AWS Legacy Infrastructure Decommissioning
*Future phase. Requires an explicit approval gate before any destructive AWS operation.*

### 1. Scope
This phase targets the cleanup of the legacy AWS deployment, completing the transition to the $0/month serverless architecture (Vercel/Supabase/Upstash). 
Do NOT include `terraform apply` in the current phase.

### 2. Read-Only Resource/Dependency Audit
It must begin with a READ-ONLY resource/application dependency audit. Do NOT assume any resource is safe to delete. 
For every AWS resource, require classification: **ACTIVE** / **REPLACED** / **LEGACY** / **UNCERTAIN**.

Potential legacy resources include:
*   ECS (API hosting)
*   ALB (Load balancer)
*   VPC/networking
*   ElastiCache
*   AWS S3 (Storage)
*   Secrets Manager
*   Terraform state/configuration
*   AWS-specific deployment configuration

### 3. Replacement Verification
*   For every ACTIVE resource, identify its exact replacement before deletion.
*   For S3 specifically, verify actual application usage and confirm Supabase Storage fully replaces it before proposing removal.
