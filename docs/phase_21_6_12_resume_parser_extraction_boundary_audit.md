# Phase 21.6.12: Resume Parser Extraction Boundary Audit

## 1. Current Resume-Processing Architecture
The current resume-processing flow in `hiron-api` is designed for asynchronous execution but is currently missing its webhook receiver.
1. **Upload**: Client calls `POST /api/v1/resumes/upload`.
2. **Validation & Storage**: The API validates the file, creates a `Candidate` (if needed), creates a `Resume` DB record (status: `pending`), uploads the file to Supabase Storage, and creates a `ResumeFile` DB record.
3. **Queueing**: The API calls `_enqueue_parse_task`, which publishes a message to QStash targeting `/api/v1/webhooks/qstash/resumes/parse`. The API returns an HTTP 202 Accepted immediately.
4. **Processing**: *Currently Broken/Missing*. The `parse_resume_pipeline` method exists in `ResumeService`, but there is no FastAPI route defined to receive the QStash webhook.

## 2. Complete Call Graph
`Router: POST /api/v1/resumes/upload`
  -> `ResumeService.upload_resume`
    -> `StorageProvider.upload_file` (S3)
    -> `ResumeRepository.create_resume` (PostgreSQL)
    -> `ResumeService._enqueue_parse_task`
      -> `qstash_publisher.publish(/qstash/resumes/parse)`
        -> QStash
          -> **[EXTRACTION BOUNDARY]** Worker receives Webhook
            -> `ResumeService.parse_resume_pipeline`
              -> `StorageProvider.download_file`
              -> `extractor.extract_text_from_file` (PDF/Docx)
              -> `parser.ResumeParser.parse(raw_text)` 
                 *(Heavy ML: spacy.load("en_core_web_trf"))*
              -> `ResumeRepository.update_resume_status`
              -> `ResumeService._enrich_candidate_profile`
              -> `AIUsageRepository.create_usage_log`

## 3. Parser Boundary
The boundary is extremely clean. The API handles the synchronous HTTP request, file storage, and DB metadata initialization. The extraction boundary sits exactly at the QStash webhook receiver. The worker only needs to receive `tenant_id` and `resume_id` to perform the heavy NLP workload.

## 4. API Responsibilities
- Authenticating user requests via JWT.
- Enforcing Tenant Isolation & RBAC permissions.
- Validating file types and sizes.
- Uploading raw files to Supabase S3.
- Creating the initial `Resume` and `Candidate` database records.
- Enqueueing the QStash webhook.
- Providing polling endpoints (`/{resume_id}/status`) for frontend clients.

## 5. Worker Responsibilities
- Receiving QStash webhook (`/qstash/resumes/parse`).
- Verifying the QStash cryptographic signature.
- Downloading the file from Supabase S3.
- Extracting raw text from PDF/Docx.
- Executing the SpaCy Transformer NER parsing pipeline.
- Updating the PostgreSQL `Resume` and `Candidate` records.
- Logging telemetry to `ai_usage_logs`.

## 6. Database Responsibilities
- PostgreSQL (Supabase) acts as the central state store.
- The `status` column on the `resumes` table (`pending` -> `processing` -> `parsed`/`failed`) mediates state between the API and the Worker.

## 7. Storage Responsibilities
- Supabase Storage (S3) holds the raw `.pdf` / `.docx` files so the API can offload the payload and the Worker can download it asynchronously.

## 8. QStash Responsibilities
- Guaranteed at-least-once delivery of the `resume_id` to the Worker.
- Automatic retries if the Worker crashes or hits transient DB errors (HTTP 5xx).
- Decoupling the Vercel API from the heavy Worker.

## 9. Tenant Isolation Analysis
- Tenant context is preserved by passing `tenant_id` in the JSON payload of the QStash webhook.
- The Worker must use this `tenant_id` in all SQLAlchemy `WHERE` clauses to ensure tenant data boundaries are respected.

