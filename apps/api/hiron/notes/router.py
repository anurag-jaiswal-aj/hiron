"""Thin FastAPI router for Candidate Notes per API Contract §NOTE-1..4."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.notes.schemas import (
    CreateNoteRequest,
    NoteListResponse,
    NoteResponse,
    UpdateNoteRequest,
)
from hiron.notes.service import NoteService
from hiron.users.models import User

router = APIRouter(tags=["Candidate Notes"])


def get_note_service() -> NoteService:
    """Dependency provider for NoteService."""
    return NoteService()


@router.get(
    "/candidates/{candidate_id}/notes",
    response_model=NoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Notes for Candidate (NOTE-1)",
)
async def list_candidate_notes_endpoint(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(default=None, alias="jobId"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: NoteService = Depends(get_note_service),
) -> NoteListResponse:
    """Get all notes on a candidate, newest first (private notes visible only to author) per §NOTE-1."""
    return await service.list_candidate_notes(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        candidate_id=candidate_id,
        job_id=job_id,
    )


@router.post(
    "/candidates/{candidate_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Note (NOTE-2)",
)
async def create_note_endpoint(
    candidate_id: uuid.UUID,
    request: CreateNoteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    """Add a note to a candidate per §NOTE-2."""
    return await service.create_note(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        candidate_id=candidate_id,
        content=request.content,
        job_id=request.job_id,
        is_private=request.is_private,
    )


@router.patch(
    "/candidates/{candidate_id}/notes/{note_id}",
    response_model=NoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Note (NOTE-3)",
)
async def update_note_endpoint(
    candidate_id: uuid.UUID,
    note_id: uuid.UUID,
    request: UpdateNoteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    """Edit a note (author only) per §NOTE-3."""
    return await service.update_note(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        candidate_id=candidate_id,
        note_id=note_id,
        content=request.content,
        is_private=request.is_private,
    )


@router.delete(
    "/candidates/{candidate_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive Note (NOTE-4)",
)
async def archive_note_endpoint(
    candidate_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: NoteService = Depends(get_note_service),
) -> None:
    """Soft-delete a note (author or org_admin) per §NOTE-4."""
    await service.archive_note(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        candidate_id=candidate_id,
        note_id=note_id,
    )
