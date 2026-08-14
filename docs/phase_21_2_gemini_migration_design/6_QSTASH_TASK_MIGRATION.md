# 6. QStash Task Migration

## Celery to QStash Mapping
Every Celery task becomes a FastAPI route in `/api/v1/webhooks/qstash/`.

| Celery Task | Target QStash Webhook | Method |
|---|---|---|
| `parse_resume` | `/api/v1/webhooks/qstash/parse-resume` | POST |
| `generate_candidate_embedding` | `/api/v1/webhooks/qstash/generate-candidate-embedding` | POST |
| `generate_job_embedding` | `/api/v1/webhooks/qstash/generate-job-embedding` | POST |
| `execute_batch_scoring` | `/api/v1/webhooks/qstash/score-candidate` (Fan-out) | POST |

## Authentication
All webhook routes must be wrapped with `UpstashSignatureVerifier(current_key, next_key)` to validate the `Upstash-Signature` header.

## Idempotency
QStash `Upstash-Message-Id` acts as the idempotency key. Routes must track message IDs in Redis or Supabase to prevent duplicate processing if QStash retries a delivered message.
