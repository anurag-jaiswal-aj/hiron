# Phase 21.6 Task Idempotency Analysis

## General Principles
QStash guarantees **at-least-once** delivery. Duplicate deliveries are a known operational reality. Idempotency must be managed at the application level through atomic state transitions and cache checks, supplemented by QStash's built-in deduplication.

## 1. QStash Deduplication (First Layer)
QStash provides deduplication via the `Upstash-Deduplication-Id` header.
- **Deterministic ID:** When publishing a task, the service must generate a deterministic ID (e.g., `parse_resume_<resume_id>`).
- **Retries:** QStash automatic retries use the *same* message identity. Deduplication prevents multiple concurrent identical publish events, but does not prevent QStash from retrying a failed delivery.
- **Manual Retries:** Manual retries via the API must intentionally append a nonce or timestamp to the deduplication ID (e.g., `parse_resume_<resume_id>_<timestamp>`) to bypass deduplication and force a new execution identity.

## 2. Application-Level Idempotency (Second Layer)

### Resume Parsing (`parse_resume`)
**Duplicate Delivery Scenario:** QStash delivers the parsing request twice due to a network timeout during the first delivery's HTTP response.
**Flawed Approach:** `if resume.status == "parsed": return`. This is vulnerable to race conditions if both deliveries execute concurrently before either commits the `"parsed"` status.
**Atomic Work-Claim Mechanism:**
1. The webhook executes a `SELECT ... FOR UPDATE SKIP LOCKED` or an atomic `UPDATE` query:
   `UPDATE resumes SET status = 'processing' WHERE id = :id AND status = 'pending' RETURNING id;`
2. If the query returns no rows, another worker has already claimed this resume (or it is already parsed/failed). The webhook immediately returns `200 OK` (Ack) and stops.
3. If successful, it proceeds to call Gemini.
**Completion Check:** The atomic claim acts as the completion/in-progress check.

### Candidate & Job Embedding Generation
**Duplicate Delivery Scenario:** QStash delivers the embedding generation request twice.
**Atomic Work-Claim Mechanism:** Embeddings rely on an Upsert (`INSERT ... ON CONFLICT (id) DO UPDATE`).
**Cache Check:** The worker computes the `source_text_hash`. If a database row exists for the target entity with the matching hash and correct vector dimensions, it skips Gemini invocation. Concurrency might result in dual-generation in extreme cases, but the Upsert ensures the DB remains consistent.

### Individual Candidate Scoring (Batch Fan-Out)
**Duplicate Delivery Scenario:** QStash delivers the scoring request for a candidate twice.
**Cache Check:** The `ScoreService` enforces a 24-hour cache (`SCORE_CACHE_TTL_SECONDS`). If a valid score exists and `force_rescore=False`, it immediately returns `200 OK`.
**Database Uniqueness:** The `scores` table requires a unique constraint on `(job_candidate_id)` or `(job_candidate_id, model_version)` to prevent race conditions from inserting duplicate scores. A concurrent race will result in a Unique Violation, which should be caught and mapped to a `200 OK` (Ack).
