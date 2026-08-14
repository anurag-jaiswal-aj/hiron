# Phase 21.6.12: Resume Worker Deployment Platform Audit & Preparation (Step 5)

## 1. Worker Architecture
The `hiron-worker` is a self-contained FastAPI application designed to execute asynchronously from the main `hiron-api` monolith. It receives push-based webhooks from QStash containing lightweight identifiers (`tenant_id`, `resume_id`), and independently retrieves, parses, and persists the extracted resume data back to the Supabase database. The heavy NLP load (SpaCy + `en_core_web_trf` + PyTorch + `pdfplumber` + `docx`) is strictly isolated within this container.

## 2. Runtime Dependencies
The core dependencies baked into the image are:
- **FastAPI/Uvicorn**: For receiving QStash webhooks and serving health checks.
- **SpaCy & `en_core_web_trf`**: Transformer-based Named Entity Recognition (NER) pipeline.
- **PyTorch**: Required underlying tensor computation engine for the SpaCy transformer.
- **pdfplumber / python-docx**: For document text extraction.
- **SQLAlchemy (asyncpg) & Supabase Storage**: For persistence.
- **Upstash QStash**: For webhook signature verification (`qstash.Receiver`).

## 3. Environment Variable Matrix

| Variable | Required? | Secret? | Source | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | Yes | Supabase | Asyncpg SQLAlchemy connection for persistence |
| `SUPABASE_URL` | **Yes** | No | Supabase | REST endpoint for Supabase Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | Yes | Supabase | Privileged access to download raw resume files |
| `QSTASH_CURRENT_SIGNING_KEY` | **Yes** | Yes | Upstash | Primary key for verifying webhook signatures |
| `QSTASH_NEXT_SIGNING_KEY` | **Yes** | Yes | Upstash | Secondary key for rotation/fallback |
| `ENVIRONMENT` | No | No | Deployment | Sets logging levels/modes (defaults to `development`) |
| `PORT` | No | No | Deployment | Port for FastAPI (defaults to 8000 via Dockerfile CMD) |
| `SUPABASE_STORAGE_BUCKET` | No | No | App | Bucket name (defaults to `resumes`) |

*Note: OpenAI API keys and Redis connection strings are **NOT** required by the worker. The AI telemetry operations in the worker rely strictly on the local SpaCy transformer models.*

## 4. Database Connection Requirements
The Worker utilizes `AsyncSessionLocal` which relies on `create_async_engine` (SQLAlchemy asyncpg). 
**Important Constraint:** The worker issues connection-scoped parameter commands (`SET app.current_tenant_id = '...'`) to enforce Row Level Security (RLS) contexts. 
Because of this, the Worker **MUST NOT** connect to a PgBouncer **Transaction Pooler** (port 6543 in transaction mode), as connection-scoped state will leak across transactions. 

Since the Worker runs as a persistent, long-running Docker container (unlike ephemeral Vercel Edge functions), it should maintain its own internal connection pool (default `pool_size=10`). 
**Recommendation:** Connect using the Supabase **Direct Connection** (port 5432) or a properly configured **Session Pooler**.

## 5. Storage Requirements
The worker strictly instantiates `SupabaseStorageProvider` referencing the bucket name `resumes` (via default `settings.supabase_storage_bucket`).
**Observation:** The database entity `ResumeFile.s3_bucket` is currently populated with `"hiron-resumes"` during API upload, but the physical bucket read by the StorageProvider is `"resumes"`. This discrepancy must be addressed as a follow-up cleanup item, but it is physically reading from the correct API URL target.

## 6. QStash Security
The `POST /api/v1/webhooks/qstash/resumes/parse` endpoint is protected by the `verify_qstash_signature` FastAPI dependency.
Invalid requests lacking a proper `Upstash-Signature` header, or signed with incorrect keys, will immediately yield a `401 Unauthorized` or `403 Forbidden` response. The payload is discarded before any tenant context is initialized or any database queries are issued.

## 7. Docker Verification
The `apps/worker/Dockerfile` was heavily scrutinized:
- Uses `python:3.12-slim`.
- Uses `uv sync --extra worker` to cleanly isolate dependencies.
- Sets `PYTHONPATH=/app/apps/api` for correct module resolution.
- Exposes standard port `8000`.
- Includes no hardcoded secrets or unnecessary local `.env` files.
- **Build Status:** Built successfully locally. 
- **Image Size:** The resulting Docker image size is approximately **9.52 GB** (3.56 GB compressed content size), heavily dominated by PyTorch, CUDA bindings (implicitly pulled by torch), and SpaCy transformer models.

