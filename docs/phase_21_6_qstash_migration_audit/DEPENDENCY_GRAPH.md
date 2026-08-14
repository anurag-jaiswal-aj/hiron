# Phase 21.6 Task Dependency Graph

## Task-to-Task Execution Triggers

### 1. Resume Parsing Pipeline
`Client Request` -> `API: /upload` -> **(Enqueues)** -> `hiron.resumes.parse_resume`
- Upon successful execution of `parse_resume`, it explicitly triggers:
`parse_resume` -> **(Enqueues)** -> `hiron.embeddings.generate_candidate_embedding`

*Note: This is a direct invocation via `generate_candidate_embedding.delay(...)` rather than using Celery's `chain` or `chord` features.*

### 2. Job Creation Pipeline
`Client Request` -> `API: POST /api/v1/jobs` -> **(Enqueues)** -> `hiron.embeddings.generate_job_embedding`

### 3. Job Update Pipeline (Conditionally)
`Client Request` -> `API: PATCH /api/v1/jobs/{id}` -> **(Enqueues)** -> `hiron.embeddings.generate_job_embedding` (triggered only if description or required_skills are modified)

### 4. Batch Scoring Pipeline
`Client Request` -> `API: POST /api/v1/scores/batch` -> **(Enqueues)** -> `hiron.scores.execute_batch_scoring`
- Note: This task executes synchronously over multiple candidates within its own single Celery task execution, rather than fanning out into smaller chunks via Celery groups.

## Database State Transitions

1. **Resume Processing**
   - **Initial State:** `Resume` created with status="pending" (in API endpoint).
   - **Task Start:** `Resume` status="processing" (first action in task).
   - **Task Success:** `Resume` status="parsed", `parsed_data` populated.
   - **Task Error:** `Resume` status="failed", `parse_error` populated.

2. **Candidate Enrichment**
   - Candidate fields (name, email, skills) are updated automatically upon successful `parse_resume`.

3. **Scoring Execution**
   - **Check Cache:** Task reads `Score` entity. If one exists and is <24 hours old, skips generation.
   - **Execution:** Task generates fit_score.
   - **Persistence:** Inserts new `Score` row.

## Summary
The system does not rely on complex Celery workflows (chains, chords, canvas primitives). Task dependencies are linear and loosely coupled, meaning a webhook-based system like QStash is highly compatible with the current architecture.
