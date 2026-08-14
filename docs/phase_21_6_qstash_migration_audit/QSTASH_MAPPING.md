# Phase 21.6 QStash Route Mapping

## Overview
This document maps the existing Celery tasks to their future RESTful QStash Webhook equivalents.

## 1. Resume Parsing
**Current Celery Task:** `hiron.resumes.parse_resume`
**Future Webhook Route:** `POST /api/v1/webhooks/qstash/resumes/parse`
**Publish Action:** Instead of `.delay(tenant_id, resume_id)`, the service will call:
`qstash_client.publish_json(url="<API_URL>/api/v1/webhooks/qstash/resumes/parse", json={"tenant_id": "...", "resume_id": "..."})`

## 2. Candidate Embedding
**Current Celery Task:** `hiron.embeddings.generate_candidate_embedding`
**Future Webhook Route:** `POST /api/v1/webhooks/qstash/embeddings/candidate`
**Publish Action:** Instead of `.delay(tenant_id, candidate_id)`, the service will call:
`qstash_client.publish_json(url="<API_URL>/api/v1/webhooks/qstash/embeddings/candidate", json={"tenant_id": "...", "candidate_id": "..."})`

## 3. Job Embedding
**Current Celery Task:** `hiron.embeddings.generate_job_embedding`
**Future Webhook Route:** `POST /api/v1/webhooks/qstash/embeddings/job`
**Publish Action:** Instead of `.delay(tenant_id, job_id)`, the service will call:
`qstash_client.publish_json(url="<API_URL>/api/v1/webhooks/qstash/embeddings/job", json={"tenant_id": "...", "job_id": "..."})`

## 4. Batch Scoring Coordinator
**Current Celery Task:** `hiron.scores.execute_batch_scoring`
**Future Webhook Route:** `POST /api/v1/webhooks/qstash/scores/batch/coordinator`
**Publish Action:** Instead of `.apply_async(...)`, the service will call:
`qstash_client.publish_json(url="<API_URL>/api/v1/webhooks/qstash/scores/batch/coordinator", json={"batch_id": "...", "tenant_id": "...", "job_id": "...", "candidate_ids": [...]})`

## 5. Batch Scoring Worker
**Current Celery Task:** (Executed synchronously inside `execute_batch_scoring`)
**Future Webhook Route:** `POST /api/v1/webhooks/qstash/scores/batch/worker`
**Publish Action:** The Coordinator webhook will call:
`qstash_client.publish_json(url="<API_URL>/api/v1/webhooks/qstash/scores/batch/worker", json={"batch_id": "...", "tenant_id": "...", "job_id": "...", "candidate_id": "...", "force_rescore": false})`

## Global Webhook Architecture
A new FastAPI router should be created at `apps/api/hiron/webhooks/qstash_router.py` to handle these specific endpoints, utilizing a custom FastAPI Dependency (`VerifyQStashSignature`) to reject unauthorized invocations.
