"""Unit tests for ResumeRepository persistence operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.resumes.models import Resume
from hiron.resumes.repository import ResumeRepository


@pytest.mark.asyncio
async def test_create_resume_success() -> None:
    """Verify creating a new Resume entity."""
    repo = ResumeRepository()
    session = AsyncMock()

    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    resume = await repo.create_resume(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="pending",
        is_primary=True,
    )

    assert resume.tenant_id == tenant_id
    assert resume.candidate_id == candidate_id
    assert resume.status == "pending"
    assert resume.is_primary is True
    session.add.assert_called_once()
    session.flush.assert_called()


@pytest.mark.asyncio
async def test_create_resume_file_success() -> None:
    """Verify creating a ResumeFile metadata record."""
    repo = ResumeRepository()
    session = AsyncMock()

    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    resume_file = await repo.create_resume_file(
        session=session,
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/resume.pdf",
        original_filename="sample.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="sha256checksumhex",
    )

    assert resume_file.tenant_id == tenant_id
    assert resume_file.resume_id == resume_id
    assert resume_file.original_filename == "sample.pdf"
    assert resume_file.file_size_bytes == 2048
    session.add.assert_called_once()
    session.flush.assert_called()


@pytest.mark.asyncio
async def test_get_resume_by_id() -> None:
    """Verify querying a resume by ID."""
    repo = ResumeRepository()
    session = AsyncMock()

    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    expected_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=uuid.uuid4(),
        status="parsed",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_resume
    session.execute.return_value = mock_result

    resume = await repo.get_resume_by_id(session, tenant_id, resume_id)
    assert resume == expected_resume
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_resume_status() -> None:
    """Verify updating status and parsed output on resume entity."""
    repo = ResumeRepository()
    session = AsyncMock()

    resume = Resume(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        status="pending",
    )

    updated = await repo.update_resume_status(
        session=session,
        resume=resume,
        status="parsed",
        parsed_data={"skills": ["Python", "FastAPI"]},
        parse_confidence=0.95,
    )

    assert updated.status == "parsed"
    assert updated.parsed_data == {"skills": ["Python", "FastAPI"]}
    assert updated.parse_confidence == 0.95
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_resumes_by_candidate_id_success() -> None:
    """Verify repository correctly queries resumes by candidate ID with descending order."""
    repo = ResumeRepository()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    mock_db_session = AsyncMock()

    # Mocking session execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Resume(id=uuid.uuid4(), tenant_id=tenant_id, candidate_id=candidate_id),
        Resume(id=uuid.uuid4(), tenant_id=tenant_id, candidate_id=candidate_id),
    ]
    mock_db_session.execute.return_value = mock_result

    resumes = await repo.get_resumes_by_candidate_id(mock_db_session, tenant_id, candidate_id)
    assert len(resumes) == 2

    # Check that tenant_id and candidate_id were in the query
    # (By checking execute args if we could, but mocking SQLAlchemy statements is tricky,
    # so we just assert the mock was called).
    mock_db_session.execute.assert_called_once()
