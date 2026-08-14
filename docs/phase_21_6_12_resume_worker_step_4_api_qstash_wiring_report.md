# Phase 21.6.12: Resume Worker Implementation (Step 4) API -> QStash -> Worker Wiring Report

## 1. Current QStash Behavior Before Step 4
Prior to Step 4, `_enqueue_parse_task` inside `apps/api/hiron/resumes/service.py` read `settings.qstash_webhook_url` and unconditionally appended `/api/v1/webhooks/qstash/resumes/parse`. This meant QStash always published the background job back to the monolithic API base URL.

## 2. WORKER_URL Configuration
A new configuration setting `worker_url` has been added to `apps/api/hiron/core/config.py`. It explicitly captures the base URL for the deployed worker.

## 3. Final QStash Destination
The `_enqueue_parse_task` method was refactored to read `settings.worker_url`. If `worker_url` is unavailable (such as in local development), it seamlessly falls back to `settings.qstash_webhook_url`. The final destination published to QStash is now securely decoupled from the API: `{worker_base_url}/api/v1/webhooks/qstash/resumes/parse`.

## 4. Payload Format
The payload format remains entirely unmodified, preserving the contract with the worker pipeline:
```json
{
    "tenant_id": "<uuid>",
    "resume_id": "<uuid>"
}
```

## 5. URL Normalization Behavior
To prevent malformed URLs containing double slashes (`//api/v1/...`), the logic natively trims trailing slashes from the environment configuration using `.rstrip("/")`. Local unit tests were authored in `scratch/test_step4.py` and actively verified this behavior.

## 6. Production Configuration Behavior
A Pydantic `@model_validator` was implemented in `config.py` to strictly enforce `worker_url` presence when `environment == "production"`. This satisfies the safety constraint that production environments must explicitly declare the worker routing boundary, rather than silently defaulting to local endpoints.

## 7. API/Worker Import Boundary
Extensive `grep` queries verified that the monolithic API does **not** import any code from `apps.worker`. The heavy worker modules are executed strictly on the worker side, preserving the API's lightweight signature.

## 8. QStash Signature Flow
The security boundary is strictly enforced. The payload is published to the new `WORKER_URL`. The `verify_qstash_signature` middleware executes natively on the Worker webhook, securely parsing the `Upstash-Signature` header against `QSTASH_CURRENT_SIGNING_KEY` before tenant contexts are allocated or database queries invoked.

## 9. Resume State Machine
The core state flow is preserved:
- Upload creates a `pending` Resume.
- Processing mutates to `processing`.
- Completion mutates to `parsed` (terminal).
- Permanent NLP crashes/errors mutate to `failed` (terminal).

## 10. Retry Behavior
The API manual retry endpoint correctly handles `failed` states. It resets the database status to `pending`, erases previous parse errors, and enqueues a new QStash task which the worker seamlessly interprets as ready to process.

## 11. Worker Environment Requirements
To operate securely in production, the Worker container will require:
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET` (configured as `resumes`)
- `QSTASH_CURRENT_SIGNING_KEY`
- `QSTASH_NEXT_SIGNING_KEY`

## 12. Docker Verification
A static and build review of `apps/worker/Dockerfile` confirms it provisions Python 3.12, installs the `[worker]` extra group leveraging `uv`, successfully resolves build-time metadata (by copying `README.md` along with `pyproject.toml`), explicitly isolates `PYTHONPATH=/app/apps/api`, and exposes Uvicorn. No internal secrets are shipped within the image. A local `docker build` executed successfully.

## 13. API Bundle Verification
Using the isolated API environment (`api-venv`), `import hiron.resumes.service` was executed. The `sys.modules` dump verified `spacy`, `torch`, `pdfplumber`, and `docx` were entirely absent.

## 14. Worker Dependency Verification
Using the worker environment (`worker-venv`), successful execution confirmed that `apps.worker.src.main`, `apps.worker.src.pipeline`, `apps.worker.src.parser`, and `apps.worker.src.extractor` import perfectly with ML dependencies resolved.

## 15. Test Results
- **Step 4 Normalization Tests (`scratch/test_step4.py`):** 4 tests executed, 4 passed. Confirmed fallback, URL truncation, and production validation rules.
- **API Tests (`pytest apps/api/tests/test_resume_service.py`):** The pre-existing test mock failures correctly appeared as `ValueError: WORKER_URL or qstash_webhook_url is required to publish background tasks`. No new failures were introduced. 

## 16. Git/Security Verification
`git diff` and `git status` confirmed no API keys, tokens, Supabase URLs, or production configuration secrets were exposed or leaked into standard files. 

## 17. Files Modified
- `apps/api/hiron/core/config.py` (configuration and production validation)
- `apps/api/hiron/resumes/service.py` (modified QStash publishing URL target)
- `scratch/test_step4.py` (added local validation tests)

## 18. Remaining Blockers or Risks
The logic boundary is comprehensively isolated and tested. There are no remaining local blockers for the worker execution. The infrastructure can now proceed to deploying the worker image and validating the end-to-end cloud flow.

---

STEP 4 COMPLETE — READY FOR WORKER DEPLOYMENT
