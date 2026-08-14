# Phase 21.6 Migration States (Parallel Migration Strategy)

To ensure zero downtime and safe rollback capabilities, the QStash migration will be executed in parallel with the existing Celery architecture. Celery and Redis will not be removed until QStash is proven stable in production.

## Migration States

### STATE A: Celery Only (Current)
- All background tasks are pushed to Redis and executed by Celery workers.
- QStash is not in the codebase.

### STATE B: Celery + QStash Implemented (Celery Active)
- QStash webhook endpoints and publish logic are merged into the codebase.
- A feature flag (e.g., `BACKGROUND_TASK_ENGINE=celery`) is introduced in the configuration.
- The application continues to use Celery for all production background tasks.
- QStash endpoints exist but receive no traffic.

### STATE C: QStash Active, Celery Retained (Rollback State)
- The feature flag is toggled: `BACKGROUND_TASK_ENGINE=qstash`.
- The application begins publishing JSON payloads to QStash instead of calling `.delay()`.
- QStash delivers webhooks to the new endpoints.
- Celery workers remain deployed and running, handling any straggler tasks in Redis queues or manual fallbacks.
- **Rollback Procedure:** If QStash exhibits latency, timeout, or delivery issues, simply toggle `BACKGROUND_TASK_ENGINE=celery`. New tasks immediately revert to Celery/Redis.

### STATE D: QStash Proven Stable
- QStash handles 100% of the production load successfully over a designated observation period (e.g., 7-14 days).
- Free-tier limits (if applicable) and timeout boundaries are confirmed to be within safe margins.
- No rollback to Celery has been required.

### STATE E: Celery / Redis Decommissioned
- Celery dependencies (`celery`, `redis`) are removed from `pyproject.toml`.
- All `tasks.py` files are deleted.
- Terraform configurations are updated to destroy the Celery Worker ECS service and ElastiCache Redis clusters.
- `BACKGROUND_TASK_ENGINE` flag can be deprecated.
