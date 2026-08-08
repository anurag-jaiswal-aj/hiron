"""Celery application initialization for background task processing per Architecture §10."""

from celery import Celery

from hiron.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hiron",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "hiron.resumes.tasks",
        "hiron.embeddings.tasks",
        "hiron.scores.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Aliases for CLI autodiscovery
celery = celery_app
app = celery_app
