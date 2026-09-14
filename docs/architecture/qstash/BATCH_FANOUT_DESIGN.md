# Phase 21.6 Batch Fan-Out Design

## Architecture Problem
The current Celery implementation processes all candidates for a batch score inside a single task execution (`execute_batch_scoring`). This creates a long-running synchronous process that heavily relies on `celery_task.update_state()` to track progress. A single QStash webhook processing 100 candidates sequentially would undoubtedly hit HTTP timeouts (FastAPI, Load Balancer, or QStash 15-30s limits) and fail repeatedly.

## Fan-Out Solution
Batch scoring must be redesigned into a **Coordinator -> Worker Fan-Out** model using QStash.

### 1. The Coordinator Webhook
The `BatchScoreAsync` API endpoint creates a PostgreSQL `BatchScoreJob` entity to track progress, then publishes a single message to the Coordinator Webhook.
The Coordinator Webhook retrieves the candidate list, generates individual QStash messages for each candidate, and publishes them (or publishes them in parallel using QStash batching capabilities).

### 2. The Worker Webhook
Each QStash message targets an individual candidate scoring webhook.

**Payload Schema (Worker Webhook):**
```json
{
  "batch_id": "uuid-string",
  "tenant_id": "uuid-string",
  "job_id": "uuid-string",
  "candidate_id": "uuid-string",
  "force_rescore": false
}
```

### 3. Database State Tracking (`BatchScoreJob`)
To replace Celery's `update_state()`, a new database entity is required.

**Entity: `BatchScoreJob`**
- `id`: UUID (Primary Key)
- `tenant_id`: UUID
- `job_id`: UUID
- `total_candidates`: Integer
- `queued_count`: Integer
- `processing_count`: Integer
- `completed_count`: Integer
- `failed_count`: Integer
- `status`: Enum ("pending", "processing", "completed", "failed")
- `retry_count`: Integer
- `created_at`: Timestamp
- `updated_at`: Timestamp

### 4. Progress Updates
When the individual worker webhook finishes (success or failure), it increments the respective counters (`completed_count` or `failed_count`) on the `BatchScoreJob` row atomically using a PostgreSQL `UPDATE ... SET completed_count = completed_count + 1 WHERE id = ...` statement.
If `completed_count + failed_count == total_candidates`, the status is updated to "completed".
The frontend will poll a standard API endpoint that reads this `BatchScoreJob` row.
