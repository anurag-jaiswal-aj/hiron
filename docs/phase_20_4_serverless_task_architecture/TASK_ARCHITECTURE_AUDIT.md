# Phase 20.4 — Serverless Task Architecture Audit

## 1. Executive Summary
This audit analyzes the existing Hiron Celery architecture to determine exactly how each background task can be migrated to an Upstash QStash + Vercel Serverless HTTP execution model in order to achieve a $0/month deployment. 

The analysis reveals that while Embedding tasks can migrate directly, the Resume Parsing task is severely blocked by the memory footprint of the SpaCy `en_core_web_trf` model, and the Batch Scoring task requires structural decomposition to survive strict 10-second serverless execution limits.

## 2. Task-by-Task Migration Matrix

### Task 1: `hiron.resumes.parse_resume`
1. **Current task name:** `hiron.resumes.parse_resume`
2. **Current trigger:** `ResumeService.upload_resume` and `retry_parse`
3. **Current inputs:** `tenant_id` (str), `resume_id` (str)
4. **Current outputs:** `dict[str, str]` with success status.
5. **Database side effects:** Reads/Updates Resume status (`processing` -> `parsed`/`failed`). Auto-enriches `Candidate` profile fields. Writes to `AIUsageLog`.
6. **External API calls:** S3/StorageProvider download.
7. **Current retry behavior:** Manual retries via API (`retry_parse`).
8. **Current timeout assumptions:** Unlimited. Can take 10s-30s depending on file size and NLP extraction.
9. **Current Redis/Celery dependency:** Enqueued via `delay()`. Uses Redis backend for results.
10. **Estimated serverless execution requirements:** The current implementation uses SpaCy `en_core_web_trf`. This transformer model requires >1GB RAM to load and significant CPU for inference, typically taking 10-15 seconds.
11. **Whether it can safely run inside a Vercel function:** **NO.** Vercel Hobby strictly limits functions to 1024MB RAM and 10 seconds. The SpaCy model will inevitably cause Out-of-Memory (OOM) errors or HTTP 504 Timeouts.
12. **Whether it requires QStash:** Yes. It is an asynchronous background process that shouldn't block the API response.
13. **Whether it requires further decomposition:** No, but it requires a fundamental rewrite of the parsing engine.
14. **Idempotency requirements:** High. Must tolerate duplicate deliveries by checking if the resume status is already `parsed`.
15. **Security/authentication requirements:** Must verify Upstash QStash JWT signatures to prevent unauthenticated POSTs from triggering heavy CPU usage.

### Task 2: `hiron.embeddings.generate_candidate_embedding` & `generate_job_embedding`
1. **Current task name:** `hiron.embeddings.generate_candidate_embedding` / `generate_job_embedding`
2. **Current trigger:** Chained from successful `parse_resume` completion; manual API invocation.
3. **Current inputs:** `tenant_id`, `candidate_id` / `job_id`, `model_version`
4. **Current outputs:** `dict[str, str]` with success status.
5. **Database side effects:** Updates Candidate/Job `embedding` pgvector columns. Writes to `AIUsageLog`.
6. **External API calls:** OpenAI / Gemini API for generating vectors.
7. **Current retry behavior:** None implemented at the Celery level (fail-fast).
8. **Current timeout assumptions:** Assumes LLM API returns within a few seconds.
9. **Current Redis/Celery dependency:** Standard Celery broker.
10. **Estimated serverless execution requirements:** Network-bound. Minimal RAM footprint. ~1-5 seconds execution time.
11. **Whether it can safely run inside a Vercel function:** **YES.**
12. **Whether it requires QStash:** Yes.
13. **Whether it requires further decomposition:** No. It is perfectly sized for a single serverless webhook.
14. **Idempotency requirements:** Moderate. Re-running it simply overwrites the vector in the database, costing a fraction of a cent in LLM tokens.
15. **Security/authentication requirements:** Must verify Upstash QStash JWT signatures.

