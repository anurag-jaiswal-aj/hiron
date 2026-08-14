# 7. Celery Removal Plan

## Audit of Celery Dependencies
- `celery.py` app initialization.
- `@celery_app.task` decorators in `hiron/*/tasks.py`.
- Redis backend/broker configurations.
- `apply_async()` and `delay()` invocations throughout the service layer.

## Phased Removal Strategy
1. **Parallel Implementation**: Implement QStash webhooks without removing Celery code.
2. **Feature Flag Flip**: Change service layer to use `QStashPublisher` instead of `.apply_async()`.
3. **Verification**: Monitor logs to ensure webhooks process background jobs successfully.
4. **Cleanup**: 
   - Delete `hiron/core/celery.py`.
   - Remove `celery[redis]` from `pyproject.toml`.
   - Delete ECS worker container configurations in Terraform.
