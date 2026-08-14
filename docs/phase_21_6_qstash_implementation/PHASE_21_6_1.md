# Phase 21.6.1 — QStash Client & Configuration

## Objective
Introduce the minimal QStash client and configuration layer required for Hiron's future migration while keeping the existing application behavior completely unchanged.

## What Was Added
1. **Configuration (`apps/api/hiron/core/config.py`)**: Added `background_task_engine` feature flag alongside three QStash secrets (`qstash_token`, `qstash_current_signing_key`, `qstash_next_signing_key`).
2. **Client Abstraction (`apps/api/hiron/core/qstash_client.py`)**: Created `QStashPublisher` class as a lightweight wrapper around the Upstash `qstash` SDK.
3. **Dependency (`pyproject.toml`)**: Added `qstash>=2.0.0` to the project dependencies.
4. **Tests (`apps/api/tests/test_qstash_client.py`)**: Added test coverage validating default behaviors, credential enforcement, and payload construction.

## Configuration Variables
- `BACKGROUND_TASK_ENGINE`: (Literal["celery", "qstash"]) Feature flag controlling the background execution environment. **Defaults to `celery`.**
- `QSTASH_TOKEN`: The Upstash REST token required for publishing.
- `QSTASH_CURRENT_SIGNING_KEY`: Webhook verification key.
- `QSTASH_NEXT_SIGNING_KEY`: Secondary webhook verification key (for rotation).

## Default Behavior
The default value for `BACKGROUND_TASK_ENGINE` is `celery`. When `celery` is active:
- QStash configuration variables are NOT required.
- The `QStashPublisher` initializes in a disabled state (`self.enabled = False`).
- Any calls to `publish()` simply return `None` with a warning log.
- All existing Celery tasks execute normally.

## Client Interface
The client abstraction (`qstash_client.py`) exposes a simple method:
```python
def publish(
    self,
    url: str,
    payload: dict | str,
    deduplication_id: str | None = None,
    retries: int | None = None,
    delay: str | int | None = None,
) -> str | None
```
Under the hood, this translates to either `client.message.publish_json(...)` or `client.message.publish(...)` depending on the payload type.

## Tests
A full test suite was written in `test_qstash_client.py` asserting:
- `celery` is the default engine.
- Credentials are not required when `celery` is selected.
- Missing credentials raise `ValidationError` only when `qstash` is selected.
- `QStashPublisher` passes configuration accurately to the underlying SDK (`upstash_deduplication_id`, `upstash_retries`, etc).
- Secrets are stripped from Pydantic's `repr()` outputs.

## Rollback
Because Celery is unchanged and is configured as the default engine, rollback is effectively a no-op. To ensure QStash is inactive, simply remove any QStash-related environment variables and ensure `BACKGROUND_TASK_ENGINE` is unset (or set to `celery`).

## Security Considerations
- Pydantic models flag all three secret keys with `repr=False`, preventing accidental logging during configuration dumps.
- `QStashPublisher` does not log the token upon initialization.
- Log outputs during message publishing include the destination URL and returned message ID, but no credentials or sensitive request payloads.
