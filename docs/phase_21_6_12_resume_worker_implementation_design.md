# Phase 21.6.12: Resume Worker Implementation Design

## 1. Current Architecture
The monolithic API architecture currently houses both the lightweight REST endpoints and the heavy background NLP workloads (`ResumeParser`). When built, `uv` installs all dependencies listed in `pyproject.toml`, resulting in a 5.4 GB bundle on Linux due to PyTorch and SpaCy models. Vercel imposes a hard 500 MB limit, causing the deployment to fail.

## 2. Exact Extraction Boundary
The extraction boundary is the QStash webhook HTTP request. 
Currently, the API calls `_enqueue_parse_task(tenant_id, resume_id)` which fires a QStash webhook intended for `/api/v1/webhooks/qstash/resumes/parse`. 
This receiver endpoint is currently missing in the API. We will implement this missing endpoint exclusively in the new Worker service.

## 3. Worker Responsibilities
- Serve a single HTTP endpoint: `POST /api/v1/webhooks/qstash/resumes/parse`.
- Verify QStash signatures to ensure request authenticity.
- Set PostgreSQL Row-Level Security (RLS) context using the `tenant_id` from the payload.
- Download the raw resume file from Supabase Storage.
- Extract raw text (via `pdfplumber` / `python-docx`).
- Perform NLP Named Entity Recognition (via `spacy` / `en_core_web_trf`).
- Mutate the database (update `resumes`, auto-enrich `candidates`, log `ai_usage_logs`).

## 4. API Responsibilities
- Serve client-facing REST endpoints (upload, bulk upload, status poll, retry).
- Authenticate JWTs and validate user permissions.
- Validate file bounds and upload raw files to Supabase Storage.
- Create pending metadata rows in the database.
- Publish task events to QStash pointing to the Worker's URL.

## 5. Shared Code Strategy
To prevent code duplication, the Worker will live in the same repository (`apps/worker`) and will import the necessary database models and repositories directly from the `apps/api/hiron` Python package (e.g., `from hiron.resumes.repository import ResumeRepository`).
The Docker build context for the Worker will be the repository root, allowing it to easily resolve the shared code.

## 6. Dependency Separation
We will utilize PEP-621 Optional Dependencies (Extras) in `pyproject.toml` to split the dependency tree without creating a complex monorepo workspace.
*   **API Dependencies (Default)**: `fastapi`, `sqlalchemy`, `asyncpg`, `pydantic`, `qstash`, `openai`, `redis`. (These will naturally fit under 200 MB).
*   **Worker Dependencies (Optional Group)**: `spacy`, `en_core_web_trf`, `pdfplumber`, `python-docx`.

When Vercel builds the API, it runs `pip install .`, which installs only the default dependencies. When Docker builds the Worker, it will run `uv sync --all-extras`, installing everything including the heavy ML dependencies.

## 7. Database Interaction Design
The Worker needs direct access to the Supabase PostgreSQL database. It will establish a SQLAlchemy `AsyncEngine` pool identical to the API.
Operations:
1. `SELECT` from `resumes` and `resume_files`.
2. `UPDATE` `resumes` status to `processing`.
3. `UPDATE` `resumes` with `parsed_data`.
4. `UPDATE` `candidates` to enrich fields.
5. `INSERT` into `ai_usage_logs`.
Transaction boundaries will remain identical to the current `parse_resume_pipeline` implementation.

## 8. Storage Interaction Design
The Worker requires direct access to Supabase Storage (S3 API). It will use the `SupabaseStorageProvider` (via `httpx`) to download the binary file bytes using the `s3_key` stored in the `resume_files` table.

## 9. QStash Interaction Design
The API's `_enqueue_parse_task` will be updated to point to a new environment variable: `WORKER_URL`.
The payload remains identical: `{"tenant_id": "...", "resume_id": "..."}`.

## 10. Tenant/RLS Design
The Worker will extract the `tenant_id` from the QStash JSON payload. Before interacting with the database, it will call `hiron.security.context.set_tenant_context(tenant_id)`. This guarantees that the SQLAlchemy `checkout` event listener automatically runs `SET app.current_tenant_id = '...'`, flawlessly enforcing RLS in the Worker.

