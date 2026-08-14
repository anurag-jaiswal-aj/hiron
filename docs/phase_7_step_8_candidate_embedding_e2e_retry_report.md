# Phase 7 Step 8: Candidate Embedding E2E Retry Report

## Objective
Perform ONE controlled production candidate embedding E2E test using the existing QStash → Railway worker pipeline, targeting the `gemini-embedding-2` model for 768 dimensions.

## Preconditions
1. **Railway Worker**: Verified Online via `railway status`.
2. **GEMINI_API_KEY**: Verified present in Railway production variables.
3. **Candidate Status**: Candidate `44b5fa13-2840-4c7c-a036-adbb347b81a8` confirmed to have a successfully parsed resume.
4. **Existing Embeddings**: Verified no existing `candidate_embeddings` row for this candidate in production (clean state).

## Exact Execution Path
- Triggered manually using local `scratch/trigger_e2e_embedding.py` connected to production.
- Payload dispatched to QStash.
- QStash relayed to `https://hiron-worker-production.up.railway.app/api/v1/webhooks/qstash/embeddings/candidate`.

## Results
- **QStash publish**: PASS (Message ID: `msg_26hZCxZCuWyyTWPmSVBrNCtiJFKp4kuGqowSLA7TB6iV5gUUg4JHNstbrNPfg1R`)
- **QStash message delivered**: PASS
- **Railway webhook received**: PASS
- **QStash signature verification**: PASS
- **Railway connects to PostgreSQL**: PASS
- **Gemini API call**: PASS (Previous `TypeError` on `await` successfully resolved)
- **Vector Dimension**: FAIL (Database constraint rejected the 768-dim vector)
- **Database result**: FAIL (HTTP 500 error raised during the `INSERT`)
- **Model version**: NOT VERIFIED (Failed prior to persistence)
- **Source hash**: NOT VERIFIED (Failed prior to persistence)
- **Telemetry**: NOT VERIFIED (Failed prior to persistence)
- **Idempotency**: NOT VERIFIED (Failed prior to persistence)

## Final PASS/FAIL
**FAIL**

## Exact Blocker
```text
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>: expected 1536 dimensions, not 768
[SQL: INSERT INTO candidate_embeddings (id, tenant_id, candidate_id, embedding, model_version, source_text_hash) VALUES ($1::UUID, $2::UUID, $3::UUID, $4, $5::VARCHAR, $6::VARCHAR) RETURNING candidate_embeddings.created_at]
```
The Gemini SDK successfully returned a 768-dimensional vector, but the `candidate_embeddings.embedding` column in the production PostgreSQL database is still strictly constrained to `1536` dimensions (the previous OpenAI standard). 

Looking at the uncommitted repository state (`git status --short`), an Alembic migration (`apps/api/alembic/versions/20260814_1453_9e4f33bbb02c_migrate_embedding_vector_dimensions_to_.py`) exists but has NOT been applied to the production database.

## Recommended Next Step
Run the Alembic migrations against the production database to alter the vector column types in `candidate_embeddings` and `job_embeddings` from `1536` to `768`, then retry the E2E execution.
