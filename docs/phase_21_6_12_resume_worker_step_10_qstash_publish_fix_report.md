# Phase 21.6.12 — Resume Worker Step 10: QStash Publish Fix Report

## 1. Previous Failure
The Vercel production `WORKER_URL` environment variable contained a trailing literal newline `\n`. This produced a malformed destination URL for QStash, causing the webhook publish call to fail. This failure was silently caught by an exception handler in the API, resulting in a false positive `202 Accepted` response while the worker never received the job.

## 2. WORKER_URL Correction
The `WORKER_URL` was safely removed and re-added to the Vercel production environment without the trailing newline or whitespace:
`WORKER_URL="https://hiron-worker-production.up.railway.app"`

## 3. Deployment ID
A fresh deployment of the Vercel API was triggered to load the corrected environment variables.
**Deployment ID:** `dpl_EDqH9aSrsVptLPxUpFDWbVUuGmaG`

## 4. Health Result
The production health endpoint (`GET https://hiron-api.vercel.app/api/v1/health`) returned HTTP 200:
```json
{"status":"healthy","version":"0.1.0","timestamp":"2026-08-14T08:24:04.928118+00:00"}
```

## 5. E2E Upload Result
A single, controlled E2E resume upload was executed using the existing synthetic test account (`e2e-test@hiron.dev`):
- **Login Result:** Succeeded. Token secured.
- **HTTP Status:** `202 Accepted`
- **Returned Resume ID:** `2744503f-6eaf-4a71-aa84-d4a2e28cb9c1`
- **Returned Task ID:** *(Not parsed by the client test script directly, but underlying infrastructure confirmed it was a valid QStash `msg_...` identifier based on logs)*

## 6. QStash Publish Result
**Success.** With the corrected `WORKER_URL`, the Vercel API successfully dispatched the webhook to QStash, and QStash successfully attempted delivery to the Railway worker.

## 7. Railway Worker Result
The Railway worker successfully received the webhook payload from QStash and passed signature verification.
However, it immediately failed during pipeline execution:
```
2026-08-14 08:22:41 [info     ] Received resume parse request  resume_id=2744503f-6eaf-4a71-aa84-d4a2e28cb9c1 tenant_id=de7dc067-f9de-42dd-bcb1-48f9f14b2213
2026-08-14 08:22:41 [error    ] Error in parse_resume_webhook  error='[Errno 101] Network is unreachable'
INFO:     100.64.0.9:37136 - "POST /api/v1/webhooks/qstash/resumes/parse HTTP/1.1" 500 Internal Server Error
```

## 8. Final Resume Status
The status of Resume `2744503f-6eaf-4a71-aa84-d4a2e28cb9c1` in the Supabase PostgreSQL database remains **`pending`**. The worker process crashed before it could extract data or update the database.

## 9. Exact Remaining Blocker
The exact execution path `Vercel API -> QStash -> Railway Worker` is **fixed and verified**. 

The new and final remaining blocker is that the Railway Worker itself is hitting `[Errno 101] Network is unreachable` upon executing the pipeline. This strongly indicates that the Railway worker is attempting to connect to a service (most likely Supabase PostgreSQL via the old IPv6 direct connection, as Railway outbound networking typically does not route IPv6) and is failing at the socket layer.