## 11. State Machine
- `pending`: Set by API upon successful upload.
- `processing`: Set by Worker upon receiving webhook.
- `parsed`: Set by Worker upon successful ML extraction.
- `failed`: Set by Worker upon corrupted PDF or unhandled Python exception.

## 12. Retry/Idempotency Design
The Worker must check the `Resume.status` upon receiving a webhook. If the status is `parsed` or `failed`, it must immediately return `HTTP 200 OK` without doing any work. This safely handles duplicate QStash deliveries.

## 13. Error Handling
- **Transient Errors** (e.g., DB Connection Timeout, S3 timeout): The Worker must let the exception bubble up to return an `HTTP 500`. QStash will capture this and retry the webhook with exponential backoff.
- **Permanent Errors** (e.g., Unparseable PDF, ML extraction crash): The Worker must catch the exception, update `Resume.status = 'failed'` along with the `parse_error` message, commit the transaction, and return `HTTP 200 OK` so QStash halts retries.

## 14. Security Model
- **Network**: The Worker will not be publicly accessible by clients. It exposes only one endpoint protected by `verify_qstash_signature`.
- **Secrets**: The Worker receives a stripped-down `.env` containing only `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `QSTASH_*_SIGNING_KEY`. It does *not* need `OPENAI_API_KEY`, `JWT_SECRET`, or `UPSTASH_REDIS_REST_URL`.

## 15. Worker Directory Structure
```text
pyproject.toml (updated with [project.optional-dependencies] worker = [...])
apps/
  api/
    hiron/
      resumes/
        service.py (stripped of parse_resume_pipeline)
  worker/
    Dockerfile
    src/
      main.py (FastAPI app & webhook receiver)
      pipeline.py (ported parse_resume_pipeline)
      parser.py (moved from api)
      extractor.py (moved from api)
```

## 16. Environment Variables (Worker)
```env
ENVIRONMENT=production
DATABASE_URL=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
QSTASH_CURRENT_SIGNING_KEY=...
QSTASH_NEXT_SIGNING_KEY=...
```

## 17. Docker Design
- Base Image: `python:3.12-slim`
- Working Directory: `/app`
- Copy root `pyproject.toml`, `uv.lock`.
- Install dependencies: `uv sync --all-extras`
- Copy `apps/` directory.
- Command: `uv run uvicorn apps.worker.src.main:app --host 0.0.0.0 --port 8000`

## 18. Deployment Requirements
- API deployed to Vercel.
- Worker deployed to a container hosting platform (e.g., AWS ECS, Render, Railway, Fly.io).

## 19. Vercel Bundle Reduction Strategy
By shifting `spacy`, `en_core_web_trf`, `pdfplumber`, and `python-docx` into the `[project.optional-dependencies] worker` block in the root `pyproject.toml`, Vercel's standard `pip install .` will entirely bypass the 5.4 GB CUDA/ML dependency tree, cleanly allowing the API to fit within the 500 MB limit.

## 20. Step-by-Step Implementation Plan
1. Move `parser.py` and `extractor.py` to `apps/worker/src/`.
2. Extract `parse_resume_pipeline` and `_enrich_candidate_profile` from `apps/api/hiron/resumes/service.py` to `apps/worker/src/pipeline.py`.
3. Create `apps/worker/src/main.py` to serve the QStash webhook endpoint.
4. Update `pyproject.toml` to move ML dependencies to `[project.optional-dependencies] worker`.
5. Update `uv.lock` via `uv sync`.
6. Add `WORKER_URL` environment variable to the API and update `_enqueue_parse_task` to use it.
7. Create `apps/worker/Dockerfile`.

## 21. Risks and Mitigations
- **Risk**: API accidentally imports `apps.worker.src.parser`, triggering an unresolved dependency error in production.
  **Mitigation**: Strict CI checks. The `apps/api` folder must remain entirely ignorant of `apps/worker`. 
- **Risk**: Worker database connection pool exhaustion if QStash fans out massively.
  **Mitigation**: Supabase PgBouncer (connection pooling) is enabled via port 6543, scaling effortlessly.

---

**READY FOR WORKER IMPLEMENTATION**
