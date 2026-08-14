# Phase 7 Step 10: Embedding Transaction Commit Fix Report

## Root Cause
The E2E candidate embedding test failed to persist because the transaction was never committed. The webhook pipeline correctly invoked the service layer, flushed the SQL insert, and returned `HTTP 200 OK`. However, the `AsyncSessionLocal` context manager closed at the end of the request without an explicit commit, triggering an automatic rollback of the uncommitted transaction.

## Transaction Ownership Analysis
- **Service Layer (`EmbeddingService`)**: The service layer (`generate_candidate_embedding_pipeline`) performs the core business logic (hashing, generation, upsert, cache checking) but correctly defers transaction management to the caller. This keeps the service flexible.
- **Webhook Endpoint (`main.py`)**: The webhook simply provisions the `AsyncSessionLocal` and delegates execution to the pipeline. It is not responsible for complex transaction coordination across distinct steps.
- **Worker Pipeline (`embeddings.py`)**: The pipeline functions (`generate_candidate_embedding_worker_pipeline`, `generate_job_embedding_worker_pipeline`) orchestrate multiple discrete operations: generating embeddings via the service, logging AI telemetry via `begin_nested()`, and returning to the webhook. This is the logical unit of work and the correct transaction ownership boundary (matching the established pattern in `parse_resume_pipeline`).

## Exact Files Changed
- `apps/worker/src/embeddings.py`
- `apps/worker/tests/test_embeddings.py`

## Exact Behavioral Change
Appended `await session.commit()` to the end of both worker pipeline functions (`generate_candidate_embedding_worker_pipeline` and `generate_job_embedding_worker_pipeline`).
- The commit safely persists both the embedding upsert and the nested AI telemetry logs in a single atomic transaction boundary.
- If an exception occurs in the Gemini generation or database upsert, the transaction is abandoned (propagating the error upward) and `session.commit()` is never reached.

## Candidate Embedding Behavior
Candidate embeddings successfully generate their vectors, write AI telemetry, and explicitly commit the transaction to PostgreSQL prior to returning to the webhook.

## Job Embedding Behavior
Job embeddings successfully generate their vectors, write AI telemetry, and explicitly commit the transaction to PostgreSQL prior to returning to the webhook.

## Test Results
Updated the worker unit tests to assert `mock_session.commit.assert_called_once()` on success and cache-hit paths, and `mock_session.commit.assert_not_called()` on Gemini/DB exception paths.

Ran all focused tests (`PYTHONPATH=. uv run pytest apps/worker/tests/test_embeddings.py apps/worker/tests/test_webhooks.py -v`), resulting in:
- `10 passed, 11 warnings`

## Any Remaining Risks
- **Network Interruptions During Commit**: If the webhook succeeds in processing but times out returning to QStash during the exact moment of the commit, QStash may retry an already committed task. The deduplication ID and `upsert` semantics handle this idempotently (resulting in a benign cache-hit update).

## Final PASS/FAIL
**PASS**
