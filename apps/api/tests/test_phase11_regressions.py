import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from hiron.auth.dependencies import get_current_user
from hiron.users.models import User
from hiron.notes.service import NoteService
from hiron.notes.schemas import UpdateNoteRequest
from hiron.core.cache import app_cache


@pytest.mark.asyncio
async def test_auth_cache_hydration_uuid_regression() -> None:
    """
    Regression test for UUID cache-hydration bug.
    Proves that a cached user with string UUIDs is properly converted
    back into a User model with uuid.UUID fields for id and tenant_id.
    """
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # 1. A User is serialized into the cache with string UUID values.
    cached_dict = {
        "id": str(user_id),
        "tenant_id": str(tenant_id),
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "recruiter",
        "is_active": True,
    }

    # Mock cache get to return the stringified dict
    with patch.object(app_cache, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = cached_dict

        # Mock credentials and dependencies
        mock_creds = MagicMock()
        mock_creds.credentials = "fake.jwt.token"

        mock_db = AsyncMock()
        mock_repo = AsyncMock()

        with patch("hiron.auth.dependencies.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": str(user_id), "tenantId": str(tenant_id)}

            # 3. get_current_user reconstructs the User.
            user = await get_current_user(db=mock_db, user_repo=mock_repo, credentials=mock_creds)

            # 4. user.id is a uuid.UUID.
            assert isinstance(user.id, uuid.UUID), f"user.id is {type(user.id)}, expected uuid.UUID"
            assert user.id == user_id

            # 5. user.tenant_id is a uuid.UUID.
            assert isinstance(user.tenant_id, uuid.UUID), (
                f"user.tenant_id is {type(user.tenant_id)}, expected uuid.UUID"
            )
            assert user.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_update_note_missing_greenlet_regression() -> None:
    """
    Regression test for MissingGreenlet issue during note update.
    Proves that update_note successfully returns the updated response after commit
    without accessing an expired SQLAlchemy attribute synchronously.
    """
    service = NoteService(note_repository=AsyncMock())

    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Mock existing note
    mock_note = MagicMock()
    mock_note.id = note_id
    mock_note.candidate_id = candidate_id
    mock_note.author_id = user_id  # 6. Notes authorization continues to recognize the actual author correctly (types match)
    mock_note.author = MagicMock()
    mock_note.author.id = user_id
    mock_note.author.full_name = "Mock User"
    mock_note.content = "updated content"
    mock_note.is_private = False
    mock_note.job_id = None
    import datetime

    mock_note.created_at = datetime.datetime.now(datetime.UTC)
    mock_note.updated_at = datetime.datetime.now(datetime.UTC)

    # We must simulate what happens if the object is returned after commit without a refetch.
    # We configure get_note_by_id to return the mock_note on both the initial fetch and the refetch.
    from typing import cast

    cast(AsyncMock, service.note_repo.get_note_by_id).side_effect = [mock_note, mock_note]

    mock_session = AsyncMock()

    request = UpdateNoteRequest(content="updated content")

    response = await service.update_note(
        session=mock_session,
        tenant_id=tenant_id,
        user_id=user_id,
        candidate_id=candidate_id,
        note_id=note_id,
        content="updated content",
    )

    # Assert commit was called
    mock_session.commit.assert_called_once()

    # Assert refetch was called
    assert cast(AsyncMock, service.note_repo.get_note_by_id).call_count == 2

    # The fact that this completes without raising MissingGreenlet (simulated by the explicit refetch)
    # and returns a valid NoteResponse verifies the behavior.
    assert response.data.id == note_id
