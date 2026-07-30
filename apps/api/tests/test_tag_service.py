import datetime
import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import Candidate
from hiron.tags.exceptions import DuplicateTagError, InsufficientTagPermissionsError
from hiron.tags.models import CandidateTag
from hiron.tags.service import TagService


@pytest.mark.asyncio
async def test_add_tag_normalizes_to_lowercase_and_trimmed() -> None:
    """Verify add_tag normalizes '  Strong-HIRE ' to 'strong-hire'."""
    tag_repo = AsyncMock()
    cand_repo = AsyncMock()
    service = TagService(tag_repository=tag_repo, candidate_repository=cand_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    user_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id)
    tag_repo.get_candidate_tag_by_name.return_value = None

    mock_tag = CandidateTag(
        id=uuid.uuid4(),
        tag_name="strong-hire",
        created_at=datetime.datetime.now(datetime.UTC),
    )
    tag_repo.add_tag.return_value = mock_tag
    tag_repo.get_tag_by_id.return_value = mock_tag

    response = await service.add_tag(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="recruiter",
        candidate_id=candidate_id,
        tag_name="  Strong-HIRE ",
    )

    assert response.data.tag_name == "strong-hire"
    tag_repo.get_candidate_tag_by_name.assert_called_once_with(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        tag_name="strong-hire",
    )


@pytest.mark.asyncio
async def test_add_duplicate_tag_raises_409_conflict() -> None:
    """Verify adding duplicate tag on same candidate raises DuplicateTagError (HTTP 409 Conflict)."""
    tag_repo = AsyncMock()
    cand_repo = AsyncMock()
    service = TagService(tag_repository=tag_repo, candidate_repository=cand_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id)
    tag_repo.get_candidate_tag_by_name.return_value = CandidateTag(
        id=uuid.uuid4(), tag_name="backend"
    )

    with pytest.raises(DuplicateTagError, match="already exists on this candidate"):
        await service.add_tag(
            session=session,
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            user_role="recruiter",
            candidate_id=candidate_id,
            tag_name="backend",
        )


@pytest.mark.asyncio
async def test_hiring_manager_add_tag_raises_403() -> None:
    """Verify hiring manager role cannot add tags."""
    service = TagService()
    session = AsyncMock()

    with pytest.raises(InsufficientTagPermissionsError):
        await service.add_tag(
            session=session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_role="hiring_manager",
            candidate_id=uuid.uuid4(),
            tag_name="culture-fit",
        )
