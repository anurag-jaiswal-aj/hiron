# Phase 21.6.4 — Candidate Embedding Webhook Implementation

## 1. Objective
Implement the `POST /api/v1/webhooks/qstash/embeddings/candidate` webhook endpoint to securely execute candidate embedding generation via Upstash QStash, while preserving the existing Celery fallback mechanism per the parallel migration strategy.

## 2. Architecture Implemented
1. **Configuration:** Added `qstash_webhook_url` to `apps/api/hiron/core/config.py` to allow the FastAPI application to know its public URL for publishing to itself or the public tunnel.
2. **Schema:** Created `CandidateEmbeddingWebhookPayload` in `apps/api/hiron/embeddings/schemas.py` to enforce strict type checking for the incoming webhook payload.
3. **Webhook Endpoint:** Added `POST /qstash/embeddings/candidate` to `apps/api/hiron/webhooks/router.py`, guarded by the existing `verify_qstash_signature` dependency. The endpoint executes the core logic via `EmbeddingService.generate_candidate_embedding_pipeline`.
4. **Publishing Layer:** Updated `EmbeddingService.generate_candidate_embedding` to respect the `BACKGROUND_TASK_ENGINE` configuration flag. When set to `qstash`, it constructs the URL and publishes the payload via `qstash_publisher`. When set to `celery`, it continues invoking the Celery `.delay()` method.

## 3. Production Files Changed
- `apps/api/hiron/core/config.py` (Added `qstash_webhook_url`)
- `apps/api/hiron/embeddings/schemas.py` (Added `CandidateEmbeddingWebhookPayload`)
- `apps/api/hiron/webhooks/router.py` (Added the candidate embedding endpoint)
- `apps/api/hiron/embeddings/service.py` (Updated `generate_candidate_embedding` to branch based on task engine)

## 4. Test Files Changed
- `apps/api/tests/test_embeddings_webhook.py` (New: focused webhook delivery tests)
- `apps/api/tests/test_embeddings_qstash_publish.py` (New: focused publish logic branching tests)
- Regression suites executed successfully without modifications.

## 5. Tests Executed
- `test_candidate_embedding_webhook_valid_signature_success`
- `test_candidate_embedding_webhook_missing_signature_rejected`
- `test_generate_candidate_embedding_uses_celery_by_default`
- `test_generate_candidate_embedding_uses_qstash_when_flag_enabled`
- Existing regression tests in `test_qstash_webhook.py` and `test_embedding_service.py`

## 6. Exact Test Results
All 41 test cases (unit and integration) across the suite executed successfully.
```
.........................................                                [100%]
41 passed, 23 warnings in 0.42s
```

## 7. Celery Compatibility
The implementation **fully preserves** the existing Celery execution path. If `BACKGROUND_TASK_ENGINE="celery"` (the default), `EmbeddingService.generate_candidate_embedding` calls `generate_candidate_embedding_task.delay()` identically to before. Celery `.tasks.py` definitions remain untouched. Any direct chained celery invocations in other files (such as `resumes/tasks.py`) continue to bypass the webhook and utilize pure Celery workers.

## 8. QStash Behavior
When `BACKGROUND_TASK_ENGINE="qstash"`, the application calculates the deterministic `deduplication_id` (e.g., `embed-cand-{uuid}-{model}`) and uses the QStash SDK to publish the payload securely to its own `qstash_webhook_url`.

## 9. Error/Retry Behavior
The webhook endpoint catches the `rate_limit` error from Gemini (via `result.error_type`) and deliberately raises an HTTP 429. QStash interprets the 429 as a retryable failure and automatically re-queues the message using exponential backoff, natively mirroring Celery's `@task(autoretry_for=...)` mechanism.

## 10. Idempotency Behavior
Idempotency is achieved via dual mechanisms:
1. **Deduplication ID:** When publishing to QStash, a unique combination of candidate UUID and model version prevents identical messages from entering the queue within the deduplication window.
2. **Cache Hit Detection:** If a duplicate delivery slips through, the `generate_candidate_embedding_pipeline` inherently performs a source text hash check. If the hash matches the existing database record, it gracefully returns a "cache_hit" and HTTP 200, bypassing the Gemini API entirely to prevent duplicate billing.

## 11. Rollback Behavior
Rollback to Celery requires exactly one step: changing the environment variable `BACKGROUND_TASK_ENGINE=celery` and restarting the API container. New requests will instantly fall back to Celery queues. Existing QStash messages will still hit the webhook endpoint (which remains valid) and drain out naturally. 

## 12. Known Limitations
- The `resumes/tasks.py` chain still directly invokes Celery's `generate_candidate_embedding.delay()`. This is expected parallel-state behavior; removing the direct `.delay()` is slated for the final decommissioning phase. 
- The real QStash delivery to this new route has not been integration-tested physically on the cloudflared tunnel, as this phase was strictly implementation and unit-testing focused.

## 13. Final Verdict
The candidate embedding webhook is securely implemented, strictly isolated, and unit-tested to prove it correctly overrides and mimics Celery when the feature flag is active.

**PHASE 21.6.4 = GREEN**
