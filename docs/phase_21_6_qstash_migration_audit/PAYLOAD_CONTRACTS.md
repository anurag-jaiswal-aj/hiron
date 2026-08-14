# Phase 21.6 Task Payload Contracts

## Current Celery Arguments vs QStash JSON Payloads

The transition from Python-native kwargs (`delay`/`apply_async`) to HTTP REST payloads requires defining strict JSON schemas for webhook endpoints.

### 1. Resume Parsing
**Celery Signature:**
`parse_resume(tenant_id: str, resume_id: str)`

**QStash Payload (Proposed):**
```json
{
  "tenant_id": "uuid-string",
  "resume_id": "uuid-string"
}
```

### 2. Candidate Embedding Generation
**Celery Signature:**
`generate_candidate_embedding(tenant_id: str, candidate_id: str, model_version: str)`

**QStash Payload (Proposed):**
```json
{
  "tenant_id": "uuid-string",
  "candidate_id": "uuid-string",
  "model_version": "models/gemini-embedding-001"
}
```

### 3. Job Embedding Generation
**Celery Signature:**
`generate_job_embedding(tenant_id: str, job_id: str, model_version: str)`

**QStash Payload (Proposed):**
```json
{
  "tenant_id": "uuid-string",
  "job_id": "uuid-string",
  "model_version": "models/gemini-embedding-001"
}
```

### 4. Batch Scoring
**Celery Signature:**
`execute_batch_scoring(tenant_id: str, job_id: str, candidate_ids: list[str], force_rescore: bool)`

**QStash Payload (Proposed):**
```json
{
  "tenant_id": "uuid-string",
  "job_id": "uuid-string",
  "candidate_ids": ["uuid-string-1", "uuid-string-2"],
  "force_rescore": false
}
```

## Security Requirements
Because tasks will transition to HTTP webhooks, the endpoints receiving these payloads must intercept the `Upstash-Signature` HTTP header and validate it using the Upstash cryptographic public key before parsing the payload.
