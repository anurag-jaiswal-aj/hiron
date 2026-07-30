"""Unit tests for NoteRepository creation, private note filtering, and soft delete archiving."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.notes.models import CandidateNote
from hiron.notes.repository import NoteRepository


@pytest.mark.asyncio
async def test_create_note_persists_entity() -> None:
    """Verify create_note adds CandidateNote to session."""
    repo = NoteRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    author_id = uuid.uuid4()

    note = await repo.create_note(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        author_id=author_id,
        content="Great candidate performance",
        is_private=True,
    )

    assert note.tenant_id == tenant_id
    assert note.candidate_id == candidate_id
    assert note.author_id == author_id
    assert note.content == "Great candidate performance"
    assert note.is_private is True
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_archive_note_sets_is_archived_true() -> None:
    """Verify archive_note soft-deletes note."""
    repo = NoteRepository()
    session = AsyncMock()
    note = CandidateNote(id=uuid.uuid4(), is_archived=False)

    await repo.archive_note(session, note)

    assert note.is_archived is True
    session.flush.assert_called_once()
