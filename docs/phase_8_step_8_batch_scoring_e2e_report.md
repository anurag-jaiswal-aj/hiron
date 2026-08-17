# Phase 8 Step 8: Batch Scoring E2E Report (FAILED)

## Validation Attempt

An attempt was made to validate the production batch scoring pipeline using a synthetic test dataset (`e2e_batch_scoring.py`).

## Blockers Discovered

The validation failed due to two distinct blockers:

### 1. Vercel Environment Variable Corruption (500 Error)
The production Vercel API returned a `500 Internal Server Error` when calling `POST /api/v1/jobs/{job_id}/score-batch`.
- **Root Cause**: The `QSTASH_WEBHOOK_URL` environment variable was added to Vercel via CLI using a command that appended a trailing newline character (`\n`).
- **Impact**: `httpx` raises a `ValueError` (`Invalid non-printable ASCII character in URL`) when `qstash_client.py` attempts to construct the Webhook URL and publish the message.

### 2. Missing Scoring Endpoints on Railway Worker (404 Error)
When the Vercel API was bypassed locally to directly enqueue the batch job to QStash, the batch job hung indefinitely in the `pending` state.
- **Root Cause**: QStash successfully delivered the webhook to the Railway worker (`https://hiron-worker-production.up.railway.app/api/v1/webhooks/qstash/scores/batch/coordinator`), but the worker returned a `404 Not Found`.
- **Impact**: The Railway worker is running a separate FastAPI application defined in `apps/worker/src/main.py`. While the scoring webhook handlers are defined in `apps/api/hiron/webhooks/router.py`, they were **never imported or registered** in the worker's router (`apps/worker/src/main.py`).

## Next Steps / Actions Required

Per the explicit rules for this step ("Do NOT modify application/source code" and "If a blocker occurs, STOP and report it instead of fixing it"), no source code or environment variables have been further modified.

1. **Fix Vercel Env Var**: The `QSTASH_WEBHOOK_URL` in the Vercel Production environment must be updated to remove the trailing newline.
2. **Fix Railway Worker Source Code**: `apps/worker/src/main.py` must be updated to include the `scores/batch/coordinator` and `scores/batch/worker` webhooks.
3. **Deploy Railway**: The code changes must be pushed to GitHub to trigger a new Railway deployment.
4. **Retry Validation**: Once fixed, the `e2e_batch_scoring.py` script can be rerun to complete Step 8.
