# Phase 21.6.6 Implementation Plan

## What Phase 21.6.6 Requires
Create the `POST /webhooks/qstash/scores/batch/worker` endpoint which receives a single candidate scoring request and executes it via `ScoreService.score_candidate_sync`. It also must enforce the `SCORE_CACHE_TTL_SECONDS` idempotency check (which is already natively handled by `score_candidate_sync`). 

## Production Files That Will Change
1. `apps/api/hiron/scores/schemas.py` - Add `BatchScoreWorkerWebhookPayload`.
2. `apps/api/hiron/webhooks/router.py` - Add `POST /qstash/scores/batch/worker` endpoint and error mapping logic.

## Test Files That Will Change/Create
1. `apps/api/tests/test_scores_webhook.py` (New) - Focused tests for the worker webhook signature validation, idempotency, success, and error mapping (429, 503, 200 ACKs for fatal errors).

## Celery Compatibility Preservation
Celery compatibility is preserved because we are NOT replacing or modifying the existing Celery task (`hiron.scores.tasks.execute_batch_scoring`). We are simply adding a new webhook endpoint. The Celery task continues to execute synchronously in its own worker process.

## Intended QStash Retry/Error Behavior
Per `ERROR_MATRIX.md`:
- HTTP 429 (Gemini Quota) -> Returned as 429 -> QStash retries.
- HTTP 500/503 (Gemini Internal/Bad Gateway) -> Returned as 503 -> QStash retries.
- `ResourceNotFoundException` -> Returned as 200 OK (Ack) -> QStash drops message.
- Pydantic/JSON parsing errors -> Returned as 422 (or 200 OK per matrix, but since FastAPI auto-handles ValidationError with 422, we catch our own payload parse errors and return 422 which QStash can drop if configured, OR we can explicitly return 200 OK for payload errors. The matrix says "200 OK (Ack) or configure QStash to ignore 400s". We will return 200 OK for fatal domain errors to stop retries).

## Intended Idempotency Behavior
When QStash delivers the same message twice, `score_candidate_sync` will query the database for an existing score for this job/candidate pair. If one exists and was created within `SCORE_CACHE_TTL_SECONDS` (24 hours), it bypasses Gemini generation, returning the cached score. The webhook returns HTTP 200 OK, acknowledging the duplicate to QStash without burning AI quota.

## Ambiguity Check
`IMPLEMENTATION_PLAN.md` asks to create the worker webhook. `QSTASH_MAPPING.md` states the Coordinator (which is Phase 21.6.7) will call it. 
There is no ambiguity: Phase 21.6.6 is solely responsible for creating the receiving endpoint (the worker). The publishing side (the fan-out) will be implemented in Phase 21.6.7. Therefore, no `qstash_publisher.publish` calls are required in Phase 21.6.6.

Verdict: Unambiguous. Proceeding to implementation.
