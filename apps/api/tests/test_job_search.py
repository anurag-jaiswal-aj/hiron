"""Unit and integration test suite for full-text search query sanitization and search logic."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.jobs.models import Job
from hiron.jobs.service import JobService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


def test_sanitize_search_query_normalizes_and_truncates() -> None:
    """Verify search query sanitization trims whitespace, removes non-printables, and limits length."""
    service = JobService()

    # None and whitespace
    assert service._sanitize_search_query(None) is None
    assert service._sanitize_search_query("   ") is None

    # Normal search query
    assert service._sanitize_search_query("  backend engineer  ") == "backend engineer"

    # Truncates queries > 200 chars
    long_q = "a" * 300
    sanitized = service._sanitize_search_query(long_q)
    assert sanitized is not None
    assert len(sanitized) == 200

    # Strips non-printable characters
    query_with_control_chars = "Python\x00\x07Developer"
    assert service._sanitize_search_query(query_with_control_chars) == "PythonDeveloper"


@pytest.mark.asyncio
async def test_search_jobs_service_delegation(mock_session: AsyncMock) -> None:
    """Verify JobService.search_jobs delegates to list_jobs with sanitized search term."""
    tenant_id = uuid.uuid4()
    job1 = Job(id=uuid.uuid4(), tenant_id=tenant_id, title="Python Lead", description="Desc")

    mock_repo = AsyncMock()
    mock_repo.list_jobs.return_value = ([job1], 1)

    service = JobService(job_repo=mock_repo)
    jobs, total, cursor = await service.search_jobs(
        session=mock_session,
        tenant_id=tenant_id,
        q="  python lead  ",
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Python Lead"
    assert total == 1
    assert cursor is None

    mock_repo.list_jobs.assert_awaited_once()
    call_kwargs = mock_repo.list_jobs.call_args[1]
    assert call_kwargs["q"] == "python lead"
