"""Service unit tests for NoteService private note security, author-only edit checks, and org_admin archive permissions."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.notes.exceptions import InsufficientNotePermissionsError, NoteValidationError
from hiron.notes.models import CandidateNote
from hiron.notes.service import NoteService


@pytest.mark.asyncio
async def test_create_empty_note_raises_validation_error() -> None:
    """Verify creating a note with empty content raises NoteValidationError."""
    service = NoteService()
    session = AsyncMock()

    with pytest.raises(NoteValidationError, match="cannot be empty"):
        await service.create_note(
            session=session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            content="   ",
        )


@pytest.mark.asyncio
async def test_update_note_non_author_raises_403() -> None:
    """Verify editing a note by a non-author user raises InsufficientNotePermissionsError."""
    note_repo = AsyncMock()
    cand_repo = AsyncMock()
    service = NoteService(note_repository=note_repo, candidate_repository=cand_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    author_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()

    mock_note = CandidateNote(
        id=note_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        author_id=author_id,
        content="Original note",
    )
    note_repo.get_note_by_id.return_value = mock_note

    with pytest.raises(InsufficientNotePermissionsError, match="Only note author can edit note"):
        await service.update_note(
            session=session,
            tenant_id=tenant_id,
            user_id=other_user_id,
            candidate_id=candidate_id,
            note_id=note_id,
            content="Attempted update",
        )


@pytest.mark.asyncio
async def test_archive_note_org_admin_permission_allowed() -> None:
    """Verify org_admin can archive notes even if they are not the author."""
    note_repo = AsyncMock()
    cand_repo = AsyncMock()
    service = NoteService(note_repository=note_repo, candidate_repository=cand_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    author_id = uuid.uuid4()
    admin_user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()

    mock_note = CandidateNote(
        id=note_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        author_id=author_id,
        content="Original note",
    )
    note_repo.get_note_by_id.return_value = mock_note

    await service.archive_note(
        session=session,
        tenant_id=tenant_id,
        user_id=admin_user_id,
        user_role="org_admin",
        candidate_id=candidate_id,
        note_id=note_id,
    )

    note_repo.archive_note.assert_called_once_with(session=session, note=mock_note)
