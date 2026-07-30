"""Unit tests for TagRepository tag creation, normalization check, and deletion."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.tags.models import CandidateTag
from hiron.tags.repository import TagRepository


@pytest.mark.asyncio
async def test_add_tag_persists_entity() -> None:
    """Verify add_tag adds CandidateTag to session."""
    repo = TagRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    user_id = uuid.uuid4()

    tag = await repo.add_tag(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        tag_name="strong-hire",
        tagged_by=user_id,
    )

    assert tag.tenant_id == tenant_id
    assert tag.candidate_id == candidate_id
    assert tag.tag_name == "strong-hire"
    assert tag.tagged_by == user_id
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_remove_tag_deletes_entity() -> None:
    """Verify remove_tag hard-deletes tag from database."""
    repo = TagRepository()
    session = AsyncMock()
    tag = CandidateTag(id=uuid.uuid4())

    await repo.remove_tag(session, tag)

    session.delete.assert_called_once_with(tag)
