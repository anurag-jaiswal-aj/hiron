# DECISION
APPROVED ARCHITECTURE: OPTION B (Change database schema to 768 dimensions and standardize on Gemini)

## 1. Problem
The Phase 7 audit identified a critical blocker:
- The database schema (`CandidateEmbedding`, `JobEmbedding`) explicitly restricts vectors to `Vector(1536)`.
- The application configuration specifies `models/text-embedding-004` (Gemini), which generates 768-dimensional vectors by default.
- A 768-dimensional vector will be rejected by a 1536-dimensional `pgvector` column.

## 2. Evidence
- `apps/api/hiron/core/config.py` explicitly defaults `gemini_embedding_model` to `"models/text-embedding-004"`.
- `apps/api/hiron/embeddings/models.py` explicitly hardcodes `pgvector.sqlalchemy.Vector(1536)`.

## 3. Gemini Verification
According to the official Google Gemini Generative AI documentation:
- **Exact model name:** `models/text-embedding-004`
- **Output dimensionality:** 768 by default. It can be reduced via the `output_dimensionality` parameter (e.g., to 256), but it **cannot** be increased to 1536.
- **SDK:** The correct Python SDK is `google-genai`.

## 4. Existing Schema Analysis
- `CandidateEmbedding.embedding` and `JobEmbedding.embedding` use `pgvector.sqlalchemy.Vector(1536)`.
- 1536 was originally selected because the project started with OpenAI's `text-embedding-3-small`.
- No HNSW indexes currently explicitly depend on the 1536 value (they use cosine distance).
- There are no embeddings currently stored in the production database (as this feature is unlaunched).

## 5. Existing Code Assumptions
- `apps/api/hiron/embeddings/generator.py` hardcodes `EMBEDDING_DIMENSION = 1536` and assumes the use of `openai`.
- `apps/api/hiron/embeddings/service.py` performs explicit validation checks: `len(existing.embedding) == 1536`.
- Over 15 unit tests across `test_embedding_service.py`, `test_embedding_repository.py`, and `test_search_service.py` hardcode mock vectors as `[0.1] * 1536`.

## 6. Downstream Impact
- **Phase 8 (Scoring) / Phase 9 (Search):** The search logic (`search/repository.py`) uses `CandidateEmbedding.embedding.cosine_distance(query_vector)`. The `pgvector` cosine distance operator (`<=>`) handles any supported dimension size (up to 2000 dimensions). 
- Changing to 768 dimensions will **not** break downstream search or scoring math, provided the query vector is also 768 dimensions.

## 7. Option A
**Keep `Vector(1536)` and revert to OpenAI embeddings.**
- **Compatibility:** Instantly compatible with all current API tests and schema.
- **Effort:** Low.
- **Drawbacks:** Violates the Phase 21 mandate which fully transitioned the platform's AI strategy from OpenAI to Google Gemini. Requires maintaining two separate AI provider billing relationships.

## 8. Option B
**Change schema to `Vector(768)` and standardize on Gemini `text-embedding-004`.**
- **Compatibility:** Requires altering the database schema and refactoring unit test mock vectors.
- **Effort:** Moderate.
- **Drawbacks:** Requires a database migration.
- **Benefits:** Perfectly aligns with the Phase 21 Gemini architectural consolidation. Saves costs and reduces external dependencies.

## 9. Recommended Architecture
**Option B.** Adhere to the Phase 21 mandate. The entire system should standardize on Gemini, meaning the database schema must be updated to 768 dimensions.

## 10. Canonical Embedding Contract
- **Provider:** Google Gemini (`google-genai` SDK)
- **Model:** `models/text-embedding-004`
- **Output dimension:** 768
- **Vector database type:** pgvector
- **Distance metric:** Cosine distance
- **Model version:** `models/text-embedding-004`
*(Note: Both Candidate and Job embeddings will use the same model and dimensionality to allow for cross-entity similarity search).*

## 11. Required DB Migration
A new Alembic migration script must be created:
```python
def upgrade() -> None:
    op.execute("ALTER TABLE candidate_embeddings ALTER COLUMN embedding TYPE vector(768)")
    op.execute("ALTER TABLE job_embeddings ALTER COLUMN embedding TYPE vector(768)")
```
*Since no embeddings exist in production, this ALTER TABLE command is safe and non-destructive.*

## 12. Worker Contract
The Railway worker (`apps/worker/src/main.py`) will expose two authenticated webhooks:

**Candidate Webhook:** `POST /api/v1/webhooks/qstash/embeddings/candidate`
**Payload:** `{"tenant_id": "<uuid>", "candidate_id": "<uuid>", "model_version": "models/text-embedding-004"}`

**Job Webhook:** `POST /api/v1/webhooks/qstash/embeddings/job`
**Payload:** `{"tenant_id": "<uuid>", "job_id": "<uuid>", "model_version": "models/text-embedding-004"}`

## 13. Failure Semantics
- **Gemini failure (API error/timeout):** Re-raise the exception. Do not mutate the DB status. QStash will automatically retry the webhook using its exponential backoff policy.
- **Database failure (connection drop):** Re-raise the exception for QStash retry.
- **QStash enqueue failure (during Phase 6 parsing):** If the API fails to publish the embedding task to QStash at the end of the parse pipeline, the failure should be logged, but the resume parsing transaction MUST NOT roll back. The resume remains `parsed`, and the embedding can be requested manually later.

## 14. Idempotency Strategy
The existing API code generates a deduplication ID like: `embed-cand-{candidate_id}-{model_version}-{uuid.uuid4()}`. 
Adding a random UUID defeats QStash's 24-hour deduplication window.
**Change:** The Phase 7 implementation must remove the random UUID and use strict deterministic keys:
- `embed-cand-{candidate_id}-{model_version}`
- `embed-job-{job_id}-{model_version}`

## 15. Telemetry Strategy
Embeddings will track telemetry via the `ai_usage_logs` table (using `AIUsageRepository.create_usage_log`).
- **Operation:** `embedding_generation`
- **Model:** `models/text-embedding-004`
- **Fields:** `input_tokens` (from Gemini response), `latency_ms`, `status` (`success` or `failed`), and `error_type` (if applicable).

## 16. Phase 7 Implementation Sequence
1. **Schema Update:** Generate and run Alembic migration to change vector columns to `768`. Update `models.py` and API validation logic in `service.py`. Update all mock vectors in unit tests.
2. **Idempotency Fix:** Remove random UUIDs from QStash deduplication IDs in `service.py`.
3. **Provider Integration:** Add `google-genai` to `pyproject.toml` and initialize the client in the worker.
4. **Worker Logic:** Implement the embedding generation functions and webhook endpoints in the worker.
5. **Trigger Chaining:** Inject the QStash publish call at the end of `parse_resume_pipeline`.

## 17. Risks
- Updating the schema and hunting down all hardcoded `1536` references in the test suite will be tedious.

## 18. Final Decision
Proceed with **Option B**. The database schema will be downgraded to 768 dimensions to support Google Gemini's `text-embedding-004` natively.
