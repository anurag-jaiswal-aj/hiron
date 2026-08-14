# Phase 21.6 Task Retry Semantics

## Current Celery Behavior
- Currently, Celery does not have explicit `autoretry_for` decorators in the task definitions.
- If a task raises an exception (e.g. `GeminiParserError` for HTTP 429), the task fails, and the exception is logged.
- The user must manually retry the parse via the API (`POST /api/v1/resumes/{resume_id}/retry`).

## QStash Delivery & Retry Semantics
QStash provides robust automatic retry mechanisms:
- If a webhook endpoint returns a `2xx` status code, QStash marks the message as delivered.
- If the endpoint returns a `4xx` or `5xx` status code, or times out, QStash enters a retry loop with exponential backoff.
- Maximum retries are configurable per QStash topic or message.

## Required Mapping
In order to seamlessly integrate with QStash without causing infinite loops or hiding errors, the webhook endpoints must map application state and AI errors to specific HTTP responses.

Please refer to the detailed [ERROR_MATRIX.md](./ERROR_MATRIX.md) for the exact mapping of HTTP 200, 429, 500, and 503 codes based on Gemini API behavior, Database constraints, and Pydantic validation failures.

**Key Design Principle:** For non-retryable logical failures (e.g., Invalid UUID, Malformed AI JSON), the endpoint MUST return `200 OK` to acknowledge receipt and terminate the QStash retry loop, while concurrently saving the `failed` status to the PostgreSQL database.