## 8. Local Smoke Test
A local container smoke test was executed without production secrets:
```bash
docker run -p 8000:8000 hiron-worker
```
- `GET /health` returned `200 OK` `{"status": "ok"}`.
- The heavy imports initialized successfully without crashing, and the container proved it can operate completely isolated from Vercel.

## 9. Platform Comparison
Four deployment platforms were evaluated for deploying this heavy, persistent Docker container, specifically prioritizing availability in/near India (Mumbai).

| Platform | Mumbai Region | Persistent Docker | Op Complexity | RAM Limitations | Recommendation Fit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AWS ECS (Fargate)** | Yes (`ap-south-1`) | Excellent | Very High | Flexible (Paid) | Overkill for early stage |
| **Render** | No (Singapore closest) | Good | Low | Strict Free Limits | Poor regional match |
| **Railway** | No | Good | Low | Strict Free Limits | Poor regional match |
| **Fly.io** | Yes (`bom`) | Excellent | Low/Medium | Flexible (Paid/Free mix) | **Strongly Recommended** |

## 10. Recommended Platform
**Fly.io** is the recommended platform for the `hiron-worker`.
- **Reasoning:** It natively supports deploying raw Dockerfiles, provides a direct region in Mumbai (`bom`), and allows granular scaling of RAM (which is critical for the 4GB+ PyTorch requirement). It also supports persistent volumes if model caching is ever required in the future. It provides the easiest developer experience while satisfying the geographic requirement.

## 11. Resource Recommendation
Due to the memory-intensive nature of transformer models (`en_core_web_trf` / PyTorch), the worker requires a generous memory footprint.
- **RAM:** Minimum **4 GB** (8 GB recommended for stable concurrency).
- **CPU:** Minimum **2 vCPUs** (Model inference without GPU acceleration is CPU-bound).
- **Startup Time:** Expect **15-30 seconds** for cold boots while the 400MB+ PyTorch binary and SpaCy models load into active RAM. Health checks should be configured with generous initial delays.

## 12. Exact Deployment Plan (Fly.io)
When approval is granted, the deployment will execute the following steps:
1. `fly launch --no-deploy --name hiron-worker --region bom` (Create app).
2. Configure `fly.toml` to expose internal port `8000` with HTTP handlers and adjust health check initial delay to `30s`.
3. Set secrets: 
   - `fly secrets set DATABASE_URL="..."`
   - `fly secrets set SUPABASE_URL="..."`
   - `fly secrets set SUPABASE_SERVICE_ROLE_KEY="..."`
   - `fly secrets set QSTASH_CURRENT_SIGNING_KEY="..."`
   - `fly secrets set QSTASH_NEXT_SIGNING_KEY="..."`
4. Set ENV: `fly env set ENVIRONMENT="production"`.
5. Scale VM: `fly scale memory 4096`.
6. Deploy: `fly deploy --dockerfile apps/worker/Dockerfile`.
7. Obtain public URL (e.g., `https://hiron-worker.fly.dev`).
8. Add URL to Vercel API production environment as `WORKER_URL`.

## 13. Vercel Implication
Once the Worker is deployed and `WORKER_URL` is configured, the `hiron-api` monolith running on Vercel is fully liberated from NLP dependencies. The API bundle size drops dramatically, eliminating previous 250MB+ Serverless Function limit blockers, allowing standard Vercel deployments to succeed.

## 14. Security Review
- The Worker exposes exactly two endpoints: `/health` (public) and `/api/v1/webhooks/qstash/resumes/parse` (protected by Upstash signatures).
- No JWT auth is required or exposed on the worker.
- The `SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are strictly confined to the backend worker container environment and never reach the frontend.
- No OpenAI or Redis credentials are used or exposed in the worker layer.
- No `.env` files or secrets are baked into the Docker layers.

## 15. Risks
- **OOM Kills:** If multiple large PDFs are parsed concurrently, 4GB RAM may be insufficient, causing the container to crash. Concurrency should be managed at the QStash layer (e.g., limiting parallel retries) or memory should be scaled.
- **Cold Boot Timeouts:** If QStash requires immediate responses, cold-booting a 4GB+ container might exceed QStash delivery timeouts. The container should be kept warm or health checks properly tuned.

---

### FINAL STATUS
READY FOR WORKER DEPLOYMENT — Fly.io
