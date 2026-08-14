# Phase 7 Step 10: Final Candidate Embedding E2E Report

## Objective
Execute exactly ONE controlled production candidate embedding E2E test using the `gemini-embedding-2` model for 768 dimensions to verify the entire pipeline, including database persistence.

## Preconditions
1. **Railway Worker**: Verified Online via `railway status` and `curl /health` returned `{"status":"ok"}`.
2. **GEMINI_API_KEY**: Verified present in Railway production variables.
3. **Candidate Status**: Candidate `44b5fa13-2840-4c7c-a036-adbb347b81a8` confirmed to have a successfully parsed resume.
4. **Existing Embeddings**: Verified no existing `candidate_embeddings` row for this candidate in production (clean state).

## Execution Path
- Triggered manually using local `scratch/trigger_e2e_embedding.py` connected to production.
- Payload dispatched to QStash.
- QStash relayed to `https://hiron-worker-production.up.railway.app/api/v1/webhooks/qstash/embeddings/candidate`.

## Results
- **QStash publish**: PASS (Message ID: `msg_26hZCxZCuWyyTWPmSVBrNB882AS9C1vrPYJzP84rh1boCbHjTVCVva4Nw4jZoLC`)
- **QStash message delivered**: PASS (QStash reported `DELIVERED` after 1 retry)
- **Railway webhook received**: PASS
- **QStash signature verification**: PASS
- **Railway connects to PostgreSQL**: PASS
- **Gemini API call**: PASS (Vector generated successfully)
- **Vector Dimension**: PASS (768-dimensional vector produced without API error)
- **PostgreSQL persistence result**: FAIL (Database insertion was rolled back)
- **Model version**: NOT VERIFIED (Rolled back)
- **Source hash**: NOT VERIFIED (Rolled back)
- **Status**: NOT VERIFIED (Rolled back)
- **Telemetry**: NOT VERIFIED (Rolled back)
- **Idempotency**: NOT VERIFIED (Rolled back)
- **Railway webhook status code**: PASS (HTTP 200 OK returned on retry)

## Final PASS/FAIL
**FAIL**

## Exact Blocker
The E2E failed to persist the embedding, even though the webhook eventually returned HTTP 200 OK. 

**Root Cause:**
1. **First Attempt (HTTP 500):** The Railway worker crashed on the first attempt with an `asyncpg.exceptions.InvalidCachedStatementError`. This occurred because the PostgreSQL schema was just altered (the 768-dimension Alembic migration was applied), invalidating `asyncpg`'s cached prepared statement. `asyncpg` threw the exception and subsequently flushed its cache.
2. **Second Attempt (HTTP 200 - Retry):** QStash automatically retried the webhook. The statement cache was now clear, so the `INSERT INTO candidate_embeddings` successfully executed and the `flush()` succeeded. The pipeline finished without raising an exception, and the webhook returned HTTP `200 OK`.
3. **The Silent Rollback:** Neither `apps/worker/src/embeddings.py` (which orchestrates the pipeline) nor `apps/worker/src/main.py` (which houses the webhook endpoint) explicitly call `await session.commit()`. While the `AsyncSessionLocal` context manager safely closes the session at the end of the request, it strictly rolls back any uncommitted transactions on exit. Thus, the successfully flushed data was silently discarded.

*(Note: The resume parsing pipeline successfully persists because `apps/worker/src/pipeline.py` manually calls `await session.commit()` internally, a step that is missing in the embedding pipelines).*
