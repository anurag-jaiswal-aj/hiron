# Phase 21.6.5 — Job Embedding Webhook Implementation

## 1. Objective
Implement the `POST /api/v1/webhooks/qstash/embeddings/job` webhook endpoint and update both explicit (API-driven) and implicit (auto-trigger) job embedding enqueue mechanisms to respect the QStash feature flag, while preserving the existing Celery fallback mechanism.

## 2. Architecture Implemented
1. **Schema:** Created `JobEmbeddingWebhookPayload` in `apps/api/hiron/embeddings/schemas.py` to strictly type check incoming webhook payloads.
2. **Webhook Endpoint:** Added `POST /qstash/embeddings/job` to `apps/api/hiron/webhooks/router.py`, guarded by `verify_qstash_signature`. The endpoint executes `EmbeddingService.generate_job_embedding_pipeline`.
3. **Publishing Layer (API Path):** Updated `EmbeddingService.generate_job_embedding` to respect the `BACKGROUND_TASK_ENGINE` flag. When set to `qstash`, it constructs the URL and publishes via `qstash_publisher`. When set to `celery`, it continues using the Celery `.delay()` method.
4. **Publishing Layer (Auto-Trigger Path):** Updated `JobService.create_job` and `JobService.update_job` to similarly respect `BACKGROUND_TASK_ENGINE`. This ensures background generation triggered indirectly by entity changes also respects the feature flag.

## 3. Production Files Changed
- `apps/api/hiron/embeddings/schemas.py` (Added `JobEmbeddingWebhookPayload`)
- `apps/api/hiron/webhooks/router.py` (Added `qstash_job_embedding_webhook`)
- `apps/api/hiron/embeddings/service.py` (Updated `generate_job_embedding` branching)
- `apps/api/hiron/jobs/service.py` (Updated `create_job` and `update_job` branching)

## 4. Test Files Changed
- `apps/api/tests/test_embeddings_webhook.py` (Added focused delivery & rate-limit tests)
- `apps/api/tests/test_embeddings_qstash_publish.py` (Added tests for `EmbeddingService` branching)
- `apps/api/tests/test_job_service_qstash_publish.py` (New: Tests for `JobService` branching)
- `apps/api/tests/conftest.py` (Added fixtures to default `BACKGROUND_TASK_ENGINE` to `celery` across all test suites, preventing environment variable leakage)

## 5. Tests Executed
- `test_job_embedding_webhook_valid_signature_success`
- `test_job_embedding_webhook_rate_limit_returns_429`
- `test_generate_job_embedding_uses_celery_by_default`
- `test_generate_job_embedding_uses_qstash_when_flag_enabled`
- `test_job_service_create_job_uses_celery_by_default`
- `test_job_service_create_job_uses_qstash_when_enabled`
- `test_job_service_update_job_uses_qstash_when_enabled`
- Existing regression tests in `test_job_service.py`, `test_embedding_service.py`, `test_qstash_webhook.py`, etc.

## 6. Exact Test Results
All 62 test cases executed successfully across the suite:
```
..............................................................           [100%]
62 passed, 27 warnings in 0.52s
```

## 7. Celery Rollback Preservation
By wrapping the new QStash publishing calls in an `if settings.background_task_engine == "qstash":` block, the exact same `generate_job_embedding.delay(...)` call is preserved in the `else` branch. Rolling back simply requires setting the environment variable `BACKGROUND_TASK_ENGINE=celery`. The existing `tasks.py` files remain untouched.

## 8. Final Verdict
The job embedding webhook and publish mechanisms are fully implemented, isolated, and unit-tested to prove they correctly mimic Celery when the feature flag is active.

**PHASE 21.6.5 = GREEN**