### Task 3: `hiron.scores.execute_batch_scoring`
1. **Current task name:** `hiron.scores.execute_batch_scoring`
2. **Current trigger:** Batch scoring API endpoint.
3. **Current inputs:** `tenant_id`, `job_id`, `candidate_ids` (list[str]), `force_rescore`
4. **Current outputs:** Progress stream via `update_state` (current, total, percent).
5. **Database side effects:** Upserts `Score` table records. Writes to `AIUsageLog`.
6. **External API calls:** OpenAI / Gemini API (1 call per candidate).
7. **Current retry behavior:** None. Fails specific items and continues loop.
8. **Current timeout assumptions:** Unbounded. A batch of 50 candidates might take 100 seconds to score synchronously in the background worker loop.
9. **Current Redis/Celery dependency:** **Critically relies on Celery's `task.update_state` mechanism**, which writes progress to the Redis result backend for the frontend to poll.
10. **Estimated serverless execution requirements:** Synchronous loop over `N` candidates making LLM calls.
11. **Whether it can safely run inside a Vercel function:** **NO.** If `len(candidate_ids)` is > 5, it will hit the 10-second Vercel timeout and silently die midway through the batch.
12. **Whether it requires QStash:** Yes.
13. **Whether it requires further decomposition:** **YES (Fan-Out).** The single batch task must be converted into a fan-out pattern. The API publishes `N` individual scoring messages to QStash (one per candidate). Each serverless execution scores exactly 1 candidate and terminates in <5 seconds.
14. **Idempotency requirements:** Moderate. Scoring the same candidate twice just overwrites the row.
15. **Security/authentication requirements:** Must verify Upstash QStash JWT signatures.

## 3. SpaCy Deep Dive
- **Model Size:** `en_core_web_trf` requires downloading ~500MB of weights.
- **Import/Startup Cost:** Loading the model into RAM takes 2-5 seconds locally and spikes memory usage dynamically up to 1-2GB during inference.
- **Current Behavior:** The codebase attempts to lazy-load it globally (`get_nlp()`) to amortize the cost, but serverless environments freeze and recycle instances rapidly, guaranteeing frequent cold boots.
- **Architectural Reality:** An LLM (e.g. Gemini 1.5 Flash Free Tier) can parse a resume into structured JSON in 3-5 seconds using standard HTTP libraries, requiring almost zero RAM. **LLM-based parsing is absolutely required** if the architecture is to survive on Vercel Hobby limits.

## 4. Recommended Architectures Compared

### Option A: Direct Port (QStash -> Vercel Endpoint -> Existing Code)
- **Result:** Fails immediately. Vercel kills `parse_resume` for OOM/Timeout, and kills `execute_batch_scoring` for Timeout.

### Option B: Recommended Serverless Refactoring (QStash -> Vercel -> LLM/Fan-out)
1. **Resume Pipeline:** API publishes `parse_resume` to QStash -> Vercel executes Webhook -> Vercel calls Gemini API to extract JSON -> Updates PostgreSQL -> Vercel publishes `generate_embedding` to QStash -> Vercel executes Embedding Webhook -> Updates PostgreSQL.
2. **Scoring Pipeline:** API publishes `N` individual `score_candidate` messages to QStash -> Vercel scales horizontally to process `N` separate Webhook invocations concurrently -> Updates PostgreSQL. 
*(Note: Celery's progress state tracking must be replaced by polling the database directly for completed scores).*

## 5. Summary
- **Can migrate directly:** Embeddings generation.
- **Cannot migrate directly:** Resume parsing (blocked by SpaCy RAM/Timeout), Batch Scoring (blocked by Timeout and `update_state` dependency).
- **Recommended Phase 21 Implementation Sequence:** 
  1. Rip out SpaCy and implement Gemini LLM parsing.
  2. Implement QStash Fan-out for batch scoring, removing `celery_task.update_state`.
  3. Replace all `.delay()` calls with Upstash QStash Publisher HTTP calls.
  4. Create a unified `/api/v1/webhooks/qstash` FastAPI router utilizing Upstash Signature verification to handle incoming jobs.
