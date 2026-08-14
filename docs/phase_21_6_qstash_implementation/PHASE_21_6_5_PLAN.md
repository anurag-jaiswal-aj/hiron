# Phase 21.6.5 Implementation Plan

## Objective
Implement the Job Embedding Webhook and update both explicit (API-driven) and implicit (auto-trigger) job embedding enqueue mechanisms to respect the QStash feature flag.

## Production Files to Modify
1. `apps/api/hiron/embeddings/schemas.py` - Add `JobEmbeddingWebhookPayload`.
2. `apps/api/hiron/webhooks/router.py` - Add `POST /qstash/embeddings/job` endpoint.
3. `apps/api/hiron/embeddings/service.py` - Update `generate_job_embedding` to branch based on `BACKGROUND_TASK_ENGINE`.
4. `apps/api/hiron/jobs/service.py` - Update auto-triggers in `create_job` and `update_job` to branch based on `BACKGROUND_TASK_ENGINE`.

## Test Files to Modify/Create
1. `apps/api/tests/test_embeddings_webhook.py` - Append tests for `POST /qstash/embeddings/job` signature verification, success, and 429 backoff logic.
2. `apps/api/tests/test_embeddings_qstash_publish.py` - Append tests for `EmbeddingService.generate_job_embedding` branching.
3. `apps/api/tests/test_job_service_qstash_publish.py` (or similar) - Tests verifying `JobService.create_job` and `update_job` use QStash when enabled.

## Celery Rollback Preservation
By wrapping the new QStash publishing calls in an `if settings.background_task_engine == "qstash":` block, the exact same `generate_job_embedding.delay(...)` call is preserved in the `else` branch. Rolling back simply requires flipping the environment variable.

## Ambiguity Check
The audit plan (`IMPLEMENTATION_PLAN.md`) explicitly lists updating `JobService` auto-triggers but omits `EmbeddingService.generate_job_embedding`. However, `QSTASH_MAPPING.md` explicitly lists `EmbeddingService.generate_job_embedding`. This is not a contradiction, just a slightly incomplete bullet list in the plan. The scope is unambiguous: all paths that push job embedding tasks to background queues must respect the feature flag.

Verdict: Unambiguous. Proceeding to implementation.
