# Phase 21.6 Celery Task Inventory

## 1. Resume Parsing Task
**Task Name:** `hiron.resumes.parse_resume`
**Location:** `apps/api/hiron/resumes/tasks.py`
**Current Caller(s):** 
- `ResumeService.upload_resume`
- `ResumeService.retry_parse`
**Arguments:** `tenant_id: str`, `resume_id: str`
**Database Reads:** `Resume`, `ResumeFile`
**Database Writes:** `Resume` (status tracking: processing, parsed, failed), `Candidate` (enrichment), `AIUsageLog` (telemetry).
**External Services:** AWS S3 (downloading file), AI Provider (Gemini/OpenAI), SpaCy (local execution fallback).

## 2. Candidate Embedding Generation Task
**Task Name:** `hiron.embeddings.generate_candidate_embedding`
**Location:** `apps/api/hiron/embeddings/tasks.py`
**Current Caller(s):** 
- `parse_resume` (triggered automatically after successful parsing)
- `EmbeddingService.generate_candidate_embedding` (triggered by API)
**Arguments:** `tenant_id: str`, `candidate_id: str`, `model_version: str` (default `models/gemini-embedding-001`)
**Database Reads:** `Candidate`, `Resume`
**Database Writes:** `CandidateEmbedding`, `AIUsageLog`
**External Services:** AI Provider (Gemini)

## 3. Job Embedding Generation Task
**Task Name:** `hiron.embeddings.generate_job_embedding`
**Location:** `apps/api/hiron/embeddings/tasks.py`
**Current Caller(s):** 
- `JobService.create_job`
- `JobService.update_job`
- `EmbeddingService.generate_job_embedding` (triggered by API)
**Arguments:** `tenant_id: str`, `job_id: str`, `model_version: str` (default `models/gemini-embedding-001`)
**Database Reads:** `Job`
**Database Writes:** `JobEmbedding`, `AIUsageLog`
**External Services:** AI Provider (Gemini)

## 4. Batch Scoring Coordinator Task
**Task Name:** `hiron.scores.execute_batch_scoring` (Celery) / `batch_coordinator` (QStash)
**Location:** `apps/api/hiron/scores/tasks.py`
**Current Caller(s):** 
- `ScoreService.batch_score_async`
**Arguments:** `batch_id: str`, `tenant_id: str`, `job_id: str`, `candidate_ids: list[str]`, `force_rescore: bool`
**Database Reads:** `BatchScoreJob`
**Database Writes:** `BatchScoreJob` (status tracking)
**External Services:** QStash API (publish workers)

## 5. Batch Scoring Worker Task
**Task Name:** (Executed synchronously inside Celery batch task) / `batch_worker` (QStash)
**Arguments:** `batch_id: str`, `tenant_id: str`, `job_id: str`, `candidate_id: str`, `force_rescore: bool`
**Database Reads:** `Job`, `Candidate`, `JobCandidate`, `Score`, `CandidateEmbedding`, `JobEmbedding`, `BatchScoreJob`
**Database Writes:** `JobCandidate` (binding), `Score`, `AIUsageLog`, `BatchScoreJob` (atomic counters)
**External Services:** AI Provider (Gemini)

## 6. Dead Letter Queue (DLQ) & Failure Handling
When QStash exhausts all configured retries for a message:
1. **QStash Behavior:** The message is moved to the Upstash QStash Dead Letter Queue (DLQ), which acts as a permanent storage for failed events.
2. **Database State:** The application must proactively log the failure on the final attempt (detected via the `Upstash-Retried` header maxing out) by updating the respective entity status to `failed` and storing the error reason.
3. **Operator Visibility:** The `failed` status becomes visible in the frontend UI (e.g. Resume Processing Failed).
4. **Manual Replay:** 
   - An operator can click "Retry" in the UI, which will generate a new QStash message with a new deduplication ID.
   - Alternatively, an infrastructure admin can replay the exact message from the Upstash QStash DLQ Dashboard.
