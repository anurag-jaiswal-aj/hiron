# Phase 7 — Embedding Pipeline Audit

## 1. Phase 7 Roadmap Requirements
**Objective:** Generate vector embeddings for candidates (from resume text) and jobs (from description text). This phase creates the data foundation for scoring (Phase 8) and semantic search (Phase 9).

**Features & Requirements:**
- **Candidate embeddings:** Generate from `resumes.raw_text`.
- **Job embeddings:** Generate from `jobs.description`.
- **State/Status:** Track staleness via `source_text_hash` and detect when regeneration is needed. Provide a coverage dashboard endpoint.
- **Storage:** Persist in `candidate_embeddings` and `job_embeddings` tables using `pgvector` with HNSW indices.
- **Queue/Tasks:** Originally planned as Celery tasks, now superseded by QStash webhooks.
- **Trigger Chaining:** Auto-trigger candidate embedding after successful resume parse; auto-trigger job embedding after job creation/update.
- **Error/Retry:** Implement resilient failure handling and `ai_usage_logs` telemetry tracking.
- **Dependencies:** Requires Phase 6 (Parsed text) and Phase 3 (Jobs).

## 2. Existing Implementation Inventory
**Directory:** `apps/api/hiron/embeddings/`

| Component | Exists | Complete | Missing | Notes |
|---|---|---|---|---|
| API Router (`router.py`) | Yes | Yes | No | Complete. Exposes EMBED-1, EMBED-2, EMBED-3 endpoints. |
| API Service (`service.py`) | Yes | Yes | No | Complete. Manages cache-hits, QStash publishing, and coverage logic. |
| Repositories (`repository.py`) | Yes | Yes | No | Complete. SQLAlchemy logic for fetching and upserting embeddings. |
| Schemas (`schemas.py`) | Yes | Yes | No | Complete. Pydantic validation for API responses. |
| Database Models (`models.py`) | Yes | Yes | No | Exists, but hardcodes `Vector(1536)`. |
| Generator Stub (`generator.py`) | Yes | No | **Yes** | Uses hardcoded OpenAI `text-embedding-3-small` and mock generation. No Gemini implementation. |
| Worker Implementation | No | No | **Yes** | No embedding worker exists in `apps/worker/src/`. |

## 3. Gemini Provider Audit
**Finding:** The Gemini SDK (`google-genai` or `google-generativeai`) is **NOT** installed in the repository (`pyproject.toml`).
- **Configuration:** `apps/api/hiron/core/config.py` explicitly declares `gemini_api_key` and sets `gemini_embedding_model` to `models/text-embedding-004`.
- **Current Code:** The API's `generator.py` still imports and uses the `openai` SDK (`text-embedding-3-small`).
- **Gap:** The existing Gemini provider does not actually exist yet in the codebase for embeddings. The repository intended to use `models/text-embedding-004`, but the migration was never executed at the code level.

## 4. Worker Architecture Audit
**Location:** `apps/worker/src/`
- The worker is a lightweight FastAPI app receiving QStash webhooks (`main.py`).
- It successfully enforces `verify_qstash_signature` and initializes the DB context via `AsyncSessionLocal()`.
- The embedding workers must follow this exact pattern: expose a new endpoint (e.g., `/api/v1/webhooks/qstash/embeddings/candidate`), verify the signature, load the context, and execute the embedding logic synchronously within the HTTP lifecycle.
- **Constraint:** Do not introduce Celery or Redis. Reuse the QStash architecture.

## 5. Database/Schema Audit
- **Models:** `CandidateEmbedding` and `JobEmbedding` exist in `models.py`.
- **Vector Dimension:** The schema **explicitly hardcodes 1536 dimensions** (`pgvector.sqlalchemy.Vector(1536)`).
- **Conflict:** The intended Gemini model (`models/text-embedding-004`) produces **768-dimensional** vectors by default. It cannot produce 1536 dimensions. Inserting a 768-dimensional vector into a 1536-dimensional `pgvector` column will throw a strict PostgreSQL type error.

## 6. QStash Audit
- **Payload Format:** `{"tenant_id": str, "candidate_id": str, "model_version": str}`
- **Destination URL:** `webhook_url = f"{settings.qstash_webhook_url.rstrip('/')}/api/v1/webhooks/qstash/embeddings/candidate"`
- **Deduplication:** The API currently uses `deduplication_id=f"embed-cand-{candidate_id}-{model_version}-{uuid.uuid4()}"`. (Note: appending a random UUID defeats deduplication, but this logic exists in the API).
- **Pattern:** We must reuse the existing `qstash_publisher` instance and the `@app.post(..., dependencies=[Depends(verify_qstash_signature)])` route decorator in the worker.

## 7. Trigger-Chain Audit
**Current Resume Parse Flow:**
- `upload_resume` → QStash → `apps/worker/src/main.py:parse_resume_webhook` → `pipeline.py:parse_resume_pipeline`.
**Missing Chaining:**
- After `parse_resume_pipeline` successfully writes `status="parsed"` and commits, it currently returns immediately.
- **Required Trigger:** At the end of `parse_resume_pipeline`, we must call `qstash_publisher.publish()` to enqueue the candidate embedding task.
- **Failure Behavior:** If the QStash publish fails during the chain, it should **not** roll back the successful resume parse. It should log the failure and allow the client to manually retry the embedding later.

## 8. Missing Implementation
1. **Gemini SDK dependency:** Missing from `pyproject.toml`.
2. **Database Migration:** Resolving the 1536 vs 768 vector dimension mismatch.
3. **Worker Embedding Pipeline:** The logic to fetch candidate text, call the LLM provider, and store the result in the database.
4. **Worker Webhook Endpoints:** Exposing the QStash callback routes.
5. **Trigger Chaining:** Injecting the QStash publish call at the end of the parser pipeline.

## 9. Risks
- **Dimension Mismatch:** The database currently expects 1536 (OpenAI) while config expects `text-embedding-004` (Gemini: 768).
- **Timeout Limitations:** Generating embeddings within the Vercel API is not feasible due to timeouts; it MUST occur within the Railway worker.
- **Dependencies:** Mixing OpenAI and Gemini SDKs in the worker bundle could inflate bundle size.

## 10. Open Questions / Blockers
1. **Dimension Conflict (BLOCKER):** Should we modify the database schema from `Vector(1536)` to `Vector(768)` to support Gemini, or should we revert the configuration to OpenAI's `text-embedding-3-small`? *NOT ESTABLISHED BY CURRENT CODEBASE.*
2. **Gemini SDK Installation:** Are we authorized to add `google-genai` to `pyproject.toml` since it is currently absent? *NOT ESTABLISHED BY CURRENT CODEBASE.*

## 11. Recommended Smallest Implementation Slice
**Goal:** Prove the worker can receive the embedding webhook and correctly load the candidate context, bypassing the LLM provider dimension conflict for now.

**Action:** 
1. Scaffold `apps/worker/src/embeddings.py` with a mock generator (returning a dummy vector matching the current DB dimensions).
2. Wire up the `/api/v1/webhooks/qstash/embeddings/candidate` route in `apps/worker/src/main.py`.
3. Add a unit/integration test directly hitting the worker webhook to ensure the DB record is created successfully.

## 12. Acceptance Criteria for that Slice
- [ ] Worker exposes the new QStash embedding webhook.
- [ ] Webhook successfully authenticates using `verify_qstash_signature`.
- [ ] Worker reads candidate text, generates a mock vector, and persists it to `candidate_embeddings`.
- [ ] Database state correctly reflects `status="current"`.
