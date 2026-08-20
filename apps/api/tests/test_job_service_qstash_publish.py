import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.core.config import get_settings
from hiron.jobs.models import Job
from hiron.jobs.service import JobService


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setenv("QSTASH_TOKEN", "test-token")
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "test-key-1")
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "test-key-2")
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://test-qstash-url")
    get_settings.cache_clear()


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.mark.asyncio
async def test_job_service_create_job_uses_qstash(admin_user_id: uuid.UUID):
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = JobService(job_repo=MagicMock())
    service.job_repo.create_job = AsyncMock(return_value=Job(id=job_id, tenant_id=tenant_id))
    service.job_repo.create_pipeline_stages = AsyncMock()

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        await service.create_job(
            session=AsyncMock(),
            tenant_id=tenant_id,
            created_by=admin_user_id,
            current_user_role="org_admin",
            title="Software Engineer",
            description="Great job",
        )
        mock_publish.assert_called_once()
        assert "api/v1/webhooks/qstash/embeddings/job" in mock_publish.call_args[1]["url"]
        assert mock_publish.call_args[1]["payload"]["job_id"] == str(job_id)
        assert mock_publish.call_args[1]["payload"]["model_version"] == "gemini-embedding-2"
        assert (
            mock_publish.call_args[1]["deduplication_id"]
            == f"embed-job-{job_id}-gemini-embedding-2"
        )


@pytest.mark.asyncio
async def test_job_service_update_job_uses_qstash(admin_user_id: uuid.UUID):
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = JobService(job_repo=MagicMock())
    existing_job = Job(
        id=job_id,
        tenant_id=tenant_id,
        title="Old",
        description="Old",
        experience_years_min=0,
        experience_years_max=5,
    )
    service.job_repo.get_job_by_id = AsyncMock(return_value=existing_job)
    service.job_repo.update_job = AsyncMock(return_value=existing_job)

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        await service.update_job(
            session=AsyncMock(),
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=admin_user_id,
            current_user_role="org_admin",
            description="New description",
        )
        mock_publish.assert_called_once()
        assert "api/v1/webhooks/qstash/embeddings/job" in mock_publish.call_args[1]["url"]
        assert mock_publish.call_args[1]["payload"]["job_id"] == str(job_id)
        assert mock_publish.call_args[1]["payload"]["model_version"] == "gemini-embedding-2"
        assert (
            mock_publish.call_args[1]["deduplication_id"]
            == f"embed-job-{job_id}-gemini-embedding-2"
        )


@pytest.mark.asyncio
async def test_job_service_update_job_no_source_change_skips_qstash(admin_user_id: uuid.UUID):
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = JobService(job_repo=MagicMock())
    existing_job = Job(
        id=job_id,
        tenant_id=tenant_id,
        title="Old",
        description="Old",
        experience_years_min=0,
        experience_years_max=5,
    )
    service.job_repo.get_job_by_id = AsyncMock(return_value=existing_job)
    service.job_repo.update_job = AsyncMock(return_value=existing_job)

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        await service.update_job(
            session=AsyncMock(),
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=admin_user_id,
            current_user_role="org_admin",
            location="New Location",
            employment_type="part_time",
        )
        mock_publish.assert_not_called()


@pytest.mark.asyncio
async def test_job_service_create_job_qstash_failure_swallowed(admin_user_id: uuid.UUID):
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = JobService(job_repo=MagicMock())
    service.job_repo.create_job = AsyncMock(return_value=Job(id=job_id, tenant_id=tenant_id))
    service.job_repo.create_pipeline_stages = AsyncMock()

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        mock_publish.side_effect = Exception("QStash network error")

        job = await service.create_job(
            session=AsyncMock(),
            tenant_id=tenant_id,
            created_by=admin_user_id,
            current_user_role="org_admin",
            title="Software Engineer",
            description="Great job",
        )
        assert job.id == job_id
        mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_job_service_update_job_qstash_failure_swallowed(admin_user_id: uuid.UUID):
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = JobService(job_repo=MagicMock())
    existing_job = Job(
        id=job_id,
        tenant_id=tenant_id,
        title="Old",
        description="Old",
        experience_years_min=0,
        experience_years_max=5,
    )
    service.job_repo.get_job_by_id = AsyncMock(return_value=existing_job)
    service.job_repo.update_job = AsyncMock(return_value=existing_job)

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        mock_publish.side_effect = Exception("QStash network error")

        updated = await service.update_job(
            session=AsyncMock(),
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=admin_user_id,
            current_user_role="org_admin",
            title="New Title",
        )
        assert updated == existing_job
        mock_publish.assert_called_once()