## 10. Transaction Analysis
- The API's `upload_resume` commits the DB transaction *before* enqueueing the QStash message. This prevents race conditions where the Worker tries to read a `Resume` that hasn't been committed yet.
- The Worker's `parse_resume_pipeline` commits state changes independently (e.g., setting `processing` status, then later committing the final `parsed` data).

## 11. Retry/Idempotency Analysis
- If QStash delivers a duplicate webhook, the Worker should check if `Resume.status` is already `parsed` or `failed` and skip processing if so (idempotency).
- If the Worker fails due to a DB timeout (HTTP 500), QStash will automatically retry.

## 12. Failure-State Analysis
- If the `ResumeParser` encounters a corrupted PDF or an unhandled exception, it logs the error, updates `Resume.status = 'failed'`, saves the `parse_error`, and returns HTTP 200 OK to QStash so it stops retrying. 
- The client sees the `failed` status via polling and can trigger a manual retry via `POST /{resume_id}/retry`.

## 13. Required Worker Inputs
- `tenant_id` (UUID)
- `resume_id` (UUID)
- Environment Variables: `DATABASE_URL`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## 14. Required Worker Outputs
- Direct PostgreSQL `UPDATE` to the `resumes` and `candidates` tables.
- HTTP 200 OK to QStash.

## 15. Dependencies Required by Worker
- `spacy`
- `en_core_web_trf`
- `spacy-curated-transformers`
- `torch`
- `pdfplumber`
- `python-docx`
- `sqlalchemy` / `asyncpg` (for DB writes)
- `httpx` (for Supabase Storage S3 interactions)

## 16. Dependencies That Can Be Removed from Vercel API
- `spacy`
- `en_core_web_trf`
- `pdfplumber`
- `python-docx`
- *(By removing these, the Vercel API bundle size drops from 5.4 GB to under 200 MB, safely under the 500 MB limit).*

## 17. Exact Files/Classes/Functions That Would Move
- `apps/api/hiron/resumes/parser.py` (entire file).
- `apps/api/hiron/resumes/extractor.py` (entire file).
- `ResumeService.parse_resume_pipeline` and `ResumeService._enrich_candidate_profile` (moved to the Worker's service layer).

## 18. Exact Files/Classes/Functions That Must Remain
- `apps/api/hiron/resumes/router.py`.
- `apps/api/hiron/resumes/models.py`.
- `apps/api/hiron/resumes/repository.py`.
- `ResumeService.upload_resume`, `bulk_upload_resumes`, `get_resume_status`, `retry_parse`.

## 19. Proposed Communication Mechanism
- QStash Webhooks. The API publishes; the Worker subscribes.

## 20. Proposed Deployment Topology
- **API**: Vercel Serverless Functions (`hiron-api`).
- **Worker**: AWS ECS, Render, or Railway Docker container (`hiron-worker`). Exposes an HTTP FastAPI server with a single route: `POST /api/v1/webhooks/qstash/resumes/parse`.

## 21. Risks
- Database connection pooling limits if the Worker scales up massively (solved via Supabase connection pooling / PgBouncer).
- Security of the Worker's endpoint (solved via QStash signature verification).

## 22. Migration Complexity
- **Low**. The codebase was already architected for asynchronous parsing via QStash. The missing webhook route in the API makes extraction even easier, as no existing API route needs to be ripped out or redirected. We simply define the missing route in a new lightweight Worker service.

## 23. Recommended Implementation Sequence
1. Create a new `apps/worker` project folder.
2. Port `parser.py`, `extractor.py`, and `parse_resume_pipeline` to the Worker.
3. Remove ML dependencies (`spacy`, `torch`, `en_core_web_trf`) from the API's `pyproject.toml`.
4. Deploy the lightweight API to Vercel.
5. Deploy the Worker as a Docker container to a persistent hosting provider.
6. Configure QStash to point the Resume Parse webhook to the Worker's URL.

---

**PARSER CAN BE CLEANLY EXTRACTED**
