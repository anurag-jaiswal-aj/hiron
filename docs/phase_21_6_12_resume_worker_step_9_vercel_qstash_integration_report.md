# Phase 21.6.12 — Resume Worker Step 9: Vercel → QStash → Railway Integration Report

## 1. Railway Worker URL
- **URL**: `https://hiron-worker-production.up.railway.app`

## 2. Railway Health Status
- **Status**: The worker is successfully deployed and the `GET /health` endpoint returned HTTP 200 with payload `{"status":"ok"}`.

## 3. Railway Authentication/Security Status
- **Verification**: An unauthenticated dummy `POST` payload to `/api/v1/webhooks/qstash/resumes/parse` was correctly intercepted by the `verify_qstash_signature` dependency.
- **Response**: `{"detail":"Missing signature"}`

## 4. Vercel API Production Deployment Status
- **Status**: The Vercel `hiron-api` was successfully built and deployed to production (`https://hiron-966o1ccla-anurag-jaiswals-projects-b742611a.vercel.app`).
- **Health Check**: `GET /api/v1/health` returned `{"status":"healthy","version":"0.1.0"}` indicating a successful boot with all internal dependencies initialized.

## 5. WORKER_URL Presence in Vercel
- **Verification**: `WORKER_URL` was securely added to the Vercel production environment variables. `npx vercel env ls production` confirmed its presence. 

## 6. API → QStash Destination
- **Verification**: Inspection of `apps/api/hiron/resumes/service.py` confirmed `_enqueue_parse_task` retrieves `settings.worker_url`, normalizes it, and dynamically provides it to the QStash publisher via the `url` parameter (targeting `/api/v1/webhooks/qstash/resumes/parse`).
- **Result**: No manual, static QStash subscription setup is needed.

## 7. QStash → Worker Routing Verification
- **Architecture Validation**: The QStash client publishes messages bound directly to the Railway worker's webhook URL with the payload exactly formatted as `{"tenant_id": "<uuid>", "resume_id": "<uuid>"}`. 

## 8. Worker Signature Verification
- **Code Audit**: Validated that `apps/worker/src/main.py` explicitly injects `dependencies=[Depends(verify_qstash_signature)]` on the QStash webhook endpoint.
- **Environment Audit**: The Railway worker environment contains `QSTASH_CURRENT_SIGNING_KEY` and `QSTASH_NEXT_SIGNING_KEY`, which are actively used by the dependency to validate incoming QStash payload hashes.

## 9. Environment Variable Audit (Names Only)
**Railway Worker (`railway variable list`)**:
- `DATABASE_URL`
- `ENVIRONMENT`
- `PORT`
- `QSTASH_CURRENT_SIGNING_KEY`
- `QSTASH_NEXT_SIGNING_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `SUPABASE_URL`
- `WORKER_URL` (Kept for `Settings` validation requirement)
- *(plus native RAILWAY_* variables)*

**Vercel API (`npx vercel env ls`)**:
- `APP_SECRET_KEY`
- `DATABASE_URL`
- `ENVIRONMENT`
- `JWT_PRIVATE_KEY_CONTENT`
- `JWT_PUBLIC_KEY_CONTENT`
- `OPENAI_API_KEY`
- `QSTASH_CURRENT_SIGNING_KEY`
- `QSTASH_NEXT_SIGNING_KEY`
- `QSTASH_TOKEN`
- `REDIS_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `SUPABASE_URL`
- `WORKER_URL`
- *(plus KV_*, Upstash, and VERCEL_* variables)*

## 10. Temporary Secret-File Cleanup
- The `.env.production` file downloaded during step 8 was removed.
- Python scripts (`filter_env.py`, `fix_env.py`, `set_env.py`) used to inject variables without printing values were permanently deleted.
- No `railway.env` remnants remain.

## 11. Git Security Verification
- **Output**: `git diff --check` and `git status --short` returned clean states containing no leaked configuration files, accidental `.env` inclusions, or hardcoded secrets.

## 12. Resume Processing Status
- **Status**: No real resumes were processed. Only a dummy unauthenticated JSON payload was dispatched to verify signature rejection.

## 13. Warnings
- The `WORKER_URL` environment variable remains in the Railway project environment. While not strictly used by the parsing function itself, it satisfies a strict structural requirement imposed by the shared `Settings` Pydantic class (`apps/api/hiron/core/config.py`). Stripping it will trigger a fatal validation boot error on the worker.

## 14. Exact Next Step
VERCEL → QSTASH → RAILWAY WORKER WIRING VERIFIED — READY FOR E2E RESUME TEST
