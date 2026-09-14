# Phase 21.6 Celery to QStash Migration Architecture Audit

## Overview
Currently, the Hiron background task system utilizes Celery and Redis as the primary broker/backend. It manages background AI processing including resume parsing, vector embedding generation, and AI candidate scoring.

The existing Celery architecture relies on dedicated worker processes continuously connected to Redis, pulling tasks from queues, tracking state, and persisting results. 
With the goal to migrate to a Serverless architecture (Upstash QStash), this model will shift from a pull-based continuous worker model to a push-based webhook model where QStash delivers tasks via HTTP POST requests to standard API endpoints.

## Current Infrastructure
- **Broker:** Redis (`celery_broker_url`)
- **Backend:** Redis (`celery_result_backend`)
- **Worker Configuration:** Defined in `apps/api/hiron/core/celery.py` with tasks dynamically discovered from modules.
- **Serialization:** JSON

## Celery Features Currently Utilized
1. **Fire-and-Forget Executions:** `.delay()` used for embedding tasks and resume parsing.
2. **Explicit Parameter Passing:** `.apply_async(kwargs=...)` used for batch scoring.
3. **Task Status Tracking:** `celery_task.update_state()` used exclusively in batch scoring to report progress (e.g. `percent: 50`, `current: 5`, `total: 10`).
4. **Task Chaining (Implicit):** `parse_resume` dynamically invokes `generate_candidate_embedding.delay()` upon success. There are no explicit Celery Chains/Groups/Chords used.

## Security Context
Tasks do NOT currently authenticate themselves when executing because Celery functions are Python functions running in a trusted worker environment with database access.
In the QStash architecture, the worker is the public API itself. 
Therefore, webhook signature verification (Upstash Signing Keys) must be implemented for all background endpoints to prevent unauthorized execution.

## Architectural Changes Required
1. **Parallel Migration Strategy:** Celery and Redis will be retained during the migration. A feature flag (`BACKGROUND_TASK_ENGINE`) will route task publishes to either Celery or QStash, allowing for instant rollback. Celery is decommissioned only after QStash is proven stable.
2. **Endpoints:** Celery `@celery_app.task` decorators will be mapped to FastAPI POST endpoints in `apps/api/hiron/webhooks/qstash_router.py`.
3. **Batch Fan-Out Architecture:** Celery's synchronous long-running loops for batch scoring will be redesigned. A Coordinator Webhook will receive the batch request, generate individual candidate-scoring messages, and publish them to a Worker Webhook.
4. **State Tracking:** QStash cannot update task status metadata natively (like `update_state(state="PROGRESS")`). Batch scoring will persist progress via atomic counters on a dedicated PostgreSQL `BatchScoreJob` entity, which the frontend will poll.
5. **Execution Delivery:** `celery_task.delay()` calls must be swapped for `qstash_client.publish_json(...)`.
6. **Local Development:** Webhooks require a public URL. Local development will utilize an HTTP tunnel (`ngrok`, `localtunnel`, or Upstash CLI) to route webhooks to `localhost:8000`.
