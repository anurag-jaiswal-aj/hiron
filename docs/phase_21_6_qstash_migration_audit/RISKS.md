# Phase 21.6 Migration Risks

## 1. Timeout Cascade Analysis
**Risk:** There are multiple timeout layers between QStash and Gemini. If timeouts are mismatched, a webhook might be retried while it is actually still succeeding in the background.

**Timeout Cascade:**
`Gemini API (7.5s)` < `FastAPI Worker (e.g. 15s)` < `ALB/Vercel (e.g. 30s-60s)` < `QStash Delivery Timeout (configurable, default usually 15-30s)`

**Analysis:**
If Gemini takes 7.4s, and DB operations take 1s, the total webhook takes 8.4s. If QStash is configured with a 5s timeout, it will drop the connection at 5s, mark it as failed, and retry. Meanwhile, the original 8.4s task completes and commits to the DB.
**Mitigation:** 
1. Ensure the QStash timeout for the specific endpoint is explicitly configured to be GREATER than `(Gemini Timeout) + (DB Latency Buffer)`. Given Gemini is 7.5s, QStash delivery timeout must be at least 15s.
2. Batch scoring is mitigated via the new Coordinator -> Worker Fan-Out architecture, ensuring no single webhook processes multiple candidates sequentially.

## 2. Lack of Task Progress State
**Risk:** Celery allows `celery_task.update_state()` which the frontend polls for `percent` complete on batch scoring. QStash cannot store arbitrary mid-execution state metadata. 
**Mitigation:** 
1. Re-architect the frontend to not rely on a progress bar.
2. Store the progress in PostgreSQL (`JobCandidate` status or a dedicated `BatchJob` table) and have the frontend poll the DB.

## 3. Duplicate Delivery (Idempotency)
**Risk:** QStash guarantees at-least-once delivery. If `parse_resume` executes successfully, but the network drops the HTTP 200 OK response, QStash will deliver the request again. This will burn AI Quota parsing the resume a second time.
**Mitigation:** Enforce idempotency. Endpoints must verify if the target entity is already processed and return HTTP 200 immediately without hitting the AI.

## 4. Local Development Disruption
**Risk:** Currently, `celery worker` runs locally with Redis. QStash requires a publicly reachable URL to send webhooks to.
**Mitigation:** Developers will need to use `ngrok`, `localtunnel`, or the Upstash CLI tool (`qstash router`) to tunnel webhooks to `localhost:8000` during local development, or fallback to FastAPI `BackgroundTasks` when `ENVIRONMENT=development`.
